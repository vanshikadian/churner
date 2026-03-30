from app.verticals.base import VerticalConfig

PLAN_PRICES = {"free": 0, "dash_pass": 10, "premium": 15}


class MarketplaceVertical(VerticalConfig):
    name = "marketplace"
    display_name = "Marketplace"
    accent_color = "orange"
    plan_tiers = PLAN_PRICES
    event_types = ["login", "order", "search", "bad_experience", "refund_request", "coupon_used", "payment_failure"]
    primary_engagement_event = "order"
    support_event = "bad_experience"

    _offers_map = {
        "bad_experience":   ["service_credit", "free_delivery_pass", "priority_redelivery"],
        "frequency_decay":  ["favorites_discount", "free_delivery_week", "loyalty_tier_up"],
        "competitor_switch": ["reactivation_credit", "exclusive_deal", "free_month_pass"],
        "promo_dependent":  ["loyalty_program", "bulk_deal", "annual_pass_discount"],
        "at_risk":          ["service_credit", "free_delivery_week", "discount_30"],
    }

    def classify_segment(self, features: dict, user) -> str:
        bad_exp = features.get("bad_experiences_30d", 0)
        order_velocity = features.get("order_velocity", features.get("engagement_decay", 0))
        orders_prev = features.get("orders_prev_30d", features.get("sessions_prev_30d", 1))
        orders_30d = features.get("orders_30d", features.get("sessions_30d", 0))
        coupon_ratio = features.get("coupon_ratio", 0)

        if bad_exp >= 2:
            return "bad_experience"
        if order_velocity < -0.5 and orders_prev > 5:
            return "frequency_decay"
        if orders_30d == 0 and orders_prev > 3:
            return "competitor_switch"
        if coupon_ratio > 0.7:
            return "promo_dependent"
        return "at_risk"

    def get_available_offers(self, segment: str) -> list:
        return self._offers_map.get(segment, ["service_credit"])

    def get_offer_details(self, offer_type: str, user) -> dict:
        monthly = float(user.monthly_spend or 0)
        if offer_type == "service_credit":
            return {"credit": 10, "applies_to": "next order"}
        if offer_type == "free_delivery_pass":
            return {"free_delivery_days": 30}
        if offer_type == "priority_redelivery":
            return {"priority": True, "next_order_sla": "30 min"}
        if offer_type == "favorites_discount":
            return {"discount_pct": 20, "applies_to": "favorite restaurants"}
        if offer_type == "free_delivery_week":
            return {"free_delivery_days": 7}
        if offer_type == "loyalty_tier_up":
            return {"tier": "Gold", "perks": "priority + free delivery"}
        if offer_type == "reactivation_credit":
            return {"credit": 15, "applies_to": "next 3 orders"}
        if offer_type == "exclusive_deal":
            return {"deal": "exclusive restaurant offers", "savings_est": 12}
        if offer_type == "free_month_pass":
            return {"free_delivery_days": 30, "cost": 0}
        if offer_type == "loyalty_program":
            return {"program": "points per order", "signup_bonus_pts": 500}
        if offer_type == "bulk_deal":
            return {"deal": "bundle 5 orders, save 15%"}
        if offer_type == "annual_pass_discount":
            return {"discount_pct": 25, "billing": "annual", "savings": round(monthly * 12 * 0.25, 2)}
        if offer_type == "discount_30":
            return {"discount_pct": 30, "months": 1}
        return {}

    def get_templates(self, segment: str) -> list:
        return TEMPLATES.get(segment, TEMPLATES["at_risk"])

    async def compute_extra_features(self, redis, user_id: int, now: float) -> dict:
        thirty_days_ago = now - (30 * 86400)
        sixty_days_ago = now - (60 * 86400)
        orders_30d = await redis.zcount(f"events:{user_id}:order", thirty_days_ago, now)
        orders_prev = await redis.zcount(f"events:{user_id}:order", sixty_days_ago, thirty_days_ago)
        order_velocity = (orders_30d - orders_prev) / max(orders_prev, 1)
        bad_exp = await redis.zcount(f"events:{user_id}:bad_experience", thirty_days_ago, now)
        coupons = await redis.zcount(f"events:{user_id}:coupon_used", thirty_days_ago, now)
        coupon_ratio = coupons / max(orders_30d, 1)
        return {
            "orders_30d": orders_30d,
            "orders_prev_30d": orders_prev,
            "order_velocity": round(order_velocity, 3),
            "bad_experiences_30d": bad_exp,
            "coupon_ratio": round(coupon_ratio, 3),
        }

    def get_all_segments(self) -> list:
        return list(self._offers_map.keys())

    def get_seed_config(self) -> dict:
        return {
            "archetypes": [
                {
                    "name": "healthy", "weight": 0.40,
                    "plans": ["dash_pass", "premium"],
                    "sessions_30d": (15, 30), "sessions_prev_30d": (12, 28),
                    "features_30d": (10, 25), "support_30d": (0, 0),
                    "payment_failures": (0, 0), "login_recency": (0, 3),
                    "churn_prob": 0.0, "metadata": {},
                },
                {
                    "name": "bad_experience", "weight": 0.15,
                    "plans": ["dash_pass", "premium"],
                    "sessions_30d": (8, 18), "sessions_prev_30d": (10, 20),
                    "features_30d": (5, 12), "support_30d": (2, 5),
                    "payment_failures": (0, 0), "login_recency": (1, 7),
                    "churn_prob": 0.30, "metadata": {},
                },
                {
                    "name": "frequency_decay", "weight": 0.15,
                    "plans": ["dash_pass", "premium"],
                    "sessions_30d": (3, 8), "sessions_prev_30d": (12, 22),
                    "features_30d": (2, 6), "support_30d": (0, 1),
                    "payment_failures": (0, 0), "login_recency": (5, 15),
                    "churn_prob": 0.30, "metadata": {},
                },
                {
                    "name": "competitor_switch", "weight": 0.15,
                    "plans": ["free", "dash_pass"],
                    "sessions_30d": (0, 2), "sessions_prev_30d": (8, 18),
                    "features_30d": (0, 1), "support_30d": (0, 1),
                    "payment_failures": (0, 1), "login_recency": (10, 30),
                    "churn_prob": 0.30, "metadata": {},
                },
                {
                    "name": "promo_dependent", "weight": 0.15,
                    "plans": ["free", "dash_pass"],
                    "sessions_30d": (8, 18), "sessions_prev_30d": (8, 18),
                    "features_30d": (6, 15), "support_30d": (0, 1),
                    "payment_failures": (0, 1), "login_recency": (1, 7),
                    "churn_prob": 0.30, "metadata": {},
                },
            ]
        }


