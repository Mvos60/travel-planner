"""Dialog for configuring online route providers."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from travel_planner.route_provider_manager import (
    RouteProviderManager,
)
from travel_planner.route_service import RouteProviderError


class ProviderSettingsDialog(Gtk.Dialog):
    """Edit and test persistent routing-provider settings."""

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

        self.test_button = Gtk.Button(
            label="Test verbinding"
        )
        self.test_button.set_halign(Gtk.Align.START)

        self.test_status = Gtk.Label()
        self.test_status.set_xalign(0)
        self.test_status.set_wrap(True)
        self.test_status.set_visible(False)

        self.provider_combo.connect(
            "changed",
            self._on_provider_changed,
        )
        self.test_button.connect(
            "clicked",
            self._on_test_connection_clicked,
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

        separator = Gtk.Separator(
            orientation=Gtk.Orientation.HORIZONTAL
        )
        separator.set_margin_top(6)

        box.append(separator)
        box.append(self.test_button)
        box.append(self.test_status)

        content.append(box)

    def _on_provider_changed(
        self,
        _combo: Gtk.ComboBoxText,
    ) -> None:
        self._clear_test_status()
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

    def _on_test_connection_clicked(
        self,
        _button: Gtk.Button,
    ) -> None:
        provider_id = self.selected_provider_id
        api_key = self.openrouteservice_api_key

        self.test_button.set_sensitive(False)
        self.provider_combo.set_sensitive(False)
        self.api_key_entry.set_sensitive(False)

        self.test_status.set_text(
            "Verbinding wordt getest…"
        )
        self.test_status.remove_css_class("error")
        self.test_status.remove_css_class("success")
        self.test_status.set_visible(True)

        worker = threading.Thread(
            target=self._test_connection_worker,
            args=(provider_id, api_key),
            daemon=True,
        )
        worker.start()

    def _test_connection_worker(
        self,
        provider_id: str,
        api_key: str,
    ) -> None:
        try:
            self.manager.test_provider_connection(
                provider_id,
                openrouteservice_api_key=api_key,
            )
        except RouteProviderError as exc:
            GLib.idle_add(
                self._finish_connection_test,
                False,
                str(exc),
            )
        except Exception as exc:
            GLib.idle_add(
                self._finish_connection_test,
                False,
                f"Onverwachte fout: {exc}",
            )
        else:
            GLib.idle_add(
                self._finish_connection_test,
                True,
                "",
            )

    def _finish_connection_test(
        self,
        succeeded: bool,
        message: str,
    ) -> bool:
        self.test_button.set_sensitive(True)
        self.provider_combo.set_sensitive(True)
        self._update_api_key_state()

        if succeeded:
            provider_name = self.manager.provider_display_name(
                self.selected_provider_id
            )
            self.test_status.set_text(
                f"✓ Verbinding met {provider_name} geslaagd."
            )
            self.test_status.remove_css_class("error")
            self.test_status.add_css_class("success")
        else:
            self.test_status.set_text(
                f"✗ Verbinding mislukt: {message}"
            )
            self.test_status.remove_css_class("success")
            self.test_status.add_css_class("error")

        self.test_status.set_visible(True)
        self.queue_resize()

        return False

    def _clear_test_status(self) -> None:
        self.test_status.set_text("")
        self.test_status.set_visible(False)
        self.test_status.remove_css_class("error")
        self.test_status.remove_css_class("success")

    @property
    def selected_provider_id(self) -> str:
        provider_id = self.provider_combo.get_active_id()

        if provider_id is None:
            return "osrm-demo"

        return provider_id

    @property
    def openrouteservice_api_key(self) -> str:
        return self.api_key_entry.get_text().strip()
