"""Central application context for Travel Planner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from travel_planner.route_provider_manager import (
    RouteProviderManager,
)
from travel_planner.route_service import RouteService
from travel_planner.settings import Settings
from travel_planner.settings_repository import SettingsRepository
from travel_planner.stop_repository import StopRepository
from travel_planner.trip import Trip
from travel_planner.vehicle_profile_repository import (
    VehicleProfileRepository,
)


@dataclass
class TravelPlannerContext:
    """Shared application state and services.

    GTK windows receive this context rather than constructing repositories,
    services, and application settings themselves.
    """

    settings: Settings
    settings_repository: SettingsRepository
    vehicle_profile_repository: VehicleProfileRepository
    stop_repository: StopRepository
    route_provider_manager: RouteProviderManager
    route_service: RouteService
    current_trip: Trip

    @classmethod
    def create_default(
        cls,
        *,
        settings_path: Path | None = None,
        vehicle_profiles_path: Path | None = None,
        stops_path: Path | None = None,
    ) -> "TravelPlannerContext":
        """Build the normal application context.

        Optional paths make the context safely testable without touching the
        user's real configuration directory.
        """

        settings_repository = SettingsRepository(
            settings_path
        )

        vehicle_profile_repository = (
            VehicleProfileRepository(
                vehicle_profiles_path
            )
        )

        stop_repository = StopRepository(
            stops_path
        )

        settings = settings_repository.load()
        vehicle_profile_repository.load()
        stop_repository.load()

        route_provider_manager = RouteProviderManager(
            active_provider_id=settings.route_provider,
            openrouteservice_api_key=(
                settings.openrouteservice_api_key
            ),
        )

        route_service = RouteService(
            provider=(
                route_provider_manager.active_provider
            ),
            fallback_provider=(
                route_provider_manager.fallback_provider
            ),
        )

        current_trip = Trip(
            name="Nieuwe reis"
        )

        return cls(
            settings=settings,
            settings_repository=settings_repository,
            vehicle_profile_repository=(
                vehicle_profile_repository
            ),
            stop_repository=stop_repository,
            route_provider_manager=(
                route_provider_manager
            ),
            route_service=route_service,
            current_trip=current_trip,
        )

    @property
    def vehicle_profiles(self):
        """Return the currently loaded vehicle profiles."""

        return (
            self.vehicle_profile_repository
            .list_profiles()
        )

    @property
    def stops(self):
        """Return the currently loaded stops in route order."""

        return self.stop_repository.list_stops()

    def replace_trip(
        self,
        trip: Trip,
    ) -> None:
        """Set the trip currently used by the application."""

        self.current_trip = trip
