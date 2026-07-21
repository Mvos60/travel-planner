"""Dialog for creating and editing a vehicle profile."""

from __future__ import annotations

from collections.abc import Callable

from gi.repository import GLib, Gtk

from travel_planner.vehicle_profile import VehicleProfile


class VehicleProfileEditorDialog(Gtk.Window):
    """Edit one reusable vehicle profile."""

    def __init__(
        self,
        parent: Gtk.Window,
        *,
        profile: VehicleProfile | None = None,
        on_save: Callable[[VehicleProfile], None],
    ) -> None:
        super().__init__(
            title=(
                "Voertuig bewerken"
                if profile is not None
                else "Nieuw voertuig"
            ),
            transient_for=parent,
            modal=True,
        )

        self.profile = profile
        self.on_save = on_save

        self.set_default_size(500, 520)
        self.set_resizable(False)

        self.name_entry = Gtk.Entry()
        self.length_entry = Gtk.Entry()
        self.width_entry = Gtk.Entry()
        self.height_entry = Gtk.Entry()
        self.weight_entry = Gtk.Entry()
        self.emission_entry = Gtk.Entry()

        self.error_label = Gtk.Label()
        self.error_label.set_xalign(0)
        self.error_label.set_wrap(True)
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
        )
        root.set_margin_top(20)
        root.set_margin_bottom(20)
        root.set_margin_start(20)
        root.set_margin_end(20)

        title_label = Gtk.Label(
            label=(
                "Voertuigprofiel bewerken"
                if profile is not None
                else "Nieuw voertuigprofiel"
            )
        )
        title_label.set_xalign(0)
        title_label.add_css_class("title-2")

        general_label = self._create_section_label(
            "Algemeen"
        )

        general_grid = Gtk.Grid(
            column_spacing=16,
            row_spacing=12,
        )
        general_grid.set_hexpand(True)

        self._add_field(
            general_grid,
            row=0,
            label="Naam",
            entry=self.name_entry,
            placeholder="bijv. Mijn camper",
        )

        dimensions_label = self._create_section_label(
            "Afmetingen"
        )

        dimensions_grid = Gtk.Grid(
            column_spacing=16,
            row_spacing=12,
        )
        dimensions_grid.set_hexpand(True)

        self._add_field(
            dimensions_grid,
            row=0,
            label="Lengte (meter)",
            entry=self.length_entry,
            placeholder="bijv. 7,20",
        )
        self._add_field(
            dimensions_grid,
            row=1,
            label="Breedte (meter)",
            entry=self.width_entry,
            placeholder="bijv. 2,30",
        )
        self._add_field(
            dimensions_grid,
            row=2,
            label="Hoogte (meter)",
            entry=self.height_entry,
            placeholder="bijv. 2,90",
        )

        technical_label = self._create_section_label(
            "Technisch"
        )

        technical_grid = Gtk.Grid(
            column_spacing=16,
            row_spacing=12,
        )
        technical_grid.set_hexpand(True)

        self._add_field(
            technical_grid,
            row=0,
            label="Max. gewicht (kg)",
            entry=self.weight_entry,
            placeholder="bijv. 3500",
        )
        self._add_field(
            technical_grid,
            row=1,
            label="Emissieklasse",
            entry=self.emission_entry,
            placeholder="bijv. Euro 6",
        )

        button_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(4)

        cancel_button = Gtk.Button(label="Annuleren")
        cancel_button.connect(
            "clicked",
            self._on_cancel_clicked,
        )

        save_button = Gtk.Button(label="Opslaan")
        save_button.add_css_class("suggested-action")
        save_button.connect(
            "clicked",
            self._on_save_clicked,
        )

        button_box.append(cancel_button)
        button_box.append(save_button)

        root.append(title_label)
        root.append(general_label)
        root.append(general_grid)
        root.append(dimensions_label)
        root.append(dimensions_grid)
        root.append(technical_label)
        root.append(technical_grid)
        root.append(self.error_label)
        root.append(button_box)

        self.set_child(root)

        self._populate_fields()

        GLib.idle_add(self._focus_name_entry)

    @staticmethod
    def _create_section_label(
        text: str,
    ) -> Gtk.Label:
        label = Gtk.Label(label=text)
        label.set_xalign(0)
        label.add_css_class("heading")
        label.set_margin_top(4)

        return label

    @staticmethod
    def _add_field(
        grid: Gtk.Grid,
        *,
        row: int,
        label: str,
        entry: Gtk.Entry,
        placeholder: str,
    ) -> None:
        field_label = Gtk.Label(label=label)
        field_label.set_xalign(0)

        entry.set_hexpand(True)
        entry.set_placeholder_text(placeholder)

        grid.attach(field_label, 0, row, 1, 1)
        grid.attach(entry, 1, row, 1, 1)

    def _focus_name_entry(self) -> bool:
        self.name_entry.grab_focus()

        if self.profile is not None:
            self.name_entry.select_region(0, -1)

        return GLib.SOURCE_REMOVE

    def _populate_fields(self) -> None:
        if self.profile is None:
            return

        self.name_entry.set_text(self.profile.name)

        self._set_optional_number(
            self.length_entry,
            self.profile.length_m,
        )
        self._set_optional_number(
            self.width_entry,
            self.profile.width_m,
        )
        self._set_optional_number(
            self.height_entry,
            self.profile.height_m,
        )
        self._set_optional_number(
            self.weight_entry,
            self.profile.max_weight_kg,
        )

        if self.profile.emission_class is not None:
            self.emission_entry.set_text(
                self.profile.emission_class
            )

    @staticmethod
    def _set_optional_number(
        entry: Gtk.Entry,
        value: float | int | None,
    ) -> None:
        if value is None:
            return

        entry.set_text(str(value).replace(".", ","))

    def _on_cancel_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        self.close()

    def _on_save_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        try:
            profile = self._build_profile()
            self.on_save(profile)
        except (TypeError, ValueError) as error:
            self._show_error(str(error))
            return

        self.close()

    def _build_profile(self) -> VehicleProfile:
        name = self.name_entry.get_text().strip()

        if not name:
            raise ValueError(
                "Vul een naam voor het voertuig in."
            )

        arguments = {
            "name": name,
            "length_m": self._optional_float(
                self.length_entry.get_text(),
                "Lengte",
            ),
            "width_m": self._optional_float(
                self.width_entry.get_text(),
                "Breedte",
            ),
            "height_m": self._optional_float(
                self.height_entry.get_text(),
                "Hoogte",
            ),
            "max_weight_kg": self._optional_int(
                self.weight_entry.get_text(),
                "Maximaal gewicht",
            ),
            "emission_class": (
                self.emission_entry.get_text().strip()
                or None
            ),
        }

        if self.profile is not None:
            arguments["profile_id"] = (
                self.profile.profile_id
            )

        return VehicleProfile(**arguments)

    @staticmethod
    def _optional_float(
        text: str,
        field_name: str,
    ) -> float | None:
        value = text.strip()

        if not value:
            return None

        try:
            number = float(value.replace(",", "."))
        except ValueError as error:
            raise ValueError(
                f"{field_name} moet een geldig getal zijn."
            ) from error

        if number <= 0:
            raise ValueError(
                f"{field_name} moet groter zijn dan nul."
            )

        return number

    @staticmethod
    def _optional_int(
        text: str,
        field_name: str,
    ) -> int | None:
        value = text.strip()

        if not value:
            return None

        try:
            number = int(value)
        except ValueError as error:
            raise ValueError(
                f"{field_name} moet een geheel getal zijn."
            ) from error

        if number <= 0:
            raise ValueError(
                f"{field_name} moet groter zijn dan nul."
            )

        return number

    def _show_error(self, message: str) -> None:
        self.error_label.set_text(message)
        self.error_label.set_visible(True)
