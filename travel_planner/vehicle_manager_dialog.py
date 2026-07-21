"""Vehicle profile manager dialog."""

from __future__ import annotations

from gi.repository import Gtk

from travel_planner.vehicle_profile_repository import (
    VehicleProfileRepository,
)


class VehicleManagerDialog(Gtk.Window):
    """Show the reusable vehicle profiles known to Travel Planner."""

    def __init__(
        self,
        parent: Gtk.Window,
        repository: VehicleProfileRepository,
    ) -> None:
        super().__init__(
            title="Voertuigen",
            transient_for=parent,
            modal=True,
        )

        self.repository = repository

        self.set_default_size(520, 380)
        self.set_resizable(True)

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        root.set_margin_top(16)
        root.set_margin_bottom(16)
        root.set_margin_start(16)
        root.set_margin_end(16)

        title_label = Gtk.Label(label="Voertuigprofielen")
        title_label.set_xalign(0)
        title_label.add_css_class("title-2")

        explanation_label = Gtk.Label(
            label=(
                "Voertuigprofielen kunnen later aan verschillende "
                "reizen worden gekoppeld."
            )
        )
        explanation_label.set_xalign(0)
        explanation_label.set_wrap(True)

        self.profile_list = Gtk.ListBox()
        self.profile_list.set_selection_mode(
            Gtk.SelectionMode.SINGLE
        )
        self.profile_list.set_vexpand(True)
        self.profile_list.connect(
            "row-selected",
            self._on_profile_selected,
        )

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )
        scroller.set_vexpand(True)
        scroller.set_child(self.profile_list)

        action_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )

        self.new_button = Gtk.Button(label="Nieuw")
        self.edit_button = Gtk.Button(label="Bewerken")
        self.delete_button = Gtk.Button(label="Verwijderen")

        self.new_button.set_sensitive(False)
        self.edit_button.set_sensitive(False)
        self.delete_button.set_sensitive(False)

        action_box.append(self.new_button)
        action_box.append(self.edit_button)
        action_box.append(self.delete_button)

        footer_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        footer_box.set_halign(Gtk.Align.END)

        close_button = Gtk.Button(label="Sluiten")
        close_button.add_css_class("suggested-action")
        close_button.connect(
            "clicked",
            self._on_close_clicked,
        )

        footer_box.append(close_button)

        root.append(title_label)
        root.append(explanation_label)
        root.append(scroller)
        root.append(action_box)
        root.append(footer_box)

        self.set_child(root)

        self._refresh_profiles()

    def _refresh_profiles(self) -> None:
        """Rebuild the visible vehicle profile list."""

        child = self.profile_list.get_first_child()

        while child is not None:
            next_child = child.get_next_sibling()
            self.profile_list.remove(child)
            child = next_child

        profiles = self.repository.list_profiles()

        if not profiles:
            row = Gtk.ListBoxRow()
            row.set_selectable(False)
            row.set_activatable(False)

            label = Gtk.Label(
                label="Er zijn nog geen voertuigprofielen."
            )
            label.set_xalign(0)
            label.set_margin_top(12)
            label.set_margin_bottom(12)
            label.set_margin_start(12)
            label.set_margin_end(12)
            label.add_css_class("dim-label")

            row.set_child(label)
            self.profile_list.append(row)
            return

        for profile in profiles:
            row = Gtk.ListBoxRow()
            row.profile_id = profile.profile_id

            content = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=4,
            )
            content.set_margin_top(10)
            content.set_margin_bottom(10)
            content.set_margin_start(12)
            content.set_margin_end(12)

            name_label = Gtk.Label(label=profile.name)
            name_label.set_xalign(0)
            name_label.add_css_class("heading")

            details = self._profile_details(profile)

            details_label = Gtk.Label(label=details)
            details_label.set_xalign(0)
            details_label.add_css_class("dim-label")

            content.append(name_label)
            content.append(details_label)

            row.set_child(content)
            self.profile_list.append(row)

    @staticmethod
    def _profile_details(profile: object) -> str:
        """Return a compact, readable profile summary."""

        parts: list[str] = []

        length_m = getattr(profile, "length_m", None)
        width_m = getattr(profile, "width_m", None)
        height_m = getattr(profile, "height_m", None)
        max_weight_kg = getattr(
            profile,
            "max_weight_kg",
            None,
        )
        emission_class = getattr(
            profile,
            "emission_class",
            None,
        )

        dimensions = [
            value
            for value in (
                length_m,
                width_m,
                height_m,
            )
            if value is not None
        ]

        if len(dimensions) == 3:
            parts.append(
                f"{length_m:.2f} × "
                f"{width_m:.2f} × "
                f"{height_m:.2f} m"
            )

        if max_weight_kg is not None:
            parts.append(f"{max_weight_kg} kg")

        if emission_class:
            parts.append(str(emission_class))

        if not parts:
            return "Nog geen voertuiggegevens ingevuld"

        return " · ".join(parts)

    def _on_profile_selected(
        self,
        _list_box: Gtk.ListBox,
        row: Gtk.ListBoxRow | None,
    ) -> None:
        """Prepare selection handling for the next sprint."""

        has_profile = (
            row is not None
            and hasattr(row, "profile_id")
        )

        # These actions become active in the next implementation phase.
        self.edit_button.set_sensitive(False)
        self.delete_button.set_sensitive(False)

        if not has_profile:
            return

    def _on_close_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        self.close()
