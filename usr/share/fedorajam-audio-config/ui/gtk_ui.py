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

    def _make_content_window(
        self,
        title: str,
        width: int = 700,
        height: int = 560,
    ) -> tuple["Adw.Window", "Adw.ToolbarView"]:
        """Create a resizable modal Adw.Window with a ToolbarView and HeaderBar.

        Returns (window, toolbar_view). Callers should set the content on
        toolbar_view and attach a bottom action bar before running the loop.
        """
        win = Adw.Window(
            transient_for=self._transient(),
            modal=True,
            default_width=width,
            default_height=height,
            title=title,
            resizable=True,
        )
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())
        win.set_content(toolbar_view)
        return win, toolbar_view

    def _run_content_window(
        self,
        win: "Adw.Window",
        ok_label: str,
        cancel_label: str,
        action_bar: "Gtk.ActionBar",
    ) -> tuple[str, GLib.MainLoop]:
        """Wire OK / Cancel buttons onto *action_bar*, run the event loop.

        Returns the response string ``"ok"`` or ``"cancel"``.
        """
        loop = GLib.MainLoop()
        result = {"response": "cancel"}

        def _respond(r: str) -> None:
            result["response"] = r
            win.close()
            loop.quit()

        cancel_btn = Gtk.Button(label=cancel_label)
        cancel_btn.connect("clicked", lambda _: _respond("cancel"))

        ok_btn = Gtk.Button(label=ok_label)
        ok_btn.add_css_class("suggested-action")
        ok_btn.connect("clicked", lambda _: _respond("ok"))

        action_bar.pack_start(cancel_btn)
        action_bar.pack_end(ok_btn)

        # Treat window-close (× button) as cancel without quitting the loop twice
        def _on_close_request(_w):
            if loop.is_running():
                result["response"] = "cancel"
                loop.quit()
            return False

        win.connect("close-request", _on_close_request)

        if self._app:
            win.set_application(self._app)
        win.present()
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
        win, toolbar_view = self._make_content_window(title, width=560, height=-1)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        label = Gtk.Label(label=text, wrap=True, use_markup=True)
        label.set_xalign(0)
        box.append(label)

        entry = Gtk.Entry(text=default)
        box.append(entry)

        toolbar_view.set_content(box)

        action_bar = Gtk.ActionBar()
        toolbar_view.add_bottom_bar(action_bar)

        resp = self._run_content_window(win, ok_label, cancel_label, action_bar)
        # entry.get_text() is still valid after window close
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
        win, toolbar_view = self._make_content_window(title, width=660, height=-1)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(18)
        box.set_margin_end(18)
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

        toolbar_view.set_content(box)

        action_bar = Gtk.ActionBar()
        toolbar_view.add_bottom_bar(action_bar)

        resp = self._run_content_window(win, ok_label, cancel_label, action_bar)
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
        win, toolbar_view = self._make_content_window(
            title,
            width=max(width, 700),
            height=max(height, 560),
        )

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        info_label = Gtk.Label(label=text, wrap=True, use_markup=True)
        info_label.set_xalign(0)
        info_label.set_margin_start(18)
        info_label.set_margin_end(18)
        info_label.set_margin_top(12)
        info_label.set_margin_bottom(8)
        outer.append(info_label)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(4)
        box.set_margin_bottom(12)

        checks: list[tuple[str, Gtk.CheckButton]] = []
        for item in items:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            cb = Gtk.CheckButton(active=item.checked)
            lbl_text = f"<b>{item.label}</b>  \u2014  {item.description}" if item.description else f"<b>{item.label}</b>"
            lbl = Gtk.Label(label=lbl_text, use_markup=True)
            lbl.set_xalign(0)
            lbl.set_wrap(True)
            lbl.set_hexpand(True)
            row.append(cb)
            row.append(lbl)
            box.append(row)
            checks.append((item.key, cb))

        scroll = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )
        scroll.set_vexpand(True)
        scroll.set_child(box)
        outer.append(scroll)

        toolbar_view.set_content(outer)

        action_bar = Gtk.ActionBar()
        toolbar_view.add_bottom_bar(action_bar)

        resp = self._run_content_window(win, ok_label, cancel_label, action_bar)
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
        win, toolbar_view = self._make_content_window(
            title,
            width=max(width, 700),
            height=max(height, 560),
        )

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        info_label = Gtk.Label(label=text, wrap=True, use_markup=True)
        info_label.set_xalign(0)
        info_label.set_margin_start(18)
        info_label.set_margin_end(18)
        info_label.set_margin_top(12)
        info_label.set_margin_bottom(8)
        outer.append(info_label)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(4)
        box.set_margin_bottom(12)

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
            lbl.set_hexpand(True)
            row.append(rb)
            row.append(lbl)
            box.append(row)
            radios.append((item.key, rb))

        scroll = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )
        scroll.set_vexpand(True)
        scroll.set_child(box)
        outer.append(scroll)

        toolbar_view.set_content(outer)

        action_bar = Gtk.ActionBar()
        toolbar_view.add_bottom_bar(action_bar)

        resp = self._run_content_window(win, ok_label, cancel_label, action_bar)
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
