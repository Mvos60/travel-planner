from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class TravelPreferences:
    avoid_highways: bool = False
    avoid_tolls: bool = False
    avoid_ferries: bool = False

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        data: object,
    ) -> "TravelPreferences":
        if not isinstance(data, dict):
            return cls()

        values: dict[str, Any] = data

        return cls(
            avoid_highways=bool(
                values.get("avoid_highways", False)
            ),
            avoid_tolls=bool(
                values.get("avoid_tolls", False)
            ),
            avoid_ferries=bool(
                values.get("avoid_ferries", False)
            ),
        )
