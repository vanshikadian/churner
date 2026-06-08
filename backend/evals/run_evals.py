"""ChurnShield retention-message eval harness (Arize Phoenix demo).

What it does
------------
1. Builds a set of realistic (user, segment, offer) cases across all 4 verticals.
2. For each case, generates a retention message using the SAME prompt the app
   uses in production (app.services.prompts.build_retention_prompt).
3. Scores every message with an LLM-as-judge across four dimensions plus
   deterministic checks, then prints a scorecard and writes results.json.

When PHOENIX_ENABLED=1 and the observability stack is installed, every Claude
call here is traced into Phoenix, so you can see prompts, latency, token usage,
and the eval scores side by side in the UI.

Modes
-----
  --mode llm        generate messages with Claude (needs ANTHROPIC_API_KEY)
  --mode template   generate messages with the app's template fallback (no key)

Run
---
  cd backend
  # optional tracing:
  pip install -r requirements-observability.txt && phoenix serve &
  PHOENIX_ENABLED=1 ANTHROPIC_API_KEY=sk-ant-... python evals/run_evals.py --mode llm
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

# Make `app` importable when run from backend/ or repo root.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.prompts import build_retention_prompt, RETENTION_MODEL, RETENTION_MAX_TOKENS  # noqa: E402
from app.verticals import get_vertical_config  # noqa: E402

JUDGE_MODEL = os.getenv("JUDGE_MODEL", "claude-sonnet-4-20250514")

# ---------------------------------------------------------------------------
# Evaluation set: (vertical, segment, user). Offer is chosen from the real
# vertical config so the message is grounded in the same logic production uses.
# ---------------------------------------------------------------------------
CASES = [
    ("b2b_saas", "price_sensitive", {"name": "Dana Reyes", "plan_tier": "starter", "monthly_spend": 9,
        "features": {"sessions_30d": 11, "feature_adoption": 0.4, "support_tickets_30d": 1,
                     "payment_failures": 2, "login_recency_days": 3}}),
    ("b2b_saas", "underutilizer", {"name": "Marcus Lin", "plan_tier": "pro", "monthly_spend": 29,
        "features": {"sessions_30d": 3, "feature_adoption": 0.15, "support_tickets_30d": 0,
                     "payment_failures": 0, "login_recency_days": 12}}),
    ("b2b_saas", "frustrated", {"name": "Priya Nair", "plan_tier": "enterprise", "monthly_spend": 79,
        "features": {"sessions_30d": 18, "feature_adoption": 0.7, "support_tickets_30d": 5,
                     "payment_failures": 0, "login_recency_days": 1}}),
    ("entertainment", "binge_cliff", {"name": "Tom Becker", "plan_tier": "standard", "monthly_spend": 15,
        "features": {"sessions_30d": 2, "content_velocity": 0.1, "login_recency_days": 18}}),
    ("entertainment", "price_shopper", {"name": "Aisha Khan", "plan_tier": "premium", "monthly_spend": 22,
        "features": {"sessions_30d": 9, "content_velocity": 0.5, "payment_failures": 1, "login_recency_days": 4}}),
    ("lifestyle", "guilt_churn", {"name": "Leo Martins", "plan_tier": "annual", "monthly_spend": 39,
        "features": {"sessions_30d": 1, "feature_adoption": 0.1, "login_recency_days": 25}}),
    ("lifestyle", "plateau", {"name": "Hannah Cole", "plan_tier": "monthly", "monthly_spend": 25,
        "features": {"sessions_30d": 8, "feature_adoption": 0.5, "login_recency_days": 5}}),
    ("marketplace", "frequency_decay", {"name": "Sofia Romano", "plan_tier": "plus", "monthly_spend": 12,
        "features": {"order_frequency": 0.2, "sessions_30d": 4, "login_recency_days": 9}}),
    ("marketplace", "bad_experience", {"name": "Derek Owens", "plan_tier": "plus", "monthly_spend": 12,
        "features": {"order_frequency": 0.6, "support_tickets_30d": 3, "sessions_30d": 7, "login_recency_days": 2}}),
    ("marketplace", "promo_dependent", {"name": "Maya Singh", "plan_tier": "plus", "monthly_spend": 12,
        "features": {"order_frequency": 0.9, "sessions_30d": 14, "payment_failures": 0, "login_recency_days": 1}}),
]

JUDGE_PROMPT = """You are evaluating a customer-retention message produced by an AI system.

