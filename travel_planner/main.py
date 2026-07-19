from __future__ import annotations

import json
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import Gio, Gtk, WebKit

from travel_planner.trip import Stop, Trip


APP_ID = "com.mac.travelplanner"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRIP_PATH = PROJECT_ROOT / "data" / "adriatic-2026.trip.json"


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
        self.name_entry.set_placeholder_text("Bijvoorbeeld: Bohinj")

        self.latitude_entry = Gtk.Entry()
        self.latitude_entry.set_placeholder_text("Bijvoorbeeld: 46.2823")

        self.longitude_entry = Gtk.Entry()
        self.longitude_entry.set_placeholder_text("Bijvoorbeeld: 13.8582")

        self.nights_spin = Gtk.SpinButton.new_with_range(
            0,
            60,
            1,
        )
        self.nights_spin.set_value(1)

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
            latitude = float(
                self.latitude_entry.get_text().strip()
            )
            longitude = float(
                self.longitude_entry.get_text().strip()
            )
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
        super().__init__(
            application=application,
            title="Travel Planner",
        )

        self.set_default_size(1200, 760)

        self.trip = Trip(name="Adriatic 2026")
        self.web_view = WebKit.WebView()
        self.stop_list = Gtk.ListBox()
        self.summary_label = Gtk.Label()

        self._build_interface()
        self._load_map()

    def _build_interface(self) -> None:
        header = Gtk.HeaderBar()

        title = Gtk.Label()
        title.set_markup("<b>Adriatic 2026</b>")
        header.set_title_widget(title)

        add_button = Gtk.Button(label="Stop toevoegen")
        add_button.connect(
            "clicked",
            self._on_add_stop_clicked,
        )
        header.pack_start(add_button)

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

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )
        scroller.set_child(self.stop_list)

        content.set_start_child(scroller)
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
        dialog.destroy()
        self._refresh_interface()

    def _on_save_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        self.trip.save(TRIP_PATH)

        self._show_message(
            "Reis opgeslagen",
            str(TRIP_PATH),
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
