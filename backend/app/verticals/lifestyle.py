from app.verticals.base import VerticalConfig

PLAN_PRICES = {"basic": 10, "plus": 20, "premium": 40}


class LifestyleVertical(VerticalConfig):
    name = "lifestyle"
    display_name = "Fitness"
    accent_color = "green"
    plan_tiers = PLAN_PRICES
    event_types = ["login", "workout", "streak_update", "goal_set", "goal_missed", "support_ticket", "payment_failure"]
    primary_engagement_event = "workout"
    support_event = "support_ticket"

    _offers_map = {
        "guilt_churn":      ["lite_plan", "pause_with_challenges", "fresh_start_program"],
        "plateau":          ["new_program_unlock", "coach_session", "goal_reset"],
        "hobbyist_cliff":   ["beginner_restart", "buddy_match", "reduced_commitment"],
        "seasonal_dropper": ["seasonal_pause", "off_season_lite", "annual_discount"],
        "at_risk":          ["discount_30", "pause_1mo", "coach_session"],
    }

    def classify_segment(self, features: dict, user) -> str:
        workouts_30d = features.get("workouts_30d", features.get("feature_adoption", 0) * 20)
        workout_velocity = features.get("workout_velocity", features.get("engagement_decay", 0))
        workouts_prev = features.get("workouts_prev_30d", features.get("sessions_prev_30d", 1))

        if workouts_30d <= 2 and features.get("login_recency_days", 0) > 14 and float(user.monthly_spend or 0) > 0:
            return "guilt_churn"
        if workout_velocity < -0.3 and workouts_prev > 8:
            return "plateau"
        if features.get("engagement_decay", 0) < -0.6 and workouts_prev > 10:
            return "hobbyist_cliff"
        if features.get("sessions_30d", 0) <= 3 and (user.user_metadata or {}).get("seasonal_pattern", False):
            return "seasonal_dropper"
        return "at_risk"

    def get_available_offers(self, segment: str) -> list:
        return self._offers_map.get(segment, ["discount_30"])

    def get_offer_details(self, offer_type: str, user) -> dict:
        monthly = float(user.monthly_spend or 0)
        if offer_type == "lite_plan":
            return {"new_plan": "basic", "new_price": 10, "savings": round(monthly - 10, 2)}
        if offer_type == "pause_with_challenges":
            return {"pause_months": 1, "bonus": "weekly challenge emails"}
        if offer_type == "fresh_start_program":
            return {"program": "14-day reboot", "access": "beginner track"}
        if offer_type == "new_program_unlock":
            return {"program": "advanced track", "trial_days": 14}
        if offer_type == "coach_session":
            return {"session": "30-min 1:1 with a coach", "cost": "free"}
        if offer_type == "goal_reset":
            return {"session": "goal-setting workshop", "format": "group"}
        if offer_type == "beginner_restart":
            return {"program": "starter track", "community": "beginner group"}
        if offer_type == "buddy_match":
            return {"feature": "accountability partner matching"}
        if offer_type == "reduced_commitment":
            return {"plan": "basic", "new_price": 10, "commitment": "month-to-month"}
        if offer_type == "seasonal_pause":
            return {"pause_months": 2, "note": "resume anytime"}
        if offer_type == "off_season_lite":
            return {"plan": "basic", "new_price": 10, "duration": "off-season"}
        if offer_type == "annual_discount":
            return {"discount_pct": 20, "billing": "annual", "annual_savings": round(monthly * 12 * 0.2, 2)}
        if offer_type == "discount_30":
            return {"discount_pct": 30, "months": 2}
        if offer_type == "pause_1mo":
            return {"pause_months": 1}
        return {}

    def get_templates(self, segment: str) -> list:
        return TEMPLATES.get(segment, TEMPLATES["at_risk"])

    async def compute_extra_features(self, redis, user_id: int, now: float) -> dict:
        thirty_days_ago = now - (30 * 86400)
        sixty_days_ago = now - (60 * 86400)
        workouts_30d = await redis.zcount(f"events:{user_id}:workout", thirty_days_ago, now)
        workouts_prev = await redis.zcount(f"events:{user_id}:workout", sixty_days_ago, thirty_days_ago)
        workout_velocity = (workouts_30d - workouts_prev) / max(workouts_prev, 1)
        goals_missed = await redis.zcount(f"events:{user_id}:goal_missed", thirty_days_ago, now)
        return {
            "workouts_30d": workouts_30d,
            "workouts_prev_30d": workouts_prev,
            "workout_velocity": round(workout_velocity, 3),
            "goals_missed": goals_missed,
        }

    def get_all_segments(self) -> list:
        return list(self._offers_map.keys())

    def get_seed_config(self) -> dict:
        return {
            "archetypes": [
                {
                    "name": "healthy", "weight": 0.40,
                    "plans": ["plus", "premium"],
                    "sessions_30d": (15, 30), "sessions_prev_30d": (14, 28),
                    "features_30d": (12, 28), "support_30d": (0, 1),
                    "payment_failures": (0, 0), "login_recency": (0, 3),
                    "churn_prob": 0.0, "metadata": {"seasonal_pattern": False},
                },
                {
                    "name": "guilt_churn", "weight": 0.15,
                    "plans": ["plus", "premium"],
                    "sessions_30d": (1, 3), "sessions_prev_30d": (2, 6),
                    "features_30d": (0, 2), "support_30d": (0, 0),
                    "payment_failures": (0, 0), "login_recency": (15, 35),
                    "churn_prob": 0.30, "metadata": {"seasonal_pattern": False},
                },
                {
                    "name": "plateau", "weight": 0.15,
                    "plans": ["plus", "premium"],
                    "sessions_30d": (5, 12), "sessions_prev_30d": (12, 22),
                    "features_30d": (4, 10), "support_30d": (0, 1),
                    "payment_failures": (0, 0), "login_recency": (3, 10),
                    "churn_prob": 0.30, "metadata": {"seasonal_pattern": False},
                },
                {
                    "name": "hobbyist_cliff", "weight": 0.15,
                    "plans": ["basic", "plus"],
                    "sessions_30d": (2, 6), "sessions_prev_30d": (14, 25),
                    "features_30d": (2, 6), "support_30d": (0, 0),
                    "payment_failures": (0, 1), "login_recency": (7, 20),
                    "churn_prob": 0.30, "metadata": {"seasonal_pattern": False},
                },
                {
                    "name": "seasonal_dropper", "weight": 0.15,
                    "plans": ["basic", "plus"],
                    "sessions_30d": (1, 4), "sessions_prev_30d": (8, 18),
                    "features_30d": (1, 4), "support_30d": (0, 0),
                    "payment_failures": (0, 1), "login_recency": (10, 25),
                    "churn_prob": 0.30, "metadata": {"seasonal_pattern": True},
                },
            ]
        }


