from __future__ import annotations

import io
import json
from urllib.error import URLError
from urllib.request import Request

import pytest

from travel_planner.route_service import (
    BaseHttpRouteProvider,
    RouteProviderError,
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


def test_json_request_uses_standard_headers() -> None:
    provider = BaseHttpRouteProvider()

    request = provider._build_json_request(
        "https://example.test/route"
    )

    assert request.get_method() == "GET"
    assert request.data is None
    assert request.get_header("Accept") == "application/json"
    assert request.get_header("User-agent") is not None


def test_json_request_serializes_post_payload() -> None:
    provider = BaseHttpRouteProvider()

    request = provider._build_json_request(
        "https://example.test/route",
        method="POST",
        headers={
            "Authorization": "test-api-key",
        },
        payload={
            "coordinates": [
                [4.6, 44.735],
                [11.4041, 47.2692],
            ]
        },
    )

    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == (
        "test-api-key"
    )
    assert request.get_header("Content-type") == (
        "application/json"
    )
    assert request.data is not None

    assert json.loads(
        request.data.decode("utf-8")
    ) == {
        "coordinates": [
            [4.6, 44.735],
            [11.4041, 47.2692],
        ]
    }


def test_json_response_uses_configured_timeout() -> None:
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
            b'{"status": "ok"}'
        )

    provider = BaseHttpRouteProvider(
        timeout_seconds=7.5,
        opener=opener,
    )

    request = provider._build_json_request(
        "https://example.test/route"
    )

    payload = provider._load_json_response(
        request,
        provider_name="TestProvider",
    )

    assert captured_request is request
    assert captured_timeout == 7.5
    assert payload == {
        "status": "ok",
    }


def test_json_response_wraps_network_errors() -> None:
    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        raise URLError("offline")

    provider = BaseHttpRouteProvider(
        opener=opener,
    )

    request = provider._build_json_request(
        "https://example.test/route"
    )

    with pytest.raises(
        RouteProviderError,
        match=(
            "TestProvider-route kon niet worden opgehaald"
        ),
    ):
        provider._load_json_response(
            request,
            provider_name="TestProvider",
        )


def test_json_response_wraps_invalid_json() -> None:
    def opener(
        request: Request,
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(
            b"not valid json"
        )

    provider = BaseHttpRouteProvider(
        opener=opener,
    )

    request = provider._build_json_request(
        "https://example.test/route"
    )

    with pytest.raises(
        RouteProviderError,
        match=(
            "TestProvider-route kon niet worden opgehaald"
        ),
    ):
        provider._load_json_response(
            request,
            provider_name="TestProvider",
        )
