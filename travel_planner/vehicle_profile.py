"""Vehicle profile model for Travel Planner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


def _new_profile_id() -> str:
    return uuid4().hex


@dataclass
class VehicleProfile:
    """Reusable physical and environmental vehicle information.

    Vehicle profiles belong to the application settings rather than to an
    individual trip. Trips will later refer to a vehicle profile by its stable
    ``profile_id``.
    """

    name: str
    profile_id: str = field(default_factory=_new_profile_id)

    length_m: float | None = None
    width_m: float | None = None
    height_m: float | None = None
    max_weight_kg: int | None = None
    emission_class: str | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.profile_id = self.profile_id.strip()

        if not self.name:
            raise ValueError("Vehicle profile name cannot be empty.")

        if not self.profile_id:
            raise ValueError("Vehicle profile ID cannot be empty.")

        self._validate_positive_number(
            "length_m",
            self.length_m,
        )
        self._validate_positive_number(
            "width_m",
            self.width_m,
        )
        self._validate_positive_number(
            "height_m",
            self.height_m,
        )
        self._validate_positive_number(
            "max_weight_kg",
            self.max_weight_kg,
        )

        if self.emission_class is not None:
            self.emission_class = self.emission_class.strip() or None

    @staticmethod
    def _validate_positive_number(
        field_name: str,
        value: float | int | None,
    ) -> None:
        if value is not None and value <= 0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "length_m": self.length_m,
            "width_m": self.width_m,
            "height_m": self.height_m,
            "max_weight_kg": self.max_weight_kg,
            "emission_class": self.emission_class,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> VehicleProfile:
        """Create a vehicle profile from stored JSON data.

        A missing profile ID is accepted for compatibility with early profile
        files and results in a newly generated stable ID.
        """

        profile_id = data.get("profile_id")

        keyword_arguments: dict[str, Any] = {
            "name": str(data.get("name", "")),
            "length_m": cls._optional_float(
                data.get("length_m")
            ),
            "width_m": cls._optional_float(
                data.get("width_m")
            ),
            "height_m": cls._optional_float(
                data.get("height_m")
            ),
            "max_weight_kg": cls._optional_int(
                data.get("max_weight_kg")
            ),
            "emission_class": cls._optional_string(
                data.get("emission_class")
            ),
        }

        if profile_id is not None:
            keyword_arguments["profile_id"] = str(profile_id)

        return cls(**keyword_arguments)

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None or value == "":
            return None

        return float(value)

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None or value == "":
            return None

        return int(value)

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        return text or None
