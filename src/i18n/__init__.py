"""Internationalization (i18n) support for Apple Health Analyzer.

Provides a ``t()`` translation function that reads the current language from
NiceGUI user storage and returns the appropriate translated string.
"""

from i18n.translations import DEFAULT_LANGUAGE, LANGUAGES, TRANSLATIONS

__all__ = ["DEFAULT_LANGUAGE", "LANGUAGES", "t"]


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


def t(key: str, **kwargs: str) -> str:
    """Translate *key* into the currently selected language.

    Extra keyword arguments are forwarded to :meth:`str.format` so that
    dynamic values (e.g. ``period``) can be injected into the string::

        t("chart.count_by_period", period=t("period_label.M"))
        # → "Count by month"  (English)
        # → "Nombre par mois"  (French)

    If the key is missing in the active language the English translation is
    used as a fallback.  If it is also missing in English the key itself is
    returned so that untranslated text is still visible rather than crashing.
    """
    lang = get_language()
    lang_translations = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])
    text = lang_translations.get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text
