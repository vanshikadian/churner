"""Standalone seed script — run once on startup to populate the database."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import redis.asyncio as aioredis
from app.database import AsyncSessionLocal, engine
from app.models import Base
from app.services.seed_service import seed_database
from app.config import settings


async def main():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    redis_client = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async with AsyncSessionLocal() as db:
        await seed_database(db, redis_client, force=False)

    await redis_client.aclose()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
