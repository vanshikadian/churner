from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, Dict, Any, List


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    plan_tier: str
    monthly_spend: float
    signup_date: Optional[date] = None
    last_login: Optional[datetime] = None
    sessions_last_30d: int = 0
    sessions_prev_30d: int = 0
    features_used: int = 0
    total_features: int = 8
    support_tickets_last_30d: int = 0
    payment_failures: int = 0
    status: str
    vertical: str = "b2b_saas"
    created_at: Optional[datetime] = None
    risk_score: Optional[float] = None
    segment: Optional[str] = None

    class Config:
        from_attributes = True


class InterventionResponse(BaseModel):
    id: int
    user_id: int
    vertical: str = "b2b_saas"
    churn_risk_score: float
    risk_factors: Optional[Dict[str, float]] = {}
    segment: str
    offer_type: str
    offer_message: str
    offer_details: Optional[Dict[str, Any]] = None
    outcome: str
    revenue_at_risk: float
    revenue_saved: float
    message_source: str
    created_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InterventionOutcomeRequest(BaseModel):
    outcome: str  # 'accepted' or 'rejected'


class SegmentStats(BaseModel):
    count: int
    retained: int
    revenue_saved: float


class OfferTypeStats(BaseModel):
    count: int
    acceptance_rate: float


class RecentIntervention(BaseModel):
    id: int
    user_name: str
    segment: str
    offer_type: str
    outcome: str
    created_at: Optional[datetime] = None


class BanditOfferStat(BaseModel):
    offer_type: str
    alpha: float
    beta: float
    total_trials: int
    estimated_success_rate: float
    confidence: str  # 'low', 'medium', 'high'


class AnalyticsResponse(BaseModel):
    vertical: str = "all"
    total_users: int
    active_users: int
    total_interventions: int
    retention_rate: float
    total_revenue_at_risk: float
    total_revenue_saved: float
    by_segment: Dict[str, SegmentStats]
    by_offer_type: Dict[str, OfferTypeStats]
    recent_interventions: List[RecentIntervention]
    bandit_state: Dict[str, List[Dict[str, Any]]] = {}
