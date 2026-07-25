import pytest

from travel_planner.vehicle_dimensions import VehicleDimensions


def test_vehicle_dimensions_defaults_to_empty() -> None:
    dimensions = VehicleDimensions()

    assert dimensions.is_empty
    assert dimensions.to_dict() == {
        "length_m": None,
        "width_m": None,
        "height_m": None,
        "weight_kg": None,
    }


def test_vehicle_dimensions_store_values() -> None:
    dimensions = VehicleDimensions(
        length_m=7.20,
        width_m=2.30,
        height_m=3.05,
        weight_kg=3500,
    )

    assert not dimensions.is_empty
    assert dimensions.to_dict() == {
        "length_m": 7.20,
        "width_m": 2.30,
        "height_m": 3.05,
        "weight_kg": 3500,
    }


@pytest.mark.parametrize(
    "field_name",
    (
        "length_m",
        "width_m",
        "height_m",
        "weight_kg",
    ),
)
def test_vehicle_dimensions_reject_non_positive_values(
    field_name: str,
) -> None:
    with pytest.raises(ValueError):
        VehicleDimensions(**{field_name: 0})


def test_vehicle_dimensions_can_load_dict() -> None:
    dimensions = VehicleDimensions.from_dict(
        {
            "length_m": 7.2,
            "width_m": 2.3,
            "height_m": 3.05,
            "weight_kg": 3500,
        }
    )

    assert dimensions == VehicleDimensions(
        length_m=7.2,
        width_m=2.3,
        height_m=3.05,
        weight_kg=3500.0,
    )
