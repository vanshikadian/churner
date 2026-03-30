"""Per-vertical ML model loading + prediction with feature importance."""
import joblib
import numpy as np
from pathlib import Path

from app.services.features import features_to_model_input, FEATURE_NAMES

_models: dict = {}  # vertical_name -> model
ML_DIR = Path(__file__).parent.parent.parent / "ml"


def load_model(vertical: str = "b2b_saas"):
    """Load a single vertical's model from disk."""
    model_path = ML_DIR / f"{vertical}_model.joblib"
    if model_path.exists():
        _models[vertical] = joblib.load(model_path)
        print(f"ML model loaded for {vertical}")
    else:
        print(f"Warning: No ML model found for {vertical} at {model_path}")


def load_all_models():
    """Load models for all verticals at startup."""
    for vertical in ["b2b_saas", "entertainment", "lifestyle", "marketplace"]:
        load_model(vertical)


def predict_with_explanation(features: dict, user, vertical: str = "b2b_saas") -> tuple[float, dict]:
    """
    Returns (churn_score, risk_factors).
    risk_factors is a dict of {feature_name: contribution} sorted by importance.
    """
    feature_vector = features_to_model_input(features, user)
    model = _models.get(vertical)

    if model is None:
        score = _heuristic_score(features)
        risk_factors = _heuristic_factors(features)
        return score, risk_factors

    score = float(model.predict_proba([feature_vector])[0][1])
    importances = model.feature_importances_

    # Contribution = |feature_value| * importance, normalized to sum to 1
    raw_contributions = [abs(v) * imp for v, imp in zip(feature_vector, importances)]
    total = sum(raw_contributions) or 1.0
    contributions = {
        name: round(raw / total, 4)
        for name, raw in zip(FEATURE_NAMES, raw_contributions)
    }

    # Sort descending by contribution
    risk_factors = dict(
        sorted(contributions.items(), key=lambda x: x[1], reverse=True)
    )

    return round(score, 4), risk_factors


def _heuristic_score(features: dict) -> float:
    score = 0.3
    if features.get("login_recency_days", 0) > 14:
        score += 0.25
    if features.get("engagement_decay", 0) < -0.3:
        score += 0.2
    if features.get("support_tickets_30d", 0) >= 3:
        score += 0.15
    if features.get("payment_failures", 0) >= 2:
        score += 0.15
    return round(min(score, 0.99), 4)


def _heuristic_factors(features: dict) -> dict:
    """Build a rough factor breakdown when no model is available."""
    raw = {
        "login_recency": max(features.get("login_recency_days", 0) / 60, 0),
        "engagement_decay": max(-features.get("engagement_decay", 0), 0),
        "support_intensity": features.get("support_tickets_30d", 0) / 8,
        "payment_reliability": features.get("payment_failures", 0) / 5,
        "feature_adoption": max(1 - features.get("feature_adoption", 1), 0),
        "plan_value": 0.05,
        "engagement_velocity": max(-features.get("engagement_velocity", 0), 0),
    }
    total = sum(raw.values()) or 1.0
    return {k: round(v / total, 4) for k, v in sorted(raw.items(), key=lambda x: x[1], reverse=True)}
