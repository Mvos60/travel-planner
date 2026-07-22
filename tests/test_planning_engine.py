from datetime import date

import pytest

from travel_planner.planning_engine import plan_trip
from travel_planner.stop import Stop
from travel_planner.trip import Trip
from travel_planner.trip_settings import TripSettings


def _stop(
    title: str,
    nights: int,
) -> Stop:
    return Stop(
        title=title,
        latitude=50.0,
        longitude=5.0,
        nights=nights,
    )


def test_empty_trip_returns_empty_plan() -> None:
    trip = Trip(name="Lege reis")

    result = plan_trip(trip)

    assert result.stops == ()
    assert result.total_nights == 0
    assert result.total_days == 0
    assert result.planned_start_date is None
    assert result.planned_end_date is None


def test_plan_trip_assigns_sequential_day_ranges() -> None:
    first = _stop("Bad Aibling", 1)
    second = _stop("Caltagirone", 1)
    third = _stop("Saint-Jean-de-Galaure", 2)
    fourth = _stop("Viviers-lès-Lavaur", 3)

    trip = Trip(
        name="11",
        stops=[
            first,
            second,
            third,
            fourth,
        ],
    )

    result = plan_trip(trip)

    assert result.total_nights == 7
    assert result.total_days == 8

    assert result.stops[0].start_day == 1
    assert result.stops[0].end_day == 1
    assert result.stops[0].departure_day == 2
    assert result.stops[0].day_label == "Dag 1"

    assert result.stops[1].start_day == 2
    assert result.stops[1].end_day == 2
    assert result.stops[1].departure_day == 3
    assert result.stops[1].day_label == "Dag 2"

    assert result.stops[2].start_day == 3
    assert result.stops[2].end_day == 4
    assert result.stops[2].departure_day == 5
    assert result.stops[2].day_label == "Dag 3–4"

    assert result.stops[3].start_day == 5
    assert result.stops[3].end_day == 7
    assert result.stops[3].departure_day == 8
    assert result.stops[3].day_label == "Dag 5–7"


def test_plan_trip_calculates_dates_from_start_date() -> None:
    trip = Trip(
        name="Adriatic 2026",
        stops=[
            _stop("Bad Aibling", 1),
            _stop("Caltagirone", 2),
        ],
        trip_settings=TripSettings(
            planned_duration_days=60,
            planned_start_date="2026-09-12",
            shift_following_dates=True,
        ),
    )

    result = plan_trip(trip)

    first = result.stops[0]
    second = result.stops[1]

    assert result.planned_start_date == date(2026, 9, 12)
    assert result.planned_end_date == date(2026, 9, 15)

    assert first.arrival_date == date(2026, 9, 12)
    assert first.departure_date == date(2026, 9, 13)
    assert first.date_label == "2026-09-12"

    assert second.arrival_date == date(2026, 9, 13)
    assert second.departure_date == date(2026, 9, 15)
    assert second.date_label == "2026-09-13 → 2026-09-14"


def test_plan_result_can_find_stop_by_instance_and_id() -> None:
    stop = _stop("Ardèche", 2)
    trip = Trip(
        name="Test",
        stops=[stop],
    )

    result = plan_trip(trip)

    assert result.for_stop(stop) is result.stops[0]
    assert result.for_stop_id(stop.stop_id) is result.stops[0]
    assert result.for_stop_id("onbekend") is None


def test_plan_trip_does_not_modify_manual_stop_dates() -> None:
    stop = Stop(
        title="Handmatige stop",
        latitude=50.0,
        longitude=5.0,
        nights=2,
        arrival_date="2026-10-01",
        departure_date="2026-10-03",
    )

    trip = Trip(
        name="Test",
        stops=[stop],
        trip_settings=TripSettings(
            planned_start_date="2026-09-12",
        ),
    )

    plan_trip(trip)

    assert stop.arrival_date == "2026-10-01"
    assert stop.departure_date == "2026-10-03"


def test_plan_trip_rejects_non_trip_object() -> None:
    with pytest.raises(
        TypeError,
        match="Planning requires a Trip object",
    ):
        plan_trip(object())  # type: ignore[arg-type]
