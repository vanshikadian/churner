"""Real-time feature computation from Redis sorted sets, with User-column fallback."""
import time
import json
from datetime import datetime

CACHE_TTL = 3600  # 1 hour


async def compute_features(user, redis_client=None, vertical_config=None) -> dict:
    cache_key = f"features:{user.id}"

    if redis_client:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    features = await _compute_from_redis(user, redis_client, vertical_config)

    if redis_client:
        try:
            await redis_client.setex(cache_key, CACHE_TTL, json.dumps(features))
        except Exception:
            pass

    return features


async def _compute_from_redis(user, redis_client, vertical_config) -> dict:
    now = time.time()
    thirty_days_ago = now - (30 * 86400)
    sixty_days_ago = now - (60 * 86400)
    seven_days_ago = now - (7 * 86400)

    engagement_event = "feature_use"
    support_event = "support_ticket"
    if vertical_config:
        engagement_event = getattr(vertical_config, "primary_engagement_event", "feature_use")
        support_event = getattr(vertical_config, "support_event", "support_ticket")

    if redis_client:
        try:
            # Login sessions
            sessions_30d = await redis_client.zcount(
                f"events:{user.id}:login", thirty_days_ago, now
            )
            sessions_prev_30d = await redis_client.zcount(
                f"events:{user.id}:login", sixty_days_ago, thirty_days_ago
            )

            # Engagement (feature use / content views / workouts / orders)
            eng_30d = await redis_client.zcount(
                f"events:{user.id}:{engagement_event}", thirty_days_ago, now
            )

            # Support / bad experiences
            support_30d = await redis_client.zcount(
                f"events:{user.id}:{support_event}", thirty_days_ago, now
            )

            # Payment failures
            payment_failures = await redis_client.zcount(
                f"events:{user.id}:payment_failure", thirty_days_ago, now
            )

            # Last login recency
            last_login_entries = await redis_client.zrevrange(
                f"events:{user.id}:login", 0, 0, withscores=True
            )
            if last_login_entries:
                login_recency_days = (now - last_login_entries[0][1]) / 86400
            elif user.last_login:
                login_recency_days = max((datetime.utcnow() - user.last_login).total_seconds() / 86400, 0)
            else:
                login_recency_days = 30.0

            # Weekly engagement trend (4 weeks)
            weekly_counts = []
            for i in range(4):
                w_start = now - ((i + 1) * 7 * 86400)
                w_end = now - (i * 7 * 86400)
                cnt = await redis_client.zcount(f"events:{user.id}:login", w_start, w_end)
                weekly_counts.append(cnt)

            # Use Redis data if we got any real events, else fall back
            redis_has_data = (sessions_30d + sessions_prev_30d + eng_30d) > 0

            if redis_has_data:
                sessions_prev_safe = max(sessions_prev_30d, 1)
                engagement_decay = (sessions_30d - sessions_prev_30d) / sessions_prev_safe
                feature_adoption = min(eng_30d / 20, 1.0)

                recent_avg = (weekly_counts[0] + weekly_counts[1]) / 2
                older_avg = (weekly_counts[2] + weekly_counts[3]) / 2 if sum(weekly_counts[2:]) > 0 else 1
                engagement_velocity = (recent_avg - older_avg) / max(older_avg, 1)

                features = {
                    "sessions_30d": sessions_30d,
                    "sessions_prev_30d": sessions_prev_30d,
                    "engagement_decay": round(engagement_decay, 4),
                    "engagement_velocity": round(engagement_velocity, 4),
                    "login_recency_days": round(login_recency_days, 1),
                    "feature_adoption": round(feature_adoption, 4),
                    "support_tickets_30d": support_30d,
                    "payment_failures": payment_failures,
                    "weekly_trend": weekly_counts,
                }

                if vertical_config:
                    extras = await vertical_config.compute_extra_features(redis_client, user.id, now)
                    features.update(extras)

                return features
        except Exception:
            pass

    # Fallback: compute from stored User columns
    return _compute_from_user_columns(user)


def _compute_from_user_columns(user) -> dict:
    now = datetime.utcnow()
    sessions_prev = max(user.sessions_prev_30d or 1, 1)
    engagement_decay = (
        (user.sessions_last_30d - user.sessions_prev_30d) / sessions_prev
    )
    last_login = user.last_login if user.last_login else now
    login_recency_days = max((now - last_login).total_seconds() / 86400, 0)
    feature_adoption = (user.features_used or 0) / max(user.total_features or 8, 1)
    payment_reliability = 1.0 - (min(user.payment_failures or 0, 5) / 5)

    return {
        "sessions_30d": user.sessions_last_30d or 0,
        "sessions_prev_30d": user.sessions_prev_30d or 0,
        "engagement_decay": round(engagement_decay, 4),
        "engagement_velocity": 0.0,
        "login_recency_days": round(login_recency_days, 1),
        "feature_adoption": round(feature_adoption, 4),
        "support_tickets_30d": user.support_tickets_last_30d or 0,
        "payment_failures": user.payment_failures or 0,
        "weekly_trend": [],
    }


def features_to_model_input(features: dict, user) -> list:
    """Convert feature dict to the array the sklearn model expects (7 values)."""
    monthly = float(user.monthly_spend or 0)
    payment_failures = features.get("payment_failures", user.payment_failures or 0)
    return [
        features.get("engagement_decay", 0.0),
        features.get("login_recency_days", 0.0),
        features.get("feature_adoption", 0.0),
        features.get("support_tickets_30d", 0.0),
        1.0 - (min(payment_failures, 5) / 5),        # payment_reliability
        monthly / 79.0,                               # plan_value
        features.get("engagement_velocity", 0.0),
    ]


FEATURE_NAMES = [
    "engagement_decay",
    "login_recency",
    "feature_adoption",
    "support_intensity",
    "payment_reliability",
    "plan_value",
    "engagement_velocity",
]
