from travel_planner.route_cache import RouteCache
import travel_planner.route_service as route_service


def _install_fake_network(monkeypatch):
    calls = {"count": 0}

    def fake_network(self, *args, **kwargs):
        calls["count"] += 1
        return {
            "code": "Ok",
            "routes": [
                {
                    "distance": 1234.0,
                    "duration": 567.0,
                    "geometry": "encoded-route",
                }
            ],
        }

    monkeypatch.setattr(
        route_service,
        "_travel_planner_uncached_http_method",
        fake_network,
    )
    return calls


def test_identical_osrm_http_call_uses_cache(tmp_path, monkeypatch):
    calls = _install_fake_network(monkeypatch)
    provider = object.__new__(route_service.OSRMRouteProvider)
    provider._route_cache = RouteCache(tmp_path)

    method = getattr(provider, route_service._ROUTE_CACHE_HTTP_METHOD_NAME)

    first = method(
        "https://router.project-osrm.org/route/v1/driving/4,52;5,53",
        params={"overview": "full", "steps": False},
    )
    second = method(
        "https://router.project-osrm.org/route/v1/driving/4,52;5,53",
        params={"overview": "full", "steps": False},
    )

    assert first == second
    assert calls["count"] == 1
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_changed_osrm_request_bypasses_previous_cache(tmp_path, monkeypatch):
    calls = _install_fake_network(monkeypatch)
    provider = object.__new__(route_service.OSRMRouteProvider)
    provider._route_cache = RouteCache(tmp_path)

    method = getattr(provider, route_service._ROUTE_CACHE_HTTP_METHOD_NAME)

    method("https://example.test/route-a", params={"overview": "full"})
    method("https://example.test/route-b", params={"overview": "full"})

    assert calls["count"] == 2
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_openrouteservice_is_not_cached_in_this_sprint(tmp_path, monkeypatch):
    calls = _install_fake_network(monkeypatch)
    provider = object.__new__(route_service.OpenRouteServiceProvider)
    provider._route_cache = RouteCache(tmp_path)

    method = getattr(provider, route_service._ROUTE_CACHE_HTTP_METHOD_NAME)

    method("https://example.test/ors", payload={"coordinates": [[4, 52], [5, 53]]})
    method("https://example.test/ors", payload={"coordinates": [[4, 52], [5, 53]]})

    assert calls["count"] == 2
    assert list(tmp_path.glob("*.json")) == []


def test_cache_persists_between_provider_instances(tmp_path, monkeypatch):
    calls = _install_fake_network(monkeypatch)

    first_provider = object.__new__(route_service.OSRMRouteProvider)
    first_provider._route_cache = RouteCache(tmp_path)
    first_method = getattr(first_provider, route_service._ROUTE_CACHE_HTTP_METHOD_NAME)
    first_method("https://example.test/shared", params={"steps": False})

    second_provider = object.__new__(route_service.OSRMRouteProvider)
    second_provider._route_cache = RouteCache(tmp_path)
    second_method = getattr(second_provider, route_service._ROUTE_CACHE_HTTP_METHOD_NAME)
    second_method("https://example.test/shared", params={"steps": False})

    assert calls["count"] == 1
