from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from travel_planner.routing_profile import RoutingProfile
from travel_planner.stop import Stop
from travel_planner.travel_preferences import TravelPreferences
from travel_planner.trip_settings import TripSettings


@dataclass
class Trip:
    """A planned journey containing an ordered collection of stops."""

    name: str
    stops: list[Stop] = field(default_factory=list)
    routing_profile: RoutingProfile = RoutingProfile.CAMPER
    travel_preferences: TravelPreferences = field(
        default_factory=TravelPreferences
    )
    trip_settings: TripSettings = field(
        default_factory=TripSettings
    )
    vehicle_profile_id: str | None = None
    avoid_motorways: bool = False

    def add_stop(self, stop: Stop) -> None:
        """Append one stop to the trip."""

        if not isinstance(stop, Stop):
            raise TypeError(
                "A trip can only contain Stop objects."
            )

        self.stops.append(stop)

    def save(self, path: Path) -> None:
        """Save the trip as JSON."""

        data = {
            "name": self.name,
            "stops": [
                stop.to_dict()
                for stop in self.stops
            ],
            "routing_profile": self.routing_profile.value,
            "travel_preferences": (
                self.travel_preferences.to_dict()
            ),
            "trip_settings": self.trip_settings.to_dict(),
            "vehicle_profile_id": self.vehicle_profile_id,
            "avoid_motorways": self.avoid_motorways,
        }

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "Trip":
        """
        Load a trip from current or legacy JSON data.

        Legacy stop dictionaries containing ``name`` instead of ``title``
        and no stable ``stop_id`` are migrated by Stop.from_dict().
        """

        data = json.loads(
            path.read_text(encoding="utf-8")
        )

        trip = cls(
            name=data["name"],
            routing_profile=RoutingProfile.from_value(
                data.get("routing_profile")
            ),
            travel_preferences=(
                TravelPreferences.from_dict(
                    data.get("travel_preferences")
                )
            ),
            trip_settings=TripSettings.from_dict(
                data.get("trip_settings")
            ),
            vehicle_profile_id=data.get(
                "vehicle_profile_id"
            ),
            avoid_motorways=bool(
                data.get(
                    "avoid_motorways",
                    False,
                )
            ),
        )

        stop_records = data.get("stops", [])

        if not isinstance(stop_records, list):
            raise ValueError(
                "Trip stops must be stored as a list."
            )

        for stop_data in stop_records:
            trip.add_stop(
                Stop.from_dict(stop_data)
            )

        return trip

    @property
    def total_nights(self) -> int:
        """Return the combined number of planned nights."""

        return sum(
            stop.nights
            for stop in self.stops
        )

    @property
    def start_date(self) -> date | None:
        """Return the earliest known arrival date."""

        arrival_dates = [
            date.fromisoformat(stop.arrival_date)
            for stop in self.stops
            if stop.arrival_date is not None
        ]

        if not arrival_dates:
            return None

        return min(arrival_dates)

    @property
    def end_date(self) -> date | None:
        """Return the latest known departure or arrival date."""

        known_dates: list[date] = []

        for stop in self.stops:
            if stop.departure_date is not None:
                known_dates.append(
                    date.fromisoformat(stop.departure_date)
                )
            elif stop.arrival_date is not None:
                known_dates.append(
                    date.fromisoformat(stop.arrival_date)
                )

        if not known_dates:
            return None

        return max(known_dates)

    @property
    def total_days(self) -> int | None:
        """Return inclusive calendar duration when both ends are known."""

        if self.start_date is None or self.end_date is None:
            return None

        return (
            self.end_date - self.start_date
        ).days + 1

    @property
    def remaining_days(self) -> int | None:
        """
        Return days remaining against the planning guideline.

        A negative value means the trip exceeds the guideline.
        """

        if self.total_days is None:
            return None

        return (
            self.trip_settings.planned_duration_days
            - self.total_days
        )

    @property
    def is_overplanned(self) -> bool:
        """Return whether the dated trip exceeds its guideline."""

        return (
            self.remaining_days is not None
            and self.remaining_days < 0
        )

    @property
    def has_partial_dates(self) -> bool:
        """Return whether some, but not all, stops have complete dates."""

        if not self.stops:
            return False

        complete_count = sum(
            1
            for stop in self.stops
            if (
                stop.arrival_date is not None
                and stop.departure_date is not None
            )
        )

        return 0 < complete_count < len(self.stops)

    @property
    def planning_summary(self) -> str:
        """Return a flexible human-readable planning summary."""

        planned_days = (
            self.trip_settings.planned_duration_days
        )

        if self.total_days is None:
            return (
                f"{self.total_nights} nachten gepland  •  "
                f"richtwaarde {planned_days} dagen"
            )

        if self.remaining_days is None:
            return (
                f"{self.total_days} dagen gepland  •  "
                f"richtwaarde {planned_days} dagen"
            )

        if self.remaining_days > 0:
            status = (
                f"{self.remaining_days} dagen ruimte"
            )
        elif self.remaining_days == 0:
            status = "precies op richtwaarde"
        else:
            status = (
                f"{abs(self.remaining_days)} dagen langer"
            )

        partial_text = (
            "  •  datums gedeeltelijk ingevuld"
            if self.has_partial_dates
            else ""
        )

        return (
            f"{self.total_days} / {planned_days} dagen"
            f"  •  {status}"
            f"{partial_text}"
        )
