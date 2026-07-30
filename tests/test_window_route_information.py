"""Tests for truthful route-information presentation."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WINDOW_SOURCE = (
    PROJECT_ROOT / "travel_planner" / "window.py"
).read_text(encoding="utf-8")
PANEL_SOURCE = (
    PROJECT_ROOT / "travel_planner" / "route_information_panel.py"
).read_text(encoding="utf-8")


def test_sidebar_uses_actual_paned_position() -> None:
    assert "content.set_position(400)" in WINDOW_SOURCE
    assert "content.set_resize_start_child(False)" in WINDOW_SOURCE
    assert "content.set_shrink_start_child(False)" in WINDOW_SOURCE
    assert "sidebar.set_size_request(360, -1)" not in WINDOW_SOURCE


def test_route_panel_wraps_values_without_left_clipping() -> None:
    assert "value_label.set_xalign(0)" in PANEL_SOURCE
    assert "value_label.set_wrap(True)" in PANEL_SOURCE
    assert (
        "value_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)"
        in PANEL_SOURCE
    )


def test_window_does_not_present_unverified_travel_time() -> None:
    assert "personal_duration=" not in WINDOW_SOURCE
    assert "realistic_duration=" not in WINDOW_SOURCE
    assert "_formatted_personal_route_duration" not in WINDOW_SOURCE
    assert "_formatted_realistic_route_duration" not in WINDOW_SOURCE


def test_panel_does_not_contain_unverified_time_row() -> None:
    assert "Jouw reistijd" not in PANEL_SOURCE
    assert "Realistische reistijd" not in PANEL_SOURCE
    assert "personal_duration" not in PANEL_SOURCE
    assert "realistic_duration" not in PANEL_SOURCE
