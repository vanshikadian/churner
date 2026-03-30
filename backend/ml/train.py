"""Train a GradientBoostingClassifier per vertical and save {vertical}_model.joblib."""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.models import User
from app.config import settings

ML_DIR = Path(__file__).parent


def compute_features(user, now: datetime) -> list:
    sessions_prev = max(user.sessions_prev_30d or 1, 1)
    engagement_decay = (user.sessions_last_30d - user.sessions_prev_30d) / sessions_prev

    last_login = user.last_login if user.last_login else now
    login_recency_days = max((now - last_login).total_seconds() / 86400, 0)

    feature_adoption = (user.features_used or 0) / max(user.total_features or 8, 1)
    support_intensity = user.support_tickets_last_30d or 0
    payment_reliability = 1.0 - (min(user.payment_failures or 0, 5) / 5)
    plan_value = float(user.monthly_spend or 0) / 79.0
    engagement_velocity = 0.0  # not available from stored columns

    return [
        engagement_decay,
        login_recency_days,
        feature_adoption,
        support_intensity,
        payment_reliability,
        plan_value,
        engagement_velocity,
    ]


async def fetch_users_for_vertical(vertical: str) -> list:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.vertical == vertical))
        users = result.scalars().all()
    await engine.dispose()
    return users


def train_for_vertical(vertical: str, users: list) -> bool:
    now = datetime.utcnow()
    X, y = [], []
    for user in users:
        X.append(compute_features(user, now))
        y.append(1 if user.status == "churned" else 0)

    X = np.array(X)
    y = np.array(y)

    print(f"\n[{vertical}] Training on {len(y)} users | churn rate: {y.mean():.1%}")

    if len(set(y)) < 2:
        print(f"[{vertical}] Skipping — need both churned and retained examples.")
        return False

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = GradientBoostingClassifier(
        n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=["retained", "churned"]))

    model_path = ML_DIR / f"{vertical}_model.joblib"
    joblib.dump(model, model_path)
    print(f"Saved → {model_path}")
    return True


async def main():
    verticals = ["b2b_saas", "entertainment", "lifestyle", "marketplace"]
    for vertical in verticals:
        print(f"\nFetching users for {vertical}...")
        users = await fetch_users_for_vertical(vertical)
        if not users:
            print(f"No users found for {vertical}. Run seed first.")
            continue
        train_for_vertical(vertical, users)


if __name__ == "__main__":
    asyncio.run(main())
