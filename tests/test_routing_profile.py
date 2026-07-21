from travel_planner.routing_profile import RoutingProfile


def test_profile_has_stable_storage_values() -> None:
    assert RoutingProfile.FASTEST.value == "fastest"
    assert RoutingProfile.CAMPER.value == "camper"
    assert (
        RoutingProfile.PHOTOGRAPHER.value
        == "photographer"
    )
    assert RoutingProfile.CUSTOM.value == "custom"


def test_profile_has_display_names() -> None:
    assert RoutingProfile.FASTEST.display_name == "Fastest"
    assert RoutingProfile.CAMPER.display_name == "Camper"
    assert (
        RoutingProfile.PHOTOGRAPHER.display_name
        == "Photographer"
    )
    assert RoutingProfile.CUSTOM.display_name == "Custom"


def test_unknown_profile_falls_back_to_camper() -> None:
    profile = RoutingProfile.from_value("unknown-profile")

    assert profile is RoutingProfile.CAMPER


def test_missing_profile_falls_back_to_camper() -> None:
    profile = RoutingProfile.from_value(None)

    assert profile is RoutingProfile.CAMPER
