from __future__ import annotations

import io
import json
from urllib.request import Request

import pytest

from travel_planner.route_service import (
    OpenRouteServiceProvider,
    RouteCoordinate,
    RouteProviderError,
    RoutingRequest,
)
from travel_planner.stop import Stop
from travel_planner.travel_preferences import (
    TravelPreferences,
)


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
    ]


def successful_payload() -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [4.6000, 44.7350],
                        [8.2000, 46.1000],
                        [11.4041, 47.2692],
                    ],
                },
                "properties": {},
            }
        ],
    }


def test_ors_builds_post_geojson_request() -> None:
    captured_request: Request | None = None
    captured_timeout: float | None = None

    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        nonlocal captured_request
        nonlocal captured_timeout

        captured_request = request
        captured_timeout = timeout

        return FakeResponse(
            json.dumps(
                successful_payload()
            ).encode("utf-8")
        )

    provider = OpenRouteServiceProvider(
        api_key="secret-key",
        base_url="https://example.test",
        timeout_seconds=6.5,
        opener=opener,
    )

    route = provider.calculate_route(
        RoutingRequest.create(make_stops())
    )

    assert captured_request is not None
    assert captured_timeout == 6.5
    assert captured_request.get_method() == "POST"

    assert captured_request.full_url == (
        "https://example.test/v2/directions/"
        "driving-car/geojson"
    )

    assert captured_request.get_header(
        "Authorization"
    ) == "secret-key"

    assert captured_request.data is not None

    assert json.loads(
        captured_request.data.decode("utf-8")
    ) == {
        "coordinates": [
            [4.6, 44.735],
            [11.4041, 47.2692],
        ]
    }

    assert route == [
        RouteCoordinate(44.7350, 4.6000),
        RouteCoordinate(46.1000, 8.2000),
        RouteCoordinate(47.2692, 11.4041),
    ]


def test_ors_translates_route_preferences() -> None:
    captured_request: Request | None = None

    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        nonlocal captured_request
        captured_request = request

        return FakeResponse(
            json.dumps(
                successful_payload()
            ).encode("utf-8")
        )

    provider = OpenRouteServiceProvider(
        api_key="secret-key",
        opener=opener,
    )

    request = RoutingRequest.create(
        make_stops(),
        preferences=TravelPreferences(
            avoid_highways=True,
            avoid_tolls=True,
            avoid_ferries=True,
        ),
    )

    provider.calculate_route(request)

    assert captured_request is not None
    assert captured_request.data is not None

    payload = json.loads(
        captured_request.data.decode("utf-8")
    )

    assert payload["options"] == {
        "avoid_features": [
            "highways",
            "tollways",
            "ferries",
        ]
    }


def test_ors_omits_empty_options() -> None:
    captured_request: Request | None = None

    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        nonlocal captured_request
        captured_request = request

        return FakeResponse(
            json.dumps(
                successful_payload()
            ).encode("utf-8")
        )

    provider = OpenRouteServiceProvider(
        api_key="secret-key",
        opener=opener,
    )

    provider.calculate_route(
        RoutingRequest.create(make_stops())
    )

    assert captured_request is not None
    assert captured_request.data is not None

    payload = json.loads(
        captured_request.data.decode("utf-8")
    )

    assert "options" not in payload


def test_ors_reads_api_key_from_environment(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "OPENROUTESERVICE_API_KEY",
        "environment-key",
    )

    provider = OpenRouteServiceProvider()

    assert provider.api_key == "environment-key"


def test_ors_rejects_missing_api_key(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "OPENROUTESERVICE_API_KEY",
        raising=False,
    )

    provider = OpenRouteServiceProvider()

    with pytest.raises(
        RouteProviderError,
        match="API-key ontbreekt",
    ):
        provider.calculate_route(
            RoutingRequest.create(make_stops())
        )


def test_ors_does_not_need_key_for_one_stop(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "OPENROUTESERVICE_API_KEY",
        raising=False,
    )

    provider = OpenRouteServiceProvider()

    route = provider.calculate_route(
        RoutingRequest.create(make_stops()[:1])
    )

    assert route == [
        RouteCoordinate(44.7350, 4.6000),
    ]


def test_ors_reports_provider_error() -> None:
    payload = {
        "error": {
            "message": "Route could not be found",
        }
    }

    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(
            json.dumps(payload).encode("utf-8")
        )

    provider = OpenRouteServiceProvider(
        api_key="secret-key",
        opener=opener,
    )

    with pytest.raises(
        RouteProviderError,
        match="Route could not be found",
    ):
        provider.calculate_route(
            RoutingRequest.create(make_stops())
        )


def test_ors_capabilities_include_avoid_options() -> None:
    capabilities = (
        OpenRouteServiceProvider.capabilities
    )

    assert capabilities.supports_avoid_highways is True
    assert capabilities.supports_avoid_tolls is True
    assert capabilities.supports_avoid_ferries is True
    assert capabilities.supports_vehicle_dimensions is False
