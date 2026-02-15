"""Qt 6 (PyQt6) implementation of the Audio Config UI."""

from __future__ import annotations

import threading
from collections.abc import Callable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
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
        QMessageBox.information(None, title, text)

    def show_error(self, title: str, text: str) -> None:
        QMessageBox.critical(None, title, text)

    def show_warning(self, title: str, text: str) -> None:
        QMessageBox.warning(None, title, text)

    def show_question(
        self,
        title: str,
        text: str,
        ok_label: str = "Yes",
        cancel_label: str = "No",
    ) -> bool:
        box = QMessageBox(QMessageBox.Icon.Question, title, text)
        box.setWindowIcon(QIcon(ICON_PATH))
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
        width: int = 850,
        height: int = 350,
    ) -> list[str] | None:
        dlg = QDialog()
        dlg.setWindowTitle(title)
        dlg.setWindowIcon(QIcon(ICON_PATH))
        dlg.resize(width, height)

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
            cb = QCheckBox(f"{item.label}  —  {item.description}")
            cb.setChecked(item.checked)
            vbox.addWidget(cb)
            checks.append((item.key, cb))

        scroll.setWidget(container)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox()
        btn_ok = buttons.addButton(ok_label, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(cancel_label, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

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
        width: int = 850,
        height: int = 350,
    ) -> str | None:
        dlg = QDialog()
        dlg.setWindowTitle(title)
        dlg.setWindowIcon(QIcon(ICON_PATH))
        dlg.resize(width, height)

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
            rb = QRadioButton(f"{item.label}  —  {item.description}")
            rb.setChecked(item.checked)
            group.addButton(rb)
            vbox.addWidget(rb)
            radios.append((item.key, rb))

        scroll.setWidget(container)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox()
        buttons.addButton(ok_label, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(cancel_label, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

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
