from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from travel_planner.routing_profile import RoutingProfile
from travel_planner.stop import Stop
from travel_planner.travel_preferences import TravelPreferences


@dataclass
class Trip:
    """A planned journey containing an ordered collection of stops."""

    name: str
    stops: list[Stop] = field(default_factory=list)
    routing_profile: RoutingProfile = RoutingProfile.CAMPER
    travel_preferences: TravelPreferences = field(
        default_factory=TravelPreferences
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
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> Trip:
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
