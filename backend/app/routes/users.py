from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database import get_db
from app.models import User, Intervention
from app.schemas import UserResponse

router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    vertical: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=500, le=1000),
    offset: int = 0,
):
    # Latest intervention per user
    latest_sub = (
        select(
            Intervention.user_id,
            Intervention.churn_risk_score,
            Intervention.segment,
            func.row_number()
            .over(
                partition_by=Intervention.user_id,
                order_by=Intervention.created_at.desc(),
            )
            .label("rn"),
        )
    ).subquery()
    latest = select(latest_sub).where(latest_sub.c.rn == 1).subquery()

    query = (
        select(
            User,
            latest.c.churn_risk_score.label("risk_score"),
            latest.c.segment.label("segment"),
        )
        .outerjoin(latest, User.id == latest.c.user_id)
        .order_by(User.id)
    )
    if vertical:
        query = query.where(User.vertical == vertical)
    if status:
        query = query.where(User.status == status)
    query = query.limit(limit).offset(offset)

    rows = (await db.execute(query)).all()
    users = []
    for row in rows:
        user = row.User
        users.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "plan_tier": user.plan_tier,
            "monthly_spend": float(user.monthly_spend or 0),
            "signup_date": user.signup_date,
            "last_login": user.last_login,
            "sessions_last_30d": user.sessions_last_30d or 0,
            "sessions_prev_30d": user.sessions_prev_30d or 0,
            "features_used": user.features_used or 0,
            "total_features": user.total_features or 8,
            "support_tickets_last_30d": user.support_tickets_last_30d or 0,
            "payment_failures": user.payment_failures or 0,
            "status": user.status,
            "vertical": user.vertical or "b2b_saas",
            "created_at": user.created_at,
            "risk_score": float(row.risk_score) if row.risk_score is not None else None,
            "segment": row.segment,
        })
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "plan_tier": user.plan_tier,
        "monthly_spend": float(user.monthly_spend or 0),
        "signup_date": user.signup_date,
        "last_login": user.last_login,
        "sessions_last_30d": user.sessions_last_30d or 0,
        "sessions_prev_30d": user.sessions_prev_30d or 0,
        "features_used": user.features_used or 0,
        "total_features": user.total_features or 8,
        "support_tickets_last_30d": user.support_tickets_last_30d or 0,
        "payment_failures": user.payment_failures or 0,
        "status": user.status,
        "vertical": user.vertical or "b2b_saas",
        "created_at": user.created_at,
        "risk_score": None,
        "segment": None,
    }
