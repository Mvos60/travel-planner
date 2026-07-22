"""Date parsing and display helpers."""

from __future__ import annotations

from datetime import date, datetime


DISPLAY_DATE_FORMAT = "%d-%m-%Y"


def parse_display_date(value: str) -> str | None:
    """
    Convert user-entered dates to ISO format.

    Accepted formats:

    - DD-MM-YYYY
    - YYYY-MM-DD

    Empty input returns None.
    """

    cleaned = value.strip()

    if not cleaned:
        return None

    for date_format in (
        DISPLAY_DATE_FORMAT,
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(
                cleaned,
                date_format,
            ).date()
        except ValueError:
            continue

        return parsed.isoformat()

    raise ValueError(
        "Gebruik een geldige datum als DD-MM-JJJJ."
    )


def format_date_for_display(
    iso_date: str | None,
) -> str:
    """Convert an ISO date to DD-MM-YYYY for display."""

    if iso_date is None or not iso_date.strip():
        return ""

    try:
        parsed = date.fromisoformat(
            iso_date.strip()
        )
    except ValueError as exc:
        raise ValueError(
            f"Ongeldige interne ISO-datum: {iso_date}"
        ) from exc

    return parsed.strftime(DISPLAY_DATE_FORMAT)
