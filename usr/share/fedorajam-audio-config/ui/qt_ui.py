"""Qt 6 (PyQt6) implementation of the Audio Config UI."""

from __future__ import annotations

import threading
from collections.abc import Callable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFontMetrics, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QProgressBar,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .base import AudioConfigUI, ChecklistItem, ComboItem
from i18n import _

ICON_PATH = "/usr/share/icons/hicolor/scalable/apps/start-here.svg"

_MAX_DLG_WIDTH = 950


def _item_text(label: str, description: str) -> str:
    """Format a checklist / radio-list item, omitting the dash when
    *description* is empty."""
    if description:
        return f"{label}  \u2014  {description}"
    return label


def _msgbox(icon: QMessageBox.Icon, title: str, text: str) -> QMessageBox:
    """Create a QMessageBox with word-wrapped text."""
    box = QMessageBox(icon, title, text)
    box.setWindowIcon(QIcon(ICON_PATH))
    for lbl in box.findChildren(QLabel):
        lbl.setWordWrap(True)
        lbl.setMaximumWidth(_MAX_DLG_WIDTH - 80)
    # Centre the dialog on the primary screen
    screen = QApplication.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        hint = box.sizeHint()
        box.move(
            geo.x() + (geo.width() - hint.width()) // 2,
            geo.y() + (geo.height() - hint.height()) // 2,
        )
    return box


def _wrapping_row(button: QCheckBox | QRadioButton, text: str) -> QWidget:
    """Pair *button* (with no text) and a word-wrapping QLabel in a row.

    Clicking the label toggles the button so the whole row is clickable."""
    label = QLabel(text)
    label.setWordWrap(True)
    label.mousePressEvent = lambda _ev: button.toggle()
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(4, 3, 4, 3)
    h.addWidget(button)
    h.addWidget(label, 1)
    return row


def _auto_size(dlg: QDialog, width: int = 0, height: int = 0) -> None:
    """Size *dlg* to fit its content.

    If *width*/*height* are provided (> 0) they are used as explicit hints;
    otherwise the dialog uses its sizeHint, clamped to *_MAX_DLG_WIDTH*
    and 80 % of the screen height.
    """
    if width > 0:
        screen = QApplication.primaryScreen()
        max_h = int(screen.availableGeometry().height() * 0.8) if screen else 800
        dlg.resize(width, 0)
        dlg.adjustSize()
        h = height if height > 0 else min(dlg.sizeHint().height(), max_h)
        dlg.resize(width, h)
        return

    dlg.adjustSize()
    hint = dlg.sizeHint()
    w = min(hint.width(), _MAX_DLG_WIDTH)
    screen = QApplication.primaryScreen()
    max_h = int(screen.availableGeometry().height() * 0.8) if screen else 800
    h = min(hint.height(), max_h)
    dlg.resize(w, h)


def _items_width(items: list[ChecklistItem]) -> int:
    """Return the pixel width needed for the widest item text,
    plus padding for the checkbox/radio indicator and margins."""
    fm = QFontMetrics(QApplication.font())
    widest = max(
        fm.horizontalAdvance(_item_text(it.label, it.description))
        for it in items
    )
    # ~60 px for checkbox/radio indicator + layout margins + scrollbar
    return min(widest + 60, _MAX_DLG_WIDTH)


