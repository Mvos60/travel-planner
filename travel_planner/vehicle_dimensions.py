from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class VehicleDimensions:
    """Physical vehicle limits used by routing providers."""

    length_m: float | None = None
    width_m: float | None = None
    height_m: float | None = None
    weight_kg: float | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "length_m",
            "width_m",
            "height_m",
            "weight_kg",
        ):
            value = getattr(self, field_name)

            if value is not None and value <= 0:
                raise ValueError(
                    f"{field_name} must be greater than zero."
                )

    @property
    def is_empty(self) -> bool:
        return all(
            value is None
            for value in (
                self.length_m,
                self.width_m,
                self.height_m,
                self.weight_kg,
            )
        )

    def to_dict(self) -> dict[str, float | None]:
        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "VehicleDimensions":
        if not isinstance(data, dict):
            return cls()

        def optional_number(key: str) -> float | None:
            value = data.get(key)

            if value is None:
                return None

            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                raise ValueError(
                    f"{key} must be a positive number or null."
                )

            return float(value)

        return cls(
            length_m=optional_number("length_m"),
            width_m=optional_number("width_m"),
            height_m=optional_number("height_m"),
            weight_kg=optional_number("weight_kg"),
        )
