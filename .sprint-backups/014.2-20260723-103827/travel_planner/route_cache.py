"""Persistent route-response cache for Travel Planner.

Sprint 014.0 introduces the cache foundation as an isolated, tested component.
Provider integration follows in the next sprint, after the cache behaviour has
been validated independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_TTL = timedelta(days=30)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_route_cache_key(
    *,
    provider: str,
    profile: str,
    coordinates: Sequence[Sequence[float]],
    options: Mapping[str, Any] | None = None,
) -> str:
    """Return a stable SHA-256 key for one routing request.

    Floating-point coordinates are normalised to six decimal places. This is
    precise enough for road routing while preventing tiny representation
    differences from creating unnecessary duplicate entries.
    """

    normalised_coordinates = [
        [round(float(longitude), 6), round(float(latitude), 6)]
        for longitude, latitude in coordinates
    ]

    payload = {
        "provider": str(provider).strip().lower(),
        "profile": str(profile).strip().lower(),
        "coordinates": normalised_coordinates,
        "options": dict(options or {}),
    }

    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class RouteCacheEntry:
    """One cached routing response."""

    key: str
    created_at: datetime
    payload: dict[str, Any]

    def is_expired(
        self,
        *,
        ttl: timedelta = DEFAULT_TTL,
        now: datetime | None = None,
    ) -> bool:
        current_time = now or _utc_now()
        return current_time - self.created_at > ttl


class RouteCache:
    """Small JSON-file cache with one file per routing request."""

    def __init__(
        self,
        directory: Path | str | None = None,
        *,
        ttl: timedelta = DEFAULT_TTL,
    ) -> None:
        self.directory = Path(directory or self.default_directory()).expanduser()
        self.ttl = ttl

    @staticmethod
    def default_directory() -> Path:
        return Path.home() / ".cache" / "travel-planner" / "routes"

    def get(
        self,
        key: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        path = self._entry_path(key)

        if not path.is_file():
            return None

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            entry = RouteCacheEntry(
                key=str(raw["key"]),
                created_at=datetime.fromisoformat(str(raw["created_at"])),
                payload=dict(raw["payload"]),
            )
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            self._remove_quietly(path)
            return None

        if entry.key != key or entry.is_expired(ttl=self.ttl, now=now):
            self._remove_quietly(path)
            return None

        return dict(entry.payload)

    def put(
        self,
        key: str,
        payload: Mapping[str, Any],
        *,
        created_at: datetime | None = None,
    ) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)

        timestamp = created_at or _utc_now()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        data = {
            "key": key,
            "created_at": timestamp.astimezone(timezone.utc).isoformat(),
            "payload": dict(payload),
        }

        destination = self._entry_path(key)
        temporary = destination.with_suffix(".tmp")

        temporary.write_text(
            json.dumps(data, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        temporary.replace(destination)

    def clear(self) -> int:
        if not self.directory.exists():
            return 0

        removed = 0
        for path in self.directory.glob("*.json"):
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            removed += 1

        return removed

    def prune(
        self,
        *,
        now: datetime | None = None,
    ) -> int:
        if not self.directory.exists():
            return 0

        removed = 0
        current_time = now or _utc_now()

        for path in self.directory.glob("*.json"):
            key = path.stem
            if self.get(key, now=current_time) is None and not path.exists():
                removed += 1

        return removed

    def _entry_path(self, key: str) -> Path:
        if len(key) != 64 or any(character not in "0123456789abcdef" for character in key):
            raise ValueError("Route-cache key must be a lowercase SHA-256 hex digest.")
        return self.directory / f"{key}.json"

    @staticmethod
    def _remove_quietly(path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
