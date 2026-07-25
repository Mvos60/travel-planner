from travel_planner.route_information_panel import (
    ROUTE_INFORMATION_ROWS,
)


def test_route_information_rows_have_stable_order() -> None:
    assert ROUTE_INFORMATION_ROWS == (
        ("distance", "Afstand"),
        ("duration", "Rijtijd (provider)"),
        ("personal_duration", "Jouw reistijd"),
        ("provider", "Provider"),
        ("profile", "Profiel"),
        ("applied", "Toegepast"),
        ("unavailable", "Niet toegepast"),
    )


def test_route_information_keys_are_unique() -> None:
    keys = [key for key, _caption in ROUTE_INFORMATION_ROWS]

    assert len(keys) == len(set(keys))
