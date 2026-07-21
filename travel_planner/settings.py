"""Application settings."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class Settings:
    """Persistent application settings."""

    font_scale: float = 1.0

    default_route_profile: str = "camper"
    default_vehicle_profile: str | None = None

    map_provider: str = "osm"

    autosave_minutes: int = 5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "Settings":
        return cls(
            font_scale=float(
                data.get("font_scale", 1.0)
            ),
            default_route_profile=str(
                data.get(
                    "default_route_profile",
                    "camper",
                )
            ),
            default_vehicle_profile=data.get(
                "default_vehicle_profile"
            ),
            map_provider=str(
                data.get(
                    "map_provider",
                    "osm",
                )
            ),
            autosave_minutes=int(
                data.get(
                    "autosave_minutes",
                    5,
                )
            ),
        )
