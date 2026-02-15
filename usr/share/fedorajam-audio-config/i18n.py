"""Internationalisation (i18n) setup for Fedora Jam Audio Configuration.

Usage in any module::

    from i18n import _

Then wrap every user-visible string with ``_("…")``.

At runtime ``gettext`` will look for compiled ``.mo`` files under
``/usr/share/locale/`` (system-wide) or the ``locale/`` directory next
to this file (for development).
"""

from __future__ import annotations

import gettext
import locale
from pathlib import Path

DOMAIN = "fedorajam-audio-config"

# Standard system locale directory; development fallback beside this file.
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
