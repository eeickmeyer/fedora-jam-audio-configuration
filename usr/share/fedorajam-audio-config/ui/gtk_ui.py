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
        pass  # no global init needed; dialogs are standalone

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
        if buttons is None:
            dlg.add_response("ok", _("OK"))
            dlg.set_default_response("ok")
        else:
            for label, resp_id in buttons:
                dlg.add_response(str(resp_id), label)
        return dlg

    @staticmethod
    def _run_adw_dialog(dlg: Adw.MessageDialog) -> str:
        """Run an Adw.MessageDialog and return the response id string."""
        loop = GLib.MainLoop()
        result = {"response": "cancel"}

        def on_response(_dlg, resp):
            result["response"] = resp
            loop.quit()

        dlg.connect("response", on_response)
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

        label = Gtk.Label(label=text, wrap=True, use_markup=True)
        label.set_xalign(0)
        box.append(label)

        entry = Gtk.Entry(text=default)
        entry.set_activates_default(True)
        box.append(entry)

        dlg.set_extra_child(box)
        dlg.add_response("cancel", cancel_label)
        dlg.add_response("ok", ok_label)
        dlg.set_default_response("ok")
        dlg.set_close_response("cancel")

        resp = self._run_adw_dialog(dlg)
        if resp == "ok":
            return entry.get_text()
        return None

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

        dlg.set_extra_child(box)
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
        scroll.set_min_content_width(max(width - 80, 850))
        scroll.set_min_content_height(max(height - 120, 200))
        scroll.set_child(box)

        dlg.set_extra_child(scroll)
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
        scroll.set_min_content_width(max(width - 80, 850))
        scroll.set_min_content_height(max(height - 120, 200))
        scroll.set_child(box)

        dlg.set_extra_child(scroll)
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
        dlg.present()
        loop.run()
        return success["value"]
