"""Estimate personal driving time from vehicle cruising speeds."""

from __future__ import annotations


DEFAULT_MOTORWAY_SHARE = 0.35


def estimate_personal_duration_seconds(
    distance_km: float,
    motorway_speed_kmh: float,
    local_speed_kmh: float,
    *,
    motorway_share: float = DEFAULT_MOTORWAY_SHARE,
) -> int | None:
    """Estimate duration using motorway and local-road distance portions."""

    if distance_km < 0:
        raise ValueError("Distance cannot be negative.")

    if not 0.0 <= motorway_share <= 1.0:
        raise ValueError("Motorway share must be between 0 and 1.")

    if motorway_speed_kmh <= 0 or local_speed_kmh <= 0:
        return None

    motorway_distance_km = distance_km * motorway_share
    local_distance_km = distance_km - motorway_distance_km
    duration_hours = (
        motorway_distance_km / motorway_speed_kmh
        + local_distance_km / local_speed_kmh
    )

    return round(duration_hours * 3600)


def format_duration_seconds(duration_seconds: int | None) -> str:
    """Format a duration for the Dutch user interface."""

    if duration_seconds is None:
        return "—"

    total_minutes = max(0, round(duration_seconds / 60))
    hours, minutes = divmod(total_minutes, 60)

    if hours == 0:
        return f"{minutes} min"
    if minutes == 0:
        return f"{hours} u"
    return f"{hours} u {minutes} min"
