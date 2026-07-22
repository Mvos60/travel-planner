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


def test_routing_settings_round_trip(
    tmp_path,
) -> None:
    repo = SettingsRepository(
        tmp_path / "settings.json"
    )

    original = Settings(
        route_provider="openrouteservice",
        openrouteservice_api_key="test-secret-key",
    )

    repo.save(original)

    restored = repo.load()

    assert restored.route_provider == "openrouteservice"
    assert (
        restored.openrouteservice_api_key
        == "test-secret-key"
    )


def test_legacy_settings_use_default_route_provider(
    tmp_path,
) -> None:
    settings_path = tmp_path / "settings.json"

    settings_path.write_text(
        """{
  "version": 1,
  "settings": {
    "font_scale": 1.0,
    "map_provider": "osm"
  }
}
""",
        encoding="utf-8",
    )

    restored = SettingsRepository(
        settings_path
    ).load()

    assert restored.route_provider == "osrm-demo"
    assert restored.openrouteservice_api_key == ""


def test_unknown_saved_route_provider_uses_default(
    tmp_path,
) -> None:
    settings_path = tmp_path / "settings.json"

    settings_path.write_text(
        """{
  "version": 1,
  "settings": {
    "route_provider": "unknown-provider"
  }
}
""",
        encoding="utf-8",
    )

    restored = SettingsRepository(
        settings_path
    ).load()

    assert restored.route_provider == "osrm-demo"