TEMPLATES = {
    "guilt_churn": [
        "{name}, no guilt here. Life happens. Instead of canceling, how about our basic plan at $10/mo? Lower commitment, same app, and when you're ready to push again, everything's right where you left it.",
        "Hey {name}, we get it. How about pausing for a month instead? Your streaks, progress, and history all stay saved. Come back when you're ready.",
    ],
    "plateau": [
        "Hey {name}, hitting a wall is normal. You've built real consistency and that's the hardest part. We just unlocked a new program designed for exactly this moment. Try it free for 14 days before you decide.",
        "{name}, plateaus mean progress. We've got a coach session on the house, 30 minutes to reset your goals and get unstuck. No strings.",
    ],
    "hobbyist_cliff": [
        "{name}, starting something new is hard, and most people hit this exact wall. What if we matched you with a beginner group starting fresh next week? Sometimes you just need people doing it with you.",
        "Hey {name}, you built real momentum early on. Our basic plan at $10/mo keeps you in it without the pressure. Come back to the full program whenever you're ready.",
    ],
    "seasonal_dropper": [
        "{name}, we see this pattern. You always come back strong. How about we pause your billing for 2 months? Your progress and streaks stay saved, pick it up whenever you're ready.",
        "Hey {name}, take the off-season on us. Everything will be right here when it's time to get back at it.",
    ],
    "at_risk": [
        "{name}, 30% off for 2 months. Same workouts, same tracking, just a better deal while you figure things out.",
        "Hey {name}, we'd hate for you to lose your progress. Here's 30% off and a free coach session to help you reset.",
    ],
}