TEMPLATES = {
    "bad_experience": [
        "{name}, we know your last couple orders weren't what you expected, and that's on us. Here's a $10 credit for your next order. We're also flagging your account for priority handling going forward.",
        "Hey {name}, that experience wasn't good enough and we want to make it right. $10 credit, applied automatically. You shouldn't have to fight for a good delivery.",
    ],
    "frequency_decay": [
        "Hey {name}, your favorite spots miss you. Free delivery for a week, no code needed, already on your account. Come back and try what's new.",
        "{name}, it's been a while. We added a lot of new restaurants in your area. Free delivery this week to help you explore.",
    ],
    "competitor_switch": [
        "{name}, been a while. We get it, options are everywhere. But here's $15 across your next 3 orders to come back and try what's new in your area.",
        "Hey {name}, we'd love another shot. $15 in credits, no strings. Just try us again and see what's changed.",
    ],
    "promo_dependent": [
        "{name}, instead of waiting for deals, our annual pass gives you free delivery on every order all year. Based on your order history, you'd easily come out ahead.",
        "Hey {name}, DashPass annual is ${annual_savings} cheaper than monthly when you order as often as you do. Lock it in and stop thinking about delivery fees.",
    ],
    "at_risk": [
        "{name}, $10 credit on your next order, no hoops. We just want you back.",
        "Hey {name}, free delivery for a week, already on your account. Come see what's new.",
    ],
}
