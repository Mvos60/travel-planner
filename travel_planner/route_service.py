from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from travel_planner.routing_profile import RoutingProfile
from travel_planner.stop import Stop
from travel_planner.travel_preferences import TravelPreferences


DEFAULT_OSRM_BASE_URL = "https://router.project-osrm.org"
DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class RouteCoordinate:
    latitude: float
    longitude: float

    def to_dict(self) -> dict[str, float]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


@dataclass(frozen=True)
class RoutingRequest:
    """Complete input for one routing calculation."""

    stops: tuple[Stop, ...]
    profile: RoutingProfile = RoutingProfile.CAMPER
    preferences: TravelPreferences = field(
        default_factory=TravelPreferences
    )

    @classmethod
    def create(
        cls,
        stops: Sequence[Stop],
        profile: RoutingProfile = RoutingProfile.CAMPER,
        preferences: TravelPreferences | None = None,
    ) -> "RoutingRequest":
        """Create an immutable request from application input."""

        return cls(
            stops=tuple(stops),
            profile=profile,
            preferences=(
                preferences
                if preferences is not None
                else TravelPreferences()
            ),
        )


@dataclass(frozen=True)
class RouteProviderCapabilities:
    """Features supported by one route provider."""

    supports_avoid_highways: bool = False
    supports_avoid_tolls: bool = False
    supports_avoid_ferries: bool = False
    supports_vehicle_dimensions: bool = False


class RouteProviderError(RuntimeError):
    """Raised when a route provider cannot calculate a route."""


class RouteProvider(Protocol):
    capabilities: RouteProviderCapabilities

    def calculate_route(
        self,
        request: RoutingRequest,
    ) -> list[RouteCoordinate]:
        """Calculate route geometry for the supplied request."""


class DirectRouteProvider:
    """Returns direct lines between the supplied stops."""

    capabilities = RouteProviderCapabilities()

    def calculate_route(
        self,
        request: RoutingRequest,
    ) -> list[RouteCoordinate]:
        return [
            RouteCoordinate(
                latitude=stop.latitude,
                longitude=stop.longitude,
            )
            for stop in request.stops
        ]


class OSRMRouteProvider:
    """Calculates a driving route using an OSRM HTTP server."""

    capabilities = RouteProviderCapabilities(
        supports_avoid_highways=False,
        supports_avoid_tolls=False,
        supports_avoid_ferries=False,
        supports_vehicle_dimensions=False,
    )

    def __init__(
        self,
        base_url: str = DEFAULT_OSRM_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Callable[..., object] = urlopen,
        avoid_motorways: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.opener = opener
        self.avoid_motorways = avoid_motorways

    def calculate_route(
        self,
        request: RoutingRequest,
    ) -> list[RouteCoordinate]:
        stops = request.stops

        if len(stops) < 2:
            return DirectRouteProvider().calculate_route(request)

        http_request = Request(
            self._build_route_url(stops),
            headers={
                "User-Agent": (
                    "TravelPlanner/0.1 "
                    "(desktop route-planning application)"
                ),
                "Accept": "application/json",
            },
        )

        try:
            response = self.opener(
                http_request,
                timeout=self.timeout_seconds,
            )

            with response:
                payload = json.load(response)
        except (
            HTTPError,
            URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise RouteProviderError(
                f"OSRM-route kon niet worden opgehaald: {exc}"
            ) from exc

        return self._parse_response(payload)

    def _build_route_url(
        self,
        stops: Sequence[Stop],
    ) -> str:
        coordinates = ";".join(
            f"{stop.longitude},{stop.latitude}"
            for stop in stops
        )

        query_parameters = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        }

        # The public OSRM demo server does not support
        # exclude=motorway. Route preferences will be handled
        # by a provider that supports dynamic costing.

        query = urlencode(query_parameters)

        return (
            f"{self.base_url}/route/v1/driving/"
            f"{coordinates}?{query}"
        )

    def _parse_response(
        self,
        payload: object,
    ) -> list[RouteCoordinate]:
        if not isinstance(payload, dict):
            raise RouteProviderError(
                "OSRM gaf geen geldig antwoord terug."
            )

        if payload.get("code") != "Ok":
            message = payload.get("message")

            if not isinstance(message, str):
                message = str(
                    payload.get(
                        "code",
                        "onbekende OSRM-fout",
                    )
                )

            raise RouteProviderError(
                f"OSRM kon geen route berekenen: {message}"
            )

        routes = payload.get("routes")

        if not isinstance(routes, list) or not routes:
            raise RouteProviderError(
                "OSRM gaf geen route terug."
            )

        first_route = routes[0]

        if not isinstance(first_route, dict):
            raise RouteProviderError(
                "OSRM gaf ongeldige routegegevens terug."
            )

        geometry = first_route.get("geometry")

        if not isinstance(geometry, dict):
            raise RouteProviderError(
                "OSRM-route bevat geen geometrie."
            )

        coordinates = geometry.get("coordinates")

        if not isinstance(coordinates, list):
            raise RouteProviderError(
                "OSRM-route bevat geen coördinaten."
            )

        result: list[RouteCoordinate] = []

        for coordinate in coordinates:
            if (
                not isinstance(coordinate, list)
                or len(coordinate) < 2
                or not isinstance(coordinate[0], (int, float))
                or not isinstance(coordinate[1], (int, float))
            ):
                raise RouteProviderError(
                    "OSRM-route bevat een ongeldige coördinaat."
                )

            longitude = float(coordinate[0])
            latitude = float(coordinate[1])

            result.append(
                RouteCoordinate(
                    latitude=latitude,
                    longitude=longitude,
                )
            )

        if len(result) < 2:
            raise RouteProviderError(
                "OSRM-route bevat onvoldoende coördinaten."
            )

        return result


class RouteService:
    """
    Calculates route geometry using a primary provider.

    When the primary provider fails, the direct provider keeps
    the map functional by drawing straight lines between stops.
    """

    def __init__(
        self,
        provider: RouteProvider | None = None,
        fallback_provider: RouteProvider | None = None,
    ) -> None:
        self.provider = provider or DirectRouteProvider()
        self.fallback_provider = (
            fallback_provider or DirectRouteProvider()
        )

    def set_provider(
        self,
        provider: RouteProvider,
    ) -> None:
        self.provider = provider

    @property
    def capabilities(self) -> RouteProviderCapabilities:
        """Return the capabilities of the active provider."""

        return self.provider.capabilities

    def calculate_route(
        self,
        stops: Sequence[Stop],
        profile: RoutingProfile = RoutingProfile.CAMPER,
        preferences: TravelPreferences | None = None,
    ) -> list[RouteCoordinate]:
        request = RoutingRequest.create(
            stops=stops,
            profile=profile,
            preferences=preferences,
        )

        try:
            return self.provider.calculate_route(request)
        except RouteProviderError:
            return self.fallback_provider.calculate_route(request)
