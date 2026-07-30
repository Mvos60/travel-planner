# Regression tests for Dutch Custom route-profile labels.

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _window_source() -> str:
    return (
        PROJECT_ROOT / "travel_planner" / "window.py"
    ).read_text(encoding="utf-8")


def test_custom_travel_preference_labels_are_dutch() -> None:
    source = _window_source()

    assert 'label="Reisvoorkeuren"' in source
    assert '"Snelwegen vermijden"' in source
    assert '"Tolwegen vermijden"' in source
    assert '"Veerboten vermijden"' in source

    assert 'label="Travel Preferences"' not in source
    assert '"Avoid highways"' not in source
    assert '"Avoid toll roads"' not in source
    assert '"Avoid ferries"' not in source


def test_custom_preferences_remain_editable_for_all_providers() -> None:
    source = _window_source()

    assert "checkbox.set_sensitive(True)" in source
    assert "checkbox.set_sensitive(supported)" not in source
    assert (
        '"Deze voorkeur wordt opgeslagen, maar "'
        in source
    )
    assert (
        '"de huidige routeprovider ondersteunt "'
        in source
    )
