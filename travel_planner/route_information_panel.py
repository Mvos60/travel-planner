from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Pango


ROUTE_INFORMATION_ROWS = (
    ("distance", "Afstand"),
    ("duration", "Rijtijd (provider)"),
    ("provider", "Provider"),
    ("profile", "Profiel"),
    ("applied", "Toegepast"),
    ("unavailable", "Niet toegepast"),
)


class RouteInformationPanel(Gtk.Box):
    """Present the currently calculated route information."""

    def __init__(
        self,
        *,
        on_recalculate: Callable[[Gtk.Button], None],
    ) -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
        )

        self._value_labels: dict[str, Gtk.Label] = {}
        self._caption_labels: dict[str, Gtk.Label] = {}

        separator = Gtk.Separator(
            orientation=Gtk.Orientation.HORIZONTAL,
        )
        separator.set_margin_top(8)
        self.append(separator)

        title = Gtk.Label(label="Route")
        title.set_xalign(0)
        title.add_css_class("heading")
        title.set_margin_top(4)
        self.append(title)

        recalculate_button = Gtk.Button(
            label="Route opnieuw berekenen"
        )
        recalculate_button.set_hexpand(True)
        recalculate_button.set_margin_top(4)
        recalculate_button.set_margin_bottom(4)
        recalculate_button.connect(
            "clicked",
            on_recalculate,
        )
        self.append(recalculate_button)

        grid = Gtk.Grid(
            column_spacing=12,
            row_spacing=4,
        )
        grid.set_hexpand(True)

        for row_index, (key, caption) in enumerate(
            ROUTE_INFORMATION_ROWS
        ):
            caption_label = Gtk.Label(label=caption)
            caption_label.set_xalign(0)

            value_label = Gtk.Label(label="—")
            value_label.set_xalign(0)
            value_label.set_hexpand(True)
            value_label.set_wrap(True)
            value_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)

            grid.attach(
                caption_label,
                0,
                row_index,
                1,
                1,
            )
            grid.attach(
                value_label,
                1,
                row_index,
                1,
                1,
            )

            self._caption_labels[key] = caption_label
            self._value_labels[key] = value_label

        self.append(grid)
        self.clear()

    def update(
        self,
        *,
        distance: str,
        duration: str,
        provider: str,
        profile: str,
        applied: str,
        unavailable: str,
        show_unavailable: bool,
    ) -> None:
        """Show the latest route information."""

        values = {
            "distance": distance,
            "duration": duration,
            "provider": provider,
            "profile": profile,
            "applied": applied,
            "unavailable": unavailable,
        }

        for key, value in values.items():
            self._value_labels[key].set_text(value)

        self._caption_labels["unavailable"].set_visible(
            show_unavailable
        )
        self._value_labels["unavailable"].set_visible(
            show_unavailable
        )

    def clear(self) -> None:
        """Reset the panel when no calculated route is available."""

        for value_label in self._value_labels.values():
            value_label.set_text("—")

        self._caption_labels["unavailable"].set_visible(False)
        self._value_labels["unavailable"].set_visible(False)
