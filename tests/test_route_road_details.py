"""Tests for provider-reported road-detail metadata."""

from __future__ import annotations

import io
import json

from travel_planner.route_service import (
    OpenRouteServiceProvider,
    RouteExtraInfo,
    RouteExtraSummary,
    RouteMetrics,
    RouteRoadDetails,
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


def detailed_payload() -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [4.600, 44.735],
                        [8.200, 46.100],
                        [11.4041, 47.2692],
                    ],
                },
                "properties": {
                    "summary": {
                        "distance": 3000.0,
                        "duration": 300.0,
                    },
                    "segments": [
                        {
                            "distance": 1000.0,
                            "duration": 100.0,
                            "avgspeed": 36.0,
                        },
                        {
                            "distance": 2000.0,
                            "duration": 200.0,
                            "avgspeed": 36.0,
                        },
                    ],
                    "extras": {
                        "waycategory": {
                            "values": [
                                [0, 1, 1],
                                [1, 2, 0],
                            ],
                            "summary": [
                                {
                                    "value": 1,
                                    "distance": 1500.0,
                                    "amount": 50.0,
                                },
                                {
                                    "value": 0,
                                    "distance": 1500.0,
                                    "amount": 50.0,
                                },
                            ],
                        },
                        "waytype": {
                            "values": [
                                [0, 1, 1],
                                [1, 2, 3],
                            ],
                            "summary": [
                                {
                                    "value": 1,
                                    "distance": 2000.0,
                                    "amount": 66.67,
                                },
                                {
                                    "value": 3,
                                    "distance": 1000.0,
                                    "amount": 33.33,
                                },
                            ],
                        },
                    },
                },
            }
        ],
    }


def test_route_metrics_keeps_road_details_optional() -> None:
    metrics = RouteMetrics(
        distance_meters=1000.0,
        duration_seconds=60.0,
    )

    assert metrics.road_details is None


def test_ors_preserves_returned_road_details() -> None:
    provider = OpenRouteServiceProvider(
        api_key="test-key",
        opener=lambda request, timeout: FakeResponse(
            json.dumps(detailed_payload()).encode("utf-8")
        ),
    )

    provider.calculate_route(
        RoutingRequest.create(make_stops())
    )

    assert provider.last_route_metrics == RouteMetrics(
        distance_meters=3000.0,
        duration_seconds=300.0,
        road_details=RouteRoadDetails(
            extras=(
                RouteExtraInfo(
                    name="waycategory",
                    summary=(
                        RouteExtraSummary(
                            value=1,
                            distance_meters=1500.0,
                            amount_percent=50.0,
                        ),
                        RouteExtraSummary(
                            value=0,
                            distance_meters=1500.0,
                            amount_percent=50.0,
                        ),
                    ),
                ),
                RouteExtraInfo(
                    name="waytype",
                    summary=(
                        RouteExtraSummary(
                            value=1,
                            distance_meters=2000.0,
                            amount_percent=66.67,
                        ),
                        RouteExtraSummary(
                            value=3,
                            distance_meters=1000.0,
                            amount_percent=33.33,
                        ),
                    ),
                ),
            ),
            segment_average_speeds_kmh=(
                36.0,
                36.0,
            ),
        ),
    )


def test_ors_without_details_keeps_none() -> None:
    payload = detailed_payload()
    feature = payload["features"][0]
    properties = feature["properties"]
    properties.pop("segments")
    properties.pop("extras")

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
        distance_meters=3000.0,
        duration_seconds=300.0,
        road_details=None,
    )


def test_malformed_extra_rows_are_ignored() -> None:
    payload = detailed_payload()
    feature = payload["features"][0]
    properties = feature["properties"]
    properties["extras"]["waytype"]["summary"].append(
        {
            "value": "unknown",
            "distance": 12.0,
            "amount": 1.0,
        }
    )

    provider = OpenRouteServiceProvider(
        api_key="test-key",
        opener=lambda request, timeout: FakeResponse(
            json.dumps(payload).encode("utf-8")
        ),
    )

    provider.calculate_route(
        RoutingRequest.create(make_stops())
    )

    assert provider.last_route_metrics is not None
    details = provider.last_route_metrics.road_details

    assert details is not None
    waytype = next(
        extra
        for extra in details.extras
        if extra.name == "waytype"
    )
    assert len(waytype.summary) == 2
