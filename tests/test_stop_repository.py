import json

import pytest

from travel_planner.stop import Stop
from travel_planner.stop_repository import StopRepository


def _stop(
    *,
    stop_id: str,
    title: str,
) -> Stop:
    return Stop(
        stop_id=stop_id,
        title=title,
        latitude=45.0,
        longitude=5.0,
    )


def test_missing_file_loads_empty_repository(tmp_path):
    repository = StopRepository(
        tmp_path / "stops.json"
    )

    assert repository.load() == []
    assert repository.list_stops() == []


def test_repository_saves_and_loads_stops(tmp_path):
    storage_path = tmp_path / "stops.json"

    repository = StopRepository(storage_path)
    repository.add(
        _stop(
            stop_id="stop-1",
            title="Ardèche",
        )
    )
    repository.add(
        _stop(
            stop_id="stop-2",
            title="Triglav",
        )
    )
    repository.save()

    loaded_repository = StopRepository(storage_path)
    loaded = loaded_repository.load()

    assert [
        stop.stop_id
        for stop in loaded
    ] == [
        "stop-1",
        "stop-2",
    ]
    assert [
        stop.title
        for stop in loaded
    ] == [
        "Ardèche",
        "Triglav",
    ]


def test_add_rejects_duplicate_id(tmp_path):
    repository = StopRepository(
        tmp_path / "stops.json"
    )

    repository.add(
        _stop(
            stop_id="stop-1",
            title="First",
        )
    )

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        repository.add(
            _stop(
                stop_id="stop-1",
                title="Duplicate",
            )
        )


def test_update_preserves_route_position(tmp_path):
    repository = StopRepository(
        tmp_path / "stops.json"
    )

    repository.add(
        _stop(
            stop_id="stop-1",
            title="First",
        )
    )
    repository.add(
        _stop(
            stop_id="stop-2",
            title="Second",
        )
    )

    repository.update(
        _stop(
            stop_id="stop-1",
            title="Updated first",
        )
    )

    stops = repository.list_stops()

    assert stops[0].stop_id == "stop-1"
    assert stops[0].title == "Updated first"
    assert stops[1].stop_id == "stop-2"


def test_update_unknown_stop_raises_key_error(tmp_path):
    repository = StopRepository(
        tmp_path / "stops.json"
    )

    with pytest.raises(KeyError):
        repository.update(
            _stop(
                stop_id="unknown",
                title="Unknown",
            )
        )


def test_remove_existing_stop(tmp_path):
    repository = StopRepository(
        tmp_path / "stops.json"
    )

    repository.add(
        _stop(
            stop_id="stop-1",
            title="Temporary",
        )
    )

    assert repository.remove("stop-1") is True
    assert repository.get("stop-1") is None
    assert repository.remove("stop-1") is False


def test_load_rejects_invalid_json(tmp_path):
    storage_path = tmp_path / "stops.json"
    storage_path.write_text(
        "{ invalid JSON",
        encoding="utf-8",
    )

    repository = StopRepository(storage_path)

    with pytest.raises(
        ValueError,
        match="invalid JSON",
    ):
        repository.load()


def test_load_rejects_duplicate_ids(tmp_path):
    storage_path = tmp_path / "stops.json"
    storage_path.write_text(
        json.dumps(
            {
                "version": 1,
                "stops": [
                    _stop(
                        stop_id="duplicate",
                        title="First",
                    ).to_dict(),
                    _stop(
                        stop_id="duplicate",
                        title="Second",
                    ).to_dict(),
                ],
            }
        ),
        encoding="utf-8",
    )

    repository = StopRepository(storage_path)

    with pytest.raises(
        ValueError,
        match="unique",
    ):
        repository.load()


def test_load_rejects_unsupported_version(tmp_path):
    storage_path = tmp_path / "stops.json"
    storage_path.write_text(
        json.dumps(
            {
                "version": 999,
                "stops": [],
            }
        ),
        encoding="utf-8",
    )

    repository = StopRepository(storage_path)

    with pytest.raises(
        ValueError,
        match="Unsupported",
    ):
        repository.load()
