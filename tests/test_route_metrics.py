import pytest

from travel_planner.route_metrics import (
    calculate_route_distance_km,
    calculate_segment_distance_km,
    format_distance_km,
)


def test_empty_route_has_zero_distance():
    assert calculate_route_distance_km([]) == 0.0


def test_single_coordinate_has_zero_distance():
    coordinates = [
        {
            "latitude": 52.0,
            "longitude": 5.0,
        }
    ]

    assert calculate_route_distance_km(coordinates) == 0.0


def test_segment_distance_supports_full_names():
    distance = calculate_segment_distance_km(
        {
            "latitude": 52.0,
            "longitude": 5.0,
        },
        {
            "latitude": 53.0,
            "longitude": 5.0,
        },
    )

    assert distance == pytest.approx(
        111.2,
        abs=0.2,
    )


def test_route_distance_adds_consecutive_segments():
    coordinates = [
        {
            "latitude": 52.0,
            "longitude": 5.0,
        },
        {
            "latitude": 53.0,
            "longitude": 5.0,
        },
        {
            "latitude": 54.0,
            "longitude": 5.0,
        },
    ]

    distance = calculate_route_distance_km(coordinates)

    assert distance == pytest.approx(
        222.4,
        abs=0.4,
    )


def test_short_coordinate_names_are_supported():
    distance = calculate_route_distance_km(
        [
            {
                "lat": 52.0,
                "lng": 5.0,
            },
            {
                "lat": 53.0,
                "lng": 5.0,
            },
        ]
    )

    assert distance > 111.0


def test_missing_coordinate_values_are_rejected():
    with pytest.raises(
        ValueError,
        match="latitude en longitude",
    ):
        calculate_route_distance_km(
            [
                {
                    "latitude": 52.0,
                },
                {
                    "latitude": 53.0,
                },
            ]
        )


@pytest.mark.parametrize(
    ("distance", "expected"),
    [
        (0.0, "0 km"),
        (12.4, "12 km"),
        (12.6, "13 km"),
        (2184.2, "2.184 km"),
    ],
)
def test_distance_formatting(
    distance,
    expected,
):
    assert format_distance_km(distance) == expected
