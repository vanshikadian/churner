from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.seed_service import seed_vertical, seed_database

router = APIRouter()


@router.post("/seed")
async def seed_endpoint(
    request: Request,
    vertical: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Re-seed. ?vertical=b2b_saas seeds one vertical; omit for all."""
    redis_client = getattr(request.app.state, "redis", None)
    if vertical:
        await seed_vertical(db, redis_client, vertical_name=vertical, num_users=125)
        return {"status": "ok", "seeded": vertical}
    await seed_database(db, redis_client, force=True)
    return {"status": "ok", "seeded": "all"}
