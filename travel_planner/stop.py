"""Travel stop data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Stop:
    """One planned location within a trip."""

    title: str
    latitude: float
    longitude: float

    stop_id: str = field(
        default_factory=lambda: uuid4().hex
    )

    arrival_date: str | None = None
    departure_date: str | None = None
    notes: str | None = None

    overnight: bool = False
    favorite: bool = False
    photo_location: bool = False

    def __post_init__(self) -> None:
        """Normalize and validate stop data."""

        self.title = self.title.strip()

        if not self.title:
            raise ValueError(
                "A stop must have a title."
            )

        self.stop_id = self.stop_id.strip()

        if not self.stop_id:
            raise ValueError(
                "A stop must have a stable ID."
            )

        self.latitude = self._validate_coordinate(
            self.latitude,
            minimum=-90.0,
            maximum=90.0,
            field_name="Latitude",
        )
        self.longitude = self._validate_coordinate(
            self.longitude,
            minimum=-180.0,
            maximum=180.0,
            field_name="Longitude",
        )

        self.arrival_date = self._normalize_date(
            self.arrival_date,
            "Arrival date",
        )
        self.departure_date = self._normalize_date(
            self.departure_date,
            "Departure date",
        )
        self.notes = self._normalize_optional_text(
            self.notes
        )

        if (
            self.arrival_date is not None
            and self.departure_date is not None
            and self.departure_date < self.arrival_date
        ):
            raise ValueError(
                "Departure date cannot be before arrival date."
            )

        self._validate_boolean(
            self.overnight,
            "overnight",
        )
        self._validate_boolean(
            self.favorite,
            "favorite",
        )
        self._validate_boolean(
            self.photo_location,
            "photo_location",
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return {
            "stop_id": self.stop_id,
            "title": self.title,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "arrival_date": self.arrival_date,
            "departure_date": self.departure_date,
            "notes": self.notes,
            "overnight": self.overnight,
            "favorite": self.favorite,
            "photo_location": self.photo_location,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> Stop:
        """Create a stop from stored JSON data."""

        if not isinstance(data, dict):
            raise ValueError(
                "Stop data must be a JSON object."
            )

        required_fields = (
            "stop_id",
            "title",
            "latitude",
            "longitude",
        )

        missing_fields = [
            field_name
            for field_name in required_fields
            if field_name not in data
        ]

        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ValueError(
                f"Stop data is missing required fields: {missing}"
            )

        return cls(
            stop_id=data["stop_id"],
            title=data["title"],
            latitude=data["latitude"],
            longitude=data["longitude"],
            arrival_date=data.get("arrival_date"),
            departure_date=data.get("departure_date"),
            notes=data.get("notes"),
            overnight=data.get("overnight", False),
            favorite=data.get("favorite", False),
            photo_location=data.get(
                "photo_location",
                False,
            ),
        )

    @staticmethod
    def _validate_coordinate(
        value: float,
        *,
        minimum: float,
        maximum: float,
        field_name: str,
    ) -> float:
        if isinstance(value, bool):
            raise TypeError(
                f"{field_name} must be a number."
            )

        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise TypeError(
                f"{field_name} must be a number."
            ) from error

        if not minimum <= number <= maximum:
            raise ValueError(
                f"{field_name} must be between "
                f"{minimum:g} and {maximum:g}."
            )

        return number

    @staticmethod
    def _normalize_date(
        value: str | None,
        field_name: str,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a date string."
            )

        normalized = value.strip()

        if not normalized:
            return None

        try:
            parsed = date.fromisoformat(normalized)
        except ValueError as error:
            raise ValueError(
                f"{field_name} must use YYYY-MM-DD."
            ) from error

        return parsed.isoformat()

    @staticmethod
    def _normalize_optional_text(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                "Stop notes must be text."
            )

        normalized = value.strip()

        return normalized or None

    @staticmethod
    def _validate_boolean(
        value: bool,
        field_name: str,
    ) -> None:
        if not isinstance(value, bool):
            raise TypeError(
                f"{field_name} must be a boolean."
            )
