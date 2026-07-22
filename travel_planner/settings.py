"""Application settings."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Settings:
    """Persistent application settings."""

    font_scale: float = 1.0

    default_route_profile: str = "camper"
    default_vehicle_profile: str | None = None

    map_provider: str = "osm"

    route_provider: str = "osrm-demo"
    openrouteservice_api_key: str = ""

    autosave_minutes: int = 5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "Settings":
        route_provider = str(
            data.get(
                "route_provider",
                "osrm-demo",
            )
        )

        if route_provider not in {
            "osrm-demo",
            "openrouteservice",
        }:
            route_provider = "osrm-demo"

        api_key_value = data.get(
            "openrouteservice_api_key",
            "",
        )

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
            route_provider=route_provider,
            openrouteservice_api_key=(
                ""
                if api_key_value is None
                else str(api_key_value).strip()
            ),
            autosave_minutes=int(
                data.get(
                    "autosave_minutes",
                    5,
                )
            ),
        )
