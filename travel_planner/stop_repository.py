"""Persistent storage for travel stops."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from travel_planner.stop import Stop


class StopRepository:
    """Load and save an ordered collection of stops."""

    FILE_VERSION = 1

    def __init__(
        self,
        storage_path: Path | None = None,
    ) -> None:
        self.storage_path = (
            storage_path
            if storage_path is not None
            else self.default_storage_path()
        )
        self._stops: list[Stop] = []

    @staticmethod
    def default_storage_path() -> Path:
        """Return the standard stop storage path."""

        return (
            Path.home()
            / ".config"
            / "travel-planner"
            / "stops.json"
        )

    def load(self) -> list[Stop]:
        """Load all stops from disk.

        A missing file represents an empty repository.
        """

        if not self.storage_path.exists():
            self._stops = []
            return []

        try:
            raw_data = json.loads(
                self.storage_path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as error:
            raise ValueError(
                "Stop file contains invalid JSON."
            ) from error

        stops_data = self._extract_stops(raw_data)

        loaded_stops = [
            Stop.from_dict(stop_data)
            for stop_data in stops_data
        ]

        self._ensure_unique_ids(loaded_stops)
        self._stops = loaded_stops

        return list(self._stops)

    def save(self) -> None:
        """Write the current ordered stop list to disk."""

        self._ensure_unique_ids(self._stops)

        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "version": self.FILE_VERSION,
            "stops": [
                stop.to_dict()
                for stop in self._stops
            ],
        }

        temporary_path = self.storage_path.with_suffix(
            self.storage_path.suffix + ".tmp"
        )

        temporary_path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        temporary_path.replace(self.storage_path)

    def list_stops(self) -> list[Stop]:
        """Return stops in their stored route order."""

        return list(self._stops)

    def get(
        self,
        stop_id: str,
    ) -> Stop | None:
        """Return a stop by stable ID."""

        for stop in self._stops:
            if stop.stop_id == stop_id:
                return stop

        return None

    def add(
        self,
        stop: Stop,
    ) -> None:
        """Append a new stop to the route."""

        if self.get(stop.stop_id) is not None:
            raise ValueError(
                "A stop with this ID already exists."
            )

        self._stops.append(stop)

    def update(
        self,
        stop: Stop,
    ) -> None:
        """Replace an existing stop in-place."""

        for index, existing in enumerate(self._stops):
            if existing.stop_id == stop.stop_id:
                self._stops[index] = stop
                return

        raise KeyError(
            f"Unknown stop: {stop.stop_id}"
        )

    def remove(
        self,
        stop_id: str,
    ) -> bool:
        """Remove a stop and report whether it existed."""

        for index, stop in enumerate(self._stops):
            if stop.stop_id == stop_id:
                del self._stops[index]
                return True

        return False

    @staticmethod
    def _extract_stops(
        raw_data: Any,
    ) -> list[dict[str, Any]]:
        if not isinstance(raw_data, dict):
            raise ValueError(
                "Stop file must contain a JSON object."
            )

        version = raw_data.get("version")

        if version != StopRepository.FILE_VERSION:
            raise ValueError(
                f"Unsupported stop file version: {version}"
            )

        stops_data = raw_data.get("stops", [])

        if not isinstance(stops_data, list):
            raise ValueError(
                "Stop file field 'stops' must be a list."
            )

        for stop_data in stops_data:
            if not isinstance(stop_data, dict):
                raise ValueError(
                    "Each stop must be a JSON object."
                )

        return stops_data

    @staticmethod
    def _ensure_unique_ids(
        stops: list[Stop],
    ) -> None:
        seen_ids: set[str] = set()

        for stop in stops:
            if stop.stop_id in seen_ids:
                raise ValueError(
                    "Stop IDs must be unique."
                )

            seen_ids.add(stop.stop_id)
