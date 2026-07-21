from pathlib import Path

from travel_planner.settings import Settings
from travel_planner.settings_repository import (
    SettingsRepository,
)


def _repo(tmp_path: Path):
    return SettingsRepository(
        tmp_path / "settings.json"
    )


def test_default_settings_loaded_when_missing(
    tmp_path: Path,
):
    repo = _repo(tmp_path)

    settings = repo.load()

    assert settings.font_scale == 1.0
    assert settings.default_route_profile == "camper"
    assert settings.default_vehicle_profile is None


def test_settings_round_trip(
    tmp_path: Path,
):
    repo = _repo(tmp_path)

    original = Settings(
        font_scale=1.25,
        default_route_profile="photographer",
        default_vehicle_profile="hymer",
        map_provider="osm",
        autosave_minutes=10,
    )

    repo.save(original)

    restored = repo.load()

    assert restored == original
