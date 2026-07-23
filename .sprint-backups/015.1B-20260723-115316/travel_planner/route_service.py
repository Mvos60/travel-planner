from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from travel_planner.route_cache import (
    RouteCache,
    build_route_cache_key,
)
from travel_planner.routing_profile import RoutingProfile
from travel_planner.stop import Stop
from travel_planner.travel_preferences import TravelPreferences


DEFAULT_OSRM_BASE_URL = "https://router.project-osrm.org"
DEFAULT_ORS_BASE_URL = "https://api.openrouteservice.org"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_USER_AGENT = (
    "TravelPlanner/0.1 "
    "(desktop route-planning application)"
)


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

    def check_connection(self) -> None:
        """Verify that the route provider is reachable."""


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

    def check_connection(self) -> None:
        """The direct provider does not require a network."""


class BaseHttpRouteProvider:
    """
    Shared HTTP and JSON support for online route providers.

    Concrete providers remain responsible for:
    - choosing the endpoint;
    - constructing the request data;
    - interpreting the provider response.
    """

    def __init__(
        self,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Callable[..., object] = urlopen,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.opener = opener

    def _build_json_request(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: Mapping[str, str] | None = None,
        payload: object | None = None,
    ) -> Request:
        """
        Build an HTTP request that accepts JSON.

        When a payload is supplied, it is serialized as JSON and
        the Content-Type header is added automatically.
        """

        request_headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json",
        }

        if headers is not None:
            request_headers.update(headers)

        request_data: bytes | None = None

        if payload is not None:
            request_data = json.dumps(payload).encode("utf-8")
            request_headers.setdefault(
                "Content-Type",
                "application/json",
            )

        return Request(
            url=url,
            data=request_data,
            headers=request_headers,
            method=method,
        )

    def _load_json_response(
        self,
        request: Request,
        *,
        provider_name: str,
    ) -> Any:
        """
        Execute an HTTP request and decode its JSON response.

        Network, timeout, operating-system and malformed-JSON
        errors are converted to a consistent RouteProviderError.
        """

        try:
            response = self.opener(
                request,
                timeout=self.timeout_seconds,
            )

            with response:
                return json.load(response)
        except (
            HTTPError,
            URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise RouteProviderError(
                f"{provider_name}-route kon niet worden "
                f"opgehaald: {exc}"
            ) from exc


class OSRMRouteProvider(BaseHttpRouteProvider):
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
        route_cache: RouteCache | None = None,
    ) -> None:
        super().__init__(
            timeout_seconds=timeout_seconds,
            opener=opener,
        )

        self.base_url = base_url.rstrip("/")
        self.avoid_motorways = avoid_motorways

        self.route_cache = (
            route_cache
            if route_cache is not None
            else RouteCache()
            if opener is urlopen
            else None
        )

    def calculate_route(
        self,
        request: RoutingRequest,
    ) -> list[RouteCoordinate]:
        stops = request.stops

        if len(stops) < 2:
            return DirectRouteProvider().calculate_route(request)

        route_url = self._build_route_url(stops)
        cache_key = build_route_cache_key(
            provider="osrm",
            profile="driving",
            coordinates=[
                (stop.longitude, stop.latitude)
                for stop in stops
            ],
            options={
                "base_url": self.base_url,
                "avoid_motorways": self.avoid_motorways,
            },
        )

        payload: object | None = None

        if self.route_cache is not None:
            cached = self.route_cache.get(cache_key)
            if cached is not None:
                payload = cached.get("response")

        if payload is None:
            http_request = self._build_json_request(route_url)
            payload = self._load_json_response(
                http_request,
                provider_name="OSRM",
            )

            if (
                self.route_cache is not None
                and isinstance(payload, dict)
            ):
                self.route_cache.put(
                    cache_key,
                    {"response": payload},
                )

        return self._parse_response(payload)

    def check_connection(self) -> None:
        """Test the public OSRM route service."""

        url = (
            f"{self.base_url}/route/v1/driving/"
            "4.895168,52.370216;"
            "4.899431,52.379189"
            "?overview=full&geometries=geojson&steps=false"
        )

        payload = self._load_json_response(
            self._build_json_request(url),
            provider_name="OSRM",
        )

        self._parse_response(payload)

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
                or not isinstance(
                    coordinate[0],
                    (int, float),
                )
                or not isinstance(
                    coordinate[1],
                    (int, float),
                )
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


