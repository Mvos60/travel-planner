import pytest

from travel_planner.trip_settings import TripSettings


def test_trip_settings_defaults() -> None:
    settings = TripSettings()

    assert settings.planned_duration_days == 60
    assert settings.planned_start_date is None
    assert settings.shift_following_dates is True


def test_trip_settings_round_trip() -> None:
    settings = TripSettings(
        planned_duration_days=75,
        planned_start_date="2026-09-14",
        shift_following_dates=False,
    )

    loaded = TripSettings.from_dict(
        settings.to_dict()
    )

    assert loaded == settings


def test_legacy_trip_settings_remain_supported() -> None:
    settings = TripSettings.from_dict(
        {
            "planned_duration_days": 45,
            "shift_following_dates": False,
        }
    )

    assert settings.planned_duration_days == 45
    assert settings.planned_start_date is None
    assert settings.shift_following_dates is False


def test_trip_settings_reject_invalid_duration() -> None:
    with pytest.raises(ValueError):
        TripSettings(planned_duration_days=0)


def test_trip_settings_reject_boolean_duration() -> None:
    with pytest.raises(TypeError):
        TripSettings(planned_duration_days=True)


def test_trip_settings_reject_invalid_start_date() -> None:
    with pytest.raises(
        ValueError,
        match="YYYY-MM-DD",
    ):
        TripSettings(
            planned_start_date="14-09-2026"
        )
