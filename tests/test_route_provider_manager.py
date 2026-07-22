import pytest

from travel_planner.route_provider_manager import (
    RouteProviderManager,
)
from travel_planner.route_service import (
    DirectRouteProvider,
    OpenRouteServiceProvider,
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
        "openrouteservice",
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


def test_manager_returns_provider_display_name():
    manager = RouteProviderManager()

    assert (
        manager.provider_display_name("osrm-demo")
        == "OSRM Demo"
    )


def test_manager_rejects_display_name_for_unknown_provider():
    manager = RouteProviderManager()

    with pytest.raises(KeyError):
        manager.provider_display_name("unknown")


def test_manager_can_select_openrouteservice():
    manager = RouteProviderManager()

    manager.set_active_provider("openrouteservice")

    assert manager.active_provider_id == (
        "openrouteservice"
    )
    assert isinstance(
        manager.active_provider,
        OpenRouteServiceProvider,
    )


def test_manager_returns_openrouteservice_display_name():
    manager = RouteProviderManager()

    assert (
        manager.provider_display_name(
            "openrouteservice"
        )
        == "OpenRouteService"
    )


def test_manager_restores_selected_provider():
    manager = RouteProviderManager(
        active_provider_id="openrouteservice"
    )

    assert (
        manager.active_provider_id
        == "openrouteservice"
    )

    assert isinstance(
        manager.active_provider,
        OpenRouteServiceProvider,
    )


def test_manager_uses_default_for_unknown_initial_provider():
    manager = RouteProviderManager(
        active_provider_id="unknown-provider"
    )

    assert manager.active_provider_id == "osrm-demo"


def test_manager_passes_saved_api_key_to_ors():
    manager = RouteProviderManager(
        openrouteservice_api_key="saved-api-key"
    )

    provider = manager.provider(
        "openrouteservice"
    )

    assert isinstance(
        provider,
        OpenRouteServiceProvider,
    )
    assert provider.api_key == "saved-api-key"


def test_manager_updates_openrouteservice_api_key():
    manager = RouteProviderManager()

    manager.set_openrouteservice_api_key(
        "new-api-key"
    )

    provider = manager.provider(
        "openrouteservice"
    )

    assert isinstance(
        provider,
        OpenRouteServiceProvider,
    )
    assert provider.api_key == "new-api-key"

