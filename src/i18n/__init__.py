"""Internationalization (i18n) support for Apple Health Analyzer.

Translations are stored in GNU gettext ``.po``/``.mo`` files under
``src/i18n/locales/`` and can be edited with any PO-file editor such as
`Poedit <https://poedit.net/>`_.

Provides a ``t()`` translation function that reads the current language from
NiceGUI user storage and returns the appropriate translated string.
"""

import gettext
from functools import lru_cache
from pathlib import Path

DEFAULT_LANGUAGE = "en"

LANGUAGES: dict[str, str] = {
    "en": "English",
    "fr": "Français",
}

_DOMAIN = "messages"
_LOCALE_DIR = Path(__file__).parent / "locales"

__all__ = ["DEFAULT_LANGUAGE", "LANGUAGES", "t"]


@lru_cache(maxsize=None)
def _get_translation(lang: str) -> gettext.NullTranslations:
    """Load and cache the compiled ``.mo`` translation for *lang*.

    Returns a :class:`~gettext.NullTranslations` instance (which passes
    strings through unchanged) when no compiled catalog is found for *lang*.
    This means English strings are always returned as-is without needing an
    English ``.mo`` file.
    """
    try:
        return gettext.translation(_DOMAIN, localedir=str(_LOCALE_DIR), languages=[lang])
    except FileNotFoundError:
        return gettext.NullTranslations()


def get_language() -> str:
    """Return the active language code from NiceGUI user storage.

    Falls back to ``DEFAULT_LANGUAGE`` when storage is not available
    (e.g., during unit tests that do not set up a NiceGUI session).
    """
    try:
        from nicegui import app  # pylint: disable=import-outside-toplevel

        return str(app.storage.user.get("language", DEFAULT_LANGUAGE))
    except Exception:  # pylint: disable=broad-except
        return DEFAULT_LANGUAGE


def t(message: str, **kwargs: str) -> str:
    """Translate *message* into the currently selected language.

    Uses standard GNU gettext look-up: *message* is the English source string
    (the ``msgid`` in the ``.po`` file).  When no translation is available the
    original *message* is returned unchanged so the UI always shows readable
    text.

    Extra keyword arguments are forwarded to :meth:`str.format` so that
    dynamic values can be injected into the translated string::

        t("Count by {period}", period=t("month"))
        # → "Count by month"   (English)
        # → "Nombre par mois"  (French)
    """
    translation = _get_translation(get_language())
    result = translation.gettext(message)
    if kwargs:
        return result.format(**kwargs)
    return result
