import json
from pathlib import Path

import pytest

from travel_planner.stop import Stop
from travel_planner.trip import Trip


def test_trip_can_be_saved_and_loaded(
    tmp_path: Path,
) -> None:
    path = tmp_path / "test.trip.json"

    trip = Trip(name="Testreis")
    trip.add_stop(
        Stop(
            title="Bohinj",
            latitude=46.2823,
            longitude=13.8582,
            nights=3,
        )
    )

    trip.save(path)

    loaded = Trip.load(path)

    assert loaded.name == "Testreis"
    assert len(loaded.stops) == 1
    assert loaded.stops[0].title == "Bohinj"
    assert loaded.stops[0].name == "Bohinj"
    assert loaded.total_nights == 3


def test_trip_saves_canonical_stop_format(
    tmp_path: Path,
) -> None:
    path = tmp_path / "canonical.trip.json"

    trip = Trip(name="Canonical")
    trip.add_stop(
        Stop(
            stop_id="stop-1",
            name="Kotor",
            latitude=42.4247,
            longitude=18.7712,
            nights=2,
        )
    )

    trip.save(path)

    data = json.loads(
        path.read_text(encoding="utf-8")
    )
    saved_stop = data["stops"][0]

    assert saved_stop["stop_id"] == "stop-1"
    assert saved_stop["title"] == "Kotor"
    assert saved_stop["nights"] == 2
    assert "name" not in saved_stop


