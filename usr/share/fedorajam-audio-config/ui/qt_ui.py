"""Qt 6 (PyQt6) implementation of the Audio Config UI."""

from __future__ import annotations

import threading
from collections.abc import Callable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFontMetrics, QIcon, QScreen
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QProgressDialog,
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
    return box


def _wrapping_row(button: QCheckBox | QRadioButton, text: str) -> QWidget:
    """Pair *button* (with no text) and a word-wrapping QLabel in a row.

    Clicking the label toggles the button so the whole row is clickable."""
    label = QLabel(text)
    label.setWordWrap(True)
    label.mousePressEvent = lambda _ev: button.toggle()
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
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
        info = QLabel(text)
        info.setWordWrap(True)
        layout.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        vbox = QVBoxLayout(container)

        checks: list[tuple[str, QCheckBox]] = []
        for item in items:
            cb = QCheckBox()
            cb.setChecked(item.checked)
            vbox.addWidget(_wrapping_row(cb, _item_text(item.label, item.description)))
            checks.append((item.key, cb))

        scroll.setWidget(container)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox()
        btn_ok = buttons.addButton(ok_label, QDialogButtonBox.ButtonRole.AcceptRole)
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
        info = QLabel(text)
        info.setWordWrap(True)
        layout.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        vbox = QVBoxLayout(container)

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
        dlg = QProgressDialog(text, None, 0, 0)
        dlg.setWindowTitle(title)
        dlg.setWindowIcon(QIcon(ICON_PATH))
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setCancelButton(None)
        dlg.setMinimumDuration(0)

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
