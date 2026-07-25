from travel_planner.route_service import RouteProviderCapabilities
from travel_planner.routing_explanation import (
    RoutingExplanation,
    build_routing_explanation,
)
from travel_planner.travel_preferences import TravelPreferences
from travel_planner.vehicle_dimensions import VehicleDimensions


def test_empty_explanation_uses_clear_defaults() -> None:
    explanation = RoutingExplanation()

    assert explanation.applied_text == "Geen"
    assert explanation.unavailable_text == "Geen"


def test_supported_options_are_reported_as_applied() -> None:
    explanation = build_routing_explanation(
        preferences=TravelPreferences(
            avoid_highways=True,
            avoid_tolls=True,
            avoid_ferries=False,
        ),
        vehicle_dimensions=VehicleDimensions(
            length_m=7.20,
            width_m=2.30,
            height_m=3.05,
            weight_kg=3500,
        ),
        capabilities=RouteProviderCapabilities(
            supports_avoid_highways=True,
            supports_avoid_tolls=True,
            supports_avoid_ferries=True,
            supports_vehicle_dimensions=True,
        ),
    )

    assert explanation.applied == (
        "snelwegen vermijden",
        "tolwegen vermijden",
        "voertuigafmetingen",
    )
    assert explanation.unavailable == ()


def test_unsupported_options_are_reported_separately() -> None:
    explanation = build_routing_explanation(
        preferences=TravelPreferences(
            avoid_highways=True,
            avoid_tolls=False,
            avoid_ferries=True,
        ),
        vehicle_dimensions=VehicleDimensions(height_m=3.05),
        capabilities=RouteProviderCapabilities(),
    )

    assert explanation.applied == ()
    assert explanation.unavailable == (
        "snelwegen vermijden",
        "veerponten vermijden",
        "voertuigafmetingen",
    )


def test_unrequested_options_are_not_reported() -> None:
    explanation = build_routing_explanation(
        preferences=TravelPreferences(),
        vehicle_dimensions=VehicleDimensions(),
        capabilities=RouteProviderCapabilities(
            supports_avoid_highways=True,
            supports_avoid_tolls=True,
            supports_avoid_ferries=True,
            supports_vehicle_dimensions=True,
        ),
    )

    assert explanation.applied_text == "Geen"
    assert explanation.unavailable_text == "Geen"


def test_missing_vehicle_profile_is_safe() -> None:
    explanation = build_routing_explanation(
        preferences=TravelPreferences(),
        vehicle_dimensions=None,
        capabilities=RouteProviderCapabilities(
            supports_vehicle_dimensions=True,
        ),
    )

    assert explanation.applied_text == "Geen"
    assert explanation.unavailable_text == "Geen"


def test_unavailable_tuple_controls_optional_gui_row() -> None:
    empty = RoutingExplanation()
    unavailable = RoutingExplanation(
        unavailable=("voertuigafmetingen",),
    )

    assert bool(empty.unavailable) is False
    assert bool(unavailable.unavailable) is True
