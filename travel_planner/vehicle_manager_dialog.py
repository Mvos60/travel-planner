"""Vehicle profile manager dialog."""

from __future__ import annotations

from collections.abc import Callable

from gi.repository import Gtk

from travel_planner.context import TravelPlannerContext
from travel_planner.vehicle_profile import VehicleProfile
from travel_planner.vehicle_profile_editor_dialog import (
    VehicleProfileEditorDialog,
)
from travel_planner.vehicle_profile_repository import (
    VehicleProfileRepository,
)


class VehicleManagerDialog(Gtk.Window):
    """Manage reusable vehicle profiles."""

    def __init__(
        self,
        parent: Gtk.Window,
        repository: VehicleProfileRepository,
        *,
        context: TravelPlannerContext,
        on_profiles_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            title="Voertuigen",
            transient_for=parent,
            modal=True,
        )

        self.repository = repository
        self.context = context
        self.on_profiles_changed = on_profiles_changed

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
                "Voertuigprofielen kunnen aan verschillende "
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
        self.profile_list.connect(
            "row-activated",
            self._on_profile_activated,
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
        self.new_button.connect(
            "clicked",
            self._on_new_clicked,
        )

        self.edit_button = Gtk.Button(label="Bewerken")
        self.edit_button.set_sensitive(False)
        self.edit_button.connect(
            "clicked",
            self._on_edit_clicked,
        )

        self.delete_button = Gtk.Button(label="Verwijderen")
        self.delete_button.set_sensitive(False)
        self.delete_button.add_css_class("destructive-action")
        self.delete_button.connect(
            "clicked",
            self._on_delete_clicked,
        )

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

    def _refresh_profiles(
        self,
        *,
        select_profile_id: str | None = None,
    ) -> None:
        child = self.profile_list.get_first_child()

        while child is not None:
            next_child = child.get_next_sibling()
            self.profile_list.remove(child)
            child = next_child

        self.edit_button.set_sensitive(False)
        self.delete_button.set_sensitive(False)

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

        row_to_select: Gtk.ListBoxRow | None = None

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

            details_label = Gtk.Label(
                label=self._profile_details(profile)
            )
            details_label.set_xalign(0)
            details_label.add_css_class("dim-label")

            content.append(name_label)
            content.append(details_label)

            row.set_child(content)
            self.profile_list.append(row)

            if profile.profile_id == select_profile_id:
                row_to_select = row

        if row_to_select is not None:
            self.profile_list.select_row(row_to_select)

    @staticmethod
    def _profile_details(
        profile: VehicleProfile,
    ) -> str:
        parts: list[str] = []

        if (
            profile.length_m is not None
            and profile.width_m is not None
            and profile.height_m is not None
        ):
            parts.append(
                f"{profile.length_m:.2f} × "
                f"{profile.width_m:.2f} × "
                f"{profile.height_m:.2f} m"
            )

        if profile.max_weight_kg is not None:
            parts.append(f"{profile.max_weight_kg} kg")

        if profile.emission_class:
            parts.append(profile.emission_class)

        if not parts:
            return "Nog geen voertuiggegevens ingevuld"

        return " · ".join(parts)

    def _selected_profile(
        self,
    ) -> VehicleProfile | None:
        row = self.profile_list.get_selected_row()

        if row is None or not hasattr(row, "profile_id"):
            return None

        return self.repository.get(row.profile_id)

    def _on_profile_selected(
        self,
        _list_box: Gtk.ListBox,
        row: Gtk.ListBoxRow | None,
    ) -> None:
        has_profile = (
            row is not None
            and hasattr(row, "profile_id")
        )

        self.edit_button.set_sensitive(has_profile)
        self.delete_button.set_sensitive(has_profile)

    def _on_profile_activated(
        self,
        _list_box: Gtk.ListBox,
        row: Gtk.ListBoxRow,
    ) -> None:
        if not hasattr(row, "profile_id"):
            return

        self._open_editor(
            self.repository.get(row.profile_id)
        )

    def _on_new_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        self._open_editor(None)

    def _on_edit_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        profile = self._selected_profile()

        if profile is None:
            return

        self._open_editor(profile)

    def _on_delete_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        profile = self._selected_profile()

        if profile is None:
            return

        if (
            self.context.current_trip.vehicle_profile_id
            == profile.profile_id
        ):
            self._show_information_dialog(
                title="Voertuig in gebruik",
                message=(
                    f'Het voertuigprofiel "{profile.name}" wordt '
                    "gebruikt door de huidige reis en kan daarom "
                    "niet worden verwijderd.\n\n"
                    "Kies eerst een ander voertuig voor de reis."
                ),
            )
            return

        self._show_delete_confirmation(profile)

    def _show_delete_confirmation(
        self,
        profile: VehicleProfile,
    ) -> None:
        dialog = Gtk.Window(
            title="Voertuig verwijderen",
            transient_for=self,
            modal=True,
        )
        dialog.set_default_size(430, 210)
        dialog.set_resizable(False)

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
        )
        root.set_margin_top(20)
        root.set_margin_bottom(20)
        root.set_margin_start(20)
        root.set_margin_end(20)

        title_label = Gtk.Label(
            label="Voertuigprofiel verwijderen?"
        )
        title_label.set_xalign(0)
        title_label.add_css_class("title-3")

        message_label = Gtk.Label(
            label=(
                f'Weet u zeker dat u "{profile.name}" '
                "wilt verwijderen?\n\n"
                "Deze actie kan niet ongedaan worden gemaakt."
            )
        )
        message_label.set_xalign(0)
        message_label.set_wrap(True)

        button_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        button_box.set_halign(Gtk.Align.END)

        cancel_button = Gtk.Button(label="Annuleren")
        cancel_button.connect(
            "clicked",
            lambda _button: dialog.close(),
        )

        delete_button = Gtk.Button(label="Verwijderen")
        delete_button.add_css_class("destructive-action")
        delete_button.connect(
            "clicked",
            self._confirm_delete,
            dialog,
            profile,
        )

        button_box.append(cancel_button)
        button_box.append(delete_button)

        root.append(title_label)
        root.append(message_label)
        root.append(button_box)

        dialog.set_child(root)
        dialog.present()

    def _confirm_delete(
        self,
        _button: Gtk.Button,
        dialog: Gtk.Window,
        profile: VehicleProfile,
    ) -> None:
        removed = self.repository.remove(
            profile.profile_id
        )

        if not removed:
            dialog.close()
            self._show_information_dialog(
                title="Verwijderen mislukt",
                message=(
                    "Het voertuigprofiel bestaat niet meer."
                ),
            )
            return

        self.repository.save()
        dialog.close()

        self._refresh_profiles()

        if self.on_profiles_changed is not None:
            self.on_profiles_changed()

    def _show_information_dialog(
        self,
        *,
        title: str,
        message: str,
    ) -> None:
        dialog = Gtk.Window(
            title=title,
            transient_for=self,
            modal=True,
        )
        dialog.set_default_size(430, 210)
        dialog.set_resizable(False)

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
        )
        root.set_margin_top(20)
        root.set_margin_bottom(20)
        root.set_margin_start(20)
        root.set_margin_end(20)

        title_label = Gtk.Label(label=title)
        title_label.set_xalign(0)
        title_label.add_css_class("title-3")

        message_label = Gtk.Label(label=message)
        message_label.set_xalign(0)
        message_label.set_wrap(True)

        close_button = Gtk.Button(label="Sluiten")
        close_button.set_halign(Gtk.Align.END)
        close_button.add_css_class("suggested-action")
        close_button.connect(
            "clicked",
            lambda _button: dialog.close(),
        )

        root.append(title_label)
        root.append(message_label)
        root.append(close_button)

        dialog.set_child(root)
        dialog.present()

    def _open_editor(
        self,
        profile: VehicleProfile | None,
    ) -> None:
        editor = VehicleProfileEditorDialog(
            parent=self,
            profile=profile,
            on_save=self._save_profile,
        )
        editor.present()

    def _save_profile(
        self,
        profile: VehicleProfile,
    ) -> None:
        if self.repository.get(profile.profile_id) is None:
            self.repository.add(profile)
        else:
            self.repository.update(profile)

        self.repository.save()

        self._refresh_profiles(
            select_profile_id=profile.profile_id
        )

        if self.on_profiles_changed is not None:
            self.on_profiles_changed()

    def _on_close_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        self.close()
