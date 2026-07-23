from datetime import datetime, timedelta, timezone
import json

import pytest

from travel_planner.route_cache import RouteCache, build_route_cache_key


def test_build_route_cache_key_is_stable():
    first = build_route_cache_key(
        provider="OSRM",
        profile="driving",
        coordinates=[(4.123456789, 52.123456789), (5.0, 53.0)],
        options={"avoid_tolls": True},
    )
    second = build_route_cache_key(
        provider="osrm",
        profile="DRIVING",
        coordinates=[(4.1234567, 52.1234567), (5, 53)],
        options={"avoid_tolls": True},
    )

    assert first == second
    assert len(first) == 64


def test_different_route_requests_get_different_keys():
    first = build_route_cache_key(
        provider="osrm",
        profile="driving",
        coordinates=[(4.0, 52.0), (5.0, 53.0)],
    )
    second = build_route_cache_key(
        provider="osrm",
        profile="driving",
        coordinates=[(4.0, 52.0), (6.0, 53.0)],
    )

    assert first != second


def test_put_and_get_round_trip(tmp_path):
    cache = RouteCache(tmp_path)
    key = "a" * 64
    payload = {
        "distance_m": 12345.0,
        "duration_s": 678.0,
        "geometry": [[4.0, 52.0], [5.0, 53.0]],
    }

    cache.put(key, payload)

    assert cache.get(key) == payload


def test_expired_entry_is_removed(tmp_path):
    cache = RouteCache(tmp_path, ttl=timedelta(days=1))
    key = "b" * 64
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    cache.put(key, {"distance_m": 1000}, created_at=created_at)

    assert cache.get(
        key,
        now=datetime(2026, 1, 3, tzinfo=timezone.utc),
    ) is None
    assert not (tmp_path / f"{key}.json").exists()


def test_corrupt_entry_is_ignored_and_removed(tmp_path):
    cache = RouteCache(tmp_path)
    key = "c" * 64
    path = tmp_path / f"{key}.json"
    path.write_text("{not valid json", encoding="utf-8")

    assert cache.get(key) is None
    assert not path.exists()


def test_clear_removes_only_cache_json_files(tmp_path):
    cache = RouteCache(tmp_path)
    cache.put("d" * 64, {"route": 1})
    cache.put("e" * 64, {"route": 2})
    (tmp_path / "keep.txt").write_text("keep", encoding="utf-8")

    assert cache.clear() == 2
    assert (tmp_path / "keep.txt").exists()


def test_invalid_cache_key_is_rejected(tmp_path):
    cache = RouteCache(tmp_path)

    with pytest.raises(ValueError):
        cache.put("not-a-sha256-key", {"route": 1})
