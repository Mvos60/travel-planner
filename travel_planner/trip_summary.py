"""Read-only trip summary calculations."""

from __future__ import annotations

from dataclasses import dataclass

from travel_planner.trip import Trip


@dataclass(frozen=True)
class TripSummary:
    """Stable presentation data for one trip."""

    stop_count: int
    total_nights: int
    planned_duration_days: int | None
    route_distance_km: float | None = None
    route_duration_seconds: int | None = None

    @classmethod
    def from_trip(
        cls,
        trip: Trip,
        *,
        route_distance_km: float | None = None,
        route_duration_seconds: int | None = None,
    ) -> "TripSummary":
        return cls(
            stop_count=len(trip.stops),
            total_nights=trip.total_nights,
            planned_duration_days=(
                trip.trip_settings.planned_duration_days
            ),
            route_distance_km=route_distance_km,
            route_duration_seconds=route_duration_seconds,
        )

    @property
    def formatted_distance(self) -> str:
        if self.route_distance_km is None:
            return "—"

        rounded = round(self.route_distance_km)
        return f"{rounded:,}".replace(",", ".") + " km"

    @property
    def formatted_duration(self) -> str:
        if self.route_duration_seconds is None:
            return "—"

        total_minutes = round(self.route_duration_seconds / 60)
        hours, minutes = divmod(total_minutes, 60)

        if hours == 0:
            return f"{minutes} min"

        if minutes == 0:
            return f"{hours} u"

        return f"{hours} u {minutes} min"

    @property
    def formatted_planned_days(self) -> str:
        if self.planned_duration_days is None:
            return "—"

        return f"{self.planned_duration_days} dagen"
