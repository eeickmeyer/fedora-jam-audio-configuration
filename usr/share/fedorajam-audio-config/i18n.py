"""Gettext setup for Fedora Jam Audio Configuration."""

from __future__ import annotations

import gettext
import locale
from pathlib import Path

DOMAIN = "fedorajam-audio-config"

_LOCALE_DIRS = [
    "/usr/share/locale",
    str(Path(__file__).resolve().parent / "locale"),
]


def _install() -> gettext.GNUTranslations | gettext.NullTranslations:
    """Bind the gettext domain and return the translation object."""
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass

    for loc_dir in _LOCALE_DIRS:
        if Path(loc_dir).is_dir():
            localedir = loc_dir
            break
    else:
        localedir = _LOCALE_DIRS[0]

    gettext.bindtextdomain(DOMAIN, localedir)
    gettext.textdomain(DOMAIN)

    return gettext.translation(DOMAIN, localedir=localedir, fallback=True)


_translation = _install()

# The actual translation function — import this in other modules.
_ = _translation.gettext
