"""Per-trip planning settings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(slots=True)
class TripSettings:
    """Flexible planning preferences belonging to one trip."""

    planned_duration_days: int = 60
    planned_start_date: str | None = None
    shift_following_dates: bool = True

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.planned_duration_days,
                int,
            )
            or isinstance(
                self.planned_duration_days,
                bool,
            )
        ):
            raise TypeError(
                "Planned trip duration must be an integer."
            )

        if self.planned_duration_days < 1:
            raise ValueError(
                "Planned trip duration must be at least one day."
            )

        if self.planned_start_date is not None:
            if not isinstance(
                self.planned_start_date,
                str,
            ):
                raise TypeError(
                    "Planned start date must be a string or None."
                )

            try:
                date.fromisoformat(
                    self.planned_start_date
                )
            except ValueError as exc:
                raise ValueError(
                    "Planned start date must use YYYY-MM-DD."
                ) from exc

        if not isinstance(
            self.shift_following_dates,
            bool,
        ):
            raise TypeError(
                "Shift-following-dates must be boolean."
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return {
            "planned_duration_days": (
                self.planned_duration_days
            ),
            "planned_start_date": (
                self.planned_start_date
            ),
            "shift_following_dates": (
                self.shift_following_dates
            ),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "TripSettings":
        """Load settings while supporting older trip files."""

        if data is None:
            return cls()

        if not isinstance(data, dict):
            raise ValueError(
                "Trip settings must be stored as an object."
            )

        return cls(
            planned_duration_days=data.get(
                "planned_duration_days",
                60,
            ),
            planned_start_date=data.get(
                "planned_start_date"
            ),
            shift_following_dates=data.get(
                "shift_following_dates",
                True,
            ),
        )
