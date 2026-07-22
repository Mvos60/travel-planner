"""Calculate useful metrics from route geometry."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from math import asin, cos, radians, sin, sqrt
from typing import Any


EARTH_RADIUS_KM = 6371.0088


def _coordinate_values(
    coordinate: Any,
) -> tuple[float, float]:
    """
    Return latitude and longitude from a route coordinate.

    Supported representations:
    - dictionaries with latitude/longitude
    - dictionaries with lat/lng or lat/lon
    - objects with matching attributes
    """

    if isinstance(coordinate, Mapping):
        latitude = coordinate.get(
            "latitude",
            coordinate.get("lat"),
        )
        longitude = coordinate.get(
            "longitude",
            coordinate.get(
                "lng",
                coordinate.get("lon"),
            ),
        )
    else:
        latitude = getattr(
            coordinate,
            "latitude",
            getattr(coordinate, "lat", None),
        )
        longitude = getattr(
            coordinate,
            "longitude",
            getattr(
                coordinate,
                "lng",
                getattr(coordinate, "lon", None),
            ),
        )

    if latitude is None or longitude is None:
        raise ValueError(
            "Routecoördinaat bevat geen geldige "
            "latitude en longitude."
        )

    return float(latitude), float(longitude)


def calculate_segment_distance_km(
    start: Any,
    end: Any,
) -> float:
    """Calculate the great-circle distance between two points."""

    start_latitude, start_longitude = (
        _coordinate_values(start)
    )
    end_latitude, end_longitude = (
        _coordinate_values(end)
    )

    latitude_delta = radians(
        end_latitude - start_latitude
    )
    longitude_delta = radians(
        end_longitude - start_longitude
    )

    start_latitude_radians = radians(start_latitude)
    end_latitude_radians = radians(end_latitude)

    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(start_latitude_radians)
        * cos(end_latitude_radians)
        * sin(longitude_delta / 2) ** 2
    )

    angular_distance = 2 * asin(
        sqrt(min(1.0, haversine))
    )

    return EARTH_RADIUS_KM * angular_distance


def calculate_route_distance_km(
    coordinates: Iterable[Any],
) -> float:
    """
    Calculate the total length of a route geometry.

    Consecutive route coordinates are measured and added
    together. An empty route or a route with one coordinate
    has a distance of zero.
    """

    coordinate_list = list(coordinates)

    return sum(
        calculate_segment_distance_km(start, end)
        for start, end in zip(
            coordinate_list,
            coordinate_list[1:],
        )
    )


def format_distance_km(distance_km: float) -> str:
    """Return a Dutch display value for a distance."""

    rounded_distance = round(distance_km)

    return f"{rounded_distance:,}".replace(",", ".") + " km"