class QtUI(AudioConfigUI):
    """Concrete UI using PyQt6."""

    def __init__(self) -> None:
        self._app: QApplication | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init(self) -> None:
        if QApplication.instance() is None:
            self._app = QApplication([])
            self._app.setApplicationName(_("Fedora Jam Audio Configuration"))
            self._app.setWindowIcon(QIcon(ICON_PATH))
        else:
            self._app = QApplication.instance()

    def quit(self) -> None:
        pass  # no explicit quit — dialogs are modal

    # ------------------------------------------------------------------
    # Simple message dialogs
    # ------------------------------------------------------------------

    def show_info(self, title: str, text: str) -> None:
        _msgbox(QMessageBox.Icon.Information, title, text).exec()

    def show_error(self, title: str, text: str) -> None:
        _msgbox(QMessageBox.Icon.Critical, title, text).exec()

    def show_warning(self, title: str, text: str) -> None:
        _msgbox(QMessageBox.Icon.Warning, title, text).exec()

    def show_question(
        self,
        title: str,
        text: str,
        ok_label: str = "Yes",
        cancel_label: str = "No",
    ) -> bool:
        box = _msgbox(QMessageBox.Icon.Question, title, text)
        btn_ok = box.addButton(ok_label, QMessageBox.ButtonRole.AcceptRole)
        box.addButton(cancel_label, QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() == btn_ok

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
        value, ok = QInputDialog.getText(None, title, text, text=default)
        if ok:
            return value
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
        dlg = QDialog()
        dlg.setWindowTitle(title)
        dlg.setWindowIcon(QIcon(ICON_PATH))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        if text.strip():
            intro = QLabel(text)
            intro.setWordWrap(True)
            layout.addWidget(intro)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        layout.addWidget(tabs)

        # Audio tab
        audio_tab = QWidget()
        audio_layout = QVBoxLayout(audio_tab)
        audio_layout.setSpacing(8)

        if quantum_managed_by_widget:
            note = QLabel(
                _(
                    "Quantum and Sample Rate are managed by your desktop "
                    "widget or extension."
                )
            )
            note.setWordWrap(True)
            audio_layout.addWidget(note)

        quantum_row = QWidget()
        quantum_layout = QHBoxLayout(quantum_row)
        quantum_layout.setContentsMargins(0, 0, 0, 0)
        quantum_layout.setSpacing(10)

        quantum_layout.addWidget(
            QLabel(
                _("<b>Quantum</b> <small>(Default: {value})</small>").format(
                    value=default_buffer,
                )
            )
        )
        audio_buffer_cb = QComboBox()
        audio_buffer_cb.addItems(buffer_options)
        if current_buffer in buffer_options:
            audio_buffer_cb.setCurrentText(current_buffer)
        audio_buffer_cb.setEnabled(not quantum_managed_by_widget)
        quantum_layout.addWidget(audio_buffer_cb)

        quantum_layout.addWidget(
            QLabel(
                _("<b>Sample Rate (Hz)</b> <small>(Default: {value} Hz)</small>").format(
                    value=default_sample_rate,
                )
            )
        )
        audio_rate_cb = QComboBox()
        audio_rate_cb.addItems(sample_rate_options)
        if current_sample_rate in sample_rate_options:
            audio_rate_cb.setCurrentText(current_sample_rate)
        audio_rate_cb.setEnabled(not quantum_managed_by_widget)
        quantum_layout.addWidget(audio_rate_cb)

        audio_layout.addWidget(quantum_row)

        jack_header = QLabel(f"<b>{_('JACK Options')}</b>")
        audio_layout.addWidget(jack_header)
        jack_container = QWidget()
        jack_box = QVBoxLayout(jack_container)
        jack_box.setSpacing(2)
        jack_box.setContentsMargins(0, 0, 0, 0)
        jack_checks: list[tuple[str, QCheckBox]] = []
        for item in jack_items:
            cb = QCheckBox()
            cb.setChecked(item.checked)
            jack_box.addWidget(_wrapping_row(cb, _item_text(item.label, item.description)))
            jack_checks.append((item.key, cb))
        audio_layout.addWidget(jack_container)

        sc_header = QLabel(f"<b>{_('Self-Connect Mode')}</b>")
        audio_layout.addWidget(sc_header)
        sc_container = QWidget()
        sc_box = QVBoxLayout(sc_container)
        sc_box.setSpacing(2)
        sc_box.setContentsMargins(0, 0, 0, 0)
        sc_group = QButtonGroup(dlg)
        sc_radios: list[tuple[str, QRadioButton]] = []
        for item in self_connect_items:
            rb = QRadioButton()
            rb.setChecked(item.checked)
            sc_group.addButton(rb)
            sc_box.addWidget(_wrapping_row(rb, _item_text(item.label, item.description)))
            sc_radios.append((item.key, rb))
        audio_layout.addWidget(sc_container)
        audio_layout.addStretch(1)

        tabs.addTab(audio_tab, _("Audio"))

        # Boot tab
        boot_tab = QWidget()
        boot_layout = QVBoxLayout(boot_tab)
        boot_layout.setSpacing(8)
        boot_note = QLabel(
            _("Kernel low-latency options (restart required).")
        )
        boot_note.setWordWrap(True)
        boot_layout.addWidget(boot_note)
        boot_container = QWidget()
        boot_box = QVBoxLayout(boot_container)
        boot_box.setSpacing(2)
        boot_box.setContentsMargins(0, 0, 0, 0)
        boot_checks: list[tuple[str, QCheckBox]] = []
        for item in boot_items:
            cb = QCheckBox()
            cb.setChecked(item.checked)
            boot_box.addWidget(_wrapping_row(cb, _item_text(item.label, item.description)))
            boot_checks.append((item.key, cb))
        boot_layout.addWidget(boot_container)
        boot_layout.addStretch(1)
        tabs.addTab(boot_tab, _("Kernel"))

        # Dummy tab
        dummy_tab = QWidget()
        dummy_layout = QVBoxLayout(dummy_tab)
        dummy_layout.setSpacing(8)
        dummy_note = QLabel(
            _("Use a dummy device to isolate routing in studio workflows.")
        )
        dummy_note.setWordWrap(True)
        dummy_layout.addWidget(dummy_note)
        dummy_active_cb = QCheckBox(_("Dummy device active"))
        dummy_active_cb.setChecked(dummy_active)
        dummy_layout.addWidget(dummy_active_cb)
        dummy_autostart_cb = QCheckBox(_("Start dummy device at login"))
        dummy_autostart_cb.setChecked(dummy_autostart)
        dummy_layout.addWidget(dummy_autostart_cb)
        dummy_layout.addStretch(1)
        tabs.addTab(dummy_tab, _("Dummy Device"))

        fw_action_group = QButtonGroup(dlg)
        fw_keep = None
        fw_configure = None
        fw_remove = None

        if fw_present:
            fw_tab = QWidget()
            fw_layout = QVBoxLayout(fw_tab)
            fw_layout.setSpacing(8)
            fw_note = QLabel(_("Manage FireWire (FFADO) integration."))
            fw_note.setWordWrap(True)
            fw_layout.addWidget(fw_note)
            fw_keep = QRadioButton(_("No changes"))
            fw_keep.setChecked(True)
            fw_action_group.addButton(fw_keep)
            fw_layout.addWidget(fw_keep)
            fw_configure = QRadioButton(_("Configure or reconfigure FireWire"))
            fw_action_group.addButton(fw_configure)
            fw_layout.addWidget(fw_configure)
            if fw_configured:
                fw_remove = QRadioButton(_("Remove FireWire configuration"))
                fw_action_group.addButton(fw_remove)
                fw_layout.addWidget(fw_remove)
            fw_layout.addStretch(1)
            tabs.addTab(fw_tab, _("FireWire"))

        buttons = QDialogButtonBox()
        apply_btn = buttons.addButton(ok_label, QDialogButtonBox.ButtonRole.ApplyRole)
        close_btn = buttons.addButton(cancel_label, QDialogButtonBox.ButtonRole.RejectRole)

        def _collect_result() -> dict[str, object]:
            fw_action = "none"
            if fw_present:
                if fw_configure is not None and fw_configure.isChecked():
                    fw_action = "configure"
                elif fw_remove is not None and fw_remove.isChecked():
                    fw_action = "remove"

            return {
                "audio_buffer": audio_buffer_cb.currentText(),
                "audio_rate": audio_rate_cb.currentText(),
                "audio_jack_selected": [key for key, cb in jack_checks if cb.isChecked()],
                "audio_self_connect_mode": next(
                    (key for key, rb in sc_radios if rb.isChecked()),
                    self_connect_items[0].key,
                ),
                "boot_selected": [key for key, cb in boot_checks if cb.isChecked()],
                "dummy_active": dummy_active_cb.isChecked(),
                "dummy_autostart": dummy_autostart_cb.isChecked(),
                "firewire_action": fw_action,
            }

        def _on_apply() -> None:
            if on_apply is None:
                return
            try:
                on_apply(_collect_result())
            except Exception:
                self.show_error(title, _("An error has occurred."))

        apply_btn.clicked.connect(_on_apply)
        close_btn.clicked.connect(dlg.reject)
        layout.addWidget(buttons)

        _auto_size(dlg, 740, 620)

        dlg.exec()
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
        dlg = QDialog()
        dlg.setWindowTitle(title)
        dlg.setWindowIcon(QIcon(ICON_PATH))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)
        info = QLabel(text)
        info.setWordWrap(True)
        layout.addWidget(info)

        combo_widgets: list[QComboBox] = []
        for combo in combos:
            lbl = QLabel(f"<b>{combo.label}</b>")
            layout.addWidget(lbl)
            cb = QComboBox()
            cb.addItems(combo.options)
            if combo.default in combo.options:
                cb.setCurrentText(combo.default)
            layout.addWidget(cb)
            combo_widgets.append(cb)

        buttons = QDialogButtonBox()
        buttons.addButton(ok_label, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(cancel_label, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        _auto_size(dlg)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            return [cb.currentText() for cb in combo_widgets]
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
        dlg = QDialog()
        dlg.setWindowTitle(title)
        dlg.setWindowIcon(QIcon(ICON_PATH))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)
        info = QLabel(text)
        info.setWordWrap(True)
        layout.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setSpacing(2)
        vbox.setContentsMargins(4, 4, 4, 4)

        checks: list[tuple[str, QCheckBox]] = []
        for item in items:
            cb = QCheckBox()
            cb.setChecked(item.checked)
            vbox.addWidget(_wrapping_row(cb, _item_text(item.label, item.description)))
            checks.append((item.key, cb))

        scroll.setWidget(container)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox()
        buttons.addButton(ok_label, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(cancel_label, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        _auto_size(dlg, _items_width(items), height)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            return [key for key, cb in checks if cb.isChecked()]
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
        dlg = QDialog()
        dlg.setWindowTitle(title)
        dlg.setWindowIcon(QIcon(ICON_PATH))

        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)
        info = QLabel(text)
        info.setWordWrap(True)
        layout.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setSpacing(2)
        vbox.setContentsMargins(4, 4, 4, 4)

        group = QButtonGroup(dlg)
        radios: list[tuple[str, QRadioButton]] = []
        for item in items:
            rb = QRadioButton()
            rb.setChecked(item.checked)
            group.addButton(rb)
            vbox.addWidget(_wrapping_row(rb, _item_text(item.label, item.description)))
            radios.append((item.key, rb))

        scroll.setWidget(container)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox()
        buttons.addButton(ok_label, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(cancel_label, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        _auto_size(dlg, _items_width(items), height)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            for key, rb in radios:
                if rb.isChecked():
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
        dlg = QDialog()
        dlg.setWindowTitle(title)
        dlg.setWindowIcon(QIcon(ICON_PATH))
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setMinimumWidth(400)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)

        bar = QProgressBar()
        bar.setRange(0, 0)  # indeterminate / pulsating
        layout.addWidget(bar)

        success = {"value": False}

        def worker():
            try:
                callback()
                success["value"] = True
            except Exception:
                success["value"] = False
            finally:
                QTimer.singleShot(0, dlg.close)

        threading.Thread(target=worker, daemon=True).start()
        dlg.exec()
        return success["value"]
