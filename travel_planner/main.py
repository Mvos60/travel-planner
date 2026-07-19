from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, Gtk

from travel_planner.window import TravelPlannerWindow


APP_ID = "com.mac.travelplanner"


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
