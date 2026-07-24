"""Tests for personal route-time estimation."""

import pytest

from travel_planner.route_time_estimation import (
    estimate_personal_duration_seconds,
    format_duration_seconds,
)


def test_estimate_uses_motorway_and_local_distance_parts() -> None:
    duration = estimate_personal_duration_seconds(
        distance_km=100,
        motorway_speed_kmh=100,
        local_speed_kmh=50,
        motorway_share=0.40,
    )

    assert duration == 5760


def test_estimate_uses_default_35_65_mix() -> None:
    duration = estimate_personal_duration_seconds(
        distance_km=100,
        motorway_speed_kmh=90,
        local_speed_kmh=55,
    )

    assert duration == pytest.approx(5655, abs=1)


def test_estimate_returns_none_for_invalid_vehicle_speed() -> None:
    assert estimate_personal_duration_seconds(100, 0, 55) is None


def test_estimate_rejects_negative_distance() -> None:
    with pytest.raises(ValueError, match="Distance"):
        estimate_personal_duration_seconds(-1, 90, 55)


def test_estimate_rejects_invalid_motorway_share() -> None:
    with pytest.raises(ValueError, match="Motorway share"):
        estimate_personal_duration_seconds(
            100,
            90,
            55,
            motorway_share=1.1,
        )


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (None, "—"),
        (45 * 60, "45 min"),
        (2 * 3600, "2 u"),
        ((2 * 3600) + (15 * 60), "2 u 15 min"),
    ],
)
def test_format_duration_seconds(
    seconds: int | None,
    expected: str,
) -> None:
    assert format_duration_seconds(seconds) == expected
