from datetime import datetime, timedelta, timezone

from travel_planner.main import maintain_route_cache
from travel_planner.route_cache import RouteCache


def test_startup_maintenance_removes_expired_entry(
    tmp_path,
) -> None:
    cache = RouteCache(
        tmp_path,
        ttl=timedelta(days=1),
    )
    key = "a" * 64
    cache.put(
        key,
        {"response": {"code": "Ok"}},
        created_at=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
    )

    removed = maintain_route_cache(cache)

    assert removed == 1
    assert not (tmp_path / f"{key}.json").exists()


def test_startup_maintenance_keeps_current_entry(
    tmp_path,
) -> None:
    cache = RouteCache(
        tmp_path,
        ttl=timedelta(days=30),
    )
    key = "b" * 64
    now = datetime.now(timezone.utc)
    cache.put(
        key,
        {"response": {"code": "Ok"}},
        created_at=now,
    )

    removed = maintain_route_cache(cache)

    assert removed == 0
    assert (tmp_path / f"{key}.json").exists()
