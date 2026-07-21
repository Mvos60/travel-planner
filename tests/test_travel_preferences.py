from travel_planner.travel_preferences import (
    TravelPreferences,
)


def test_default_travel_preferences_are_disabled() -> None:
    preferences = TravelPreferences()

    assert preferences.avoid_highways is False
    assert preferences.avoid_tolls is False
    assert preferences.avoid_ferries is False


def test_travel_preferences_convert_to_dict() -> None:
    preferences = TravelPreferences(
        avoid_highways=True,
        avoid_tolls=True,
        avoid_ferries=False,
    )

    assert preferences.to_dict() == {
        "avoid_highways": True,
        "avoid_tolls": True,
        "avoid_ferries": False,
    }


def test_travel_preferences_load_from_dict() -> None:
    preferences = TravelPreferences.from_dict(
        {
            "avoid_highways": True,
            "avoid_tolls": False,
            "avoid_ferries": True,
        }
    )

    assert preferences.avoid_highways is True
    assert preferences.avoid_tolls is False
    assert preferences.avoid_ferries is True


def test_missing_travel_preferences_use_defaults() -> None:
    assert TravelPreferences.from_dict(None) == (
        TravelPreferences()
    )


def test_unknown_fields_are_ignored() -> None:
    preferences = TravelPreferences.from_dict(
        {
            "avoid_highways": True,
            "future_option": True,
        }
    )

    assert preferences == TravelPreferences(
        avoid_highways=True,
    )
