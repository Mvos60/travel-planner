from travel_planner.route_service import RouteService
from travel_planner.vehicle_dimensions import VehicleDimensions

from tests.test_route_service import make_stops


def test_route_service_passes_vehicle_dimensions_to_provider() -> None:
    captured_request = None

    class Provider:
        capabilities = type(
            "Capabilities",
            (),
            {
                "supports_avoid_highways": False,
                "supports_avoid_tolls": False,
                "supports_avoid_ferries": False,
                "supports_vehicle_dimensions": True,
            },
        )()
        last_route_metrics = None

        def calculate_route(self, request):
            nonlocal captured_request
            captured_request = request
            return []

    dimensions = VehicleDimensions(
        length_m=7.20,
        width_m=2.30,
        height_m=3.05,
        weight_kg=3500,
    )

    service = RouteService(provider=Provider())
    service.calculate_route(
        make_stops(),
        vehicle_dimensions=dimensions,
    )

    assert captured_request is not None
    assert captured_request.vehicle_dimensions is dimensions
