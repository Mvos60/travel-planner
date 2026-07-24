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

from gi.repository import Gio, GLib, Gtk, Pango, WebKit

from travel_planner.planning_engine import plan_trip
from travel_planner.provider_settings_dialog import (
    ProviderSettingsDialog,
)
from travel_planner.context import TravelPlannerContext
from travel_planner.route_cache import RouteCache
from travel_planner.route_time_estimation import (
    estimate_personal_duration_seconds,
    format_duration_seconds,
)
from travel_planner.routing_profile import RoutingProfile
from travel_planner.stop import Stop
from travel_planner.stop_editor_dialog import StopEditorDialog
from travel_planner.trip_summary import TripSummary
from travel_planner.trip import Trip
from travel_planner.trip_settings_dialog import TripSettingsDialog
from travel_planner.vehicle_manager_dialog import VehicleManagerDialog


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TRIP_PATH = DATA_DIR / "adriatic-2026.trip.json"
RECOVERY_STATE_PATH = DATA_DIR / "recovery-state.json"


class TravelPlannerWindow(Gtk.ApplicationWindow):
    def __init__(
        self,
        application: Gtk.Application,
        *,
        context: TravelPlannerContext,
    ) -> None:
        super().__init__(application=application)

        self.context = context

        self.set_default_size(1200, 760)
        self.maximize()
        self.close_request_handler_id = self.connect(
            "close-request",
            self._on_close_request,
        )

        self.route_service = self.context.route_service
        self.osrm_route_provider = self.route_service.provider
        self.current_trip_path: Path | None = None
        self.modified = False
        self.pending_action: str | None = None
        self.destructive_dialog_open = False

        self.recovery_autosave_path: Path | None = None
        self.recovery_trip_path: Path | None = None

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
        self.trip_summary_value_labels: dict[str, Gtk.Label] = {}
        self.route_info_value_labels: dict[str, Gtk.Label] = {}
        self.header_title = Gtk.Label()
        self.move_up_button = Gtk.Button(label="Omhoog")
        self.move_down_button = Gtk.Button(label="Omlaag")
        self.edit_button = Gtk.Button(label="Bewerken")
        self.delete_button = Gtk.Button(label="Verwijderen")
        self.vehicle_profile_combo = Gtk.ComboBoxText()
        self.route_provider_combo = Gtk.ComboBoxText()
        self.route_profile_combo = Gtk.ComboBoxText()

        self.preferences_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
        )

        self.preferences_placeholder = Gtk.Label(
            label="No options for this profile."
        )
        self.preferences_placeholder.set_xalign(0)

        for profile in RoutingProfile:
            self.route_profile_combo.append(
                profile.value,
                profile.display_name,
            )

        self.syncing_vehicle_profile = False
        self.syncing_route_provider = False
        self.syncing_route_profile = False
        self.syncing_preferences = False

        self.avoid_motorways_check = Gtk.CheckButton(
            label="Snelwegen vermijden"
        )

        self.editing_stop_index: int | None = None
        self.map_click_name: str | None = None
        self.map_click_latitude: float | None = None
        self.map_click_longitude: float | None = None

        self._build_interface()
        self._refresh_vehicle_profile_selector()
        self._refresh_route_provider_selector()
        self._load_map()
        self._update_window_title()
        self._update_trip_summary()

        self.autosave_timer_id = GLib.timeout_add_seconds(
            30,
            self._on_autosave_timer,
        )

        GLib.idle_add(
            self._check_startup_recovery,
        )

    @property
    def trip(self) -> Trip:
        """Return the trip currently held by the application context."""

        return self.context.current_trip

    @trip.setter
    def trip(self, trip: Trip) -> None:
        """Replace the trip currently held by the application context."""

        self.context.replace_trip(trip)

        if hasattr(self, "vehicle_profile_combo"):
            self._refresh_vehicle_profile_selector()

    def _build_interface(self) -> None:
        header = Gtk.HeaderBar()
        header.set_title_widget(self.header_title)

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_tooltip_text("Menu")

        menu_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )
        menu_box.set_margin_top(6)
        menu_box.set_margin_bottom(6)
        menu_box.set_margin_start(6)
        menu_box.set_margin_end(6)

        trip_settings_button = Gtk.Button(
            label="Reisinstellingen..."
        )
        trip_settings_button.add_css_class("flat")
        trip_settings_button.connect(
            "clicked",
            self._on_menu_action_clicked,
            self._on_trip_settings_clicked,
        )
        menu_box.append(trip_settings_button)

        provider_settings_button = Gtk.Button(
            label="Routeproviderinstellingen..."
        )
        provider_settings_button.add_css_class("flat")
        provider_settings_button.connect(
            "clicked",
            self._on_menu_action_clicked,
            self._on_provider_settings_clicked,
        )
        menu_box.append(provider_settings_button)

        vehicles_button = Gtk.Button(
            label="Voertuigen..."
        )
        vehicles_button.add_css_class("flat")
        vehicles_button.connect(
            "clicked",
            self._on_menu_action_clicked,
            self._on_vehicle_manager_clicked,
        )
        menu_box.append(vehicles_button)

        route_cache_button = Gtk.Button(
            label="Routecache..."
        )
        route_cache_button.add_css_class("flat")
        route_cache_button.connect(
            "clicked",
            self._on_menu_action_clicked,
            self._on_route_cache_clicked,
        )
        menu_box.append(route_cache_button)

        separator = Gtk.Separator(
            orientation=Gtk.Orientation.HORIZONTAL,
        )
        separator.set_margin_top(4)
        separator.set_margin_bottom(4)
        menu_box.append(separator)

        quit_button = Gtk.Button(label="Afsluiten")
        quit_button.add_css_class("flat")
        quit_button.connect(
            "clicked",
            self._on_quit_clicked,
        )
        menu_box.append(quit_button)

        menu_popover = Gtk.Popover()
        menu_popover.set_child(menu_box)
        menu_button.set_popover(menu_popover)

        header.pack_end(menu_button)

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

        vehicle_label = Gtk.Label(
            label="Voertuig"
        )
        vehicle_label.set_xalign(0)
        vehicle_label.add_css_class("heading")
        vehicle_label.set_margin_top(4)

        self.vehicle_profile_combo.set_hexpand(True)
        self.vehicle_profile_combo.set_margin_bottom(8)
        self.vehicle_profile_combo.connect(
            "changed",
            self._on_vehicle_profile_changed,
        )

        sidebar.append(vehicle_label)
        sidebar.append(self.vehicle_profile_combo)

        route_provider_label = Gtk.Label(
            label="Routeprovider"
        )
        route_provider_label.set_xalign(0)
        route_provider_label.set_margin_top(8)
        sidebar.append(route_provider_label)

        self.route_provider_combo.set_hexpand(True)
        self.route_provider_combo.set_margin_bottom(8)
        self.route_provider_combo.connect(
            "changed",
            self._on_route_provider_changed,
        )
        sidebar.append(self.route_provider_combo)

        profile_label = Gtk.Label(
            label="Routeprofiel"
        )
        profile_label.set_xalign(0)
        profile_label.add_css_class("heading")
        profile_label.set_margin_top(4)

        self.route_profile_combo.set_hexpand(True)
        self.route_profile_combo.set_margin_bottom(4)
        self.route_profile_combo.connect(
            "changed",
            self._on_route_profile_changed,
        )

        sidebar.append(profile_label)
        sidebar.append(self.route_profile_combo)

        preferences_label = Gtk.Label(
            label="Travel Preferences"
        )
        preferences_label.set_xalign(0)
        preferences_label.add_css_class("heading")
        preferences_label.set_margin_top(12)

        self.preferences_box.append(
            self.preferences_placeholder
        )

        sidebar.append(preferences_label)
        sidebar.append(self.preferences_box)

        trip_summary_separator = Gtk.Separator(
            orientation=Gtk.Orientation.HORIZONTAL,
        )
        trip_summary_separator.set_margin_top(8)
        sidebar.append(trip_summary_separator)

        trip_summary_title = Gtk.Label(
            label="Reisoverzicht"
        )
        trip_summary_title.set_xalign(0)
        trip_summary_title.add_css_class("heading")
        trip_summary_title.set_margin_top(4)
        sidebar.append(trip_summary_title)

        trip_summary_grid = Gtk.Grid(
            column_spacing=12,
            row_spacing=4,
        )
        trip_summary_grid.set_hexpand(True)

        summary_rows = (
            ("stops", "Stops"),
            ("nights", "Overnachtingen"),
            ("days", "Reisduur"),
        )

        for row_index, (key, caption) in enumerate(
            summary_rows
        ):
            caption_label = Gtk.Label(label=caption)
            caption_label.set_xalign(0)

            value_label = Gtk.Label(label="—")
            value_label.set_xalign(1)
            value_label.set_hexpand(True)

            trip_summary_grid.attach(
                caption_label,
                0,
                row_index,
                1,
                1,
            )
            trip_summary_grid.attach(
                value_label,
                1,
                row_index,
                1,
                1,
            )
            self.trip_summary_value_labels[key] = value_label

        sidebar.append(trip_summary_grid)

        route_info_separator = Gtk.Separator(
            orientation=Gtk.Orientation.HORIZONTAL,
        )
        route_info_separator.set_margin_top(8)
        sidebar.append(route_info_separator)

        route_info_title = Gtk.Label(label="Route")
        route_info_title.set_xalign(0)
        route_info_title.add_css_class("heading")
        route_info_title.set_margin_top(4)
        sidebar.append(route_info_title)

        recalculate_route_button = Gtk.Button(
            label="Route opnieuw berekenen"
        )
        recalculate_route_button.set_hexpand(True)
        recalculate_route_button.set_margin_top(4)
        recalculate_route_button.set_margin_bottom(4)
        recalculate_route_button.connect(
            "clicked",
            self._on_recalculate_route_clicked,
        )
        sidebar.append(recalculate_route_button)

        route_info_grid = Gtk.Grid(
            column_spacing=12,
            row_spacing=4,
        )
        route_info_grid.set_hexpand(True)

        route_info_rows = (
            ("distance", "Afstand"),
            ("duration", "Rijtijd (provider)"),
            ("personal_duration", "Jouw reistijd"),
            ("provider", "Provider"),
            ("profile", "Profiel"),
        )

        for row_index, (key, caption) in enumerate(
            route_info_rows
        ):
            caption_label = Gtk.Label(label=caption)
            caption_label.set_xalign(0)

            value_label = Gtk.Label(label="—")
            value_label.set_xalign(1)
            value_label.set_hexpand(True)

            route_info_grid.attach(
                caption_label,
                0,
                row_index,
                1,
                1,
            )
            route_info_grid.attach(
                value_label,
                1,
                row_index,
                1,
                1,
            )
            self.route_info_value_labels[key] = value_label

        sidebar.append(route_info_grid)

        self.avoid_motorways_check.set_margin_top(4)
        self.avoid_motorways_check.set_margin_bottom(4)
        self.avoid_motorways_check.connect(
            "toggled",
            self._on_avoid_motorways_toggled,
        )

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
        self._update_trip_summary()

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
            self._write_recovery_state(autosave_path)
        except OSError:
            return True

        return True

    def _write_recovery_state(
        self,
        autosave_path: Path,
    ) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        state = {
            "autosave_path": str(autosave_path),
            "trip_path": (
                str(self.current_trip_path)
                if self.current_trip_path is not None
                else None
            ),
        }

        try:
            RECOVERY_STATE_PATH.write_text(
                json.dumps(
                    state,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _check_startup_recovery(self) -> bool:
        candidate = self._find_recovery_candidate()

        if candidate is None:
            return False

        autosave_path, trip_path = candidate

        try:
            Trip.load(autosave_path)
        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            self._remove_recovery_state()
            return False

        self.recovery_autosave_path = autosave_path
        self.recovery_trip_path = trip_path

        dialog = Gtk.AlertDialog()
        dialog.set_message(
            "Automatisch opgeslagen reis gevonden"
        )
        dialog.set_detail(
            "Travel Planner is eerder afgesloten terwijl "
            "er nog niet-opgeslagen wijzigingen waren. "
            "Wilt u deze reis herstellen?"
        )
        dialog.set_buttons(
            [
                "Negeren",
                "Herstellen",
            ]
        )
        dialog.set_cancel_button(0)
        dialog.set_default_button(1)

        dialog.choose(
            self,
            None,
            self._on_recovery_dialog_finished,
            None,
        )

        return False

    def _find_recovery_candidate(
        self,
    ) -> tuple[Path, Path | None] | None:
        candidates: list[tuple[Path, Path | None]] = []

        try:
            state = json.loads(
                RECOVERY_STATE_PATH.read_text(
                    encoding="utf-8"
                )
            )

            autosave_value = state.get("autosave_path")
            trip_value = state.get("trip_path")

            if isinstance(autosave_value, str):
                autosave_path = Path(autosave_value)
                trip_path = (
                    Path(trip_value)
                    if isinstance(trip_value, str)
                    else None
                )
                candidates.append(
                    (autosave_path, trip_path)
                )
        except (
            OSError,
            json.JSONDecodeError,
            AttributeError,
            TypeError,
        ):
            pass

        fallback_candidates = [
            (
                DATA_DIR / "unsaved-trip.autosave",
                None,
            ),
            (
                Path(f"{TRIP_PATH}.autosave"),
                TRIP_PATH,
            ),
        ]

        for candidate in fallback_candidates:
            if candidate not in candidates:
                candidates.append(candidate)

        usable: list[tuple[Path, Path | None]] = []

        for autosave_path, trip_path in candidates:
            if not autosave_path.is_file():
                continue

            if trip_path is not None and trip_path.is_file():
                try:
                    if (
                        autosave_path.stat().st_mtime
                        <= trip_path.stat().st_mtime
                    ):
                        continue
                except OSError:
                    continue

            usable.append(
                (autosave_path, trip_path)
            )

        if not usable:
            self._remove_recovery_state()
            return None

        try:
            return max(
                usable,
                key=lambda item: item[0].stat().st_mtime,
            )
        except OSError:
            return None

    def _on_recovery_dialog_finished(
        self,
        dialog: Gtk.AlertDialog,
        result: Gio.AsyncResult,
        _user_data: object | None,
    ) -> None:
        try:
            choice = dialog.choose_finish(result)
        except GLib.Error:
            return

        autosave_path = self.recovery_autosave_path
        trip_path = self.recovery_trip_path

        self.recovery_autosave_path = None
        self.recovery_trip_path = None

        if autosave_path is None:
            return

        if choice == 1:
            self._restore_autosave(
                autosave_path,
                trip_path,
            )
            return

        self._discard_autosave(autosave_path)

    def _restore_autosave(
        self,
        autosave_path: Path,
        trip_path: Path | None,
    ) -> None:
        try:
            trip = Trip.load(autosave_path)
        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            self._show_message(
                "Automatische opslag kon niet worden hersteld",
                str(exc),
            )
            self._remove_recovery_state()
            return

        self.trip = trip
        self.current_trip_path = trip_path
        self.modified = True
        self.pending_action = None

        self.editing_stop_index = None
        self.map_click_name = None
        self.map_click_latitude = None
        self.map_click_longitude = None

        self._update_window_title()
        self._refresh_interface()
        self._update_trip_summary()

    def _discard_autosave(
        self,
        autosave_path: Path,
    ) -> None:
        try:
            autosave_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

        self._remove_recovery_state()

    def _remove_recovery_state(self) -> None:
        try:
            RECOVERY_STATE_PATH.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

    def _update_window_title(self) -> None:
        marker = " [gewijzigd]" if self.modified else ""
        title = f"{self.trip.name}{marker}"

        self.set_title(f"{title} — Travel Planner")
        self.header_title.set_markup(f"<b>{title}</b>")

    def _refresh_vehicle_profile_selector(self) -> None:
        """Show available vehicles and select the trip's reference."""

        self.syncing_vehicle_profile = True

        try:
            self.vehicle_profile_combo.remove_all()
            self.vehicle_profile_combo.append(
                "__none__",
                "Geen voertuig",
            )

            profiles = self.context.vehicle_profiles

            for profile in profiles:
                self.vehicle_profile_combo.append(
                    profile.profile_id,
                    profile.name,
                )

            selected_id = self.trip.vehicle_profile_id

            if selected_id is None:
                self.vehicle_profile_combo.set_active_id(
                    "__none__"
                )
                return

            profile = (
                self.context.vehicle_profile_repository.get(
                    selected_id
                )
            )

            if profile is not None:
                self.vehicle_profile_combo.set_active_id(
                    selected_id
                )
                return

            self.vehicle_profile_combo.append(
                selected_id,
                f"Onbekend voertuig ({selected_id})",
            )
            self.vehicle_profile_combo.set_active_id(
                selected_id
            )
        finally:
            self.syncing_vehicle_profile = False

    def _on_vehicle_profile_changed(
        self,
        combo: Gtk.ComboBoxText,
    ) -> None:
        """Store the selected vehicle reference in the current trip."""

        if self.syncing_vehicle_profile:
            return

        active_id = combo.get_active_id()

        if active_id is None:
            return

        vehicle_profile_id = (
            None
            if active_id == "__none__"
            else active_id
        )

        if self.trip.vehicle_profile_id == vehicle_profile_id:
            return

        self.trip.vehicle_profile_id = vehicle_profile_id
        self._mark_modified()
        self._update_trip_summary()

    def _refresh_route_provider_selector(self) -> None:
        """Synchronize the provider selector with the manager."""

        manager = self.context.route_provider_manager

        self.syncing_route_provider = True

        try:
            self.route_provider_combo.remove_all()

            for provider_id in manager.available_provider_ids():
                self.route_provider_combo.append(
                    provider_id,
                    manager.provider_display_name(provider_id),
                )

            self.route_provider_combo.set_active_id(
                manager.active_provider_id
            )
        finally:
            self.syncing_route_provider = False

    def _on_route_provider_changed(
        self,
        combo: Gtk.ComboBoxText,
    ) -> None:
        """Switch the active provider for this application session."""

        if self.syncing_route_provider:
            return

        provider_id = combo.get_active_id()

        if provider_id is None:
            return

        manager = self.context.route_provider_manager

        if manager.active_provider_id == provider_id:
            return

        manager.set_active_provider(provider_id)

        self.context.settings.route_provider = provider_id
        self.context.settings_repository.save(
            self.context.settings
        )

        self.route_service.set_provider(
            manager.active_provider
        )

        # Temporary compatibility reference. This remains safe while
        # OSRM Demo is the only registered provider.
        self.osrm_route_provider = manager.active_provider

        self._refresh_preferences_panel()
        self._refresh_map()

    def _clear_preferences_panel(self) -> None:
        child = self.preferences_box.get_first_child()

        while child is not None:
            next_child = child.get_next_sibling()
            self.preferences_box.remove(child)
            child = next_child

    def _refresh_preferences_panel(self) -> None:
        self._clear_preferences_panel()

        if self.trip.routing_profile is RoutingProfile.CUSTOM:
            self._build_custom_preferences()
            return

        self.preferences_box.append(
            self.preferences_placeholder
        )

    def _build_custom_preferences(self) -> None:
        preferences = self.trip.travel_preferences
        capabilities = self.route_service.capabilities

        options = (
            (
                "Avoid highways",
                "avoid_highways",
                preferences.avoid_highways,
                capabilities.supports_avoid_highways,
            ),
            (
                "Avoid toll roads",
                "avoid_tolls",
                preferences.avoid_tolls,
                capabilities.supports_avoid_tolls,
            ),
            (
                "Avoid ferries",
                "avoid_ferries",
                preferences.avoid_ferries,
                capabilities.supports_avoid_ferries,
            ),
        )

        self.syncing_preferences = True

        try:
            for (
                label,
                attribute_name,
                active,
                supported,
            ) in options:
                checkbox = Gtk.CheckButton(label=label)
                checkbox.set_active(active)
                checkbox.set_sensitive(supported)

                if not supported:
                    checkbox.set_tooltip_text(
                        "Niet ondersteund door de huidige "
                        "routeprovider."
                    )

                checkbox.connect(
                    "toggled",
                    self._on_travel_preference_toggled,
                    attribute_name,
                )
                self.preferences_box.append(checkbox)
        finally:
            self.syncing_preferences = False

    def _on_travel_preference_toggled(
        self,
        checkbox: Gtk.CheckButton,
        attribute_name: str,
    ) -> None:
        if self.syncing_preferences:
            return

        preferences = self.trip.travel_preferences
        new_value = checkbox.get_active()
        current_value = getattr(preferences, attribute_name)

        if current_value == new_value:
            return

        setattr(
            preferences,
            attribute_name,
            new_value,
        )

        self.modified = True
        self._update_window_title()
        self._refresh_interface()
        self._update_trip_summary()

    def _on_route_profile_changed(
        self,
        combo: Gtk.ComboBoxText,
    ) -> None:
        if self.syncing_route_profile:
            return

        profile_id = combo.get_active_id()

        if profile_id is None:
            return

        profile = RoutingProfile.from_value(profile_id)

        if self.trip.routing_profile == profile:
            return

        self.trip.routing_profile = profile
        self.modified = True

        self._update_window_title()
        self._refresh_interface()
        self._update_trip_summary()

    def _on_avoid_motorways_toggled(
        self,
        check_button: Gtk.CheckButton,
    ) -> None:
        avoid_motorways = check_button.get_active()

        if self.trip.avoid_motorways == avoid_motorways:
            return

        self.trip.avoid_motorways = avoid_motorways
        self.osrm_route_provider.avoid_motorways = (
            avoid_motorways
        )

        self.modified = True
        self._update_window_title()
        self._refresh_map()

    def _refresh_interface(self) -> None:
        self._refresh_route_provider_selector()
        self.syncing_route_profile = True

        try:
            self.route_profile_combo.set_active_id(
                self.trip.routing_profile.value
            )
        finally:
            self.syncing_route_profile = False

        self._refresh_preferences_panel()

        self.osrm_route_provider.avoid_motorways = (
            self.trip.avoid_motorways
        )

        self.avoid_motorways_check.set_active(
            self.trip.avoid_motorways
        )
        self.avoid_motorways_check.set_sensitive(
            self.route_service.capabilities.supports_avoid_highways
        )

        if self.route_service.capabilities.supports_avoid_highways:
            self.avoid_motorways_check.set_tooltip_text(None)
        else:
            self.avoid_motorways_check.set_tooltip_text(
                "Niet ondersteund door de huidige routeprovider."
            )

        route_coordinates = (
            self._calculate_route_coordinates()
        )
        metrics = self.route_service.last_route_metrics
        route_summary = TripSummary.from_trip(
            self.trip,
            route_distance_km=(
                metrics.distance_km
                if metrics is not None
                else None
            ),
            route_duration_seconds=(
                round(metrics.duration_seconds)
                if metrics is not None
                else None
            ),
        )

        summary_parts = [
            f"{route_summary.stop_count} stops",
            f"{route_summary.total_nights} nachten",
        ]

        if (
            len(self.trip.stops) >= 2
            and metrics is not None
        ):
            summary_parts.append(
                route_summary.formatted_distance
            )

        summary_parts.append(
            self.trip.planning_summary
        )

        self.summary_label.set_text(
            "  •  ".join(summary_parts)
        )
        self._update_trip_summary()

        child = self.stop_list.get_first_child()

        while child is not None:
            next_child = child.get_next_sibling()
            self.stop_list.remove(child)
            child = next_child

        planning = plan_trip(self.trip)

        for index, stop in enumerate(
            self.trip.stops,
            start=1,
        ):
            planned_stop = planning.for_stop(stop)

            if planned_stop is None:
                raise RuntimeError(
                    "Planning information ontbreekt voor een stop."
                )
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
                f"<b>{index}. {stop.title}</b>"
            )
            name_label.set_xalign(0)
            name_label.set_hexpand(True)
            name_label.set_ellipsize(
                Pango.EllipsizeMode.END
            )
            name_label.set_tooltip_text(
                f"{index}. {stop.title}"
            )

            stop_features = []

            if stop.overnight:
                stop_features.append("overnachting")

            if stop.favorite:
                stop_features.append("favoriet")

            if stop.photo_location:
                stop_features.append("fotolocatie")

            feature_text = (
                "  •  " + ", ".join(stop_features)
                if stop_features
                else ""
            )

            date_text = ""

            if stop.arrival_date and stop.departure_date:
                date_text = (
                    f"  •  {stop.arrival_date}"
                    f" → {stop.departure_date}"
                )
            elif stop.arrival_date:
                date_text = (
                    f"  •  vanaf {stop.arrival_date}"
                )

            planning_parts = [
                planned_stop.day_label,
            ]

            if planned_stop.date_label is not None:
                planning_parts.append(
                    planned_stop.date_label
                )

            planning_text = "  •  ".join(
                planning_parts
            )

            night_label = (
                "1 nacht"
                if stop.nights == 1
                else f"{stop.nights} nachten"
            )

            details_label = Gtk.Label(
                label=(
                    f"{planning_text}\n"
                    f"{night_label}"
                    f"{date_text}"
                    f"{feature_text}\n"
                    f"{stop.latitude:.5f}, "
                    f"{stop.longitude:.5f}"
                )
            )
            details_label.set_xalign(0)
            details_label.set_hexpand(True)
            details_label.set_wrap(True)
            details_label.set_wrap_mode(
                Pango.WrapMode.WORD_CHAR
            )
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
        self._refresh_map(
            route_coordinates=route_coordinates
        )

    def _calculate_route_coordinates(
        self,
    ) -> list[dict]:
        """Return the route geometry for the current trip."""

        return [
            coordinate.to_dict()
            for coordinate in self.route_service.calculate_route(
                self.trip.stops,
                profile=self.trip.routing_profile,
            )
        ]

    def _refresh_map(
        self,
        *,
        route_coordinates: list[dict] | None = None,
    ) -> None:
        stops = [
            {
                "stop_id": stop.stop_id,
                "title": stop.title,
                "latitude": stop.latitude,
                "longitude": stop.longitude,
                "nights": stop.nights,
                "arrival_date": stop.arrival_date,
                "departure_date": stop.departure_date,
                "overnight": stop.overnight,
                "favorite": stop.favorite,
                "photo_location": stop.photo_location,
            }
            for stop in self.trip.stops
        ]

        if route_coordinates is None:
            route_coordinates = (
                self._calculate_route_coordinates()
            )

        script = (
            f"window.setStops({json.dumps(stops)});"
            f"window.setRoute({json.dumps(route_coordinates)});"
        )

        self.web_view.evaluate_javascript(
            script,
            -1,
            None,
            None,
            None,
            None,
            None,
        )

    def _on_menu_action_clicked(
        self,
        button: Gtk.Button,
        callback: object,
    ) -> None:
        """Close the menu before opening its requested dialog."""

        popover = button.get_ancestor(Gtk.Popover)

        if popover is not None:
            popover.popdown()

        GLib.idle_add(
            self._run_menu_action,
            callback,
            button,
        )

    def _run_menu_action(
        self,
        callback: object,
        button: Gtk.Button,
    ) -> bool:
        callback(button)
        return GLib.SOURCE_REMOVE

    def _on_provider_settings_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        """Open persistent route-provider settings."""

        dialog = ProviderSettingsDialog(
            self,
            manager=self.context.route_provider_manager,
            selected_provider_id=(
                self.context.settings.route_provider
            ),
            openrouteservice_api_key=(
                self.context.settings
                .openrouteservice_api_key
            ),
        )

        dialog.connect(
            "response",
            self._on_provider_settings_response,
        )
        dialog.present()

    def _on_provider_settings_response(
        self,
        dialog: ProviderSettingsDialog,
        response_id: int,
    ) -> None:
        """Save provider settings or close without changes."""

        if response_id != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        provider_id = dialog.selected_provider_id
        api_key = dialog.openrouteservice_api_key

        manager = self.context.route_provider_manager

        try:
            manager.set_openrouteservice_api_key(
                api_key
            )
            manager.set_active_provider(provider_id)
        except (KeyError, TypeError) as exc:
            dialog.destroy()
            self._show_error_dialog(
                "Routeproviderinstellingen konden niet "
                f"worden opgeslagen: {exc}"
            )
            return

        self.context.settings.route_provider = (
            provider_id
        )
        self.context.settings.openrouteservice_api_key = (
            api_key
        )

        self.context.settings_repository.save(
            self.context.settings
        )

        self.route_service.set_provider(
            manager.active_provider
        )
        self.osrm_route_provider = (
            manager.active_provider
        )

        self._refresh_route_provider_selector()

        dialog.destroy()

    def _on_trip_settings_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        """Open settings for the current trip."""

        dialog = TripSettingsDialog(
            parent=self,
            trip_name=self.trip.name,
            settings=self.trip.trip_settings,
        )
        dialog.connect(
            "response",
            self._on_trip_settings_response,
        )
        dialog.present()

    def _on_trip_settings_response(
        self,
        dialog: TripSettingsDialog,
        response_id: int,
    ) -> None:
        """Apply validated trip settings or close the dialog."""

        if response_id != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        try:
            new_trip_name = dialog.get_trip_name()
            new_settings = dialog.get_settings()
        except ValueError as exc:
            dialog.show_validation_error(str(exc))
            return

        changed = False

        if new_trip_name != self.trip.name:
            self.trip.name = new_trip_name
            changed = True

        if new_settings != self.trip.trip_settings:
            self.trip.trip_settings = new_settings
            changed = True

        if changed:
            self.modified = True
            self._update_window_title()
            self._refresh_interface()
            self._update_trip_summary()

        dialog.destroy()

    def _on_vehicle_manager_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        """Open the reusable vehicle profile manager."""

        dialog = VehicleManagerDialog(
            parent=self,
            repository=(
                self.context.vehicle_profile_repository
            ),
            context=self.context,
            on_profiles_changed=self._refresh_interface,
        )
        dialog.present()

    def _on_quit_clicked(
        self,
        button: Gtk.Button,
    ) -> None:
        """Close the application through the normal safety checks."""

        popover = button.get_ancestor(Gtk.Popover)

        if popover is not None:
            popover.popdown()

        # Wait until the menu popover has released its input grab.
        GLib.idle_add(self._request_close_after_menu)

    def _request_close_after_menu(self) -> bool:
        self._request_destructive_action("close")
        return GLib.SOURCE_REMOVE

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
        if self.destructive_dialog_open:
            return

        if not self.modified:
            self._execute_pending_action(action)
            return

        self.destructive_dialog_open = True

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
        self.destructive_dialog_open = False

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
            # The user has already confirmed closing. Disconnect the
            # close-request handler so GTK cannot ask a second time.
            if self.close_request_handler_id is not None:
                self.disconnect(self.close_request_handler_id)
                self.close_request_handler_id = None

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
        self._update_trip_summary()

    def _on_add_stop_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        self.editing_stop_index = None

        dialog = StopEditorDialog(
            self,
            initial_title=self.map_click_name,
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

        dialog = StopEditorDialog(
            self,
            stop=stop,
        )
        dialog.connect(
            "response",
            self._on_add_stop_response,
        )
        dialog.present()

    def _on_add_stop_response(
        self,
        dialog: StopEditorDialog,
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
        self._update_trip_summary()

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
        self._update_trip_summary()

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
        self._update_trip_summary()

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
        self._update_trip_summary()

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
        self._update_trip_summary()

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
            RECOVERY_STATE_PATH,
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

    def _on_route_cache_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        """Show route-cache statistics and management actions."""

        cache = RouteCache()
        statistics = cache.statistics()

        dialog = Gtk.AlertDialog()
        dialog.set_message("Routecache")
        dialog.set_detail(
            f"Opgeslagen routes: {statistics.entry_count}\n"
            f"Verlopen routes: {statistics.expired_count}\n"
            f"Ongeldige bestanden: {statistics.invalid_count}\n"
            f"Schijfgebruik: "
            f"{statistics.size_megabytes:.2f} MB"
        )
        dialog.set_buttons(
            [
                "Sluiten",
                "Verlopen wissen",
                "Alles wissen",
            ]
        )
        dialog.set_cancel_button(0)
        dialog.set_default_button(0)
        dialog.choose(
            self,
            None,
            self._on_route_cache_response,
        )

    def _on_route_cache_response(
        self,
        dialog: Gtk.AlertDialog,
        result: Gio.AsyncResult,
    ) -> None:
        """Apply the selected route-cache management action."""

        try:
            response = dialog.choose_finish(result)
        except GLib.Error:
            return

        cache = RouteCache()

        if response == 1:
            removed = cache.prune()
            self._show_message(
                "Routecache opgeschoond",
                f"{removed} verlopen of ongeldige "
                "cachebestanden verwijderd.",
            )
        elif response == 2:
            removed = cache.clear()
            self._show_message(
                "Routecache gewist",
                f"{removed} cachebestanden verwijderd.",
            )

    def _on_recalculate_route_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        # Recalculate and redraw the current route.
        self._refresh_interface()

    def _update_trip_summary(self) -> bool:
        """Refresh the read-only trip summary panel."""

        if not self.trip_summary_value_labels:
            return True

        metrics = self.route_service.last_route_metrics
        summary = TripSummary.from_trip(
            self.trip,
            route_distance_km=(
                metrics.distance_km
                if metrics is not None
                else None
            ),
            route_duration_seconds=(
                round(metrics.duration_seconds)
                if metrics is not None
                else None
            ),
        )

        trip_values = {
            "stops": str(summary.stop_count),
            "nights": str(summary.total_nights),
            "days": summary.formatted_planned_days,
        }

        for key, value in trip_values.items():
            self.trip_summary_value_labels[key].set_text(value)

        manager = self.context.route_provider_manager
        provider_name = manager.provider_display_name(
            manager.active_provider_id
        )

        route_values = {
            "distance": summary.formatted_distance,
            "duration": summary.formatted_duration,
            "personal_duration": (
                self._formatted_personal_route_duration(metrics)
            ),
            "provider": provider_name,
            "profile": self.trip.routing_profile.display_name,
        }

        for key, value in route_values.items():
            self.route_info_value_labels[key].set_text(value)

        return True

    def _formatted_personal_route_duration(
        self,
        metrics: object | None,
    ) -> str:
        """Return estimated driving time for the selected vehicle."""

        if metrics is None or self.trip.vehicle_profile_id is None:
            return "—"

        profile = self.context.vehicle_profile_repository.get(
            self.trip.vehicle_profile_id
        )

        if profile is None:
            return "—"

        duration_seconds = estimate_personal_duration_seconds(
            distance_km=metrics.distance_km,
            motorway_speed_kmh=profile.average_motorway_speed_kmh,
            local_speed_kmh=profile.average_local_speed_kmh,
        )

        return format_duration_seconds(duration_seconds)

    def _show_message(
        self,
        title: str,
        message: str,
    ) -> None:
        dialog = Gtk.AlertDialog()
        dialog.set_message(title)
        dialog.set_detail(message)
        dialog.show(self)
