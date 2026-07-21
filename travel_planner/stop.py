"""Travel stop data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import uuid4


@dataclass(slots=True, init=False)
class Stop:
    """
    One planned location within a trip.

    The canonical stop title is stored in ``title``.

    During the migration from the original trip model, ``name`` remains
    available as a fully compatible alias. The legacy ``nights`` value is
    also retained until trip dates become the sole source of stay duration.
    """

    title: str
    latitude: float
    longitude: float

    stop_id: str = field(
        default_factory=lambda: uuid4().hex
    )

    arrival_date: str | None = None
    departure_date: str | None = None
    notes: str | None = None

    nights: int = 1

    overnight: bool = False
    favorite: bool = False
    photo_location: bool = False

    def __init__(
        self,
        title: str | None = None,
        latitude: float = 0.0,
        longitude: float = 0.0,
        *,
        name: str | None = None,
        stop_id: str | None = None,
        arrival_date: str | None = None,
        departure_date: str | None = None,
        notes: str | None = None,
        nights: int = 1,
        overnight: bool = False,
        favorite: bool = False,
        photo_location: bool = False,
    ) -> None:
        """
        Create a stop using either the new or legacy naming API.

        New code should use ``title``. Legacy callers may still use ``name``.
        Supplying both is allowed only when both values are identical after
        whitespace normalization.
        """

        normalized_title = self._resolve_title(
            title=title,
            name=name,
        )

        self.title = normalized_title
        self.latitude = latitude
        self.longitude = longitude
        self.stop_id = stop_id or uuid4().hex
        self.arrival_date = arrival_date
        self.departure_date = departure_date
        self.notes = notes
        self.nights = nights
        self.overnight = overnight
        self.favorite = favorite
        self.photo_location = photo_location

        self.__post_init__()

    def __post_init__(self) -> None:
        """Normalize and validate stop data."""

        self.title = self.title.strip()

        if not self.title:
            raise ValueError(
                "A stop must have a title."
            )

        if not isinstance(self.stop_id, str):
            raise TypeError(
                "A stop ID must be text."
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

        self.nights = self._validate_nights(
            self.nights
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

    @property
    def name(self) -> str:
        """Return the legacy alias for the stop title."""

        return self.title

    @name.setter
    def name(self, value: str) -> None:
        """Update the title through the legacy attribute name."""

        if not isinstance(value, str):
            raise TypeError(
                "A stop name must be text."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "A stop must have a title."
            )

        self.title = normalized

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
            "nights": self.nights,
            "overnight": self.overnight,
            "favorite": self.favorite,
            "photo_location": self.photo_location,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> Stop:
        """
        Create a stop from current or legacy stored JSON data.

        Current data uses ``title`` and ``stop_id``. Legacy trip data may use
        ``name`` and may not yet contain a stable stop ID.
        """

        if not isinstance(data, dict):
            raise ValueError(
                "Stop data must be a JSON object."
            )

        if (
            "title" not in data
            and "name" not in data
        ):
            raise ValueError(
                "Stop data is missing required field: title"
            )

        missing_fields = [
            field_name
            for field_name in (
                "latitude",
                "longitude",
            )
            if field_name not in data
        ]

        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ValueError(
                f"Stop data is missing required fields: {missing}"
            )

        return cls(
            title=data.get("title"),
            name=data.get("name"),
            stop_id=data.get("stop_id"),
            latitude=data["latitude"],
            longitude=data["longitude"],
            arrival_date=data.get("arrival_date"),
            departure_date=data.get("departure_date"),
            notes=data.get("notes"),
            nights=data.get("nights", 1),
            overnight=data.get("overnight", False),
            favorite=data.get("favorite", False),
            photo_location=data.get(
                "photo_location",
                False,
            ),
        )

    @staticmethod
    def _resolve_title(
        *,
        title: str | None,
        name: str | None,
    ) -> str:
        if title is None and name is None:
            raise ValueError(
                "A stop must have a title."
            )

        if title is not None and not isinstance(
            title,
            str,
        ):
            raise TypeError(
                "A stop title must be text."
            )

        if name is not None and not isinstance(
            name,
            str,
        ):
            raise TypeError(
                "A stop name must be text."
            )

        normalized_title = (
            title.strip()
            if title is not None
            else None
        )
        normalized_name = (
            name.strip()
            if name is not None
            else None
        )

        if (
            normalized_title is not None
            and normalized_name is not None
            and normalized_title != normalized_name
        ):
            raise ValueError(
                "Stop title and legacy name do not match."
            )

        resolved = (
            normalized_title
            if normalized_title is not None
            else normalized_name
        )

        if not resolved:
            raise ValueError(
                "A stop must have a title."
            )

        return resolved

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
    def _validate_nights(
        value: int,
    ) -> int:
        if isinstance(value, bool):
            raise TypeError(
                "Nights must be a whole number."
            )

        if isinstance(value, float) and not value.is_integer():
            raise TypeError(
                "Nights must be a whole number."
            )

        try:
            nights = int(value)
        except (TypeError, ValueError) as error:
            raise TypeError(
                "Nights must be a whole number."
            ) from error

        if nights < 0:
            raise ValueError(
                "Nights cannot be negative."
            )

        return nights

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
