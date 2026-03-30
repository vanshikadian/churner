from app.verticals.base import VerticalConfig

PLAN_PRICES = {"basic_ads": 7, "standard": 13, "premium": 20, "family": 25}


class EntertainmentVertical(VerticalConfig):
    name = "entertainment"
    display_name = "Streaming"
    accent_color = "purple"
    plan_tiers = PLAN_PRICES
    event_types = ["login", "content_view", "content_complete", "search", "add_to_list", "payment_failure"]
    primary_engagement_event = "content_view"
    support_event = "support_ticket"

    _offers_map = {
        "binge_cliff":        ["coming_soon_preview", "personalized_recs", "ad_tier_downgrade"],
        "passive_subscriber": ["pause_1mo", "ad_tier_downgrade", "annual_discount"],
        "content_mismatch":   ["personalized_recs", "new_genre_spotlight", "premium_trial"],
        "price_shopper":      ["annual_lock_in", "ad_tier_downgrade", "discount_30"],
        "at_risk":            ["discount_30", "pause_1mo", "personalized_recs"],
    }

    def classify_segment(self, features: dict, user) -> str:
        content_velocity = features.get("content_velocity", 0)
        content_views_prev = features.get("content_views_prev_30d", 0)
        if content_velocity < -0.5 and content_views_prev > 15:
            return "binge_cliff"
        if (
            features.get("sessions_30d", 0) <= 3
            and features.get("login_recency_days", 0) > 10
            and float(user.monthly_spend or 0) > 0
        ):
            return "passive_subscriber"
        if features.get("genre_diversity", 1.0) < 0.35 and features.get("sessions_30d", 0) >= 5:
            return "content_mismatch"
        if features.get("payment_failures", 0) >= 1 or (user.user_metadata or {}).get("promo_signup", False):
            return "price_shopper"
        return "at_risk"

    def get_available_offers(self, segment: str) -> list:
        return self._offers_map.get(segment, ["discount_30"])

    def get_offer_details(self, offer_type: str, user) -> dict:
        monthly = float(user.monthly_spend or 0)
        if offer_type == "coming_soon_preview":
            return {"access": "early preview", "titles": "3 upcoming releases"}
        if offer_type == "personalized_recs":
            return {"type": "AI-curated watchlist", "refresh": "weekly"}
        if offer_type == "ad_tier_downgrade":
            return {"new_plan": "basic_ads", "new_price": 7, "savings": round(monthly - 7, 2)}
        if offer_type == "pause_1mo":
            return {"pause_months": 1}
        if offer_type == "annual_discount":
            return {"discount_pct": 20, "billing": "annual", "annual_savings": round(monthly * 12 * 0.2, 2)}
        if offer_type == "new_genre_spotlight":
            return {"curated_titles": 10, "genre": "new picks for you"}
        if offer_type == "premium_trial":
            return {"trial_days": 7, "plan": "premium"}
        if offer_type == "annual_lock_in":
            return {"discount_pct": 17, "billing": "annual", "annual_savings": round(monthly * 12 * 0.17, 2)}
        if offer_type == "discount_30":
            return {"discount_pct": 30, "months": 2, "savings": round(monthly * 0.3 * 2, 2)}
        return {}

    def get_templates(self, segment: str) -> list:
        return TEMPLATES.get(segment, TEMPLATES["at_risk"])

    async def compute_extra_features(self, redis, user_id: int, now: float) -> dict:
        thirty_days_ago = now - (30 * 86400)
        sixty_days_ago = now - (60 * 86400)
        content_views_30d = await redis.zcount(f"events:{user_id}:content_view", thirty_days_ago, now)
        content_views_prev = await redis.zcount(f"events:{user_id}:content_view", sixty_days_ago, thirty_days_ago)
        content_velocity = (content_views_30d - content_views_prev) / max(content_views_prev, 1)
        completions = await redis.zcount(f"events:{user_id}:content_complete", thirty_days_ago, now)
        completion_rate = completions / max(content_views_30d, 1)
        return {
            "content_views_30d": content_views_30d,
            "content_views_prev_30d": content_views_prev,
            "content_velocity": round(content_velocity, 3),
            "completion_rate": round(completion_rate, 3),
            "genre_diversity": 0.45,  # simplified; real impl would parse event_data
        }

    def get_all_segments(self) -> list:
        return list(self._offers_map.keys())

    def get_seed_config(self) -> dict:
        return {
            "archetypes": [
                {
                    "name": "healthy", "weight": 0.40,
                    "plans": ["standard", "premium", "family"],
                    "sessions_30d": (20, 40), "sessions_prev_30d": (18, 35),
                    "features_30d": (25, 50), "support_30d": (0, 1),
                    "payment_failures": (0, 0), "login_recency": (0, 2),
                    "churn_prob": 0.0, "metadata": {"promo_signup": False},
                },
                {
                    "name": "binge_cliff", "weight": 0.15,
                    "plans": ["standard", "premium"],
                    "sessions_30d": (4, 10), "sessions_prev_30d": (22, 45),
                    "features_30d": (5, 12), "support_30d": (0, 0),
                    "payment_failures": (0, 0), "login_recency": (5, 15),
                    "churn_prob": 0.30, "metadata": {"promo_signup": False},
                },
                {
                    "name": "passive_subscriber", "weight": 0.15,
                    "plans": ["standard", "premium"],
                    "sessions_30d": (1, 3), "sessions_prev_30d": (3, 8),
                    "features_30d": (1, 5), "support_30d": (0, 0),
                    "payment_failures": (0, 0), "login_recency": (10, 25),
                    "churn_prob": 0.30, "metadata": {"promo_signup": False},
                },
                {
                    "name": "content_mismatch", "weight": 0.15,
                    "plans": ["standard", "premium"],
                    "sessions_30d": (8, 20), "sessions_prev_30d": (8, 18),
                    "features_30d": (8, 20), "support_30d": (0, 1),
                    "payment_failures": (0, 0), "login_recency": (2, 10),
                    "churn_prob": 0.30, "metadata": {"promo_signup": False},
                },
                {
                    "name": "price_shopper", "weight": 0.15,
                    "plans": ["basic_ads", "standard"],
                    "sessions_30d": (5, 15), "sessions_prev_30d": (5, 15),
                    "features_30d": (5, 15), "support_30d": (0, 1),
                    "payment_failures": (1, 2), "login_recency": (0, 7),
                    "churn_prob": 0.30, "metadata": {"promo_signup": True},
                },
            ]
        }


