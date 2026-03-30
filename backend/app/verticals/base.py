from abc import ABC, abstractmethod


class VerticalConfig(ABC):
    name: str
    display_name: str
    accent_color: str  # tailwind color name: emerald, purple, green, orange
    plan_tiers: dict   # tier_name -> monthly_price
    event_types: list
    primary_engagement_event: str = "feature_use"  # event type used for feature_adoption
    support_event: str = "support_ticket"           # event type used for support intensity

    @abstractmethod
    def classify_segment(self, features: dict, user) -> str:
        """Return segment name based on computed feature dict and user object."""
        pass

    @abstractmethod
    def get_available_offers(self, segment: str) -> list:
        """Return list of possible offer_type strings for this segment."""
        pass

    @abstractmethod
    def get_offer_details(self, offer_type: str, user) -> dict:
        """Return offer details dict for the given offer type and user."""
        pass

    @abstractmethod
    def get_templates(self, segment: str) -> list:
        """Return message template strings for this segment."""
        pass

    @abstractmethod
    async def compute_extra_features(self, redis, user_id: int, now: float) -> dict:
        """Compute vertical-specific extra features from Redis sorted sets."""
        pass

    @abstractmethod
    def get_seed_config(self) -> dict:
        """Return archetype config for synthetic data generation."""
        pass

    @abstractmethod
    def get_all_segments(self) -> list:
        """Return list of all segment names for this vertical."""
        pass
