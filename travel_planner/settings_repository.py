"""Persistent application settings."""

from __future__ import annotations

import json
from pathlib import Path

from travel_planner.settings import Settings


class SettingsRepository:

    FILE_VERSION = 1

    def __init__(
        self,
        storage_path: Path | None = None,
    ):
        self.storage_path = (
            storage_path
            if storage_path
            else self.default_storage_path()
        )

    @staticmethod
    def default_storage_path() -> Path:
        return (
            Path.home()
            / ".config"
            / "travel-planner"
            / "settings.json"
        )

    def load(self) -> Settings:

        if not self.storage_path.exists():
            return Settings()

        data = json.loads(
            self.storage_path.read_text(
                encoding="utf-8"
            )
        )

        return Settings.from_dict(
            data.get("settings", {})
        )

    def save(
        self,
        settings: Settings,
    ) -> None:

        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "version": self.FILE_VERSION,
            "settings": settings.to_dict(),
        }

        self.storage_path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
