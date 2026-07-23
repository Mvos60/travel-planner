from travel_planner.route_provider_manager import (
    RouteProviderManager,
)
from travel_planner.route_service import (
    OpenRouteServiceProvider,
)


def test_provider_settings_can_update_manager():
    manager = RouteProviderManager()

    manager.set_openrouteservice_api_key(
        "dialog-test-key"
    )
    manager.set_active_provider(
        "openrouteservice"
    )

    provider = manager.provider(
        "openrouteservice"
    )

    assert (
        manager.active_provider_id
        == "openrouteservice"
    )
    assert isinstance(
        provider,
        OpenRouteServiceProvider,
    )
    assert provider.api_key == "dialog-test-key"


def test_provider_settings_can_clear_api_key():
    manager = RouteProviderManager(
        openrouteservice_api_key="old-key"
    )

    manager.set_openrouteservice_api_key("")

    provider = manager.provider(
        "openrouteservice"
    )

    assert isinstance(
        provider,
        OpenRouteServiceProvider,
    )
    assert provider.api_key == ""


def test_provider_settings_strip_api_key_whitespace():
    manager = RouteProviderManager()

    manager.set_openrouteservice_api_key(
        "  trimmed-key  "
    )

    provider = manager.provider(
        "openrouteservice"
    )

    assert isinstance(
        provider,
        OpenRouteServiceProvider,
    )
    assert provider.api_key == "trimmed-key"
