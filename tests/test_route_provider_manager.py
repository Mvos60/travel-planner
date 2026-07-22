import pytest

from travel_planner.route_provider_manager import (
    RouteProviderManager,
)
from travel_planner.route_service import (
    DirectRouteProvider,
    OSRMRouteProvider,
)


def test_manager_uses_osrm_demo_by_default():
    manager = RouteProviderManager()

    assert manager.active_provider_id == "osrm-demo"
    assert isinstance(
        manager.active_provider,
        OSRMRouteProvider,
    )


def test_manager_lists_available_providers():
    manager = RouteProviderManager()

    assert manager.available_provider_ids() == [
        "osrm-demo",
    ]


def test_manager_rejects_unknown_provider():
    manager = RouteProviderManager()

    with pytest.raises(KeyError):
        manager.set_active_provider("unknown")


def test_manager_supplies_direct_fallback_provider():
    manager = RouteProviderManager()

    assert isinstance(
        manager.fallback_provider,
        DirectRouteProvider,
    )


def test_setting_active_provider_keeps_registered_provider():
    manager = RouteProviderManager()

    manager.set_active_provider("osrm-demo")

    assert manager.active_provider_id == "osrm-demo"
    assert isinstance(
        manager.active_provider,
        OSRMRouteProvider,
    )
