import io
import json

import pytest

from travel_planner.route_provider_manager import (
    RouteProviderManager,
)
from travel_planner.route_service import (
    OpenRouteServiceProvider,
    OSRMRouteProvider,
    RouteProviderError,
)


def _response(payload: object) -> io.BytesIO:
    return io.BytesIO(
        json.dumps(payload).encode("utf-8")
    )


def _osrm_payload() -> dict[str, object]:
    return {
        "code": "Ok",
        "routes": [
            {
                "geometry": {
                    "coordinates": [
                        [4.895168, 52.370216],
                        [4.899431, 52.379189],
                    ],
                },
            },
        ],
    }


def _ors_payload() -> dict[str, object]:
    return {
        "features": [
            {
                "geometry": {
                    "coordinates": [
                        [4.895168, 52.370216],
                        [4.899431, 52.379189],
                    ],
                },
            },
        ],
    }


def test_osrm_health_check_uses_provider() -> None:
    provider = OSRMRouteProvider(
        opener=lambda request, timeout: _response(
            _osrm_payload()
        )
    )

    provider.check_connection()


def test_openrouteservice_health_check_requires_key() -> None:
    provider = OpenRouteServiceProvider(
        api_key="",
        opener=lambda request, timeout: _response(
            _ors_payload()
        ),
    )

    with pytest.raises(
        RouteProviderError,
        match="API-key ontbreekt",
    ):
        provider.check_connection()


def test_openrouteservice_health_check_uses_key() -> None:
    captured_authorization = None

    def opener(request, timeout):
        nonlocal captured_authorization
        captured_authorization = request.get_header(
            "Authorization"
        )
        return _response(_ors_payload())

    provider = OpenRouteServiceProvider(
        api_key="test-key",
        opener=opener,
    )

    provider.check_connection()

    assert captured_authorization == "test-key"


def test_manager_restores_original_api_key() -> None:
    manager = RouteProviderManager(
        openrouteservice_api_key="saved-key"
    )
    provider = manager.provider("openrouteservice")

    assert isinstance(
        provider,
        OpenRouteServiceProvider,
    )

    provider.opener = lambda request, timeout: _response(
        _ors_payload()
    )

    manager.test_provider_connection(
        "openrouteservice",
        openrouteservice_api_key="temporary-key",
    )

    assert provider.api_key == "saved-key"
