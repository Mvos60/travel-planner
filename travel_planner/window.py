from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import Gio, GLib, Gtk, WebKit

from travel_planner.trip import Stop, Trip


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TRIP_PATH = DATA_DIR / "adriatic-2026.trip.json"


class AddStopDialog(Gtk.Dialog):
    def __init__(
        self,
        parent: Gtk.Window,
        stop: Stop | None = None,
        initial_name: str | None = None,
        initial_latitude: float | None = None,
        initial_longitude: float | None = None,
    ) -> None:
        super().__init__(
            title="Stop toevoegen",
            transient_for=parent,
            modal=True,
        )

        self.add_button("Annuleren", Gtk.ResponseType.CANCEL)
        self.add_button("Toevoegen", Gtk.ResponseType.OK)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_width_chars(32)
        self.latitude_entry = Gtk.Entry()
        self.longitude_entry = Gtk.Entry()
        self.nights_spin = Gtk.SpinButton.new_with_range(0, 60, 1)

        if stop is None:
            if (
                initial_latitude is not None
                and initial_longitude is not None
            ):
                self.name_entry.set_text(initial_name or "")
                self.latitude_entry.set_text(
                    f"{initial_latitude:.6f}"
                )
                self.longitude_entry.set_text(
                    f"{initial_longitude:.6f}"
                )
            else:
                self.name_entry.set_text("")
                self.latitude_entry.set_text("")
                self.longitude_entry.set_text("")

            self.nights_spin.set_value(1)
        else:
            self.set_title("Stop bewerken")
            self.name_entry.set_text(stop.name)
            self.latitude_entry.set_text(str(stop.latitude))
            self.longitude_entry.set_text(str(stop.longitude))
            self.nights_spin.set_value(stop.nights)

        grid = Gtk.Grid(
            column_spacing=12,
            row_spacing=12,
        )
        grid.set_margin_top(18)
        grid.set_margin_bottom(18)
        grid.set_margin_start(18)
        grid.set_margin_end(18)

        grid.attach(Gtk.Label(label="Plaats"), 0, 0, 1, 1)
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
            raise ValueError("De plaatsnaam ontbreekt.")

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
        self.connect(
            "close-request",
            self._on_close_request,
        )

        self.trip = Trip(name="Adriatic 2026")
        self.current_trip_path: Path | None = TRIP_PATH
        self.modified = False
        self.pending_action: str | None = None

        self.web_content_manager = WebKit.UserContentManager()
        self.web_content_manager.connect(
            "script-message-received::mapClick",
            self._on_map_click_message,
        )
        self.web_content_manager.register_script_message_handler(
            "mapClick",
            None,
        )

        self.web_content_manager.connect(
            "script-message-received::markerClick",
            self._on_map_marker_click_message,
        )
        self.web_content_manager.register_script_message_handler(
            "markerClick",
            None,
        )

        self.web_view = WebKit.WebView(
            user_content_manager=self.web_content_manager
        )
        self.stop_list = Gtk.ListBox()
        self.summary_label = Gtk.Label()
        self.header_title = Gtk.Label()
        self.move_up_button = Gtk.Button(label="Omhoog")
        self.move_down_button = Gtk.Button(label="Omlaag")
        self.edit_button = Gtk.Button(label="Bewerken")
        self.delete_button = Gtk.Button(label="Verwijderen")

        self.editing_stop_index: int | None = None
        self.map_click_name: str | None = None
        self.map_click_latitude: float | None = None
        self.map_click_longitude: float | None = None

        self._build_interface()
        self._load_map()
        self._update_window_title()

        self.autosave_timer_id = GLib.timeout_add_seconds(
            30,
            self._on_autosave_timer,
        )

    def _build_interface(self) -> None:
        header = Gtk.HeaderBar()
        header.set_title_widget(self.header_title)

        new_button = Gtk.Button(label="Nieuw")
        new_button.connect(
            "clicked",
            self._on_new_clicked,
        )
        header.pack_start(new_button)

        open_button = Gtk.Button(label="Openen")
        open_button.connect(
            "clicked",
            self._on_open_clicked,
        )
        header.pack_start(open_button)

        add_button = Gtk.Button(label="Stop toevoegen")
        add_button.connect(
            "clicked",
            self._on_add_stop_clicked,
        )
        header.pack_start(add_button)

        show_trip_button = Gtk.Button(label="Hele reis")
        show_trip_button.connect(
            "clicked",
            self._on_show_entire_trip_clicked,
        )
        header.pack_start(show_trip_button)

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

        double_click = Gtk.GestureClick()
        double_click.set_button(1)
        double_click.connect(
            "pressed",
            self._on_stop_double_clicked,
        )
        self.stop_list.add_controller(double_click)

        scroller.set_child(self.stop_list)

        button_grid = Gtk.Grid(
            column_spacing=8,
            row_spacing=8,
        )
        button_grid.set_column_homogeneous(True)

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

        self.edit_button.set_sensitive(False)
        self.edit_button.connect(
            "clicked",
            self._on_edit_stop_clicked,
        )

        self.delete_button.set_sensitive(False)
        self.delete_button.connect(
            "clicked",
            self._on_delete_stop_clicked,
        )

        button_grid.attach(self.move_up_button, 0, 0, 1, 1)
        button_grid.attach(self.move_down_button, 1, 0, 1, 1)
        button_grid.attach(self.edit_button, 0, 1, 1, 1)
        button_grid.attach(self.delete_button, 1, 1, 1, 1)

        sidebar.append(scroller)
        sidebar.append(button_grid)

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

    def _on_map_click_message(
        self,
        _manager: WebKit.UserContentManager,
        value: object,
    ) -> None:
        try:
            message = json.loads(value.to_string())

            if isinstance(message, str):
                message = json.loads(message)

            latitude = float(message["latitude"])
            longitude = float(message["longitude"])
        except (
            AttributeError,
            TypeError,
            ValueError,
            KeyError,
            json.JSONDecodeError,
        ):
            return

        self.map_click_name = None
        self.map_click_latitude = latitude
        self.map_click_longitude = longitude

        thread = threading.Thread(
            target=self._reverse_geocode,
            args=(latitude, longitude),
            daemon=True,
        )
        thread.start()

    def _on_map_marker_click_message(
        self,
        _manager: WebKit.UserContentManager,
        value: object,
    ) -> None:
        try:
            marker_index = int(value.to_string())
        except (AttributeError, TypeError, ValueError):
            return

        row = self.stop_list.get_row_at_index(marker_index)

        if row is not None:
            self.stop_list.select_row(row)

    def _on_show_entire_trip_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        self.web_view.evaluate_javascript(
            "window.showEntireTrip();",
            -1,
            None,
            None,
            None,
            None,
            None,
        )

    def _focus_map_stop(self, stop_index: int) -> None:
        script = f"window.focusStop({stop_index});"

        self.web_view.evaluate_javascript(
            script,
            -1,
            None,
            None,
            None,
            None,
            None,
        )

    def _reverse_geocode(
        self,
        latitude: float,
        longitude: float,
    ) -> None:
        parameters = urlencode(
            {
                "lat": f"{latitude:.6f}",
                "lon": f"{longitude:.6f}",
                "format": "jsonv2",
                "addressdetails": "1",
                "accept-language": "nl",
                "zoom": "14",
            }
        )

        request = Request(
            "https://nominatim.openstreetmap.org/reverse?"
            + parameters,
            headers={
                "User-Agent": (
                    "MacTravelPlanner/0.1 "
                    "(personal GTK desktop application)"
                ),
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=10) as response:
                result = json.load(response)
        except (
            HTTPError,
            URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ):
            return

        address = result.get("address", {})

        name = next(
            (
                address.get(key)
                for key in (
                    "city",
                    "town",
                    "village",
                    "municipality",
                    "hamlet",
                    "locality",
                    "county",
                )
                if address.get(key)
            ),
            None,
        )

        if name is None:
            display_name = result.get("display_name", "")
            name = display_name.split(",", 1)[0].strip() or None

        if name is None:
            return

        GLib.idle_add(
            self._store_reverse_geocode_result,
            latitude,
            longitude,
            name,
        )

    def _store_reverse_geocode_result(
        self,
        latitude: float,
        longitude: float,
        name: str,
    ) -> bool:
        if (
            self.map_click_latitude != latitude
            or self.map_click_longitude != longitude
        ):
            return False

        self.map_click_name = name
        return False

    def _mark_modified(self) -> None:
        self.modified = True
        self._update_window_title()

    def _get_autosave_path(self) -> Path:
        if self.current_trip_path is not None:
            return Path(
                f"{self.current_trip_path}.autosave"
            )

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR / "unsaved-trip.autosave"

    def _on_autosave_timer(self) -> bool:
        if not self.modified:
            return True

        autosave_path = self._get_autosave_path()

        try:
            self.trip.save(autosave_path)
        except OSError:
            return True

        return True

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
        self.edit_button.set_sensitive(False)
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

    def _on_close_request(
        self,
        _window: Gtk.Window,
    ) -> bool:
        if not self.modified:
            return False

        self._request_destructive_action("close")
        return True

    def _on_new_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        self._request_destructive_action("new")

    def _request_destructive_action(
        self,
        action: str,
    ) -> None:
        if not self.modified:
            self._execute_pending_action(action)
            return

        dialog = Gtk.AlertDialog()
        dialog.set_message(
            "Niet-opgeslagen wijzigingen"
        )
        dialog.set_detail(
            "De huidige reis bevat wijzigingen die nog "
            "niet zijn opgeslagen."
        )
        dialog.set_buttons(
            [
                "Annuleren",
                "Niet opslaan",
                "Opslaan",
            ]
        )
        dialog.set_cancel_button(0)
        dialog.set_default_button(2)

        dialog.choose(
            self,
            None,
            self._on_unsaved_changes_finished,
            action,
        )

    def _on_unsaved_changes_finished(
        self,
        dialog: Gtk.AlertDialog,
        result: Gio.AsyncResult,
        action: object,
    ) -> None:
        try:
            choice = dialog.choose_finish(result)
        except GLib.Error:
            return

        if not isinstance(action, str):
            return

        if choice == 0:
            return

        if choice == 1:
            self._execute_pending_action(action)
            return

        if choice != 2:
            return

        self.pending_action = action

        if self.current_trip_path is None:
            self._show_save_dialog()
            return

        if self._save_trip_to(self.current_trip_path):
            self._finish_pending_action()

    def _finish_pending_action(self) -> None:
        action = self.pending_action
        self.pending_action = None

        if action is not None:
            self._execute_pending_action(action)

    def _execute_pending_action(
        self,
        action: str,
    ) -> None:
        if action == "new":
            self._create_new_trip()
        elif action == "open":
            self._show_open_dialog()
        elif action == "close":
            self.destroy()

    def _create_new_trip(self) -> None:
        self.trip = Trip(name="Nieuwe reis")
        self.current_trip_path = None
        self.modified = False

        self.editing_stop_index = None
        self.map_click_name = None
        self.map_click_latitude = None
        self.map_click_longitude = None

        self._update_window_title()
        self._refresh_interface()

    def _on_add_stop_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        self.editing_stop_index = None

        dialog = AddStopDialog(
            self,
            initial_name=self.map_click_name,
            initial_latitude=self.map_click_latitude,
            initial_longitude=self.map_click_longitude,
        )
        dialog.connect(
            "response",
            self._on_add_stop_response,
        )
        dialog.present()

    def _on_edit_stop_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        selected_row = self.stop_list.get_selected_row()

        if selected_row is None:
            return

        self._open_edit_dialog(selected_row.get_index())

    def _on_stop_double_clicked(
        self,
        _gesture: Gtk.GestureClick,
        press_count: int,
        _x: float,
        y: float,
    ) -> None:
        if press_count != 2:
            return

        row = self.stop_list.get_row_at_y(int(y))

        if row is None:
            return

        self.stop_list.select_row(row)
        self._open_edit_dialog(row.get_index())

    def _open_edit_dialog(
        self,
        stop_index: int,
    ) -> None:
        if not 0 <= stop_index < len(self.trip.stops):
            return

        self.editing_stop_index = stop_index
        stop = self.trip.stops[stop_index]

        dialog = AddStopDialog(self, stop)
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

        selected_index = self.editing_stop_index

        if selected_index is None:
            self.trip.add_stop(stop)
        else:
            self.trip.stops[selected_index] = stop

        self.editing_stop_index = None
        self._mark_modified()
        dialog.destroy()
        self._refresh_interface()

        if selected_index is not None:
            edited_row = self.stop_list.get_row_at_index(
                selected_index
            )

            if edited_row is not None:
                self.stop_list.select_row(edited_row)

    def _on_stop_selected(
        self,
        _list_box: Gtk.ListBox,
        row: Gtk.ListBoxRow | None,
    ) -> None:
        has_selection = row is not None

        self.edit_button.set_sensitive(has_selection)
        self.delete_button.set_sensitive(has_selection)

        if not has_selection:
            self.move_up_button.set_sensitive(False)
            self.move_down_button.set_sensitive(False)
            return

        index = row.get_index()
        self._focus_map_stop(index)

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

    def _on_open_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        self._request_destructive_action("open")

    def _show_open_dialog(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        dialog = Gtk.FileDialog()
        dialog.set_title("Reis openen")
        dialog.set_modal(True)
        dialog.set_accept_label("Openen")
        dialog.set_initial_folder(
            Gio.File.new_for_path(str(DATA_DIR))
        )

        trip_filter = Gtk.FileFilter()
        trip_filter.set_name("Travel Planner-reizen")
        trip_filter.add_pattern("*.trip.json")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(trip_filter)

        dialog.set_filters(filters)
        dialog.set_default_filter(trip_filter)

        dialog.open(
            self,
            None,
            self._on_open_dialog_finished,
            None,
        )

    def _on_open_dialog_finished(
        self,
        dialog: Gtk.FileDialog,
        result: Gio.AsyncResult,
        _user_data: object | None,
    ) -> None:
        try:
            selected_file = dialog.open_finish(result)
        except GLib.Error:
            return

        selected_path = selected_file.get_path()

        if selected_path is None:
            self._show_message(
                "Reis kon niet worden geopend",
                "De gekozen locatie is niet lokaal beschikbaar.",
            )
            return

        self._load_trip(Path(selected_path))

    def _load_trip(self, path: Path) -> None:
        try:
            trip = Trip.load(path)
        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            self._show_message(
                "Reis kon niet worden geopend",
                str(exc),
            )
            return

        self.trip = trip
        self.current_trip_path = path
        self.modified = False

        self.editing_stop_index = None
        self.map_click_name = None
        self.map_click_latitude = None
        self.map_click_longitude = None

        self._update_window_title()
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
        self.pending_action = None
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
            self.pending_action = None
            return

        selected_path = selected_file.get_path()

        if selected_path is None:
            self._show_message(
                "Reis kon niet worden opgeslagen",
                "De gekozen locatie is niet lokaal beschikbaar.",
            )
            self.pending_action = None
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

        filename_name = path.name.removesuffix(
            ".trip.json"
        )
        readable_name = filename_name.replace(
            "-",
            " ",
        ).replace(
            "_",
            " ",
        ).strip()

        if readable_name:
            self.trip.name = (
                readable_name[:1].upper()
                + readable_name[1:]
            )

        self.current_trip_path = path

        if self._save_trip_to(path):
            self._finish_pending_action()
        else:
            self.pending_action = None

    def _save_trip_to(self, path: Path) -> bool:
        try:
            self.trip.save(path)
        except OSError as exc:
            self._show_message(
                "Reis kon niet worden opgeslagen",
                str(exc),
            )
            return False

        for autosave in (
            DATA_DIR / "unsaved-trip.autosave",
            Path(f"{path}.autosave"),
        ):
            try:
                autosave.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

        self.modified = False
        self._update_window_title()

        if self.pending_action is None:
            self._show_message(
                "Reis opgeslagen",
                str(path),
            )

        return True

    def _show_message(
        self,
        title: str,
        message: str,
    ) -> None:
        dialog = Gtk.AlertDialog()
        dialog.set_message(title)
        dialog.set_detail(message)
        dialog.show(self)
