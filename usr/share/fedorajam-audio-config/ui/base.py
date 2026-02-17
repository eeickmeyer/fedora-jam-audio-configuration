"""Abstract UI interface for Fedora Jam Audio Configuration.

Both the GTK and Qt implementations inherit from :class:`AudioConfigUI`
and provide concrete versions of every dialog method.  The application
controller (:mod:`main`) only ever talks to this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class ChecklistItem:
    """One row in a checklist or radio-list dialog."""

    key: str
    label: str
    description: str
    checked: bool = False


@dataclass
class ComboItem:
    """Configuration for a single dropdown selector."""

    label: str
    options: list[str]
    default: str = ""


class AudioConfigUI(ABC):
    """Toolkit-agnostic interface for every dialog the app needs."""

    # ------------------------------------------------------------------
    # Simple message dialogs
    # ------------------------------------------------------------------

    @abstractmethod
    def show_info(self, title: str, text: str) -> None:
        """Show an informational message with an OK button."""

    @abstractmethod
    def show_error(self, title: str, text: str) -> None:
        """Show an error message with an OK button."""

    @abstractmethod
    def show_warning(self, title: str, text: str) -> None:
        """Show a warning message with an OK button."""

    @abstractmethod
    def show_question(
        self,
        title: str,
        text: str,
        ok_label: str = "Yes",
        cancel_label: str = "No",
    ) -> bool:
        """Show a yes/no question.  Return True if the user clicked OK."""

    # ------------------------------------------------------------------
    # Entry dialog
    # ------------------------------------------------------------------

    @abstractmethod
    def show_entry(
        self,
        title: str,
        text: str,
        default: str = "",
        ok_label: str = "OK",
        cancel_label: str = "Cancel",
    ) -> str | None:
        """Show a text-entry dialog.  Return the entered string or *None*
        if the user cancelled."""

    # ------------------------------------------------------------------
    # Combo-box dialog
    # ------------------------------------------------------------------

    @abstractmethod
    def show_combo_dialog(
        self,
        title: str,
        text: str,
        combos: list[ComboItem],
        ok_label: str = "OK",
        cancel_label: str = "Cancel",
    ) -> list[str] | None:
        """Show a dialog with one or more dropdown selectors.
        Return a list of selected values (one per combo), or *None*
        if the user cancelled."""

    # ------------------------------------------------------------------
    # List dialogs
    # ------------------------------------------------------------------

    @abstractmethod
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
        """Show a checklist dialog.  Return a list of selected *keys*, or
        *None* if the user cancelled."""

    @abstractmethod
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
        """Show a radio-list dialog.  Return the selected *key*, or *None*
        if the user cancelled."""

    # ------------------------------------------------------------------
    # Progress dialog
    # ------------------------------------------------------------------

    @abstractmethod
    def show_progress(
        self,
        title: str,
        text: str,
        callback: Callable[[], None],
    ) -> bool:
        """Run *callback* while showing an indeterminate progress dialog.
        Return True if it completed successfully."""

    # ------------------------------------------------------------------
    # Application lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def init(self) -> None:
        """Initialise the toolkit (if needed)."""

    @abstractmethod
    def quit(self) -> None:
        """Clean up and exit."""
