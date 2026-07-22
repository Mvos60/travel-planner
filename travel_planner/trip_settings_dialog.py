"""Dialog for editing settings of the current trip."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from travel_planner.date_utils import (
    format_date_for_display,
    parse_display_date,
)
from travel_planner.trip_settings import TripSettings


class TripSettingsDialog(Gtk.Dialog):
    """Edit flexible planning settings for one trip."""

    def __init__(
        self,
        parent: Gtk.Window,
        *,
        trip_name: str,
        settings: TripSettings,
    ) -> None:
        super().__init__(
            title="Reisinstellingen",
            transient_for=parent,
            modal=True,
        )

        self.original_settings = settings

        self.trip_name_entry = Gtk.Entry()
        self.trip_name_entry.set_hexpand(True)
        self.trip_name_entry.set_width_chars(28)
        self.trip_name_entry.set_text(trip_name)

        self.add_button(
            "Annuleren",
            Gtk.ResponseType.CANCEL,
        )
        self.add_button(
            "Opslaan",
            Gtk.ResponseType.OK,
        )

        self.start_date_entry = Gtk.Entry()
        self.start_date_entry.set_width_chars(18)
        self.start_date_entry.set_placeholder_text(
            "DD-MM-JJJJ"
        )
        self.start_date_entry.set_text(
            format_date_for_display(
                settings.planned_start_date
            )
        )

        self.duration_spin = Gtk.SpinButton.new_with_range(
            1,
            3650,
            1,
        )
        self.duration_spin.set_value(
            settings.planned_duration_days
        )

        self.shift_dates_check = Gtk.CheckButton(
            label=(
                "Datums van volgende stops automatisch "
                "doorschuiven"
            )
        )
        self.shift_dates_check.set_active(
            settings.shift_following_dates
        )

        self.error_label = Gtk.Label()
        self.error_label.set_xalign(0)
        self.error_label.set_wrap(True)
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)

        self._build_layout()

    def _build_layout(self) -> None:
        content_box = self.get_content_area()
        content_box.set_spacing(12)
        content_box.set_margin_top(18)
        content_box.set_margin_bottom(18)
        content_box.set_margin_start(18)
        content_box.set_margin_end(18)

        explanation = Gtk.Label(
            label=(
                "Deze instellingen zijn richtlijnen. "
                "De reis blijft altijd vrij aanpasbaar."
            )
        )
        explanation.set_xalign(0)
        explanation.set_wrap(True)

        grid = Gtk.Grid(
            column_spacing=12,
            row_spacing=12,
        )

        name_label = Gtk.Label(
            label="Reisnaam"
        )
        name_label.set_xalign(0)

        start_label = Gtk.Label(
            label="Geplande startdatum"
        )
        start_label.set_xalign(0)

        duration_label = Gtk.Label(
            label="Gewenste reisduur"
        )
        duration_label.set_xalign(0)

        days_label = Gtk.Label(label="dagen")
        days_label.set_xalign(0)

        grid.attach(
            name_label,
            0,
            0,
            1,
            1,
        )
        grid.attach(
            self.trip_name_entry,
            1,
            0,
            2,
            1,
        )

        grid.attach(
            start_label,
            0,
            1,
            1,
            1,
        )
        grid.attach(
            self.start_date_entry,
            1,
            1,
            2,
            1,
        )

        grid.attach(
            duration_label,
            0,
            2,
            1,
            1,
        )
        grid.attach(
            self.duration_spin,
            1,
            2,
            1,
            1,
        )
        grid.attach(
            days_label,
            2,
            2,
            1,
            1,
        )

        grid.attach(
            self.shift_dates_check,
            0,
            3,
            3,
            1,
        )

        content_box.append(explanation)
        content_box.append(grid)
        content_box.append(self.error_label)

    def get_trip_name(self) -> str:
        """Return the validated trip name."""

        trip_name = self.trip_name_entry.get_text().strip()

        if not trip_name:
            raise ValueError(
                "De reisnaam mag niet leeg zijn."
            )

        return trip_name

    def get_settings(self) -> TripSettings:
        """
        Return validated settings from the dialog fields.

        Raises ValueError when the entered start date is invalid.
        """

        planned_start_date = parse_display_date(
            self.start_date_entry.get_text()
        )

        return TripSettings(
            planned_duration_days=(
                self.duration_spin.get_value_as_int()
            ),
            planned_start_date=planned_start_date,
            shift_following_dates=(
                self.shift_dates_check.get_active()
            ),
        )

    def show_validation_error(
        self,
        message: str,
    ) -> None:
        """Show a validation message inside the dialog."""

        self.error_label.set_text(message)
        self.error_label.set_visible(True)