TEMPLATES = {
    "binge_cliff": [
        "Hey {name}, looks like you've been on a roll lately. We've got new releases dropping soon that we think you'll love. Stick around and you won't miss a thing.",
        "{name}, you just finished a great run of content and there's more coming. Give us one more month and we promise the queue won't disappoint.",
    ],
    "passive_subscriber": [
        "{name}, your account has been pretty quiet lately. How about we pause your billing for a month? Your watchlist stays saved, and you can come back whenever something catches your eye.",
        "Hey {name}, no pressure. We'd rather pause your subscription than lose you. Everything stays right where you left it.",
    ],
    "content_mismatch": [
        "{name}, we noticed you've been watching mostly in one genre. We've just added a ton of new titles we think you'll love. Let us curate a fresh watchlist for you before you go.",
        "Hey {name}, there's a lot more here that matches what you like. We're putting together a personalized list based on your taste. Give it a shot this week.",
    ],
    "price_shopper": [
        "{name}, we get it. Full price stings after a deal. Lock in our annual plan and you'll save over the year. Same content, better price.",
        "Hey {name}, our basic plan keeps you in the game at ${price}/mo with ads. All the same content at a price that works.",
    ],
    "at_risk": [
        "{name}, 30% off for 2 months. That's ${savings} to give us another shot and see what's new.",
        "Hey {name}, we'd hate to lose you. Here's 30% off, same everything, just a better deal while you decide.",
    ],
}
