from pathlib import Path

from travel_planner.context import TravelPlannerContext
from travel_planner.routing_profile import RoutingProfile
from travel_planner.settings import Settings
from travel_planner.stop import Stop
from travel_planner.trip import Trip
from travel_planner.vehicle_profile import VehicleProfile


def _context(
    tmp_path: Path,
) -> TravelPlannerContext:
    return TravelPlannerContext.create_default(
        settings_path=tmp_path / "settings.json",
        vehicle_profiles_path=(
            tmp_path / "vehicle_profiles.json"
        ),
        stops_path=tmp_path / "stops.json",
    )


def test_default_context_loads_default_settings(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)

    assert context.settings == Settings()
    assert context.current_trip.name == "Nieuwe reis"
    assert (
        context.current_trip.routing_profile
        is RoutingProfile.CAMPER
    )


def test_default_context_starts_with_empty_stops(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)

    assert context.stops == []


def test_context_loads_saved_settings(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)

    context.settings.font_scale = 1.25
    context.settings.default_route_profile = (
        "photographer"
    )
    context.settings_repository.save(
        context.settings
    )

    restored = _context(tmp_path)

    assert restored.settings.font_scale == 1.25
    assert (
        restored.settings.default_route_profile
        == "photographer"
    )


def test_context_exposes_loaded_vehicle_profiles(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)

    profile = VehicleProfile(
        profile_id="hymer-mlt",
        name="Hymer ML-T",
        length_m=7.20,
    )

    context.vehicle_profile_repository.add(profile)
    context.vehicle_profile_repository.save()

    restored = _context(tmp_path)

    assert restored.vehicle_profiles == [profile]


def test_context_exposes_loaded_stops(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)

    first_stop = Stop(
        stop_id="stop-1",
        title="Ardèche",
        latitude=44.735,
        longitude=4.599,
    )
    second_stop = Stop(
        stop_id="stop-2",
        title="Triglav National Park",
        latitude=46.3625,
        longitude=13.8194,
        overnight=True,
        photo_location=True,
    )

    context.stop_repository.add(first_stop)
    context.stop_repository.add(second_stop)
    context.stop_repository.save()

    restored = _context(tmp_path)

    assert restored.stops == [
        first_stop,
        second_stop,
    ]


def test_context_can_replace_current_trip(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    replacement = Trip(name="Nieuwe reis")

    context.replace_trip(replacement)

    assert context.current_trip is replacement
