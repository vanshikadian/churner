"""Thompson Sampling multi-armed bandit for offer selection."""
import numpy as np
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import BanditStat


class ThompsonBandit:

    async def select_offer(
        self, db: AsyncSession, vertical: str, segment: str, available_offers: list[str]
    ) -> str:
        """Sample from each offer's Beta distribution and return the best."""
        result = await db.execute(
            select(BanditStat).where(
                BanditStat.vertical == vertical,
                BanditStat.segment == segment,
                BanditStat.offer_type.in_(available_offers),
            )
        )
        stats = {s.offer_type: s for s in result.scalars().all()}

        # Create missing records with uniform Beta(1,1) prior
        for offer in available_offers:
            if offer not in stats:
                new_stat = BanditStat(
                    vertical=vertical,
                    segment=segment,
                    offer_type=offer,
                    alpha=1.0,
                    beta_param=1.0,
                    total_trials=0,
                )
                db.add(new_stat)

        try:
            await db.flush()
        except Exception:
            await db.rollback()

        # Sample from Beta(alpha, beta) for each offer
        samples = {}
        for offer in available_offers:
            if offer in stats:
                alpha = float(stats[offer].alpha)
                beta_val = float(stats[offer].beta_param)
            else:
                alpha, beta_val = 1.0, 1.0
            samples[offer] = np.random.beta(alpha, beta_val)

        return max(samples, key=samples.get)

    async def update(
        self,
        db: AsyncSession,
        vertical: str,
        segment: str,
        offer_type: str,
        accepted: bool,
    ):
        """Update bandit stats after observing an outcome."""
        result = await db.execute(
            select(BanditStat).where(
                BanditStat.vertical == vertical,
                BanditStat.segment == segment,
                BanditStat.offer_type == offer_type,
            )
        )
        stat = result.scalar_one_or_none()
        if stat:
            if accepted:
                stat.alpha = float(stat.alpha) + 1
            else:
                stat.beta_param = float(stat.beta_param) + 1
            stat.total_trials = (stat.total_trials or 0) + 1
            stat.updated_at = datetime.utcnow()
            await db.commit()


bandit = ThompsonBandit()
