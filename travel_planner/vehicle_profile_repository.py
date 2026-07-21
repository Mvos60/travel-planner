"""Persistent storage for reusable vehicle profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from travel_planner.vehicle_profile import VehicleProfile


class VehicleProfileRepository:
    """Load and save vehicle profiles in one JSON file."""

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
        self._profiles: list[VehicleProfile] = []

    @staticmethod
    def default_storage_path() -> Path:
        """Return the standard per-user profile file location."""

        return (
            Path.home()
            / ".config"
            / "travel-planner"
            / "vehicle_profiles.json"
        )

    def load(self) -> list[VehicleProfile]:
        """Load profiles from disk.

        A missing file represents an empty repository.
        """

        if not self.storage_path.exists():
            self._profiles = []
            return []

        try:
            raw_data = json.loads(
                self.storage_path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as error:
            raise ValueError(
                "Vehicle profile file contains invalid JSON."
            ) from error

        profiles_data = self._extract_profiles(raw_data)

        loaded_profiles = [
            VehicleProfile.from_dict(profile_data)
            for profile_data in profiles_data
        ]

        self._ensure_unique_ids(loaded_profiles)
        self._profiles = loaded_profiles

        return list(self._profiles)

    def save(self) -> None:
        """Write all current profiles to disk."""

        self._ensure_unique_ids(self._profiles)

        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "version": self.FILE_VERSION,
            "profiles": [
                profile.to_dict()
                for profile in self._profiles
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

    def list_profiles(self) -> list[VehicleProfile]:
        """Return all profiles in their stored order."""

        return list(self._profiles)

    def get(
        self,
        profile_id: str,
    ) -> VehicleProfile | None:
        """Return a profile by stable ID."""

        for profile in self._profiles:
            if profile.profile_id == profile_id:
                return profile

        return None

    def add(
        self,
        profile: VehicleProfile,
    ) -> None:
        """Add a new vehicle profile.

        Profile IDs must be unique.
        """

        if self.get(profile.profile_id) is not None:
            raise ValueError(
                "A vehicle profile with this ID already exists."
            )

        self._profiles.append(profile)

    def update(
        self,
        profile: VehicleProfile,
    ) -> None:
        """Replace an existing vehicle profile."""

        for index, existing in enumerate(self._profiles):
            if existing.profile_id == profile.profile_id:
                self._profiles[index] = profile
                return

        raise KeyError(
            f"Unknown vehicle profile: {profile.profile_id}"
        )

    def remove(
        self,
        profile_id: str,
    ) -> bool:
        """Remove a profile and report whether it existed."""

        for index, profile in enumerate(self._profiles):
            if profile.profile_id == profile_id:
                del self._profiles[index]
                return True

        return False

    @staticmethod
    def _extract_profiles(
        raw_data: Any,
    ) -> list[dict[str, Any]]:
        if not isinstance(raw_data, dict):
            raise ValueError(
                "Vehicle profile file must contain a JSON object."
            )

        profiles_data = raw_data.get("profiles", [])

        if not isinstance(profiles_data, list):
            raise ValueError(
                "Vehicle profile file field 'profiles' must be a list."
            )

        for profile_data in profiles_data:
            if not isinstance(profile_data, dict):
                raise ValueError(
                    "Each vehicle profile must be a JSON object."
                )

        return profiles_data

    @staticmethod
    def _ensure_unique_ids(
        profiles: list[VehicleProfile],
    ) -> None:
        seen_ids: set[str] = set()

        for profile in profiles:
            if profile.profile_id in seen_ids:
                raise ValueError(
                    "Vehicle profile IDs must be unique."
                )

            seen_ids.add(profile.profile_id)
