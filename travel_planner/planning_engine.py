"""Automatic sequential trip-planning calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from travel_planner.stop import Stop
from travel_planner.trip import Trip


@dataclass(frozen=True, slots=True)
class PlannedStop:
    """Calculated planning information for one trip stop."""

    stop: Stop
    start_day: int
    end_day: int
    departure_day: int
    arrival_date: date | None
    departure_date: date | None

    @property
    def day_label(self) -> str:
        """Return a compact human-readable day range."""

        if self.start_day == self.end_day:
            return f"Dag {self.start_day}"

        return f"Dag {self.start_day}–{self.end_day}"

    @property
    def date_label(self) -> str | None:
        """Return a compact ISO date range when dates are available."""

        if self.arrival_date is None:
            return None

        final_overnight_date = (
            self.departure_date - timedelta(days=1)
            if self.departure_date is not None
            else self.arrival_date
        )

        if self.arrival_date == final_overnight_date:
            return self.arrival_date.isoformat()

        return (
            f"{self.arrival_date.isoformat()}"
            f" → {final_overnight_date.isoformat()}"
        )


@dataclass(frozen=True, slots=True)
class PlanningResult:
    """Complete sequential planning result for one trip."""

    stops: tuple[PlannedStop, ...]
    total_nights: int
    total_days: int
    planned_start_date: date | None
    planned_end_date: date | None

    def for_stop(self, stop: Stop) -> PlannedStop | None:
        """Return planning information for a specific stop instance."""

        for planned_stop in self.stops:
            if planned_stop.stop is stop:
                return planned_stop

        return None

    def for_stop_id(self, stop_id: str) -> PlannedStop | None:
        """Return planning information for a stable stop identifier."""

        for planned_stop in self.stops:
            if planned_stop.stop.stop_id == stop_id:
                return planned_stop

        return None


def plan_trip(trip: Trip) -> PlanningResult:
    """
    Calculate a sequential plan from stop order and night counts.

    A stop starts on the current journey day and occupies ``nights``
    overnight dates. Its departure day is therefore the next stop's
    start day.

    Existing manually entered stop dates are not changed.
    """

    if not isinstance(trip, Trip):
        raise TypeError("Planning requires a Trip object.")

    planned_start_date = _parse_planned_start_date(trip)
    planned_stops: list[PlannedStop] = []

    current_day = 1

    for stop in trip.stops:
        nights = stop.nights

        if nights < 1:
            raise ValueError(
                f"Stop {stop.title!r} must contain at least one night."
            )

        start_day = current_day
        end_day = start_day + nights - 1
        departure_day = start_day + nights

        arrival_date = None
        departure_date = None

        if planned_start_date is not None:
            arrival_date = planned_start_date + timedelta(
                days=start_day - 1
            )
            departure_date = planned_start_date + timedelta(
                days=departure_day - 1
            )

        planned_stops.append(
            PlannedStop(
                stop=stop,
                start_day=start_day,
                end_day=end_day,
                departure_day=departure_day,
                arrival_date=arrival_date,
                departure_date=departure_date,
            )
        )

        current_day = departure_day

    total_nights = sum(
        planned_stop.stop.nights
        for planned_stop in planned_stops
    )

    total_days = (
        total_nights + 1
        if planned_stops
        else 0
    )

    planned_end_date = None

    if (
        planned_start_date is not None
        and planned_stops
    ):
        planned_end_date = (
            planned_start_date
            + timedelta(days=total_nights)
        )

    return PlanningResult(
        stops=tuple(planned_stops),
        total_nights=total_nights,
        total_days=total_days,
        planned_start_date=planned_start_date,
        planned_end_date=planned_end_date,
    )


def _parse_planned_start_date(
    trip: Trip,
) -> date | None:
    """Return the configured trip start date as a date object."""

    value = trip.trip_settings.planned_start_date

    if value is None:
        return None

    return date.fromisoformat(value)
