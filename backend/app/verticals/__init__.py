from app.verticals.b2b_saas import B2BSaaSVertical
from app.verticals.entertainment import EntertainmentVertical
from app.verticals.lifestyle import LifestyleVertical
from app.verticals.marketplace import MarketplaceVertical

_REGISTRY = {
    "b2b_saas":     B2BSaaSVertical(),
    "entertainment": EntertainmentVertical(),
    "lifestyle":    LifestyleVertical(),
    "marketplace":  MarketplaceVertical(),
}

VERTICAL_NAMES = list(_REGISTRY.keys())


def get_vertical_config(vertical_name: str):
    return _REGISTRY.get(vertical_name, _REGISTRY["b2b_saas"])


def list_verticals():
    return [
        {
            "name": v.name,
            "display_name": v.display_name,
            "accent_color": v.accent_color,
            "plan_tiers": v.plan_tiers,
            "segments": v.get_all_segments(),
        }
        for v in _REGISTRY.values()
    ]
