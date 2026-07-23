from travel_planner.stop import Stop
from travel_planner.trip import Trip
from travel_planner.trip_settings import TripSettings
from travel_planner.trip_summary import TripSummary


def make_trip() -> Trip:
    trip = Trip(
        name="Adriatic 2026",
        trip_settings=TripSettings(
            planned_duration_days=60,
        ),
    )
    trip.add_stop(
        Stop(
            name="Ardèche",
            latitude=44.735,
            longitude=4.600,
            nights=2,
        )
    )
    trip.add_stop(
        Stop(
            name="Innsbruck",
            latitude=47.2692,
            longitude=11.4041,
            nights=3,
        )
    )
    return trip


def test_summary_counts_stops_and_nights() -> None:
    summary = TripSummary.from_trip(make_trip())

    assert summary.stop_count == 2
    assert summary.total_nights == 5


def test_summary_reads_planned_duration() -> None:
    summary = TripSummary.from_trip(make_trip())

    assert summary.planned_duration_days == 60
    assert summary.formatted_planned_days == "60 dagen"


def test_unknown_route_metrics_use_dash() -> None:
    summary = TripSummary.from_trip(make_trip())

    assert summary.formatted_distance == "—"
    assert summary.formatted_duration == "—"


def test_summary_formats_route_distance() -> None:
    summary = TripSummary.from_trip(
        make_trip(),
        route_distance_km=1842.4,
    )

    assert summary.formatted_distance == "1.842 km"


def test_summary_formats_route_duration() -> None:
    summary = TripSummary.from_trip(
        make_trip(),
        route_duration_seconds=(28 * 3600) + (15 * 60),
    )

    assert summary.formatted_duration == "28 u 15 min"
