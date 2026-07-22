from travel_planner.route_service import RoutingRequest
from travel_planner.routing_profile import RoutingProfile
from travel_planner.stop import Stop
from travel_planner.travel_preferences import TravelPreferences


def make_stops() -> list[Stop]:
    return [
        Stop(
            name="Ardèche",
            latitude=44.7350,
            longitude=4.6000,
            nights=1,
        ),
        Stop(
            name="Innsbruck",
            latitude=47.2692,
            longitude=11.4041,
            nights=2,
        ),
    ]


def test_routing_request_preserves_stop_order():
    stops = make_stops()

    request = RoutingRequest.create(stops)

    assert request.stops == tuple(stops)


def test_routing_request_uses_camper_profile_by_default():
    request = RoutingRequest.create(make_stops())

    assert request.profile is RoutingProfile.CAMPER


def test_routing_request_creates_default_preferences():
    request = RoutingRequest.create(make_stops())

    assert request.preferences == TravelPreferences()


def test_routing_request_preserves_profile_and_preferences():
    preferences = TravelPreferences(
        avoid_highways=True,
        avoid_tolls=True,
        avoid_ferries=True,
    )

    request = RoutingRequest.create(
        stops=make_stops(),
        profile=RoutingProfile.PHOTOGRAPHER,
        preferences=preferences,
    )

    assert request.profile is RoutingProfile.PHOTOGRAPHER
    assert request.preferences is preferences


def test_routing_request_copies_stop_sequence_to_tuple():
    stops = make_stops()

    request = RoutingRequest.create(stops)

    stops.clear()

    assert len(request.stops) == 2