class OpenRouteServiceProvider(BaseHttpRouteProvider):
    """Calculate driving routes using OpenRouteService."""

    capabilities = RouteProviderCapabilities(
        supports_avoid_highways=True,
        supports_avoid_tolls=True,
        supports_avoid_ferries=True,
        supports_vehicle_dimensions=False,
    )

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_ORS_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Callable[..., object] = urlopen,
    ) -> None:
        super().__init__(
            timeout_seconds=timeout_seconds,
            opener=opener,
        )

        self.api_key = (
            api_key
            if api_key is not None
            else os.environ.get(
                "OPENROUTESERVICE_API_KEY",
                "",
            )
        ).strip()

        self.base_url = base_url.rstrip("/")

    def calculate_route(
        self,
        request: RoutingRequest,
    ) -> list[RouteCoordinate]:
        if len(request.stops) < 2:
            return DirectRouteProvider().calculate_route(request)

        if not self.api_key:
            raise RouteProviderError(
                "OpenRouteService API-key ontbreekt."
            )

        http_request = self._build_json_request(
            self._build_route_url(),
            method="POST",
            headers={
                "Authorization": self.api_key,
            },
            payload=self._build_payload(request),
        )

        payload = self._load_json_response(
            http_request,
            provider_name="OpenRouteService",
        )

        return self._parse_response(payload)

    def check_connection(self) -> None:
        """Test OpenRouteService and validate its API-key."""

        if not self.api_key:
            raise RouteProviderError(
                "OpenRouteService API-key ontbreekt."
            )

        payload = self._load_json_response(
            self._build_json_request(
                self._build_route_url(),
                method="POST",
                headers={
                    "Authorization": self.api_key,
                },
                payload={
                    "coordinates": [
                        [4.895168, 52.370216],
                        [4.899431, 52.379189],
                    ],
                },
            ),
            provider_name="OpenRouteService",
        )

        self._parse_response(payload)

    def _build_route_url(self) -> str:
        return (
            f"{self.base_url}/v2/directions/"
            "driving-car/geojson"
        )

    def _build_payload(
        self,
        request: RoutingRequest,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "coordinates": [
                [
                    stop.longitude,
                    stop.latitude,
                ]
                for stop in request.stops
            ],
        }

        avoid_features: list[str] = []

        if request.preferences.avoid_highways:
            avoid_features.append("highways")

        if request.preferences.avoid_tolls:
            avoid_features.append("tollways")

        if request.preferences.avoid_ferries:
            avoid_features.append("ferries")

        if avoid_features:
            payload["options"] = {
                "avoid_features": avoid_features,
            }

        return payload

    def _parse_response(
        self,
        payload: object,
    ) -> list[RouteCoordinate]:
        if not isinstance(payload, dict):
            raise RouteProviderError(
                "OpenRouteService gaf geen geldig antwoord terug."
            )

        features = payload.get("features")

        if not isinstance(features, list) or not features:
            message = self._extract_error_message(payload)

            raise RouteProviderError(
                "OpenRouteService kon geen route berekenen: "
                f"{message}"
            )

        first_feature = features[0]

        if not isinstance(first_feature, dict):
            raise RouteProviderError(
                "OpenRouteService gaf ongeldige routegegevens terug."
            )

        geometry = first_feature.get("geometry")

        if not isinstance(geometry, dict):
            raise RouteProviderError(
                "OpenRouteService-route bevat geen geometrie."
            )

        coordinates = geometry.get("coordinates")

        if not isinstance(coordinates, list):
            raise RouteProviderError(
                "OpenRouteService-route bevat geen coördinaten."
            )

        result: list[RouteCoordinate] = []

        for coordinate in coordinates:
            if (
                not isinstance(coordinate, list)
                or len(coordinate) < 2
                or not isinstance(
                    coordinate[0],
                    (int, float),
                )
                or not isinstance(
                    coordinate[1],
                    (int, float),
                )
            ):
                raise RouteProviderError(
                    "OpenRouteService-route bevat een "
                    "ongeldige coördinaat."
                )

            result.append(
                RouteCoordinate(
                    latitude=float(coordinate[1]),
                    longitude=float(coordinate[0]),
                )
            )

        if len(result) < 2:
            raise RouteProviderError(
                "OpenRouteService-route bevat onvoldoende "
                "coördinaten."
            )

        return result

    def _extract_error_message(
        self,
        payload: dict[str, object],
    ) -> str:
        error = payload.get("error")

        if isinstance(error, dict):
            message = error.get("message")

            if isinstance(message, str):
                return message

        if isinstance(error, str):
            return error

        message = payload.get("message")

        if isinstance(message, str):
            return message

        return "geen route ontvangen"


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
