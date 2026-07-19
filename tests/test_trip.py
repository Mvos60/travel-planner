from pathlib import Path

from travel_planner.trip import Stop, Trip


def test_trip_can_be_saved_and_loaded(tmp_path: Path) -> None:
    path = tmp_path / "test.trip.json"

    trip = Trip(name="Testreis")
    trip.add_stop(
        Stop(
            name="Bohinj",
            latitude=46.2823,
            longitude=13.8582,
            nights=3,
        )
    )

    trip.save(path)

    loaded = Trip.load(path)

    assert loaded.name == "Testreis"
    assert len(loaded.stops) == 1
    assert loaded.stops[0].name == "Bohinj"
    assert loaded.total_nights == 3
