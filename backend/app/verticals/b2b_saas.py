from app.verticals.base import VerticalConfig

PLAN_PRICES = {"free": 0, "starter": 9, "pro": 29, "enterprise": 79}
PLAN_DOWNGRADE = {"enterprise": "pro", "pro": "starter", "starter": "free", "free": "free"}


class B2BSaaSVertical(VerticalConfig):
    name = "b2b_saas"
    display_name = "B2B SaaS"
    accent_color = "emerald"
    plan_tiers = PLAN_PRICES
    event_types = ["login", "feature_use", "support_ticket", "payment_failure", "invite_teammate", "export_data"]
    primary_engagement_event = "feature_use"
    support_event = "support_ticket"

    _offers_map = {
        "price_sensitive": ["discount_30", "discount_50", "annual_lock_in", "plan_downgrade"],
        "underutilizer":   ["feature_unlock_trial", "onboarding_session", "use_case_guide"],
        "frustrated":      ["priority_support", "account_manager", "bug_fix_guarantee"],
        "disengaged":      ["pause_2mo", "pause_1mo", "reactivation_discount"],
        "at_risk":         ["plan_downgrade", "discount_30", "pause_1mo"],
    }

    def classify_segment(self, features: dict, user) -> str:
        if features.get("payment_failures", 0) >= 2 or (
            user.plan_tier in ["free", "starter"] and features.get("sessions_30d", 0) >= 5
        ):
            return "price_sensitive"
        if features.get("feature_adoption", 0) < 0.25 and float(user.monthly_spend or 0) > 0:
            return "underutilizer"
        if features.get("support_tickets_30d", 0) >= 3 and features.get("sessions_30d", 0) >= 5:
            return "frustrated"
        if features.get("sessions_30d", 0) <= 2 and features.get("login_recency_days", 0) > 14:
            return "disengaged"
        return "at_risk"

    def get_available_offers(self, segment: str) -> list:
        return self._offers_map.get(segment, ["discount_30"])

    def get_offer_details(self, offer_type: str, user) -> dict:
        monthly = float(user.monthly_spend or 0)
        if offer_type == "discount_30":
            return {"discount_pct": 30, "months": 3, "savings_per_month": round(monthly * 0.3, 2)}
        if offer_type == "discount_50":
            return {"discount_pct": 50, "months": 2, "savings_per_month": round(monthly * 0.5, 2)}
        if offer_type == "annual_lock_in":
            return {"discount_pct": 20, "billing": "annual", "annual_savings": round(monthly * 12 * 0.2, 2)}
        if offer_type == "plan_downgrade":
            suggested = PLAN_DOWNGRADE.get(user.plan_tier, "starter")
            price = PLAN_PRICES.get(suggested, 9)
            return {"suggested_plan": suggested, "price": price, "savings": round(monthly - price, 2)}
        if offer_type == "feature_unlock_trial":
            return {"trial_days": 14, "access": "all features"}
        if offer_type == "onboarding_session":
            return {"session": "1:1 onboarding", "duration_min": 45}
        if offer_type == "use_case_guide":
            return {"guide": "personalized use case walkthrough"}
        if offer_type == "priority_support":
            return {"callback_hours": 24, "tier": "priority"}
        if offer_type == "account_manager":
            return {"dedicated_manager": True, "sla_hours": 4}
        if offer_type == "bug_fix_guarantee":
            return {"fix_sla_hours": 48, "credit_if_missed": round(monthly * 0.5, 2)}
        if offer_type == "pause_2mo":
            return {"pause_months": 2}
        if offer_type == "pause_1mo":
            return {"pause_months": 1}
        if offer_type == "reactivation_discount":
            return {"discount_pct": 25, "months": 2}
        return {}

    def get_templates(self, segment: str) -> list:
        return TEMPLATES.get(segment, TEMPLATES["at_risk"])

    async def compute_extra_features(self, redis, user_id: int, now: float) -> dict:
        return {}

    def get_all_segments(self) -> list:
        return list(self._offers_map.keys())

    def get_seed_config(self) -> dict:
        return {
            "archetypes": [
                {
                    "name": "healthy", "weight": 0.40,
                    "plans": ["pro", "enterprise"],
                    "sessions_30d": (15, 30), "sessions_prev_30d": (12, 28),
                    "features_30d": (15, 30), "support_30d": (0, 1),
                    "payment_failures": (0, 0), "login_recency": (0, 2),
                    "churn_prob": 0.0, "metadata": {},
                },
                {
                    "name": "price_sensitive", "weight": 0.15,
                    "plans": ["free", "starter"],
                    "sessions_30d": (8, 20), "sessions_prev_30d": (6, 18),
                    "features_30d": (3, 8), "support_30d": (0, 2),
                    "payment_failures": (1, 3), "login_recency": (0, 5),
                    "churn_prob": 0.30, "metadata": {},
                },
                {
                    "name": "underutilizer", "weight": 0.15,
                    "plans": ["pro", "enterprise"],
                    "sessions_30d": (1, 5), "sessions_prev_30d": (8, 15),
                    "features_30d": (1, 3), "support_30d": (0, 0),
                    "payment_failures": (0, 0), "login_recency": (7, 20),
                    "churn_prob": 0.30, "metadata": {},
                },
                {
                    "name": "frustrated", "weight": 0.15,
                    "plans": ["free", "starter", "pro", "enterprise"],
                    "sessions_30d": (10, 25), "sessions_prev_30d": (8, 22),
                    "features_30d": (10, 20), "support_30d": (3, 8),
                    "payment_failures": (0, 1), "login_recency": (0, 3),
                    "churn_prob": 0.30, "metadata": {},
                },
                {
                    "name": "disengaged", "weight": 0.15,
                    "plans": ["free", "starter", "pro", "enterprise"],
                    "sessions_30d": (0, 2), "sessions_prev_30d": (5, 15),
                    "features_30d": (0, 2), "support_30d": (0, 0),
                    "payment_failures": (0, 2), "login_recency": (15, 45),
                    "churn_prob": 0.30, "metadata": {},
                },
            ]
        }


