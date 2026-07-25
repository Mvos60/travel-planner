import json
from pathlib import Path

from travel_planner.route_service import OSRMRouteProvider
from travel_planner.trip import Trip


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_trip_has_one_highway_preference_source() -> None:
    trip = Trip(name="Test")

    assert hasattr(trip, "travel_preferences")
    assert hasattr(trip.travel_preferences, "avoid_highways")
    assert not hasattr(trip, "avoid_motorways")


def test_trip_save_omits_legacy_avoid_motorways(
    tmp_path: Path,
) -> None:
    path = tmp_path / "clean.trip.json"
    trip = Trip(name="Clean")
    trip.travel_preferences.avoid_highways = True

    trip.save(path)

    data = json.loads(path.read_text(encoding="utf-8"))

    assert "avoid_motorways" not in data
    assert data["travel_preferences"]["avoid_highways"] is True


def test_legacy_avoid_motorways_migrates_to_preferences(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy.trip.json"
    path.write_text(
        json.dumps(
            {
                "name": "Legacy",
                "stops": [],
                "avoid_motorways": True,
            }
        ),
        encoding="utf-8",
    )

    trip = Trip.load(path)

    assert trip.travel_preferences.avoid_highways is True


def test_current_preferences_override_legacy_value(
    tmp_path: Path,
) -> None:
    path = tmp_path / "current.trip.json"
    path.write_text(
        json.dumps(
            {
                "name": "Current",
                "stops": [],
                "travel_preferences": {
                    "avoid_highways": False,
                    "avoid_tolls": False,
                    "avoid_ferries": False,
                },
                "avoid_motorways": True,
            }
        ),
        encoding="utf-8",
    )

    trip = Trip.load(path)

    assert trip.travel_preferences.avoid_highways is False


def test_osrm_has_no_legacy_avoid_motorways_argument() -> None:
    import inspect

    parameters = inspect.signature(
        OSRMRouteProvider.__init__
    ).parameters

    assert "avoid_motorways" not in parameters


def test_window_contains_no_legacy_motorway_controls() -> None:
    source = (
        PROJECT_ROOT
        / "travel_planner"
        / "window.py"
    ).read_text(encoding="utf-8")

    assert "avoid_motorways_check" not in source
    assert "_on_avoid_motorways_toggled" not in source
    assert "trip.avoid_motorways" not in source


def test_window_passes_trip_preferences_to_route_service() -> None:
    source = (
        PROJECT_ROOT
        / "travel_planner"
        / "window.py"
    ).read_text(encoding="utf-8")

    assert "self.route_service.calculate_route(" in source
    assert "profile=self.trip.routing_profile," in source
    assert "preferences=self.trip.travel_preferences," in source
    assert "vehicle_dimensions=(" in source
