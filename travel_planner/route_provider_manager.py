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

        self._active_provider = "osrm-demo"

    @property
    def active_provider(self) -> RouteProvider:
        return self._providers[self._active_provider]

    @property
    def active_provider_id(self) -> str:
        return self._active_provider

    def available_provider_ids(self) -> list[str]:
        return sorted(self._providers.keys())

    def set_active_provider(self, provider_id: str) -> None:
        if provider_id not in self._providers:
            raise KeyError(provider_id)

        self._active_provider = provider_id

    @property
    def fallback_provider(self) -> RouteProvider:
        return DirectRouteProvider()
