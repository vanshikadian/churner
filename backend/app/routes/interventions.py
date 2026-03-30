from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Intervention
from app.schemas import InterventionResponse, InterventionOutcomeRequest
from app.services.features import compute_features
from app.services.scoring import predict_with_explanation
from app.services.segmentation import classify_segment
from app.services.offer_engine import generate_intervention
from app.services.bandit import bandit
from app.verticals import get_vertical_config

router = APIRouter()


@router.post("/users/{user_id}/cancel", response_model=InterventionResponse)
async def cancel_user(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    redis_client = getattr(request.app.state, "redis", None)
    vertical_config = get_vertical_config(user.vertical or "b2b_saas")

    # Invalidate cached features so we get fresh computation
    if redis_client:
        try:
            await redis_client.delete(f"features:{user.id}")
        except Exception:
            pass

    features = await compute_features(user, redis_client, vertical_config)
    churn_score, risk_factors = predict_with_explanation(features, user, user.vertical or "b2b_saas")
    segment = classify_segment(features, user, vertical_config)

    payload = await generate_intervention(
        user, features, segment, churn_score, risk_factors, db, vertical_config
    )

    intervention = Intervention(
        user_id=user.id,
        vertical=user.vertical or "b2b_saas",
        churn_risk_score=payload["churn_risk_score"],
        risk_factors=payload["risk_factors"],
        segment=payload["segment"],
        offer_type=payload["offer_type"],
        offer_message=payload["offer_message"],
        offer_details=payload["offer_details"],
        outcome="pending",
        revenue_at_risk=payload["revenue_at_risk"],
        revenue_saved=0,
        message_source=payload["message_source"],
    )
    db.add(intervention)
    await db.commit()
    await db.refresh(intervention)

    return _to_response(intervention)


@router.post("/interventions/{intervention_id}/respond", response_model=InterventionResponse)
async def respond_to_intervention(
    intervention_id: int,
    body: InterventionOutcomeRequest,
    db: AsyncSession = Depends(get_db),
):
    if body.outcome not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="outcome must be 'accepted' or 'rejected'")

    result = await db.execute(select(Intervention).where(Intervention.id == intervention_id))
    intervention = result.scalar_one_or_none()
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    result = await db.execute(select(User).where(User.id == intervention.user_id))
    user = result.scalar_one_or_none()

    intervention.outcome = body.outcome
    intervention.responded_at = datetime.utcnow()

    accepted = body.outcome == "accepted"
    if accepted:
        intervention.revenue_saved = float(user.monthly_spend or 0) * 6
        user.status = "retained"
    else:
        intervention.revenue_saved = 0
        user.status = "churned"

    await db.commit()

    # Update bandit with outcome
    await bandit.update(
        db,
        vertical=intervention.vertical or "b2b_saas",
        segment=intervention.segment,
        offer_type=intervention.offer_type,
        accepted=accepted,
    )

    await db.refresh(intervention)
    return _to_response(intervention)


def _to_response(i: Intervention) -> dict:
    return {
        "id": i.id,
        "user_id": i.user_id,
        "vertical": i.vertical,
        "churn_risk_score": float(i.churn_risk_score),
        "risk_factors": i.risk_factors or {},
        "segment": i.segment,
        "offer_type": i.offer_type,
        "offer_message": i.offer_message,
        "offer_details": i.offer_details,
        "outcome": i.outcome,
        "revenue_at_risk": float(i.revenue_at_risk),
        "revenue_saved": float(i.revenue_saved),
        "message_source": i.message_source,
        "created_at": i.created_at,
        "responded_at": i.responded_at,
    }