TEMPLATES = {
    "price_sensitive": [
        "Hey {name}, we get it. ${monthly_spend}/mo adds up. What if we took 30% off for the next 3 months? That's real money back in your pocket, and you keep everything you've been using.",
        "{name}, we'd rather keep you at a price that works. How about 30% off your {plan_tier} plan for 3 months? We don't want to lose you.",
    ],
    "underutilizer": [
        "{name}, you're on {plan_tier} but there's a lot you haven't had a chance to explore. How about 14 days of full access to every feature? Most people who try it find tools that change how they work.",
        "Hey {name}, there's more here than you've seen. We're unlocking everything for 14 days, no strings. Try it, and if it's still not a fit, we part as friends.",
    ],
    "frustrated": [
        "{name}, your recent experience hasn't been what it should be, and that's on us. We're assigning you a priority support contact who'll reach out within 24 hours to sort everything out.",
        "We see the friction, {name}. A dedicated specialist will contact you within 24 hours. Not a form, an actual person who can fix what's broken.",
    ],
    "disengaged": [
        "{name}, life gets busy. How about we pause your billing for 2 months? Your data and setup stay exactly where they are. Come back when the timing is better.",
        "Hey {name}, no judgment. Take 2 months off, no charge. Everything you've built in {plan_tier} will be right here when you're ready.",
    ],
    "at_risk": [
        "{name}, what if your plan just fit better? We can move you to {suggested_plan} and save you ${savings}/mo. You keep the features you actually use without paying for what you don't.",
        "Hey {name}, would a smaller plan work? {suggested_plan} at ${price}/mo might be a better fit for where you are right now.",
    ],
}
