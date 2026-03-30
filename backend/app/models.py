from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(150), unique=True)
    plan_tier = Column(String(20))
    monthly_spend = Column(Numeric(10, 2))
    signup_date = Column(Date)
    status = Column(String(20), default="active")
    vertical = Column(String(30), default="b2b_saas")
    user_metadata = Column("metadata", JSON, default={})
    # Legacy display columns (also used as ML training fallback)
    last_login = Column(DateTime)
    sessions_last_30d = Column(Integer, default=0)
    sessions_prev_30d = Column(Integer, default=0)
    features_used = Column(Integer, default=0)
    total_features = Column(Integer, default=8)
    support_tickets_last_30d = Column(Integer, default=0)
    payment_failures = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")
    interventions = relationship("Intervention", back_populates="user", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    event_type = Column(String(50))
    event_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="events")


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    vertical = Column(String(30), default="b2b_saas")
    churn_risk_score = Column(Numeric(5, 4))
    risk_factors = Column(JSON, default={})
    segment = Column(String(50))
    offer_type = Column(String(50))
    offer_message = Column(Text)
    offer_details = Column(JSON)
    outcome = Column(String(20), default="pending")
    revenue_at_risk = Column(Numeric(10, 2))
    revenue_saved = Column(Numeric(10, 2), default=0)
    message_source = Column(String(20), default="template")
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime)

    user = relationship("User", back_populates="interventions")


class BanditStat(Base):
    __tablename__ = "bandit_stats"
    __table_args__ = (
        UniqueConstraint("vertical", "segment", "offer_type", name="uq_bandit_vertical_segment_offer"),
    )

    id = Column(Integer, primary_key=True)
    vertical = Column(String(30), nullable=False)
    segment = Column(String(50), nullable=False)
    offer_type = Column(String(50), nullable=False)
    alpha = Column(Numeric(10, 2), default=1.0)
    beta_param = Column(Numeric(10, 2), default=1.0)
    total_trials = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
