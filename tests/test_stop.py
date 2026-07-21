import pytest

from travel_planner.stop import Stop


def test_stop_has_generated_stable_id():
    stop = Stop(
        title="Ardèche",
        latitude=44.735,
        longitude=4.599,
    )

    assert stop.stop_id
    assert len(stop.stop_id) == 32


def test_stop_normalizes_values():
    stop = Stop(
        stop_id=" stop-1 ",
        title="  Triglav National Park  ",
        latitude="46.3625",
        longitude="13.8194",
        arrival_date="2026-09-14",
        departure_date="2026-09-17",
        notes="  Bergwandeling en fotografie  ",
        overnight=True,
        favorite=True,
        photo_location=True,
    )

    assert stop.stop_id == "stop-1"
    assert stop.title == "Triglav National Park"
    assert stop.latitude == pytest.approx(46.3625)
    assert stop.longitude == pytest.approx(13.8194)
    assert stop.notes == "Bergwandeling en fotografie"


def test_stop_round_trip_dictionary():
    original = Stop(
        stop_id="stop-1",
        title="Kotor",
        latitude=42.4247,
        longitude=18.7712,
        arrival_date="2026-10-03",
        departure_date="2026-10-05",
        notes="Baai en oude stad",
        overnight=True,
        photo_location=True,
    )

    restored = Stop.from_dict(original.to_dict())

    assert restored == original


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (-90.1, 0),
        (90.1, 0),
        (0, -180.1),
        (0, 180.1),
    ],
)
def test_stop_rejects_invalid_coordinates(
    latitude,
    longitude,
):
    with pytest.raises(ValueError):
        Stop(
            title="Invalid",
            latitude=latitude,
            longitude=longitude,
        )


def test_stop_rejects_empty_title():
    with pytest.raises(ValueError):
        Stop(
            title="   ",
            latitude=45.0,
            longitude=5.0,
        )


def test_stop_rejects_invalid_date():
    with pytest.raises(
        ValueError,
        match="YYYY-MM-DD",
    ):
        Stop(
            title="Invalid date",
            latitude=45.0,
            longitude=5.0,
            arrival_date="14/09/2026",
        )


def test_stop_rejects_departure_before_arrival():
    with pytest.raises(
        ValueError,
        match="before arrival",
    ):
        Stop(
            title="Invalid stay",
            latitude=45.0,
            longitude=5.0,
            arrival_date="2026-09-17",
            departure_date="2026-09-14",
        )
