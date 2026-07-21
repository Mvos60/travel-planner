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
        nights=3,
        overnight=True,
        favorite=True,
        photo_location=True,
    )

    assert stop.stop_id == "stop-1"
    assert stop.title == "Triglav National Park"
    assert stop.latitude == pytest.approx(46.3625)
    assert stop.longitude == pytest.approx(13.8194)
    assert stop.notes == "Bergwandeling en fotografie"
    assert stop.nights == 3


def test_stop_round_trip_dictionary():
    original = Stop(
        stop_id="stop-1",
        title="Kotor",
        latitude=42.4247,
        longitude=18.7712,
        arrival_date="2026-10-03",
        departure_date="2026-10-05",
        notes="Baai en oude stad",
        nights=2,
        overnight=True,
        photo_location=True,
    )

    restored = Stop.from_dict(original.to_dict())

    assert restored == original


def test_legacy_name_constructor_is_supported():
    stop = Stop(
        name="Bohinj",
        latitude=46.2823,
        longitude=13.8582,
        nights=3,
    )

    assert stop.title == "Bohinj"
    assert stop.name == "Bohinj"
    assert stop.nights == 3


def test_name_is_alias_for_title():
    stop = Stop(
        title="Kotor",
        latitude=42.4247,
        longitude=18.7712,
    )

    stop.name = "Perast"

    assert stop.name == "Perast"
    assert stop.title == "Perast"


def test_title_and_name_must_match_when_both_are_given():
    with pytest.raises(
        ValueError,
        match="do not match",
    ):
        Stop(
            title="Kotor",
            name="Perast",
            latitude=42.4247,
            longitude=18.7712,
        )


def test_matching_title_and_name_are_allowed():
    stop = Stop(
        title="  Kotor ",
        name="Kotor",
        latitude=42.4247,
        longitude=18.7712,
    )

    assert stop.title == "Kotor"
    assert stop.name == "Kotor"


def test_legacy_dictionary_can_be_loaded():
    stop = Stop.from_dict(
        {
            "name": "Ljubljana",
            "latitude": 46.0569,
            "longitude": 14.5058,
            "nights": 2,
            "notes": "",
        }
    )

    assert stop.stop_id
    assert stop.title == "Ljubljana"
    assert stop.name == "Ljubljana"
    assert stop.nights == 2
    assert stop.notes is None


def test_current_dictionary_without_nights_defaults_to_one():
    stop = Stop.from_dict(
        {
            "stop_id": "stop-1",
            "title": "Ardèche",
            "latitude": 44.735,
            "longitude": 4.599,
        }
    )

    assert stop.nights == 1


def test_stop_dictionary_uses_canonical_title():
    stop = Stop(
        name="Innsbruck",
        latitude=47.2692,
        longitude=11.4041,
        nights=2,
    )

    data = stop.to_dict()

    assert data["title"] == "Innsbruck"
    assert "name" not in data
    assert data["nights"] == 2


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


@pytest.mark.parametrize(
    "nights",
    [
        -1,
        1.5,
        True,
        "invalid",
    ],
)
def test_stop_rejects_invalid_nights(nights):
    expected_error = (
        ValueError
        if nights == -1
        else TypeError
    )

    with pytest.raises(expected_error):
        Stop(
            title="Invalid stay",
            latitude=45.0,
            longitude=5.0,
            nights=nights,
        )