def test_legacy_trip_stop_is_migrated(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy.trip.json"
    path.write_text(
        json.dumps(
            {
                "name": "Oude reis",
                "stops": [
                    {
                        "name": "Ljubljana",
                        "latitude": 46.0569,
                        "longitude": 14.5058,
                        "nights": 2,
                        "notes": "Oude gegevens",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    trip = Trip.load(path)

    assert len(trip.stops) == 1

    stop = trip.stops[0]

    assert isinstance(stop, Stop)
    assert stop.stop_id
    assert stop.title == "Ljubljana"
    assert stop.name == "Ljubljana"
    assert stop.nights == 2
    assert stop.notes == "Oude gegevens"


def test_trip_rejects_non_stop_object() -> None:
    trip = Trip(name="Invalid")

    with pytest.raises(
        TypeError,
        match="Stop objects",
    ):
        trip.add_stop("Bohinj")


def test_trip_rejects_non_list_stop_data(
    tmp_path: Path,
) -> None:
    path = tmp_path / "invalid.trip.json"
    path.write_text(
        json.dumps(
            {
                "name": "Invalid",
                "stops": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="stored as a list",
    ):
        Trip.load(path)


def test_trip_saves_and_loads_avoid_motorways(
    tmp_path: Path,
) -> None:
    path = tmp_path / "route-preferences.trip.json"
    trip = Trip(
        name="Routevoorkeuren",
        avoid_motorways=True,
    )

    trip.save(path)
    loaded_trip = Trip.load(path)

    assert loaded_trip.avoid_motorways is True


def test_old_trip_without_route_preferences_still_loads(
    tmp_path: Path,
) -> None:
    path = tmp_path / "old.trip.json"
    path.write_text(
        json.dumps(
            {
                "name": "Oude reis",
                "stops": [],
            }
        ),
        encoding="utf-8",
    )

    trip = Trip.load(path)

    assert trip.avoid_motorways is False


def test_trip_saves_and_loads_routing_profile(
    tmp_path: Path,
) -> None:
    from travel_planner.routing_profile import (
        RoutingProfile,
    )

    path = tmp_path / "profile.trip.json"
    trip = Trip(
        name="Photography trip",
        routing_profile=(
            RoutingProfile.PHOTOGRAPHER
        ),
    )

    trip.save(path)
    loaded_trip = Trip.load(path)

    assert (
        loaded_trip.routing_profile
        is RoutingProfile.PHOTOGRAPHER
    )


def test_old_trip_defaults_to_camper_profile(
    tmp_path: Path,
) -> None:
    from travel_planner.routing_profile import (
        RoutingProfile,
    )

    path = tmp_path / "old-profile.trip.json"
    path.write_text(
        json.dumps(
            {
                "name": "Oude reis",
                "stops": [],
            }
        ),
        encoding="utf-8",
    )

    trip = Trip.load(path)

    assert (
        trip.routing_profile
        is RoutingProfile.CAMPER
    )


def test_trip_saves_and_loads_travel_preferences(
    tmp_path: Path,
) -> None:
    from travel_planner.travel_preferences import (
        TravelPreferences,
    )

    path = tmp_path / "preferences.trip.json"
    trip = Trip(
        name="Custom route",
        travel_preferences=TravelPreferences(
            avoid_highways=True,
            avoid_tolls=True,
            avoid_ferries=False,
        ),
    )

    trip.save(path)
    loaded_trip = Trip.load(path)

    assert loaded_trip.travel_preferences == (
        TravelPreferences(
            avoid_highways=True,
            avoid_tolls=True,
            avoid_ferries=False,
        )
    )


def test_old_trip_defaults_to_empty_travel_preferences(
    tmp_path: Path,
) -> None:
    from travel_planner.travel_preferences import (
        TravelPreferences,
    )

    path = tmp_path / "old-trip.trip.json"
    path.write_text(
        json.dumps(
            {
                "name": "Oude reis",
                "stops": [],
                "routing_profile": "camper",
            }
        ),
        encoding="utf-8",
    )

    trip = Trip.load(path)

    assert (
        trip.travel_preferences
        == TravelPreferences()
    )


def test_old_trip_defaults_to_sixty_day_guideline(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy-duration.trip.json"
    path.write_text(
        json.dumps(
            {
                "name": "Oude reis",
                "stops": [],
            }
        ),
        encoding="utf-8",
    )

    trip = Trip.load(path)

    assert trip.trip_settings.planned_duration_days == 60
    assert trip.trip_settings.shift_following_dates is True


def test_trip_saves_and_loads_trip_settings(
    tmp_path: Path,
) -> None:
    from travel_planner.trip_settings import TripSettings

    path = tmp_path / "settings.trip.json"
    trip = Trip(
        name="Lange reis",
        trip_settings=TripSettings(
            planned_duration_days=75,
            planned_start_date="2026-09-14",
            shift_following_dates=False,
        ),
    )

    trip.save(path)
    loaded = Trip.load(path)

    assert loaded.trip_settings.planned_duration_days == 75
    assert (
        loaded.trip_settings.planned_start_date
        == "2026-09-14"
    )
    assert loaded.trip_settings.shift_following_dates is False


def test_trip_calculates_calendar_period() -> None:
    trip = Trip(name="Adriatic")

    trip.add_stop(
        Stop(
            title="Salzburg",
            latitude=47.8095,
            longitude=13.0550,
            arrival_date="2026-09-14",
            departure_date="2026-09-17",
        )
    )
    trip.add_stop(
        Stop(
            title="Bohinj",
            latitude=46.2823,
            longitude=13.8582,
            arrival_date="2026-09-18",
            departure_date="2026-09-25",
        )
    )

    assert trip.start_date.isoformat() == "2026-09-14"
    assert trip.end_date.isoformat() == "2026-09-25"
    assert trip.total_days == 12
    assert trip.remaining_days == 48
    assert trip.is_overplanned is False


def test_trip_can_exceed_duration_guideline() -> None:
    trip = Trip(name="Flexibele reis")

    trip.add_stop(
        Stop(
            title="Begin",
            latitude=45.0,
            longitude=5.0,
            arrival_date="2026-09-01",
            departure_date="2026-11-05",
        )
    )

    assert trip.total_days == 66
    assert trip.remaining_days == -6
    assert trip.is_overplanned is True
    assert "6 dagen langer" in trip.planning_summary


def test_trip_without_dates_remains_supported() -> None:
    trip = Trip(name="Vrije reis")
    trip.add_stop(
        Stop(
            title="Ergens",
            latitude=45.0,
            longitude=5.0,
            nights=3,
        )
    )

    assert trip.start_date is None
    assert trip.end_date is None
    assert trip.total_days is None
    assert trip.remaining_days is None
    assert trip.is_overplanned is False
    assert trip.planning_summary == (
        "3 nachten gepland  •  richtwaarde 60 dagen"
    )


def test_trip_reports_partially_completed_dates() -> None:
    trip = Trip(name="Deels gepland")

    trip.add_stop(
        Stop(
            title="Eerste",
            latitude=45.0,
            longitude=5.0,
            arrival_date="2026-09-01",
            departure_date="2026-09-03",
        )
    )
    trip.add_stop(
        Stop(
            title="Later bepalen",
            latitude=46.0,
            longitude=6.0,
            nights=2,
        )
    )

    assert trip.has_partial_dates is True
    assert "datums gedeeltelijk ingevuld" in (
        trip.planning_summary
    )
