import pytest

from travel_planner.date_utils import (
    format_date_for_display,
    parse_display_date,
)


def test_parse_display_date_accepts_dutch_format() -> None:
    assert (
        parse_display_date("14-09-2026")
        == "2026-09-14"
    )


def test_parse_display_date_accepts_iso_format() -> None:
    assert (
        parse_display_date("2026-09-14")
        == "2026-09-14"
    )


def test_parse_display_date_ignores_whitespace() -> None:
    assert (
        parse_display_date(" 14-09-2026 ")
        == "2026-09-14"
    )


def test_parse_display_date_accepts_empty_value() -> None:
    assert parse_display_date("") is None
    assert parse_display_date("   ") is None


def test_parse_display_date_rejects_invalid_date() -> None:
    with pytest.raises(
        ValueError,
        match="DD-MM-JJJJ",
    ):
        parse_display_date("31-02-2026")


def test_format_date_for_display() -> None:
    assert (
        format_date_for_display("2026-09-14")
        == "14-09-2026"
    )


def test_format_date_for_display_accepts_none() -> None:
    assert format_date_for_display(None) == ""


def test_format_date_rejects_invalid_iso_date() -> None:
    with pytest.raises(
        ValueError,
        match="Ongeldige interne ISO-datum",
    ):
        format_date_for_display("14-09-2026")