Here is the context the message was generated from:
{context}

Here is the message that was produced:
\"\"\"{message}\"\"\"

Score the message on each dimension from 1 to 5 (5 = best):
- grounded: uses only facts present in the context (name, plan, price, offer). Penalize invented facts, wrong numbers, or fabricated promises.
- relevant: the message fits the user's segment and the specific offer.
- tone: warm, human, and non-pushy. Penalize generic or robotic phrasing.
- instruction_following: 2 to 3 sentences, no em dashes, ends by stating what the user gets if they stay.

Return ONLY a JSON object, no prose:
{{"grounded": <int>, "relevant": <int>, "tone": <int>, "instruction_following": <int>, "rationale": "<one sentence>"}}"""


def _anthropic_client():
    from anthropic import Anthropic
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def generate_message_llm(client, prompt: str) -> str:
    resp = client.messages.create(
        model=RETENTION_MODEL,
        max_tokens=RETENTION_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def generate_message_template(user, features, segment, offer_type, offer_details, vc) -> str:
    # Reuse the app's own template fallback so template mode reflects real output.
    from app.services.offer_engine import _render_template
    return _render_template(user, features, segment, offer_type, offer_details, vc)


def deterministic_checks(message: str) -> dict:
    sentences = [s for s in re.split(r"[.!?]+", message) if s.strip()]
    return {
        "has_em_dash": ("—" in message) or ("–" in message),
        "sentence_count": len(sentences),
        "within_length": 1 <= len(sentences) <= 4,
        "char_len": len(message),
    }


def judge_message(client, context: str, message: str) -> dict:
    resp = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(context=context, message=message)}],
    )
    text = resp.content[0].text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(match.group(0)) if match else {"error": text}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["llm", "template"], default="llm")
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent / "results.json"))
    args = parser.parse_args()

    # Tracing is auto-enabled via the app's observability module if PHOENIX_ENABLED=1.
    try:
        from app.observability import init_observability
        init_observability()
    except Exception:
        pass

    if args.mode == "llm" and not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set. Use --mode template, or export your key.")
        sys.exit(1)

    client = _anthropic_client() if args.mode == "llm" else None
    rows = []

    for vertical, segment, spec in CASES:
        vc = get_vertical_config(vertical)
        user = SimpleNamespace(name=spec["name"], plan_tier=spec["plan_tier"],
                               monthly_spend=spec["monthly_spend"])
        features = spec["features"]
        offers = vc.get_available_offers(segment)
        offer_type = offers[0] if offers else "discount_30"
        offer_details = vc.get_offer_details(offer_type, user)
        prompt = build_retention_prompt(user, features, segment, offer_type, offer_details, vc)

        if args.mode == "llm":
            message = generate_message_llm(client, prompt)
        else:
            message = generate_message_template(user, features, segment, offer_type, offer_details, vc)

        checks = deterministic_checks(message)
        context = (f"vertical={vc.display_name}; name={user.name}; plan={user.plan_tier} "
                   f"(${user.monthly_spend}/mo); segment={segment}; offer={offer_type}; "
                   f"details={json.dumps(offer_details)}")
        scores = judge_message(client, context, message) if args.mode == "llm" else {}

        rows.append({
            "vertical": vertical, "segment": segment, "offer": offer_type,
            "message": message, "checks": checks, "scores": scores,
        })
        print(f"\n[{vertical}/{segment}] offer={offer_type}")
        print(f"  message: {message}")
        print(f"  checks : {checks}")
        if scores:
            print(f"  scores : {scores}")

    # ---- Aggregate ----
    print("\n" + "=" * 60)
    print("AGGREGATE")
    print("=" * 60)
    em_dash_rate = sum(r["checks"]["has_em_dash"] for r in rows) / len(rows)
    length_pass = sum(r["checks"]["within_length"] for r in rows) / len(rows)
    print(f"em-dash violations : {em_dash_rate:.0%}")
    print(f"length compliance  : {length_pass:.0%}")
    if args.mode == "llm":
        for dim in ("grounded", "relevant", "tone", "instruction_following"):
            vals = [r["scores"].get(dim) for r in rows if isinstance(r["scores"].get(dim), (int, float))]
            if vals:
                print(f"avg {dim:<22}: {sum(vals) / len(vals):.2f} / 5")

    Path(args.out).write_text(json.dumps(rows, indent=2))
    print(f"\nWrote {len(rows)} results -> {args.out}")


if __name__ == "__main__":
    main()
