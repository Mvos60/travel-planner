from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from travel_planner.routing_profile import RoutingProfile


@dataclass
class Stop:
    name: str
    latitude: float
    longitude: float
    nights: int = 1
    notes: str = ""


@dataclass
class Trip:
    name: str
    stops: list[Stop] = field(default_factory=list)
    routing_profile: RoutingProfile = RoutingProfile.CAMPER
    avoid_motorways: bool = False

    def add_stop(self, stop: Stop) -> None:
        self.stops.append(stop)

    def save(self, path: Path) -> None:
        data = {
            "name": self.name,
            "stops": [asdict(stop) for stop in self.stops],
            "routing_profile": self.routing_profile.value,
            "avoid_motorways": self.avoid_motorways,
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "Trip":
        data = json.loads(path.read_text(encoding="utf-8"))

        trip = cls(
            name=data["name"],
            routing_profile=RoutingProfile.from_value(
                data.get("routing_profile")
            ),
            avoid_motorways=bool(
                data.get("avoid_motorways", False)
            ),
        )

        for stop_data in data.get("stops", []):
            trip.add_stop(Stop(**stop_data))

        return trip

    @property
    def total_nights(self) -> int:
        return sum(stop.nights for stop in self.stops)
