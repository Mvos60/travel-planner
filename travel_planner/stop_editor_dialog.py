"""Dialog for creating and editing travel stops."""

from __future__ import annotations

from datetime import date, timedelta

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from travel_planner.stop import Stop


class StopEditorDialog(Gtk.Dialog):
    """Create or edit one canonical Stop object."""

    def __init__(
        self,
        parent: Gtk.Window,
        *,
        stop: Stop | None = None,
        initial_title: str | None = None,
        initial_latitude: float | None = None,
        initial_longitude: float | None = None,
    ) -> None:
        self.original_stop = stop

        super().__init__(
            title=(
                "Stop bewerken"
                if stop is not None
                else "Stop toevoegen"
            ),
            transient_for=parent,
            modal=True,
        )

        self.add_button(
            "Annuleren",
            Gtk.ResponseType.CANCEL,
        )
        self.add_button(
            (
                "Opslaan"
                if stop is not None
                else "Toevoegen"
            ),
            Gtk.ResponseType.OK,
        )

        self.title_entry = Gtk.Entry()
        self.title_entry.set_width_chars(34)

        self.latitude_entry = Gtk.Entry()
        self.longitude_entry = Gtk.Entry()

        self.nights_spin = Gtk.SpinButton.new_with_range(
            0,
            60,
            1,
        )

        self.arrival_entry = Gtk.Entry()
        self.arrival_entry.set_placeholder_text(
            "JJJJ-MM-DD"
        )

        self.departure_entry = Gtk.Entry()
        self.departure_entry.set_placeholder_text(
            "JJJJ-MM-DD"
        )

        self.notes_view = Gtk.TextView()
        self.notes_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.notes_view.set_size_request(320, 90)

        self.overnight_check = Gtk.CheckButton(
            label="Overnachtingsplaats"
        )
        self.favorite_check = Gtk.CheckButton(
            label="Favoriet"
        )
        self.photo_location_check = Gtk.CheckButton(
            label="Fotolocatie"
        )

        self.arrival_entry.connect(
            "changed",
            self._on_date_changed,
        )
        self.departure_entry.connect(
            "changed",
            self._on_date_changed,
        )
        self.nights_spin.connect(
            "value-changed",
            self._on_nights_changed,
        )

        self._updating_dates = False

        self._populate(
            stop=stop,
            initial_title=initial_title,
            initial_latitude=initial_latitude,
            initial_longitude=initial_longitude,
        )
        self._build_layout()

    def _populate(
        self,
        *,
        stop: Stop | None,
        initial_title: str | None,
        initial_latitude: float | None,
        initial_longitude: float | None,
    ) -> None:
        if stop is not None:
            self.title_entry.set_text(stop.title)
            self.latitude_entry.set_text(
                str(stop.latitude)
            )
            self.longitude_entry.set_text(
                str(stop.longitude)
            )
            self.nights_spin.set_value(stop.nights)

            self.arrival_entry.set_text(
                stop.arrival_date or ""
            )
            self.departure_entry.set_text(
                stop.departure_date or ""
            )

            notes_buffer = self.notes_view.get_buffer()
            notes_buffer.set_text(stop.notes or "")

            self.overnight_check.set_active(
                stop.overnight
            )
            self.favorite_check.set_active(
                stop.favorite
            )
            self.photo_location_check.set_active(
                stop.photo_location
            )
            return

        self.title_entry.set_text(initial_title or "")

        if initial_latitude is None:
            self.latitude_entry.set_text("")
        else:
            self.latitude_entry.set_text(
                f"{initial_latitude:.6f}"
            )

        if initial_longitude is None:
            self.longitude_entry.set_text("")
        else:
            self.longitude_entry.set_text(
                f"{initial_longitude:.6f}"
            )

        self.nights_spin.set_value(1)

    def _build_layout(self) -> None:
        grid = Gtk.Grid(
            column_spacing=12,
            row_spacing=10,
        )
        grid.set_margin_top(18)
        grid.set_margin_bottom(18)
        grid.set_margin_start(18)
        grid.set_margin_end(18)

        self._attach_label(
            grid,
            "Plaats",
            row=0,
        )
        grid.attach(
            self.title_entry,
            1,
            0,
            1,
            1,
        )

        self._attach_label(
            grid,
            "Breedtegraad",
            row=1,
        )
        grid.attach(
            self.latitude_entry,
            1,
            1,
            1,
            1,
        )

        self._attach_label(
            grid,
            "Lengtegraad",
            row=2,
        )
        grid.attach(
            self.longitude_entry,
            1,
            2,
            1,
            1,
        )

        self._attach_label(
            grid,
            "Aankomst",
            row=3,
        )
        grid.attach(
            self.arrival_entry,
            1,
            3,
            1,
            1,
        )

        self._attach_label(
            grid,
            "Vertrek",
            row=4,
        )
        grid.attach(
            self.departure_entry,
            1,
            4,
            1,
            1,
        )

        self._attach_label(
            grid,
            "Nachten",
            row=5,
        )
        grid.attach(
            self.nights_spin,
            1,
            5,
            1,
            1,
        )

        self._attach_label(
            grid,
            "Kenmerken",
            row=6,
        )

        features = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
        )
        features.append(self.overnight_check)
        features.append(self.favorite_check)
        features.append(self.photo_location_check)

        grid.attach(
            features,
            1,
            6,
            1,
            1,
        )

        self._attach_label(
            grid,
            "Notities",
            row=7,
        )

        notes_scroll = Gtk.ScrolledWindow()
        notes_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC,
        )
        notes_scroll.set_child(self.notes_view)
        notes_scroll.set_hexpand(True)
        notes_scroll.set_vexpand(True)

        grid.attach(
            notes_scroll,
            1,
            7,
            1,
            1,
        )

        self.get_content_area().append(grid)

    @staticmethod
    def _attach_label(
        grid: Gtk.Grid,
        text: str,
        *,
        row: int,
    ) -> None:
        label = Gtk.Label(label=text)
        label.set_xalign(0)
        label.set_valign(Gtk.Align.START)

        grid.attach(
            label,
            0,
            row,
            1,
            1,
        )

    def _on_nights_changed(
        self,
        _spin: Gtk.SpinButton,
    ) -> None:
        if self._updating_dates:
            return

        arrival_text = (
            self.arrival_entry.get_text().strip()
        )

        if not arrival_text:
            return

        try:
            arrival = date.fromisoformat(arrival_text)
        except ValueError:
            return

        nights = int(self.nights_spin.get_value())
        departure = arrival + timedelta(days=nights)

        self._updating_dates = True
        try:
            self.departure_entry.set_text(
                departure.isoformat()
            )
        finally:
            self._updating_dates = False

    def _on_date_changed(
        self,
        _entry: Gtk.Entry,
    ) -> None:
        if self._updating_dates:
            return

        arrival_text = (
            self.arrival_entry.get_text().strip()
        )
        departure_text = (
            self.departure_entry.get_text().strip()
        )

        if not arrival_text or not departure_text:
            return

        try:
            arrival = date.fromisoformat(arrival_text)
            departure = date.fromisoformat(
                departure_text
            )
        except ValueError:
            return

        nights = (departure - arrival).days

        if nights < 0:
            return

        self._updating_dates = True
        try:
            self.nights_spin.set_value(nights)
        finally:
            self._updating_dates = False

    def get_stop(self) -> Stop:
        """Return the validated stop represented by the dialog."""

        title = self.title_entry.get_text().strip()

        if not title:
            raise ValueError(
                "De plaatsnaam ontbreekt."
            )

        try:
            latitude = float(
                self.latitude_entry.get_text().strip()
            )
            longitude = float(
                self.longitude_entry.get_text().strip()
            )
        except ValueError as error:
            raise ValueError(
                "Breedtegraad en lengtegraad "
                "moeten getallen zijn."
            ) from error

        notes_buffer = self.notes_view.get_buffer()
        notes = notes_buffer.get_text(
            notes_buffer.get_start_iter(),
            notes_buffer.get_end_iter(),
            True,
        )

        return Stop(
            stop_id=(
                self.original_stop.stop_id
                if self.original_stop is not None
                else None
            ),
            title=title,
            latitude=latitude,
            longitude=longitude,
            arrival_date=(
                self.arrival_entry.get_text().strip()
                or None
            ),
            departure_date=(
                self.departure_entry.get_text().strip()
                or None
            ),
            notes=notes,
            nights=int(
                self.nights_spin.get_value()
            ),
            overnight=(
                self.overnight_check.get_active()
            ),
            favorite=self.favorite_check.get_active(),
            photo_location=(
                self.photo_location_check.get_active()
            ),
        )
