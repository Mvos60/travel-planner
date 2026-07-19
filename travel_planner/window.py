from __future__ import annotations

import json
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import Gio, GLib, Gtk, WebKit

from travel_planner.trip import Stop, Trip


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TRIP_PATH = DATA_DIR / "adriatic-2026.trip.json"


class AddStopDialog(Gtk.Dialog):
    def __init__(self, parent: Gtk.Window) -> None:
        super().__init__(
            title="Stop toevoegen",
            transient_for=parent,
            modal=True,
        )

        self.add_button("Annuleren", Gtk.ResponseType.CANCEL)
        self.add_button("Toevoegen", Gtk.ResponseType.OK)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_text("Culemborg")

        self.latitude_entry = Gtk.Entry()
        self.latitude_entry.set_text("51.955")

        self.longitude_entry = Gtk.Entry()
        self.longitude_entry.set_text("5.22778")

        self.nights_spin = Gtk.SpinButton.new_with_range(0, 60, 1)
        self.nights_spin.set_value(3)

        grid = Gtk.Grid(
            column_spacing=12,
            row_spacing=12,
        )
        grid.set_margin_top(18)
        grid.set_margin_bottom(18)
        grid.set_margin_start(18)
        grid.set_margin_end(18)

        grid.attach(Gtk.Label(label="Naam"), 0, 0, 1, 1)
        grid.attach(self.name_entry, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Breedtegraad"), 0, 1, 1, 1)
        grid.attach(self.latitude_entry, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="Lengtegraad"), 0, 2, 1, 1)
        grid.attach(self.longitude_entry, 1, 2, 1, 1)

        grid.attach(Gtk.Label(label="Nachten"), 0, 3, 1, 1)
        grid.attach(self.nights_spin, 1, 3, 1, 1)

        self.get_content_area().append(grid)

    def get_stop(self) -> Stop:
        name = self.name_entry.get_text().strip()

        if not name:
            raise ValueError("De stopnaam ontbreekt.")

        try:
            latitude = float(self.latitude_entry.get_text().strip())
            longitude = float(self.longitude_entry.get_text().strip())
        except ValueError as exc:
            raise ValueError(
                "Breedtegraad en lengtegraad moeten getallen zijn."
            ) from exc

        if not -90 <= latitude <= 90:
            raise ValueError(
                "Breedtegraad moet tussen -90 en 90 liggen."
            )

        if not -180 <= longitude <= 180:
            raise ValueError(
                "Lengtegraad moet tussen -180 en 180 liggen."
            )

        return Stop(
            name=name,
            latitude=latitude,
            longitude=longitude,
            nights=int(self.nights_spin.get_value()),
        )


class TravelPlannerWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application)

        self.set_default_size(1200, 760)

        self.trip = Trip(name="Adriatic 2026")
        self.current_trip_path: Path | None = TRIP_PATH
        self.modified = False

        self.web_view = WebKit.WebView()
        self.stop_list = Gtk.ListBox()
        self.summary_label = Gtk.Label()
        self.header_title = Gtk.Label()
        self.move_up_button = Gtk.Button(label="Omhoog")
        self.move_down_button = Gtk.Button(label="Omlaag")
        self.delete_button = Gtk.Button(label="Verwijderen")

        self._build_interface()
        self._load_map()
        self._update_window_title()

    def _build_interface(self) -> None:
        header = Gtk.HeaderBar()
        header.set_title_widget(self.header_title)

        new_button = Gtk.Button(label="Nieuw")
        new_button.connect(
            "clicked",
            self._on_new_clicked,
        )
        header.pack_start(new_button)

        add_button = Gtk.Button(label="Stop toevoegen")
        add_button.connect(
            "clicked",
            self._on_add_stop_clicked,
        )
        header.pack_start(add_button)

        save_as_button = Gtk.Button(label="Opslaan als…")
        save_as_button.connect(
            "clicked",
            self._on_save_as_clicked,
        )
        header.pack_end(save_as_button)

        save_button = Gtk.Button(label="Opslaan")
        save_button.connect(
            "clicked",
            self._on_save_clicked,
        )
        header.pack_end(save_button)

        self.set_titlebar(header)

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )

        self.summary_label.set_margin_top(10)
        self.summary_label.set_margin_bottom(10)
        self.summary_label.set_margin_start(16)
        self.summary_label.set_margin_end(16)
        self.summary_label.set_xalign(0)

        root.append(self.summary_label)

        content = Gtk.Paned(
            orientation=Gtk.Orientation.HORIZONTAL,
        )
        content.set_position(330)
        content.set_wide_handle(True)
        content.set_vexpand(True)

        sidebar = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )
        sidebar.set_margin_bottom(8)
        sidebar.set_margin_start(8)
        sidebar.set_margin_end(8)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )
        scroller.set_vexpand(True)

        self.stop_list.set_selection_mode(
            Gtk.SelectionMode.SINGLE
        )
        self.stop_list.connect(
            "row-selected",
            self._on_stop_selected,
        )
        scroller.set_child(self.stop_list)

        button_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )

        self.move_up_button.set_sensitive(False)
        self.move_up_button.connect(
            "clicked",
            self._on_move_stop_up_clicked,
        )

        self.move_down_button.set_sensitive(False)
        self.move_down_button.connect(
            "clicked",
            self._on_move_stop_down_clicked,
        )

        self.delete_button.set_sensitive(False)
        self.delete_button.connect(
            "clicked",
            self._on_delete_stop_clicked,
        )

        button_row.append(self.move_up_button)
        button_row.append(self.move_down_button)
        button_row.append(self.delete_button)

        sidebar.append(scroller)
        sidebar.append(button_row)

        content.set_start_child(sidebar)
        content.set_end_child(self.web_view)

        root.append(content)
        self.set_child(root)

        self._refresh_interface()

    def _load_map(self) -> None:
        map_path = Path(__file__).with_name("map.html")

        self.web_view.connect(
            "load-changed",
            self._on_map_load_changed,
        )
        self.web_view.load_uri(map_path.resolve().as_uri())

    def _on_map_load_changed(
        self,
        _web_view: WebKit.WebView,
        load_event: WebKit.LoadEvent,
    ) -> None:
        if load_event == WebKit.LoadEvent.FINISHED:
            self._refresh_map()

    def _mark_modified(self) -> None:
        self.modified = True
        self._update_window_title()

    def _update_window_title(self) -> None:
        marker = " [gewijzigd]" if self.modified else ""
        title = f"{self.trip.name}{marker}"

        self.set_title(f"{title} — Travel Planner")
        self.header_title.set_markup(f"<b>{title}</b>")

    def _refresh_interface(self) -> None:
        self.summary_label.set_text(
            f"{len(self.trip.stops)} stops  •  "
            f"{self.trip.total_nights} nachten  •  "
            "60 dagen beschikbaar"
        )

        child = self.stop_list.get_first_child()

        while child is not None:
            next_child = child.get_next_sibling()
            self.stop_list.remove(child)
            child = next_child

        for index, stop in enumerate(
            self.trip.stops,
            start=1,
        ):
            box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=3,
            )
            box.set_margin_top(10)
            box.set_margin_bottom(10)
            box.set_margin_start(12)
            box.set_margin_end(12)

            name_label = Gtk.Label()
            name_label.set_markup(
                f"<b>{index}. {stop.name}</b>"
            )
            name_label.set_xalign(0)

            details_label = Gtk.Label(
                label=(
                    f"{stop.nights} nacht(en)  •  "
                    f"{stop.latitude:.5f}, "
                    f"{stop.longitude:.5f}"
                )
            )
            details_label.set_xalign(0)
            details_label.add_css_class("dim-label")

            box.append(name_label)
            box.append(details_label)

            row = Gtk.ListBoxRow()
            row.set_child(box)
            self.stop_list.append(row)

        self.move_up_button.set_sensitive(False)
        self.move_down_button.set_sensitive(False)
        self.delete_button.set_sensitive(False)
        self._refresh_map()

    def _refresh_map(self) -> None:
        stops = [
            {
                "name": stop.name,
                "latitude": stop.latitude,
                "longitude": stop.longitude,
                "nights": stop.nights,
            }
            for stop in self.trip.stops
        ]

        script = f"window.setStops({json.dumps(stops)});"

        self.web_view.evaluate_javascript(
            script,
            -1,
            None,
            None,
            None,
            None,
            None,
        )

    def _on_new_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        self.trip = Trip(name="Nieuwe reis")
        self.current_trip_path = None
        self.modified = False

        self._update_window_title()
        self._refresh_interface()

    def _on_add_stop_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        dialog = AddStopDialog(self)
        dialog.connect(
            "response",
            self._on_add_stop_response,
        )
        dialog.present()

    def _on_add_stop_response(
        self,
        dialog: AddStopDialog,
        response: int,
    ) -> None:
        if response != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        try:
            stop = dialog.get_stop()
        except ValueError as exc:
            self._show_message(
                "Stop kon niet worden toegevoegd",
                str(exc),
            )
            return

        self.trip.add_stop(stop)
        self._mark_modified()
        dialog.destroy()
        self._refresh_interface()

    def _on_stop_selected(
        self,
        _list_box: Gtk.ListBox,
        row: Gtk.ListBoxRow | None,
    ) -> None:
        has_selection = row is not None

        self.delete_button.set_sensitive(has_selection)

        if not has_selection:
            self.move_up_button.set_sensitive(False)
            self.move_down_button.set_sensitive(False)
            return

        index = row.get_index()

        self.move_up_button.set_sensitive(index > 0)
        self.move_down_button.set_sensitive(
            index < len(self.trip.stops) - 1
        )

    def _on_move_stop_up_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        selected_row = self.stop_list.get_selected_row()

        if selected_row is None:
            return

        index = selected_row.get_index()

        if index <= 0:
            return

        self.trip.stops[index - 1], self.trip.stops[index] = (
            self.trip.stops[index],
            self.trip.stops[index - 1],
        )

        self._mark_modified()
        self._refresh_interface()

        new_row = self.stop_list.get_row_at_index(index - 1)

        if new_row is not None:
            self.stop_list.select_row(new_row)

    def _on_move_stop_down_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        selected_row = self.stop_list.get_selected_row()

        if selected_row is None:
            return

        index = selected_row.get_index()

        if index >= len(self.trip.stops) - 1:
            return

        self.trip.stops[index], self.trip.stops[index + 1] = (
            self.trip.stops[index + 1],
            self.trip.stops[index],
        )

        self._mark_modified()
        self._refresh_interface()

        new_row = self.stop_list.get_row_at_index(index + 1)

        if new_row is not None:
            self.stop_list.select_row(new_row)

    def _on_delete_stop_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        selected_row = self.stop_list.get_selected_row()

        if selected_row is None:
            return

        index = selected_row.get_index()
        del self.trip.stops[index]

        self._mark_modified()
        self._refresh_interface()

    def _on_save_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        if self.current_trip_path is None:
            self._show_save_dialog()
            return

        self._save_trip_to(self.current_trip_path)

    def _on_save_as_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        self._show_save_dialog()

    def _show_save_dialog(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        dialog = Gtk.FileDialog()
        dialog.set_title("Reis opslaan als")
        dialog.set_modal(True)
        dialog.set_accept_label("Opslaan")
        dialog.set_initial_folder(
            Gio.File.new_for_path(str(DATA_DIR))
        )

        if self.current_trip_path is not None:
            initial_name = self.current_trip_path.name
        else:
            initial_name = "nieuwe-reis.trip.json"

        dialog.set_initial_name(initial_name)

        trip_filter = Gtk.FileFilter()
        trip_filter.set_name("Travel Planner-reizen")
        trip_filter.add_pattern("*.trip.json")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(trip_filter)

        dialog.set_filters(filters)
        dialog.set_default_filter(trip_filter)

        dialog.save(
            self,
            None,
            self._on_save_dialog_finished,
            None,
        )

    def _on_save_dialog_finished(
        self,
        dialog: Gtk.FileDialog,
        result: Gio.AsyncResult,
        _user_data: object | None,
    ) -> None:
        try:
            selected_file = dialog.save_finish(result)
        except GLib.Error:
            return

        selected_path = selected_file.get_path()

        if selected_path is None:
            self._show_message(
                "Reis kon niet worden opgeslagen",
                "De gekozen locatie is niet lokaal beschikbaar.",
            )
            return

        path = Path(selected_path)

        if path.name.endswith(".trip.json"):
            pass
        elif path.suffix == ".json":
            path = path.with_name(
                f"{path.stem}.trip.json"
            )
        else:
            path = path.with_name(
                f"{path.name}.trip.json"
            )

        if self.trip.name == "Nieuwe reis":
            filename_name = path.name.removesuffix(
                ".trip.json"
            )
            readable_name = filename_name.replace(
                "-",
                " ",
            ).replace(
                "_",
                " ",
            )
            self.trip.name = readable_name.capitalize()

        self.current_trip_path = path
        self._save_trip_to(path)

    def _save_trip_to(self, path: Path) -> None:
        try:
            self.trip.save(path)
        except OSError as exc:
            self._show_message(
                "Reis kon niet worden opgeslagen",
                str(exc),
            )
            return

        self.modified = False
        self._update_window_title()

        self._show_message(
            "Reis opgeslagen",
            str(path),
        )

    def _show_message(
        self,
        title: str,
        message: str,
    ) -> None:
        dialog = Gtk.AlertDialog()
        dialog.set_message(title)
        dialog.set_detail(message)
        dialog.show(self)
