from __future__ import annotations

import io
import json
from collections.abc import Sequence
from urllib.error import URLError
from urllib.request import Request

import pytest

from travel_planner.route_service import (
    DirectRouteProvider,
    OSRMRouteProvider,
    RouteCoordinate,
    RouteProviderError,
    RouteService,
)
from travel_planner.trip import Stop


class FakeResponse(io.BytesIO):
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()


class FailingProvider:
    def calculate_route(
        self,
        stops: Sequence[Stop],
    ) -> list[RouteCoordinate]:
        raise RouteProviderError("Provider niet beschikbaar")


def make_stops() -> list[Stop]:
    return [
        Stop(
            name="Ardèche",
            latitude=44.7350,
            longitude=4.6000,
            nights=1,
        ),
        Stop(
            name="Innsbruck",
            latitude=47.2692,
            longitude=11.4041,
            nights=2,
        ),
        Stop(
            name="Ljubljana",
            latitude=46.0569,
            longitude=14.5058,
            nights=3,
        ),
    ]


def test_direct_provider_returns_no_coordinates_for_empty_trip() -> None:
    provider = DirectRouteProvider()

    assert provider.calculate_route([]) == []


def test_direct_provider_preserves_stop_order() -> None:
    provider = DirectRouteProvider()

    route = provider.calculate_route(make_stops())

    assert route == [
        RouteCoordinate(44.7350, 4.6000),
        RouteCoordinate(47.2692, 11.4041),
        RouteCoordinate(46.0569, 14.5058),
    ]


def test_route_coordinate_can_be_serialized() -> None:
    coordinate = RouteCoordinate(
        latitude=46.0569,
        longitude=14.5058,
    )

    assert coordinate.to_dict() == {
        "latitude": 46.0569,
        "longitude": 14.5058,
    }


def test_osrm_provider_builds_driving_request() -> None:
    captured_request: Request | None = None
    captured_timeout: float | None = None

    payload = {
        "code": "Ok",
        "routes": [
            {
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [4.6000, 44.7350],
                        [8.2000, 46.1000],
                        [11.4041, 47.2692],
                    ],
                }
            }
        ],
    }

    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        nonlocal captured_request
        nonlocal captured_timeout

        captured_request = request
        captured_timeout = timeout

        return FakeResponse(
            json.dumps(payload).encode("utf-8")
        )

    provider = OSRMRouteProvider(
        base_url="https://example.test",
        timeout_seconds=4.5,
        opener=opener,
    )

    route = provider.calculate_route(make_stops()[:2])

    assert captured_request is not None
    assert captured_timeout == 4.5

    assert captured_request.full_url == (
        "https://example.test/route/v1/driving/"
        "4.6,44.735;11.4041,47.2692"
        "?overview=full&geometries=geojson&steps=false"
    )

    assert route == [
        RouteCoordinate(44.7350, 4.6000),
        RouteCoordinate(46.1000, 8.2000),
        RouteCoordinate(47.2692, 11.4041),
    ]


def test_osrm_provider_does_not_call_server_for_one_stop() -> None:
    called = False

    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        nonlocal called
        called = True
        raise AssertionError("OSRM should not be called")

    provider = OSRMRouteProvider(opener=opener)

    route = provider.calculate_route(make_stops()[:1])

    assert called is False
    assert route == [
        RouteCoordinate(44.7350, 4.6000)
    ]


def test_osrm_provider_rejects_no_route_response() -> None:
    payload = {
        "code": "NoRoute",
        "message": "Impossible route",
    }

    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(
            json.dumps(payload).encode("utf-8")
        )

    provider = OSRMRouteProvider(opener=opener)

    with pytest.raises(
        RouteProviderError,
        match="Impossible route",
    ):
        provider.calculate_route(make_stops()[:2])


def test_osrm_provider_wraps_network_error() -> None:
    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        raise URLError("offline")

    provider = OSRMRouteProvider(opener=opener)

    with pytest.raises(
        RouteProviderError,
        match="OSRM-route kon niet worden opgehaald",
    ):
        provider.calculate_route(make_stops()[:2])


def test_route_service_falls_back_to_direct_route() -> None:
    service = RouteService(
        provider=FailingProvider(),
        fallback_provider=DirectRouteProvider(),
    )

    route = service.calculate_route(make_stops())

    assert route == [
        RouteCoordinate(44.7350, 4.6000),
        RouteCoordinate(47.2692, 11.4041),
        RouteCoordinate(46.0569, 14.5058),
    ]


def test_public_osrm_request_does_not_exclude_motorways() -> None:
    captured_request: Request | None = None

    payload = {
        "code": "Ok",
        "routes": [
            {
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [4.6000, 44.7350],
                        [11.4041, 47.2692],
                    ],
                }
            }
        ],
    }

    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        nonlocal captured_request
        captured_request = request

        return FakeResponse(
            json.dumps(payload).encode("utf-8")
        )

    provider = OSRMRouteProvider(
        base_url="https://example.test",
        opener=opener,
        avoid_motorways=True,
    )

    provider.calculate_route(make_stops()[:2])

    assert captured_request is not None
    assert "exclude=" not in captured_request.full_url



def test_route_service_accepts_routing_profile() -> None:
    from travel_planner.routing_profile import RoutingProfile

    service = RouteService(
        provider=DirectRouteProvider(),
    )

    route = service.calculate_route(
        make_stops(),
        profile=RoutingProfile.PHOTOGRAPHER,
    )

    assert route == [
        RouteCoordinate(44.7350, 4.6000),
        RouteCoordinate(47.2692, 11.4041),
        RouteCoordinate(46.0569, 14.5058),
    ]
