from __future__ import annotations

from dataclasses import dataclass

from travel_planner.route_service import RouteProviderCapabilities
from travel_planner.travel_preferences import TravelPreferences
from travel_planner.vehicle_dimensions import VehicleDimensions


@dataclass(frozen=True)
class RoutingExplanation:
    """Human-readable explanation of active routing behaviour."""

    applied: tuple[str, ...] = ()
    unavailable: tuple[str, ...] = ()

    @property
    def applied_text(self) -> str:
        return ", ".join(self.applied) if self.applied else "Geen"

    @property
    def unavailable_text(self) -> str:
        return ", ".join(self.unavailable) if self.unavailable else "Geen"


def build_routing_explanation(
    *,
    preferences: TravelPreferences,
    vehicle_dimensions: VehicleDimensions | None,
    capabilities: RouteProviderCapabilities,
) -> RoutingExplanation:
    applied: list[str] = []
    unavailable: list[str] = []

    options = (
        (
            preferences.avoid_highways,
            capabilities.supports_avoid_highways,
            "snelwegen vermijden",
        ),
        (
            preferences.avoid_tolls,
            capabilities.supports_avoid_tolls,
            "tolwegen vermijden",
        ),
        (
            preferences.avoid_ferries,
            capabilities.supports_avoid_ferries,
            "veerponten vermijden",
        ),
        (
            (
                vehicle_dimensions is not None
                and not vehicle_dimensions.is_empty
            ),
            capabilities.supports_vehicle_dimensions,
            "voertuigafmetingen",
        ),
    )

    for requested, supported, description in options:
        if not requested:
            continue

        if supported:
            applied.append(description)
        else:
            unavailable.append(description)

    return RoutingExplanation(
        applied=tuple(applied),
        unavailable=tuple(unavailable),
    )
