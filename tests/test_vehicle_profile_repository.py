import json
from pathlib import Path

import pytest

from travel_planner.vehicle_profile import VehicleProfile
from travel_planner.vehicle_profile_repository import (
    VehicleProfileRepository,
)


def _repository(
    tmp_path: Path,
) -> VehicleProfileRepository:
    return VehicleProfileRepository(
        tmp_path / "vehicle_profiles.json"
    )


def _hymer() -> VehicleProfile:
    return VehicleProfile(
        profile_id="hymer-mlt",
        name="Hymer ML-T",
        length_m=7.20,
        width_m=2.30,
        height_m=3.05,
        max_weight_kg=4100,
        emission_class="Euro 6",
    )


def test_missing_profile_file_loads_empty_repository(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)

    assert repository.load() == []
    assert repository.list_profiles() == []


def test_repository_saves_and_loads_profiles(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    profile = _hymer()

    repository.add(profile)
    repository.save()

    restored_repository = _repository(tmp_path)
    restored_profiles = restored_repository.load()

    assert restored_profiles == [profile]
    assert restored_repository.get("hymer-mlt") == profile


def test_saved_file_has_version_and_profiles(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    repository.add(_hymer())
    repository.save()

    data = json.loads(
        repository.storage_path.read_text(
            encoding="utf-8"
        )
    )

    assert data["version"] == 1
    assert len(data["profiles"]) == 1
    assert data["profiles"][0]["profile_id"] == "hymer-mlt"


def test_add_rejects_duplicate_profile_id(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    repository.add(_hymer())

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        repository.add(
            VehicleProfile(
                profile_id="hymer-mlt",
                name="Duplicate Hymer",
            )
        )


def test_repository_updates_existing_profile(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    repository.add(_hymer())

    updated = VehicleProfile(
        profile_id="hymer-mlt",
        name="Hymer ML-T Updated",
        height_m=3.10,
    )

    repository.update(updated)

    assert repository.get("hymer-mlt") == updated


def test_repository_rejects_update_of_unknown_profile(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)

    with pytest.raises(
        KeyError,
        match="unknown-profile",
    ):
        repository.update(
            VehicleProfile(
                profile_id="unknown-profile",
                name="Unknown",
            )
        )


def test_repository_removes_profile(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    repository.add(_hymer())

    assert repository.remove("hymer-mlt") is True
    assert repository.get("hymer-mlt") is None
    assert repository.remove("hymer-mlt") is False


def test_loading_invalid_json_raises_clear_error(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    repository.storage_path.write_text(
        "{not valid json",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="invalid JSON",
    ):
        repository.load()


def test_loading_duplicate_profile_ids_is_rejected(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)

    repository.storage_path.write_text(
        json.dumps(
            {
                "version": 1,
                "profiles": [
                    {
                        "profile_id": "same-id",
                        "name": "Vehicle One",
                    },
                    {
                        "profile_id": "same-id",
                        "name": "Vehicle Two",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="IDs must be unique",
    ):
        repository.load()
