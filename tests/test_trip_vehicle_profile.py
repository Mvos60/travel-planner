import json
from pathlib import Path

from travel_planner.trip import Trip


def test_trip_defaults_to_no_vehicle_profile() -> None:
    trip = Trip(name="Testreis")

    assert trip.vehicle_profile_id is None


def test_trip_saves_and_loads_vehicle_profile(
    tmp_path: Path,
) -> None:
    path = tmp_path / "trip.json"

    trip = Trip(
        name="Camperreis",
        vehicle_profile_id="hymer-mlt",
    )
    trip.save(path)

    restored = Trip.load(path)

    assert restored.vehicle_profile_id == "hymer-mlt"


def test_saved_trip_contains_only_vehicle_profile_reference(
    tmp_path: Path,
) -> None:
    path = tmp_path / "trip.json"

    Trip(
        name="Camperreis",
        vehicle_profile_id="hymer-mlt",
    ).save(path)

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert data["vehicle_profile_id"] == "hymer-mlt"
    assert "vehicle_profile" not in data


def test_old_trip_defaults_to_no_vehicle_profile(
    tmp_path: Path,
) -> None:
    path = tmp_path / "old-trip.json"

    path.write_text(
        json.dumps(
            {
                "name": "Oude reis",
                "stops": [],
                "routing_profile": "camper",
                "travel_preferences": {},
                "avoid_motorways": False,
            }
        ),
        encoding="utf-8",
    )

    restored = Trip.load(path)

    assert restored.vehicle_profile_id is None
