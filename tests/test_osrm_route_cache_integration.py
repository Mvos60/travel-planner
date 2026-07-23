from __future__ import annotations

import io
import json
from urllib.request import Request

from travel_planner.route_cache import RouteCache
from travel_planner.route_service import (
    OSRMRouteProvider,
    RoutingRequest,
)
from travel_planner.stop import Stop


class FakeResponse(io.BytesIO):
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def _stops() -> list[Stop]:
    return [
        Stop(
            name="Start",
            latitude=44.7350,
            longitude=4.6000,
        ),
        Stop(
            name="Finish",
            latitude=47.2692,
            longitude=11.4041,
        ),
    ]


def _payload() -> dict[str, object]:
    return {
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


def test_identical_osrm_route_uses_cached_response(tmp_path) -> None:
    calls = {"count": 0}

    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        calls["count"] += 1
        return FakeResponse(
            json.dumps(_payload()).encode("utf-8")
        )

    provider = OSRMRouteProvider(
        base_url="https://cache-test.invalid",
        opener=opener,
        route_cache=RouteCache(tmp_path),
    )
    request = RoutingRequest.create(_stops())

    first = provider.calculate_route(request)
    second = provider.calculate_route(request)

    assert first == second
    assert calls["count"] == 1
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_cache_survives_new_provider_instance(tmp_path) -> None:
    calls = {"count": 0}

    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        calls["count"] += 1
        return FakeResponse(
            json.dumps(_payload()).encode("utf-8")
        )

    request = RoutingRequest.create(_stops())

    first_provider = OSRMRouteProvider(
        base_url="https://cache-test.invalid",
        opener=opener,
        route_cache=RouteCache(tmp_path),
    )
    first_provider.calculate_route(request)

    second_provider = OSRMRouteProvider(
        base_url="https://cache-test.invalid",
        opener=opener,
        route_cache=RouteCache(tmp_path),
    )
    second_provider.calculate_route(request)

    assert calls["count"] == 1


def test_changed_route_creates_new_cache_entry(tmp_path) -> None:
    calls = {"count": 0}

    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        calls["count"] += 1
        return FakeResponse(
            json.dumps(_payload()).encode("utf-8")
        )

    provider = OSRMRouteProvider(
        base_url="https://cache-test.invalid",
        opener=opener,
        route_cache=RouteCache(tmp_path),
    )

    provider.calculate_route(
        RoutingRequest.create(_stops())
    )

    changed_stops = _stops()
    changed_stops[1] = Stop(
        name="Different finish",
        latitude=46.0569,
        longitude=14.5058,
    )
    provider.calculate_route(
        RoutingRequest.create(changed_stops)
    )

    assert calls["count"] == 2
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_custom_opener_has_no_implicit_persistent_cache() -> None:
    calls = {"count": 0}

    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        calls["count"] += 1
        return FakeResponse(
            json.dumps(_payload()).encode("utf-8")
        )

    provider = OSRMRouteProvider(
        base_url="https://isolated-test.invalid",
        opener=opener,
    )
    request = RoutingRequest.create(_stops())

    provider.calculate_route(request)
    provider.calculate_route(request)

    assert calls["count"] == 2
