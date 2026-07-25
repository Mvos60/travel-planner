from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_window_resolves_selected_vehicle_profile() -> None:
    source = (
        PROJECT_ROOT
        / "travel_planner"
        / "window.py"
    ).read_text(encoding="utf-8")

    assert "def _current_vehicle_dimensions(self):" in source
    assert (
        "self.context.vehicle_profile_repository.get("
        in source
    )
    assert "return profile.to_vehicle_dimensions()" in source


def test_window_passes_vehicle_dimensions_to_route_service() -> None:
    source = (
        PROJECT_ROOT
        / "travel_planner"
        / "window.py"
    ).read_text(encoding="utf-8")

    assert (
        "vehicle_dimensions=(\n"
        "                    self._current_vehicle_dimensions()\n"
        "                ),"
    ) in source
