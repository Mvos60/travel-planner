from __future__ import annotations

from enum import Enum


class RoutingProfile(str, Enum):
    FASTEST = "fastest"
    CAMPER = "camper"
    PHOTOGRAPHER = "photographer"
    CUSTOM = "custom"

    @property
    def display_name(self) -> str:
        names = {
            RoutingProfile.FASTEST: "Fastest",
            RoutingProfile.CAMPER: "Camper",
            RoutingProfile.PHOTOGRAPHER: "Photographer",
            RoutingProfile.CUSTOM: "Custom",
        }

        return names[self]

    @classmethod
    def from_value(
        cls,
        value: object,
    ) -> "RoutingProfile":
        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            try:
                return cls(value)
            except ValueError:
                pass

        return cls.CAMPER
