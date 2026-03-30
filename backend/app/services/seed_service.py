"""Per-vertical seed service — populates PostgreSQL and Redis sorted sets."""
import random
import time
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.models import User, Event, BanditStat
from app.verticals import get_vertical_config, VERTICAL_NAMES

fake = Faker()


def _weighted_choice(archetypes: list) -> dict:
    r = random.random()
    cumulative = 0.0
    for arch in archetypes:
        cumulative += arch["weight"]
        if r <= cumulative:
            return arch
    return archetypes[-1]


def _rand(rng: tuple) -> int:
    lo, hi = rng
    return random.randint(lo, hi)


def _make_user(arch: dict, plan_tiers: dict, vertical: str) -> dict:
    now = datetime.utcnow()
    plan = random.choice(arch["plans"])
    monthly_spend = plan_tiers.get(plan, 0)

    sessions_30d = _rand(arch["sessions_30d"])
    sessions_prev_30d = _rand(arch["sessions_prev_30d"])
    features_30d = _rand(arch["features_30d"])
    support_30d = _rand(arch["support_30d"])
    payment_failures = _rand(arch["payment_failures"])
    login_recency = _rand(arch["login_recency"])

    status = "churned" if (arch["churn_prob"] > 0 and random.random() < arch["churn_prob"]) else "active"
    last_login = now - timedelta(days=login_recency)
    signup_days_ago = random.randint(30, 730)
    signup_date = (now - timedelta(days=signup_days_ago)).date()

    return dict(
        name=fake.name(),
        email=fake.unique.email(),
        plan_tier=plan,
        monthly_spend=monthly_spend,
        signup_date=signup_date,
        last_login=last_login,
        sessions_last_30d=sessions_30d,
        sessions_prev_30d=sessions_prev_30d,
        features_used=min(features_30d // 3, 8),
        total_features=8,
        support_tickets_last_30d=support_30d,
        payment_failures=payment_failures,
        status=status,
        vertical=vertical,
        user_metadata=arch.get("metadata", {}),
    )


async def _write_events_for_user(
    db: AsyncSession,
    redis_client,
    user: User,
    arch: dict,
    event_types: list,
    primary_engagement_event: str,
    support_event: str,
):
    """Generate realistic events, write to PostgreSQL, push to Redis sorted sets."""
    now_dt = datetime.utcnow()
    now_ts = time.time()
    event_objects = []

    # Login events: distributed across last 60 days, weighted toward last 30
    login_count_30d = user.sessions_last_30d
    login_count_prev = user.sessions_prev_30d
    for _ in range(login_count_30d):
        days_ago = random.uniform(0, 30)
        ts = now_dt - timedelta(days=days_ago)
        event_objects.append(Event(user_id=user.id, event_type="login", event_data={}, created_at=ts))
    for _ in range(login_count_prev):
        days_ago = random.uniform(30, 60)
        ts = now_dt - timedelta(days=days_ago)
        event_objects.append(Event(user_id=user.id, event_type="login", event_data={}, created_at=ts))

    # Primary engagement events (last 30 days)
    eng_count = _rand(arch["features_30d"])
    for _ in range(eng_count):
        days_ago = random.uniform(0, 30)
        ts = now_dt - timedelta(days=days_ago)
        event_objects.append(Event(
            user_id=user.id, event_type=primary_engagement_event,
            event_data={"feature_id": random.randint(1, 8)}, created_at=ts,
        ))

    # Support / bad experience events
    for _ in range(user.support_tickets_last_30d):
        days_ago = random.uniform(0, 30)
        ts = now_dt - timedelta(days=days_ago)
        event_objects.append(Event(
            user_id=user.id, event_type=support_event,
            event_data={"severity": random.choice(["low", "medium", "high"])}, created_at=ts,
        ))

    # Payment failures
    for _ in range(user.payment_failures):
        days_ago = random.uniform(0, 60)
        ts = now_dt - timedelta(days=days_ago)
        event_objects.append(Event(
            user_id=user.id, event_type="payment_failure",
            event_data={"amount": float(user.monthly_spend or 0)}, created_at=ts,
        ))

    # Add any extra event types with light activity
    for et in event_types:
        if et in ("login", primary_engagement_event, support_event, "payment_failure"):
            continue
        for _ in range(random.randint(0, 3)):
            days_ago = random.uniform(0, 60)
            ts = now_dt - timedelta(days=days_ago)
            event_objects.append(Event(user_id=user.id, event_type=et, event_data={}, created_at=ts))

    db.add_all(event_objects)
    await db.flush()

    # Write to Redis sorted sets
    if redis_client:
        try:
            ninety_days_ago_ts = now_ts - (90 * 86400)
            pipe = redis_client.pipeline()
            for ev in event_objects:
                key = f"events:{user.id}:{ev.event_type}"
                ts_unix = ev.created_at.timestamp()
                pipe.zadd(key, {str(ev.id): ts_unix})
                pipe.zremrangebyscore(key, 0, ninety_days_ago_ts)
            await pipe.execute()
        except Exception as e:
            print(f"Redis write warning for user {user.id}: {e}")


async def _init_bandit_stats(db: AsyncSession, vertical_config):
    """Initialize Beta(1,1) priors for all segment-offer combinations."""
    for segment in vertical_config.get_all_segments():
        for offer in vertical_config.get_available_offers(segment):
            existing = await db.scalar(
                select(BanditStat).where(
                    BanditStat.vertical == vertical_config.name,
                    BanditStat.segment == segment,
                    BanditStat.offer_type == offer,
                )
            )
            if not existing:
                db.add(BanditStat(
                    vertical=vertical_config.name,
                    segment=segment,
                    offer_type=offer,
                    alpha=1.0,
                    beta_param=1.0,
                    total_trials=0,
                ))
    await db.flush()


async def seed_vertical(
    db: AsyncSession,
    redis_client=None,
    vertical_name: str = "b2b_saas",
    num_users: int = 125,
):
    config = get_vertical_config(vertical_name)
    seed_cfg = config.get_seed_config()
    archetypes = seed_cfg["archetypes"]

    print(f"Seeding {num_users} users for vertical: {vertical_name}")

    # Clear existing data for this vertical
    await db.execute(text(
        "DELETE FROM interventions WHERE vertical = :v OR user_id IN "
        "(SELECT id FROM users WHERE vertical = :v)"
    ), {"v": vertical_name})
    await db.execute(text("DELETE FROM events WHERE user_id IN (SELECT id FROM users WHERE vertical = :v)"), {"v": vertical_name})
    await db.execute(text("DELETE FROM users WHERE vertical = :v"), {"v": vertical_name})
    await db.execute(text("DELETE FROM bandit_stats WHERE vertical = :v"), {"v": vertical_name})
    await db.commit()

    fake.unique.clear()

    user_objects = []
    arch_list = []
    for _ in range(num_users):
        arch = _weighted_choice(archetypes)
        data = _make_user(arch, config.plan_tiers, vertical_name)
        user_objects.append(User(**data))
        arch_list.append(arch)

    db.add_all(user_objects)
    await db.flush()

    total_events = 0
    for user, arch in zip(user_objects, arch_list):
        await _write_events_for_user(
            db, redis_client, user, arch,
            config.event_types,
            config.primary_engagement_event,
            config.support_event,
        )
        total_events += user.sessions_last_30d + user.sessions_prev_30d + user.support_tickets_last_30d + user.payment_failures

    await _init_bandit_stats(db, config)
    await db.commit()

    print(f"Seeded {num_users} users and ~{total_events} events for {vertical_name}")


async def seed_database(db: AsyncSession, redis_client=None, force: bool = False):
    """Seed all verticals. Per-vertical: skip if already has users (unless force=True)."""
    for vertical in VERTICAL_NAMES:
        if not force:
            count = await db.scalar(
                select(func.count(User.id)).where(User.vertical == vertical)
            )
            if count and count > 0:
                print(f"Vertical '{vertical}' already has {count} users, skipping.")
                continue
        await seed_vertical(db, redis_client, vertical_name=vertical, num_users=125)

    print(f"Full seed complete — {len(VERTICAL_NAMES) * 125} users across {len(VERTICAL_NAMES)} verticals.")
