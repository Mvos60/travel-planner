from travel_planner.route_service import (
    DirectRouteProvider,
    OSRMRouteProvider,
    RouteProviderCapabilities,
    RouteService,
)


def test_capabilities_default_to_unsupported():
    capabilities = RouteProviderCapabilities()

    assert capabilities.supports_avoid_highways is False
    assert capabilities.supports_avoid_tolls is False
    assert capabilities.supports_avoid_ferries is False
    assert capabilities.supports_vehicle_dimensions is False


def test_direct_provider_has_no_routing_capabilities():
    capabilities = DirectRouteProvider.capabilities

    assert capabilities == RouteProviderCapabilities()


def test_public_osrm_provider_reports_limitations():
    capabilities = OSRMRouteProvider.capabilities

    assert capabilities.supports_avoid_highways is False
    assert capabilities.supports_avoid_tolls is False
    assert capabilities.supports_avoid_ferries is False
    assert capabilities.supports_vehicle_dimensions is False


def test_route_service_exposes_provider_capabilities():
    provider = DirectRouteProvider()
    service = RouteService(provider=provider)

    assert service.capabilities is provider.capabilities


def test_route_service_exposes_custom_provider_capabilities():
    class CustomProvider:
        capabilities = RouteProviderCapabilities(
            supports_avoid_highways=True,
            supports_avoid_tolls=True,
        )

        def calculate_route(self, stops):
            return []

    service = RouteService(provider=CustomProvider())

    assert service.capabilities.supports_avoid_highways is True
    assert service.capabilities.supports_avoid_tolls is True
    assert service.capabilities.supports_avoid_ferries is False
