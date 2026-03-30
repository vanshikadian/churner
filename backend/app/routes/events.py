"""Event ingestion endpoint — writes to PostgreSQL + Redis sorted sets."""
import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Any, Optional

from app.database import get_db
from app.models import Event

router = APIRouter()


class EventCreate(BaseModel):
    user_id: int
    event_type: str
    event_data: Optional[dict[str, Any]] = {}


@router.post("/events")
async def ingest_event(event: EventCreate, request: Request, db: AsyncSession = Depends(get_db)):
    db_event = Event(
        user_id=event.user_id,
        event_type=event.event_type,
        event_data=event.event_data or {},
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)

    # Push to Redis sorted set
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client:
        try:
            key = f"events:{event.user_id}:{event.event_type}"
            now_ts = time.time()
            await redis_client.zadd(key, {str(db_event.id): now_ts})
            # Trim to 90 days
            await redis_client.zremrangebyscore(key, 0, now_ts - (90 * 86400))
            # Invalidate feature cache
            await redis_client.delete(f"features:{event.user_id}")
        except Exception as e:
            print(f"Redis event write warning: {e}")

    return {"status": "ok", "event_id": db_event.id}
