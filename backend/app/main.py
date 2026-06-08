from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.observability import init_observability
from app.database import engine, AsyncSessionLocal
from app.models import Base
from app.services.scoring import load_all_models, ML_DIR
from app.services.seed_service import seed_database
from app.verticals import VERTICAL_NAMES
from app.routes import users, interventions, analytics, seed
from app.routes import events, verticals


async def _auto_train_missing(redis_client):
    """Train models for any vertical that has users but no .joblib on disk."""
    import asyncio
    from ml.train import fetch_users_for_vertical, train_for_vertical

    loop = asyncio.get_event_loop()
    for vertical in VERTICAL_NAMES:
        model_path = ML_DIR / f"{vertical}_model.joblib"
        if model_path.exists():
            continue
        print(f"[startup] No model for {vertical} — training now...")
        users_list = await fetch_users_for_vertical(vertical)
        if users_list:
            await loop.run_in_executor(None, train_for_vertical, vertical, users_list)
        else:
            print(f"[startup] No users for {vertical}, skipping train.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Optional Arize Phoenix tracing. No-op unless PHOENIX_ENABLED=1.
    init_observability()

    # Create/migrate tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add new columns to existing tables if they don't exist (safe migration)
        for stmt in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS vertical VARCHAR(30) DEFAULT 'b2b_saas'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS metadata JSON DEFAULT '{}'",
            "ALTER TABLE interventions ADD COLUMN IF NOT EXISTS vertical VARCHAR(30) DEFAULT 'b2b_saas'",
            "ALTER TABLE interventions ADD COLUMN IF NOT EXISTS risk_factors JSON DEFAULT '{}'",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass

    # Connect to Redis early so seed can populate sorted sets
    app.state.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    # Seed all verticals if DB is empty
    async with AsyncSessionLocal() as db:
        await seed_database(db, app.state.redis, force=False)

    # Train models for any vertical that is missing one
    await _auto_train_missing(app.state.redis)

    # Load ML models for all verticals
    load_all_models()

    yield

    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(title="ChurnShield API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/api")
app.include_router(interventions.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(seed.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(verticals.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
