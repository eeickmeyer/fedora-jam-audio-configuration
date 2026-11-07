"""GTK 4 + libadwaita implementation of the Audio Config UI."""

from __future__ import annotations

import threading
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .base import AudioConfigUI, ChecklistItem, ComboItem  # noqa: E402
from i18n import _  # noqa: E402

ICON_PATH = "/usr/share/icons/hicolor/scalable/apps/start-here.svg"


class _DialogHelper:
    """Small mixin for running modal Gtk 4 dialogs synchronously."""

    @staticmethod
    def _run_dialog(dialog: Gtk.Window) -> int:
        """Block until *dialog* is closed. Returns the response id."""
        loop = GLib.MainLoop()
        result = {"response": Gtk.ResponseType.CANCEL}

        def on_response(_dlg, resp):
            result["response"] = resp
            dialog.close()
            loop.quit()

        dialog.connect("response", on_response)
        dialog.present()
        loop.run()
        return result["response"]


class GtkUI(AudioConfigUI):
    """Concrete UI using GTK 4 / libadwaita."""

    def __init__(self) -> None:
        self._app: Adw.Application | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init(self) -> None:
        self._app = Adw.Application(application_id="org.fedorajam.AudioConfig")
        self._app.register()

    def quit(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _transient(self) -> Gtk.Window | None:
        if self._app:
            return self._app.get_active_window()
        return None

    def _make_message_dialog(
        self,
        title: str,
        text: str,
        msg_type: str = "info",
        buttons: list[tuple[str, int]] | None = None,
    ) -> Adw.MessageDialog:  # type: ignore[name-defined]
        dlg = Adw.MessageDialog(
            heading=title,
            body=text,
            transient_for=self._transient(),
            modal=True,
        )
        dlg.set_body_use_markup(True)
        dlg.set_default_size(520, -1)
        if buttons is None:
            dlg.add_response("ok", _("OK"))
            dlg.set_default_response("ok")
        else:
            for label, resp_id in buttons:
                dlg.add_response(str(resp_id), label)
        return dlg

    def _run_adw_dialog(self, dlg: Adw.MessageDialog) -> str:
        """Run an Adw.MessageDialog and return the response id string."""
        loop = GLib.MainLoop()
        result = {"response": "cancel"}

        def on_response(_dlg, resp):
            result["response"] = resp
            loop.quit()

        dlg.connect("response", on_response)
        if self._app:
            dlg.set_application(self._app)
        dlg.present()
        loop.run()
        return result["response"]

    # ------------------------------------------------------------------
    # Simple message dialogs
    # ------------------------------------------------------------------

    def show_info(self, title: str, text: str) -> None:
        dlg = self._make_message_dialog(title, text, "info")
        self._run_adw_dialog(dlg)

    def show_error(self, title: str, text: str) -> None:
        dlg = self._make_message_dialog(title, text, "error")
        self._run_adw_dialog(dlg)

    def show_warning(self, title: str, text: str) -> None:
        dlg = self._make_message_dialog(title, text, "warning")
        self._run_adw_dialog(dlg)

    def show_question(
        self,
        title: str,
        text: str,
        ok_label: str = "Yes",
        cancel_label: str = "No",
    ) -> bool:
        dlg = Adw.MessageDialog(
            heading=title,
            body=text,
            transient_for=self._transient(),
            modal=True,
        )
        dlg.set_body_use_markup(True)
        dlg.add_response("cancel", cancel_label)
        dlg.add_response("ok", ok_label)
        dlg.set_default_response("ok")
        dlg.set_close_response("cancel")
        resp = self._run_adw_dialog(dlg)
        return resp == "ok"

    # ------------------------------------------------------------------
    # Entry dialog
    # ------------------------------------------------------------------

    def show_entry(
        self,
        title: str,
        text: str,
        default: str = "",
        ok_label: str = "OK",
        cancel_label: str = "Cancel",
    ) -> str | None:
        dlg = Adw.MessageDialog(
            heading=title,
            transient_for=self._transient(),
            modal=True,
        )
        dlg.set_body_use_markup(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        label = Gtk.Label(label=text, wrap=True, use_markup=True)
        label.set_xalign(0)
        box.append(label)

        entry = Gtk.Entry(text=default)
        entry.set_activates_default(True)
        box.append(entry)

        box.set_size_request(520, -1)
        dlg.set_extra_child(box)
        dlg.set_default_size(560, -1)
        dlg.add_response("cancel", cancel_label)
        dlg.add_response("ok", ok_label)
        dlg.set_default_response("ok")
        dlg.set_close_response("cancel")

        resp = self._run_adw_dialog(dlg)
        if resp == "ok":
            return entry.get_text()
        return None

    # ------------------------------------------------------------------
    # Tabbed control panel
    # ------------------------------------------------------------------

    def show_tabbed_control_panel(
        self,
        title: str,
        text: str,
        buffer_options: list[str],
        sample_rate_options: list[str],
        current_buffer: str,
        current_sample_rate: str,
        default_buffer: str,
        default_sample_rate: str,
        jack_items: list[ChecklistItem],
        self_connect_items: list[ChecklistItem],
        boot_items: list[ChecklistItem],
        dummy_active: bool,
        dummy_autostart: bool,
        fw_present: bool,
        fw_configured: bool,
        quantum_managed_by_widget: bool = False,
        on_apply: Callable[[dict[str, object]], None] | None = None,
        ok_label: str = "Apply",
        cancel_label: str = "Close",
    ) -> None:
        dlg = Adw.MessageDialog(
            heading=title,
            transient_for=self._transient(),
            modal=True,
        )
        dlg.set_body_use_markup(True)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_start(12)
        root.set_margin_end(12)
        root.set_margin_top(12)
        root.set_margin_bottom(12)

        if text.strip():
            intro = Gtk.Label(label=text, wrap=True, use_markup=True)
            intro.set_xalign(0)
            root.append(intro)

        notebook = Gtk.Notebook()
        notebook.set_hexpand(True)
        notebook.set_vexpand(True)
        notebook.set_show_border(False)
        root.append(notebook)

        # Audio tab
        audio_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        audio_tab.set_margin_start(8)
        audio_tab.set_margin_end(8)
        audio_tab.set_margin_top(8)
        audio_tab.set_margin_bottom(8)

        if quantum_managed_by_widget:
            note = Gtk.Label(
                label=_(
                    "Quantum and Sample Rate are managed by your desktop "
                    "widget or extension."
                ),
                wrap=True,
            )
            note.set_xalign(0)
            audio_tab.append(note)

        quantum_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        buf_lbl = Gtk.Label(
            label=_("<b>Quantum</b> <small>(Default: {value})</small>").format(
                value=default_buffer,
            ),
            use_markup=True,
        )
        buf_lbl.set_xalign(0)
        quantum_row.append(buf_lbl)

        audio_buffer_dd = Gtk.DropDown(model=Gtk.StringList.new(buffer_options))
        try:
            audio_buffer_dd.set_selected(buffer_options.index(current_buffer))
        except ValueError:
            audio_buffer_dd.set_selected(0)
        audio_buffer_dd.set_sensitive(not quantum_managed_by_widget)
        quantum_row.append(audio_buffer_dd)

        rate_lbl = Gtk.Label(
            label=_("<b>Sample Rate (Hz)</b> <small>(Default: {value} Hz)</small>").format(
                value=default_sample_rate,
            ),
            use_markup=True,
        )
        rate_lbl.set_xalign(0)
        quantum_row.append(rate_lbl)

        audio_rate_dd = Gtk.DropDown(model=Gtk.StringList.new(sample_rate_options))
        try:
            audio_rate_dd.set_selected(sample_rate_options.index(current_sample_rate))
        except ValueError:
            audio_rate_dd.set_selected(0)
        audio_rate_dd.set_sensitive(not quantum_managed_by_widget)
        quantum_row.append(audio_rate_dd)
        audio_tab.append(quantum_row)

        jack_header = Gtk.Label(label=f"<b>{_('JACK Options')}</b>", use_markup=True)
        jack_header.set_xalign(0)
        audio_tab.append(jack_header)

        jack_checks: list[tuple[str, Gtk.CheckButton]] = []
        for item in jack_items:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            cb = Gtk.CheckButton(active=item.checked)
            lbl = Gtk.Label(
                label=(
                    f"<b>{item.label}</b>  \u2014  {item.description}"
                    if item.description
                    else f"<b>{item.label}</b>"
                ),
                use_markup=True,
            )
            lbl.set_xalign(0)
            lbl.set_wrap(True)
            row.append(cb)
            row.append(lbl)
            audio_tab.append(row)
            jack_checks.append((item.key, cb))

        sc_header = Gtk.Label(label=f"<b>{_('Self-Connect Mode')}</b>", use_markup=True)
        sc_header.set_xalign(0)
        audio_tab.append(sc_header)

        sc_group: Gtk.CheckButton | None = None
        sc_radios: list[tuple[str, Gtk.CheckButton]] = []
        for item in self_connect_items:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            rb = Gtk.CheckButton(active=item.checked)
            if sc_group is not None:
                rb.set_group(sc_group)
            else:
                sc_group = rb
            lbl = Gtk.Label(
                label=(
                    f"<b>{item.label}</b>  \u2014  {item.description}"
                    if item.description
                    else f"<b>{item.label}</b>"
                ),
                use_markup=True,
            )
            lbl.set_xalign(0)
            lbl.set_wrap(True)
            row.append(rb)
            row.append(lbl)
            audio_tab.append(row)
            sc_radios.append((item.key, rb))

        notebook.append_page(audio_tab, Gtk.Label(label=_("Audio")))

        # Boot tab
        boot_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        boot_tab.set_margin_start(8)
        boot_tab.set_margin_end(8)
        boot_tab.set_margin_top(8)
        boot_tab.set_margin_bottom(8)
        boot_info = Gtk.Label(
            label=_("Kernel low-latency options (restart required)."),
            wrap=True,
        )
        boot_info.set_xalign(0)
        boot_tab.append(boot_info)
        boot_checks: list[tuple[str, Gtk.CheckButton]] = []
        for item in boot_items:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            cb = Gtk.CheckButton(active=item.checked)
            lbl = Gtk.Label(
                label=(
                    f"<b>{item.label}</b>  \u2014  {item.description}"
                    if item.description
                    else f"<b>{item.label}</b>"
                ),
                use_markup=True,
            )
            lbl.set_xalign(0)
            lbl.set_wrap(True)
            row.append(cb)
            row.append(lbl)
            boot_tab.append(row)
            boot_checks.append((item.key, cb))
        notebook.append_page(boot_tab, Gtk.Label(label=_("Kernel")))

        # Dummy tab
        dummy_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        dummy_tab.set_margin_start(8)
        dummy_tab.set_margin_end(8)
        dummy_tab.set_margin_top(8)
        dummy_tab.set_margin_bottom(8)
        dummy_info = Gtk.Label(
            label=_("Use a dummy device to isolate routing in studio workflows."),
            wrap=True,
        )
        dummy_info.set_xalign(0)
        dummy_tab.append(dummy_info)
        dummy_active_cb = Gtk.CheckButton(label=_("Dummy device active"))
        dummy_active_cb.set_active(dummy_active)
        dummy_tab.append(dummy_active_cb)
        dummy_autostart_cb = Gtk.CheckButton(label=_("Start dummy device at login"))
        dummy_autostart_cb.set_active(dummy_autostart)
        dummy_tab.append(dummy_autostart_cb)
        notebook.append_page(dummy_tab, Gtk.Label(label=_("Dummy Device")))

        fw_keep = None
        fw_configure = None
        fw_remove = None

        if fw_present:
            fw_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            fw_tab.set_margin_start(8)
            fw_tab.set_margin_end(8)
            fw_tab.set_margin_top(8)
            fw_tab.set_margin_bottom(8)
            fw_info = Gtk.Label(
                label=_("Manage FireWire (FFADO) integration."),
                wrap=True,
            )
            fw_info.set_xalign(0)
            fw_tab.append(fw_info)

            fw_keep = Gtk.CheckButton(label=_("No changes"))
            fw_keep.set_active(True)
            fw_tab.append(fw_keep)

            fw_configure = Gtk.CheckButton(label=_("Configure or reconfigure FireWire"))
            fw_configure.set_group(fw_keep)
            fw_tab.append(fw_configure)

            if fw_configured:
                fw_remove = Gtk.CheckButton(label=_("Remove FireWire configuration"))
                fw_remove.set_group(fw_keep)
                fw_tab.append(fw_remove)

            notebook.append_page(fw_tab, Gtk.Label(label=_("FireWire")))

        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_min_content_width(720)
        scroll.set_min_content_height(620)
        scroll.set_propagate_natural_height(True)
        scroll.set_child(root)

        dlg.set_extra_child(scroll)
        dlg.set_default_size(820, 700)
        dlg.add_response("cancel", cancel_label)
        dlg.add_response("apply", ok_label)
        dlg.set_default_response("apply")
        dlg.set_close_response("cancel")

        def _collect_result() -> dict[str, object]:
            fw_action = "none"
            if fw_present:
                if fw_configure is not None and fw_configure.get_active():
                    fw_action = "configure"
                elif fw_remove is not None and fw_remove.get_active():
                    fw_action = "remove"

            return {
                "audio_buffer": buffer_options[audio_buffer_dd.get_selected()],
                "audio_rate": sample_rate_options[audio_rate_dd.get_selected()],
                "audio_jack_selected": [key for key, cb in jack_checks if cb.get_active()],
                "audio_self_connect_mode": next(
                    (key for key, rb in sc_radios if rb.get_active()),
                    self_connect_items[0].key,
                ),
                "boot_selected": [key for key, cb in boot_checks if cb.get_active()],
                "dummy_active": dummy_active_cb.get_active(),
                "dummy_autostart": dummy_autostart_cb.get_active(),
                "firewire_action": fw_action,
            }

        while True:
            resp = self._run_adw_dialog(dlg)
            if resp != "apply":
                break

            if on_apply is not None:
                try:
                    on_apply(_collect_result())
                except Exception:
                    self.show_error(title, _("An error has occurred."))

        return

    # ------------------------------------------------------------------
    # Combo-box dialog
    # ------------------------------------------------------------------

    def show_combo_dialog(
        self,
        title: str,
        text: str,
        combos: list[ComboItem],
        ok_label: str = "OK",
        cancel_label: str = "Cancel",
    ) -> list[str] | None:
        dlg = Adw.MessageDialog(
            heading=title,
            transient_for=self._transient(),
            modal=True,
        )
        dlg.set_body_use_markup(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        label = Gtk.Label(label=text, wrap=True, use_markup=True)
        label.set_xalign(0)
        box.append(label)

        dropdowns: list[Gtk.DropDown] = []
        for combo in combos:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            lbl = Gtk.Label(label=f"<b>{combo.label}</b>", use_markup=True)
            lbl.set_xalign(0)
            lbl.set_hexpand(True)
            row.append(lbl)

            string_list = Gtk.StringList.new(combo.options)
            dd = Gtk.DropDown(model=string_list)
            try:
                idx = combo.options.index(combo.default)
            except ValueError:
                idx = 0
            dd.set_selected(idx)
            row.append(dd)
            box.append(row)
            dropdowns.append(dd)

        box.set_size_request(580, -1)
        dlg.set_extra_child(box)
        dlg.set_default_size(660, -1)
        dlg.add_response("cancel", cancel_label)
        dlg.add_response("ok", ok_label)
        dlg.set_default_response("ok")
        dlg.set_close_response("cancel")

        resp = self._run_adw_dialog(dlg)
        if resp == "ok":
            results = []
            for dd, combo in zip(dropdowns, combos):
                idx = dd.get_selected()
                results.append(combo.options[idx])
            return results
        return None

    # ------------------------------------------------------------------
    # Checklist dialog
    # ------------------------------------------------------------------

    def show_checklist(
        self,
        title: str,
        text: str,
        items: list[ChecklistItem],
        ok_label: str = "OK",
        cancel_label: str = "Cancel",
        width: int = 0,
        height: int = 0,
    ) -> list[str] | None:
        dlg = Adw.MessageDialog(
            heading=title,
            transient_for=self._transient(),
            modal=True,
        )
        dlg.set_body_use_markup(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        info_label = Gtk.Label(label=text, wrap=True, use_markup=True)
        info_label.set_xalign(0)
        box.append(info_label)

        checks: list[tuple[str, Gtk.CheckButton]] = []
        for item in items:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            cb = Gtk.CheckButton(active=item.checked)
            lbl_text = f"<b>{item.label}</b>  \u2014  {item.description}" if item.description else f"<b>{item.label}</b>"
            lbl = Gtk.Label(label=lbl_text, use_markup=True)
            lbl.set_xalign(0)
            lbl.set_wrap(True)
            row.append(cb)
            row.append(lbl)
            box.append(row)
            checks.append((item.key, cb))

        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_min_content_width(max(width - 80, 580))
        scroll.set_min_content_height(max(height - 120, 380))
        scroll.set_propagate_natural_height(True)
        scroll.set_child(box)

        dlg.set_extra_child(scroll)
        dlg.set_default_size(max(width, 680), max(height, 600))
        dlg.add_response("cancel", cancel_label)
        dlg.add_response("ok", ok_label)
        dlg.set_default_response("ok")
        dlg.set_close_response("cancel")

        resp = self._run_adw_dialog(dlg)
        if resp == "ok":
            return [key for key, cb in checks if cb.get_active()]
        return None

    # ------------------------------------------------------------------
    # Radio-list dialog
    # ------------------------------------------------------------------

    def show_radiolist(
        self,
        title: str,
        text: str,
        items: list[ChecklistItem],
        ok_label: str = "OK",
        cancel_label: str = "Cancel",
        width: int = 0,
        height: int = 0,
    ) -> str | None:
        dlg = Adw.MessageDialog(
            heading=title,
            transient_for=self._transient(),
            modal=True,
        )
        dlg.set_body_use_markup(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        info_label = Gtk.Label(label=text, wrap=True, use_markup=True)
        info_label.set_xalign(0)
        box.append(info_label)

        group: Gtk.CheckButton | None = None
        radios: list[tuple[str, Gtk.CheckButton]] = []
        for item in items:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            rb = Gtk.CheckButton(active=item.checked)
            if group is not None:
                rb.set_group(group)
            else:
                group = rb
            lbl_text = f"<b>{item.label}</b>  \u2014  {item.description}" if item.description else f"<b>{item.label}</b>"
            lbl = Gtk.Label(label=lbl_text, use_markup=True)
            lbl.set_xalign(0)
            lbl.set_wrap(True)
            row.append(rb)
            row.append(lbl)
            box.append(row)
            radios.append((item.key, rb))

        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_min_content_width(max(width - 80, 580))
        scroll.set_min_content_height(max(height - 120, 380))
        scroll.set_propagate_natural_height(True)
        scroll.set_child(box)

        dlg.set_extra_child(scroll)
        dlg.set_default_size(max(width, 680), max(height, 600))
        dlg.add_response("cancel", cancel_label)
        dlg.add_response("ok", ok_label)
        dlg.set_default_response("ok")
        dlg.set_close_response("cancel")

        resp = self._run_adw_dialog(dlg)
        if resp == "ok":
            for key, rb in radios:
                if rb.get_active():
                    return key
        return None

    # ------------------------------------------------------------------
    # Progress dialog
    # ------------------------------------------------------------------

    def show_progress(
        self,
        title: str,
        text: str,
        callback: Callable[[], None],
    ) -> bool:
        dlg = Adw.MessageDialog(
            heading=title,
            body=text,
            transient_for=self._transient(),
            modal=True,
        )
        dlg.set_body_use_markup(True)

        spinner = Gtk.Spinner(spinning=True)
        spinner.set_size_request(48, 48)
        dlg.set_extra_child(spinner)

        success = {"value": False}
        loop = GLib.MainLoop()

        def worker():
            try:
                callback()
                success["value"] = True
            except Exception:
                success["value"] = False
            finally:
                GLib.idle_add(_finish)

        def _finish():
            dlg.close()
            loop.quit()
            return False

        threading.Thread(target=worker, daemon=True).start()
        if self._app:
            dlg.set_application(self._app)
        dlg.present()
        loop.run()
        return success["value"]
