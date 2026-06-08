"""Offer selection (Thompson Sampling bandit) + message generation (LLM or template)."""
import os
import json
import random
from datetime import datetime

from app.services.bandit import bandit
from app.services.prompts import build_retention_prompt, RETENTION_MODEL, RETENTION_MAX_TOKENS


async def generate_intervention(
    user, features: dict, segment: str, churn_score: float, risk_factors: dict,
    db, vertical_config
) -> dict:
    """Full offer generation pipeline: bandit selects → details built → message written."""
    available_offers = vertical_config.get_available_offers(segment)
    offer_type = await bandit.select_offer(db, vertical_config.name, segment, available_offers)
    offer_details = vertical_config.get_offer_details(offer_type, user)
    offer_message, message_source = await _generate_message(
        user, features, segment, offer_type, offer_details, vertical_config
    )

    return {
        "churn_risk_score": churn_score,
        "risk_factors": risk_factors,
        "segment": segment,
        "offer_type": offer_type,
        "offer_details": offer_details,
        "offer_message": offer_message,
        "message_source": message_source,
        "revenue_at_risk": float(user.monthly_spend or 0) * 12,
    }


async def _generate_message(user, features, segment, offer_type, offer_details, vertical_config):
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    if api_key:
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            prompt = build_retention_prompt(
                user, features, segment, offer_type, offer_details, vertical_config
            )
            response = client.messages.create(
                model=RETENTION_MODEL,
                max_tokens=RETENTION_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip(), "llm"
        except Exception as e:
            print(f"Claude API failed, falling back to template: {e}")

    return _render_template(user, features, segment, offer_type, offer_details, vertical_config), "template"


def _render_template(user, features, segment, offer_type, offer_details, vertical_config) -> str:
    templates = vertical_config.get_templates(segment)
    template = random.choice(templates)

    first_name = user.name.split()[0] if user.name else "there"
    monthly = float(user.monthly_spend or 0)

    # Build a context dict with everything a template might reference
    ctx = {
        "name": first_name,
        "plan_tier": (user.plan_tier or "pro").title(),
        "monthly_spend": f"{monthly:.0f}",
        "savings": f"{monthly * 0.3:.0f}",
        "price": offer_details.get("price", offer_details.get("new_price", 9)),
        "annual_savings": offer_details.get("annual_savings", 0),
        "suggested_plan": (offer_details.get("suggested_plan", "starter") or "starter").title(),
        **{k: v for k, v in offer_details.items()},
    }

    try:
        return template.format(**ctx)
    except KeyError:
        # If template references a key we don't have, just use a safe fallback
        return (
            f"Hey {first_name}, we'd love to keep you. "
            f"We've put together a special offer — check the details below."
        )
