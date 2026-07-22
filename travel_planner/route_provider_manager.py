from __future__ import annotations

from travel_planner.route_service import (
    DirectRouteProvider,
    OpenRouteServiceProvider,
    OSRMRouteProvider,
    RouteProvider,
)


DEFAULT_ROUTE_PROVIDER_ID = "osrm-demo"


class RouteProviderManager:
    """Maintains the available routing providers."""

    def __init__(
        self,
        *,
        active_provider_id: str = DEFAULT_ROUTE_PROVIDER_ID,
        openrouteservice_api_key: str | None = None,
    ) -> None:
        api_key = (
            openrouteservice_api_key.strip()
            if openrouteservice_api_key
            else None
        )

        self._providers: dict[str, RouteProvider] = {
            "osrm-demo": OSRMRouteProvider(),
            "openrouteservice": OpenRouteServiceProvider(
                api_key=api_key
            ),
        }

        self._provider_names: dict[str, str] = {
            "osrm-demo": "OSRM Demo",
            "openrouteservice": "OpenRouteService",
        }

        self._active_provider_id = (
            active_provider_id
            if active_provider_id in self._providers
            else DEFAULT_ROUTE_PROVIDER_ID
        )

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

    def provider(
        self,
        provider_id: str,
    ) -> RouteProvider:
        """Return one registered provider."""

        if provider_id not in self._providers:
            raise KeyError(provider_id)

        return self._providers[provider_id]

    def set_active_provider(
        self,
        provider_id: str,
    ) -> None:
        """Select one registered provider."""

        if provider_id not in self._providers:
            raise KeyError(provider_id)

        self._active_provider_id = provider_id

    def set_openrouteservice_api_key(
        self,
        api_key: str | None,
    ) -> None:
        """Update the API-key used by OpenRouteService."""

        provider = self.provider("openrouteservice")

        if not isinstance(
            provider,
            OpenRouteServiceProvider,
        ):
            raise TypeError(
                "OpenRouteService-provider heeft een "
                "onverwacht type."
            )

        provider.api_key = (
            api_key.strip()
            if api_key
            else ""
        )

    @property
    def fallback_provider(self) -> RouteProvider:
        return DirectRouteProvider()
