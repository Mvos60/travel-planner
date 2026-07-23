from __future__ import annotations

import io
import json

import pytest

from travel_planner.route_service import (
    OpenRouteServiceProvider,
    OSRMRouteProvider,
    RouteMetrics,
    RouteService,
    RoutingRequest,
)
from travel_planner.stop import Stop


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
            latitude=44.735,
            longitude=4.600,
        ),
        Stop(
            name="Innsbruck",
            latitude=47.2692,
            longitude=11.4041,
        ),
    ]


def test_route_metrics_exposes_kilometres() -> None:
    metrics = RouteMetrics(
        distance_meters=1_842_400,
        duration_seconds=101_700,
    )

    assert metrics.distance_km == pytest.approx(1842.4)


def test_osrm_stores_live_route_metrics() -> None:
    payload = {
        "code": "Ok",
        "routes": [
            {
                "distance": 1_842_400.0,
                "duration": 101_700.0,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [4.600, 44.735],
                        [11.4041, 47.2692],
                    ],
                },
            }
        ],
    }

    provider = OSRMRouteProvider(
        opener=lambda request, timeout: FakeResponse(
            json.dumps(payload).encode("utf-8")
        )
    )

    provider.calculate_route(
        RoutingRequest.create(make_stops())
    )

    assert provider.last_route_metrics == RouteMetrics(
        distance_meters=1_842_400.0,
        duration_seconds=101_700.0,
    )


def test_ors_stores_live_route_metrics() -> None:
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [4.600, 44.735],
                        [11.4041, 47.2692],
                    ],
                },
                "properties": {
                    "summary": {
                        "distance": 1_842_400.0,
                        "duration": 101_700.0,
                    }
                },
            }
        ],
    }

    provider = OpenRouteServiceProvider(
        api_key="test-key",
        opener=lambda request, timeout: FakeResponse(
            json.dumps(payload).encode("utf-8")
        ),
    )

    provider.calculate_route(
        RoutingRequest.create(make_stops())
    )

    assert provider.last_route_metrics == RouteMetrics(
        distance_meters=1_842_400.0,
        duration_seconds=101_700.0,
    )


def test_route_service_exposes_provider_metrics() -> None:
    class MetricsProvider:
        last_route_metrics = RouteMetrics(
            distance_meters=12_300,
            duration_seconds=900,
        )

        def calculate_route(self, request):
            return []

    service = RouteService(provider=MetricsProvider())

    service.calculate_route(make_stops())

    assert service.last_route_metrics == RouteMetrics(
        distance_meters=12_300,
        duration_seconds=900,
    )


def test_route_service_clears_metrics_on_provider_change() -> None:
    class Provider:
        last_route_metrics = RouteMetrics(
            distance_meters=1000,
            duration_seconds=60,
        )

        def calculate_route(self, request):
            return []

    service = RouteService(provider=Provider())

    service.calculate_route(make_stops())
    assert service.last_route_metrics is not None

    service.set_provider(Provider())

    assert service.last_route_metrics is None
