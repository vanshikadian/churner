"""Segment classification delegated to the active vertical config."""


def classify_segment(features: dict, user, vertical_config=None) -> str:
    if vertical_config:
        return vertical_config.classify_segment(features, user)

    # Fallback: B2B SaaS rules
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
