"""Dialog for configuring online route providers."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from travel_planner.route_provider_manager import (
    RouteProviderManager,
)


class ProviderSettingsDialog(Gtk.Dialog):
    """Edit persistent routing-provider settings."""

    def __init__(
        self,
        parent: Gtk.Window,
        *,
        manager: RouteProviderManager,
        selected_provider_id: str,
        openrouteservice_api_key: str,
    ) -> None:
        super().__init__(
            title="Routeproviderinstellingen",
            transient_for=parent,
            modal=True,
        )

        self.manager = manager

        self.add_button(
            "Annuleren",
            Gtk.ResponseType.CANCEL,
        )
        self.add_button(
            "Opslaan",
            Gtk.ResponseType.OK,
        )

        self.provider_combo = Gtk.ComboBoxText()

        for provider_id in manager.available_provider_ids():
            self.provider_combo.append(
                provider_id,
                manager.provider_display_name(provider_id),
            )

        if (
            selected_provider_id
            not in manager.available_provider_ids()
        ):
            selected_provider_id = "osrm-demo"

        self.provider_combo.set_active_id(
            selected_provider_id
        )

        self.api_key_entry = Gtk.PasswordEntry()
        self.api_key_entry.set_show_peek_icon(True)
        self.api_key_entry.set_hexpand(True)
        self.api_key_entry.set_text(
            openrouteservice_api_key
        )

        self.api_key_hint = Gtk.Label(
            label=(
                "De API-key wordt lokaal opgeslagen in "
                "~/.config/travel-planner/settings.json."
            )
        )
        self.api_key_hint.set_xalign(0)
        self.api_key_hint.set_wrap(True)
        self.api_key_hint.add_css_class("dim-label")

        self.provider_combo.connect(
            "changed",
            self._on_provider_changed,
        )

        self._build_layout()
        self._update_api_key_state()

    def _build_layout(self) -> None:
        content = self.get_content_area()

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_size_request(460, -1)

        provider_label = Gtk.Label(
            label="Standaard routeprovider"
        )
        provider_label.set_xalign(0)
        provider_label.add_css_class("heading")

        box.append(provider_label)
        box.append(self.provider_combo)

        self.api_key_label = Gtk.Label(
            label="OpenRouteService API-key"
        )
        self.api_key_label.set_xalign(0)
        self.api_key_label.set_margin_top(8)
        self.api_key_label.add_css_class("heading")

        box.append(self.api_key_label)
        box.append(self.api_key_entry)
        box.append(self.api_key_hint)

        content.append(box)

    def _on_provider_changed(
        self,
        _combo: Gtk.ComboBoxText,
    ) -> None:
        self._update_api_key_state()

    def _update_api_key_state(self) -> None:
        uses_openrouteservice = (
            self.selected_provider_id
            == "openrouteservice"
        )

        self.api_key_label.set_visible(
            uses_openrouteservice
        )
        self.api_key_entry.set_visible(
            uses_openrouteservice
        )
        self.api_key_hint.set_visible(
            uses_openrouteservice
        )

        self.api_key_entry.set_sensitive(
            uses_openrouteservice
        )

        self.set_default_size(460, -1)
        self.queue_resize()

    @property
    def selected_provider_id(self) -> str:
        provider_id = self.provider_combo.get_active_id()

        if provider_id is None:
            return "osrm-demo"

        return provider_id

    @property
    def openrouteservice_api_key(self) -> str:
        return self.api_key_entry.get_text().strip()
