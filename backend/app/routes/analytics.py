from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from typing import Optional

from app.database import get_db
from app.models import User, Intervention, BanditStat
from app.schemas import AnalyticsResponse, SegmentStats, OfferTypeStats, RecentIntervention

router = APIRouter()


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    vertical: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    user_filter = User.vertical == vertical if vertical else True
    int_filter = Intervention.vertical == vertical if vertical else True

    total_users = (await db.scalar(select(func.count(User.id)).where(user_filter))) or 0
    active_users = (
        await db.scalar(select(func.count(User.id)).where(user_filter, User.status == "active"))
    ) or 0
    total_interventions = (await db.scalar(select(func.count(Intervention.id)).where(int_filter))) or 0

    total_responded = (
        await db.scalar(
            select(func.count(Intervention.id)).where(
                int_filter, Intervention.outcome.in_(["accepted", "rejected"])
            )
        )
    ) or 0
    total_accepted = (
        await db.scalar(
            select(func.count(Intervention.id)).where(int_filter, Intervention.outcome == "accepted")
        )
    ) or 0
    retention_rate = round(total_accepted / total_responded, 3) if total_responded else 0.0

    total_revenue_at_risk = float(
        (await db.scalar(select(func.sum(Intervention.revenue_at_risk)).where(int_filter))) or 0
    )
    total_revenue_saved = float(
        (await db.scalar(select(func.sum(Intervention.revenue_saved)).where(int_filter))) or 0
    )

    seg_q = (
        select(
            Intervention.segment,
            func.count(Intervention.id).label("count"),
            func.sum(case((Intervention.outcome == "accepted", 1), else_=0)).label("retained"),
            func.coalesce(func.sum(Intervention.revenue_saved), 0).label("revenue_saved"),
        )
        .where(int_filter)
        .group_by(Intervention.segment)
    )
    by_segment = {}
    for row in (await db.execute(seg_q)):
        by_segment[row.segment] = SegmentStats(
            count=row.count,
            retained=int(row.retained or 0),
            revenue_saved=float(row.revenue_saved or 0),
        )

    offer_q = (
        select(
            Intervention.offer_type,
            func.count(Intervention.id).label("count"),
            func.sum(case((Intervention.outcome == "accepted", 1), else_=0)).label("accepted"),
        )
        .where(int_filter)
        .group_by(Intervention.offer_type)
    )
    by_offer_type = {}
    for row in (await db.execute(offer_q)):
        by_offer_type[row.offer_type] = OfferTypeStats(
            count=row.count,
            acceptance_rate=round(int(row.accepted or 0) / row.count, 3) if row.count else 0.0,
        )

    recent_q = (
        select(Intervention, User.name.label("user_name"))
        .join(User, Intervention.user_id == User.id)
        .where(int_filter)
        .order_by(Intervention.created_at.desc())
        .limit(10)
    )
    recent_interventions = []
    for row in (await db.execute(recent_q)):
        i = row.Intervention
        recent_interventions.append(
            RecentIntervention(
                id=i.id,
                user_name=row.user_name,
                segment=i.segment,
                offer_type=i.offer_type,
                outcome=i.outcome,
                created_at=i.created_at,
            )
        )

    bandit_q = select(BanditStat)
    if vertical:
        bandit_q = bandit_q.where(BanditStat.vertical == vertical)
    bandit_rows = (await db.execute(bandit_q)).scalars().all()
    bandit_state: dict = {}
    for s in bandit_rows:
        if s.segment not in bandit_state:
            bandit_state[s.segment] = []
        alpha = float(s.alpha)
        beta = float(s.beta_param)
        bandit_state[s.segment].append({
            "offer_type": s.offer_type,
            "alpha": alpha,
            "beta": beta,
            "total_trials": s.total_trials or 0,
            "estimated_success_rate": round(alpha / (alpha + beta), 3),
            "confidence": (
                "low" if (s.total_trials or 0) < 10
                else "medium" if (s.total_trials or 0) < 30
                else "high"
            ),
        })

    return AnalyticsResponse(
        vertical=vertical or "all",
        total_users=total_users,
        active_users=active_users,
        total_interventions=total_interventions,
        retention_rate=retention_rate,
        total_revenue_at_risk=total_revenue_at_risk,
        total_revenue_saved=total_revenue_saved,
        by_segment=by_segment,
        by_offer_type=by_offer_type,
        recent_interventions=recent_interventions,
        bandit_state=bandit_state,
    )
