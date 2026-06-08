"""Prompt construction for LLM retention messages.

Kept dependency-free on purpose so it can be imported by both the app
(offer_engine) and the standalone eval harness (evals/run_evals.py) without
pulling in the database, Redis, or ML stack. Single source of truth for the
retention prompt, so evals always score exactly what production sends.
"""
import json

RETENTION_MODEL = "claude-sonnet-4-20250514"
RETENTION_MAX_TOKENS = 300


def build_retention_prompt(user, features, segment, offer_type, offer_details, vertical_config) -> str:
    """Build the retention message prompt. Mirrors the exact prompt used in production."""
    safe_features = {k: v for k, v in features.items() if k != "weekly_trend"}
    return (
        f"You are a retention specialist for a {vertical_config.display_name} subscription product. "
        f"Write a short, warm, personalized retention message.\n\n"
        f"User context:\n"
        f"- Name: {user.name}\n"
        f"- Plan: {user.plan_tier} (${user.monthly_spend}/mo)\n"
        f"- Segment: {segment}\n"
        f"- Key signals: {json.dumps(safe_features, indent=2)}\n\n"
        f"Offer: {offer_type}\n"
        f"Details: {json.dumps(offer_details)}\n\n"
        f"Rules:\n"
        f"- Use ONLY facts explicitly listed in the user context and offer above. "
        f"Do NOT invent or assume sessions, dates, percentages, past behavior, or events that are not listed. "
        f"If a number is not given, do not state a number.\n"
        f"- Keep it to 2 or 3 sentences.\n"
        f"- Do not use em dashes.\n"
        f"- End with a sentence that states what they keep or get if they stay.\n"
        f"Be warm, human, and direct. Return ONLY the message text."
    )
