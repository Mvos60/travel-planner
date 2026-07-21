import pytest

from travel_planner.vehicle_profile import VehicleProfile


def test_vehicle_profile_generates_stable_identifier() -> None:
    profile = VehicleProfile(name="Hymer ML-T")

    assert profile.profile_id
    assert profile.name == "Hymer ML-T"


def test_vehicle_profile_stores_vehicle_dimensions() -> None:
    profile = VehicleProfile(
        name="Hymer ML-T",
        length_m=7.20,
        width_m=2.30,
        height_m=3.05,
        max_weight_kg=4100,
        emission_class="Euro 6",
    )

    assert profile.length_m == 7.20
    assert profile.width_m == 2.30
    assert profile.height_m == 3.05
    assert profile.max_weight_kg == 4100
    assert profile.emission_class == "Euro 6"


def test_vehicle_profile_round_trip_preserves_data() -> None:
    original = VehicleProfile(
        profile_id="hymer-mlt",
        name="Hymer ML-T",
        length_m=7.20,
        width_m=2.30,
        height_m=3.05,
        max_weight_kg=4100,
        emission_class="Euro 6",
    )

    restored = VehicleProfile.from_dict(
        original.to_dict()
    )

    assert restored == original


def test_vehicle_profile_accepts_missing_optional_values() -> None:
    profile = VehicleProfile.from_dict(
        {
            "name": "Future camper",
        }
    )

    assert profile.profile_id
    assert profile.length_m is None
    assert profile.width_m is None
    assert profile.height_m is None
    assert profile.max_weight_kg is None
    assert profile.emission_class is None


def test_vehicle_profile_rejects_empty_name() -> None:
    with pytest.raises(
        ValueError,
        match="name cannot be empty",
    ):
        VehicleProfile(name="   ")


def test_vehicle_profile_rejects_invalid_dimensions() -> None:
    with pytest.raises(
        ValueError,
        match="height_m must be greater than zero",
    ):
        VehicleProfile(
            name="Invalid camper",
            height_m=0,
        )
