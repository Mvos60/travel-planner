from __future__ import annotations

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import Gio, Gtk, WebKit


APP_ID = "com.mac.travelplanner"


STOPS = [
    {"id": 1, "name": "Vertrek Nederland", "nights": 0},
    {"id": 2, "name": "Eifel / Hunsrück", "nights": 1},
    {"id": 3, "name": "Obere Donau", "nights": 3},
    {"id": 4, "name": "Allgäu", "nights": 1},
    {"id": 5, "name": "Nockberge", "nights": 3},
    {"id": 6, "name": "Gailtal / Weissensee", "nights": 2},
    {"id": 7, "name": "Lesachtal", "nights": 4},
    {"id": 8, "name": "Rateče / Planica", "nights": 3},
    {"id": 9, "name": "Trenta / Soča", "nights": 5},
    {"id": 10, "name": "Breginjski Kot", "nights": 3},
    {"id": 11, "name": "Bohinj", "nights": 3},
]


class TravelPlannerWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(
            application=application,
            title="Travel Planner",
        )

        self.set_default_size(1200, 760)

        self.web_view = WebKit.WebView()
        self.stop_list = Gtk.ListBox()

        self._build_interface()
        self._load_map()

    def _build_interface(self) -> None:
        header = Gtk.HeaderBar()

        title = Gtk.Label()
        title.set_markup("<b>Adriatic 2026</b>")
        header.set_title_widget(title)

        route_button = Gtk.Button(label="Complete route")
        route_button.connect(
            "clicked",
            self._on_complete_route_clicked,
        )
        header.pack_end(route_button)

        self.set_titlebar(header)

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )

        root.append(self._create_summary())

        content = Gtk.Paned(
            orientation=Gtk.Orientation.HORIZONTAL,
        )
        content.set_position(330)
        content.set_wide_handle(True)
        content.set_vexpand(True)

        content.set_start_child(self._create_sidebar())
        content.set_end_child(self.web_view)

        root.append(content)
        self.set_child(root)

    def _create_summary(self) -> Gtk.Widget:
        total_nights = sum(stop["nights"] for stop in STOPS)

        summary = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=24,
        )
        summary.set_margin_top(10)
        summary.set_margin_bottom(10)
        summary.set_margin_start(16)
        summary.set_margin_end(16)

        version_label = Gtk.Label(
            label="Standalone Travel Planner v0.1"
        )
        version_label.set_xalign(0)

        totals_label = Gtk.Label(
            label=(
                f"{len(STOPS)} stops  •  "
                f"{total_nights} nachten  •  "
                "60 dagen beschikbaar"
            )
        )
        totals_label.set_xalign(1)
        totals_label.set_hexpand(True)

        summary.append(version_label)
        summary.append(totals_label)

        return summary

    def _create_sidebar(self) -> Gtk.Widget:
        self.stop_list.set_selection_mode(
            Gtk.SelectionMode.SINGLE
        )
        self.stop_list.connect(
            "row-activated",
            self._on_stop_activated,
        )

        for stop in STOPS:
            row = Gtk.ListBoxRow()
            row.stop_id = stop["id"]

            box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=3,
            )
            box.set_margin_top(10)
            box.set_margin_bottom(10)
            box.set_margin_start(12)
            box.set_margin_end(12)

            name = Gtk.Label()
            name.set_markup(
                f"<b>{stop['id']}. {stop['name']}</b>"
            )
            name.set_xalign(0)

            nights = Gtk.Label(
                label=f"{stop['nights']} nacht(en)"
            )
            nights.set_xalign(0)
            nights.add_css_class("dim-label")

            box.append(name)
            box.append(nights)

            row.set_child(box)
            self.stop_list.append(row)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )
        scroller.set_child(self.stop_list)

        return scroller

    def _load_map(self) -> None:
        map_path = Path(__file__).with_name("map.html")
        self.web_view.load_uri(map_path.resolve().as_uri())

    def _run_javascript(self, script: str) -> None:
        self.web_view.evaluate_javascript(
            script,
            -1,
            None,
            None,
            None,
            None,
            None,
        )

    def _on_stop_activated(
        self,
        _list_box: Gtk.ListBox,
        row: Gtk.ListBoxRow,
    ) -> None:
        self._run_javascript(
            f"window.focusStop({row.stop_id});"
        )

    def _on_complete_route_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        self._run_javascript(
            "window.showCompleteRoute();"
        )


class TravelPlannerApplication(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self) -> None:
        window = self.props.active_window

        if window is None:
            window = TravelPlannerWindow(self)

        window.present()


def main() -> int:
    application = TravelPlannerApplication()
    return application.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
