from __future__ import annotations

from travel_planner.route_service import (
    DirectRouteProvider,
    OSRMRouteProvider,
    RouteProvider,
)


class RouteProviderManager:
    """Maintains the available routing providers."""

    def __init__(self) -> None:
        self._providers: dict[str, RouteProvider] = {
            "osrm-demo": OSRMRouteProvider(),
        }

        self._provider_names: dict[str, str] = {
            "osrm-demo": "OSRM Demo",
        }

        self._active_provider_id = "osrm-demo"

    @property
    def active_provider(self) -> RouteProvider:
        return self._providers[self._active_provider_id]

    @property
    def active_provider_id(self) -> str:
        return self._active_provider_id

    def available_provider_ids(self) -> list[str]:
        """Return registered provider identifiers."""

        return list(self._providers)

    def provider_display_name(
        self,
        provider_id: str,
    ) -> str:
        """Return the user-facing name of a provider."""

        if provider_id not in self._providers:
            raise KeyError(provider_id)

        return self._provider_names[provider_id]

    def set_active_provider(
        self,
        provider_id: str,
    ) -> None:
        """Select one registered provider."""

        if provider_id not in self._providers:
            raise KeyError(provider_id)

        self._active_provider_id = provider_id

    @property
    def fallback_provider(self) -> RouteProvider:
        return DirectRouteProvider()
