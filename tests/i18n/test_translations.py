"""Tests for the i18n translations module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from babel.messages.pofile import read_po

import i18n as i18n_module
from i18n import DEFAULT_LANGUAGE, LANGUAGES, t

_LOCALE_DIR = Path(__file__).resolve().parents[2] / "src" / "i18n" / "locales"
_POT_FILE = _LOCALE_DIR / "messages.pot"


def _read_msgids_from_pot() -> set[str]:
    """Return all non-empty msgids defined in the .pot template."""
    with _POT_FILE.open("rb") as f:
        catalog = read_po(f)
    return {str(msg.id) for msg in catalog if msg.id}


def _read_po_for_lang(lang: str) -> dict[str, str]:
    """Return {msgid: msgstr} for a language's .po file."""
    po_path = _LOCALE_DIR / lang / "LC_MESSAGES" / "messages.po"
    with po_path.open("rb") as f:
        catalog = read_po(f)
    return {str(msg.id): str(msg.string) for msg in catalog if msg.id}


# Languages that have a .po file (all except the default/English base)
_TRANSLATED_LANGUAGES = [code for code in LANGUAGES if code != DEFAULT_LANGUAGE]


class TestPoFiles:
    """Verify the .pot template and per-language .po files are consistent."""

    def test_pot_template_exists(self) -> None:
        """The .pot template file must exist."""
        assert _POT_FILE.exists(), f"Missing .pot template: {_POT_FILE}"

    def test_pot_template_is_not_empty(self) -> None:
        """The .pot template must contain at least one msgid."""
        msgids = _read_msgids_from_pot()
        assert msgids, ".pot template has no msgids"

    @pytest.mark.parametrize("lang", _TRANSLATED_LANGUAGES)
    def test_po_file_exists(self, lang: str) -> None:
        """A .po file must exist for every non-English language."""
        po_path = _LOCALE_DIR / lang / "LC_MESSAGES" / "messages.po"
        assert po_path.exists(), f"Missing .po file for language '{lang}': {po_path}"

    @pytest.mark.parametrize("lang", _TRANSLATED_LANGUAGES)
    def test_mo_file_exists(self, lang: str) -> None:
        """A compiled .mo file must exist next to each .po file."""
        mo_path = _LOCALE_DIR / lang / "LC_MESSAGES" / "messages.mo"
        assert mo_path.exists(), (
            f"Missing compiled .mo file for '{lang}'. "
            f'Run: python -c "from babel.messages.mofile import write_mo; '
            f"from babel.messages.pofile import read_po; "
            f"[write_mo(open(str(p).replace('.po','.mo'),'wb'), read_po(open(p,'rb'))) "
            f"for p in ['{mo_path.with_suffix('.po')}']]\" "
            f"or use Poedit to save the .po file."
        )

    @pytest.mark.parametrize("lang", _TRANSLATED_LANGUAGES)
    def test_all_pot_msgids_present_in_po(self, lang: str) -> None:
        """Every msgid in the .pot template must appear in the language .po file."""
        pot_msgids = _read_msgids_from_pot()
        po_translations = _read_po_for_lang(lang)
        missing = pot_msgids - set(po_translations.keys())
        assert not missing, f"Language '{lang}' is missing translations for: {sorted(missing)}"

    @pytest.mark.parametrize("lang", _TRANSLATED_LANGUAGES)
    def test_no_empty_msgstr_in_po(self, lang: str) -> None:
        """No msgstr should be empty in any .po file."""
        po_translations = _read_po_for_lang(lang)
        empty = [msgid for msgid, msgstr in po_translations.items() if not msgstr]
        assert not empty, f"Language '{lang}' has empty translations for: {sorted(empty)}"

    @pytest.mark.parametrize("lang", _TRANSLATED_LANGUAGES)
    def test_no_extra_msgids_in_po(self, lang: str) -> None:
        """A .po file must not define msgids that are absent from the .pot template."""
        pot_msgids = _read_msgids_from_pot()
        po_translations = _read_po_for_lang(lang)
        extra = set(po_translations.keys()) - pot_msgids
        assert not extra, f"Language '{lang}' has msgids not in .pot template: {sorted(extra)}"


class TestTranslationFunction:
    """Tests for the t() helper function."""

    def test_t_returns_english_string_by_default(self) -> None:
        """t() should return the English source string when no language is stored."""
        result = t("Apple Health Analyzer")
        assert result == "Apple Health Analyzer"

    def test_t_returns_msgid_for_unknown_strings(self) -> None:
        """t() should return the input unchanged when no translation exists."""
        unknown = "This string does not exist in any .po file"
        assert t(unknown) == unknown

    def test_t_supports_format_kwargs(self) -> None:
        """t() should interpolate keyword arguments into the translated string."""
        result = t("Count by {period}", period="month")
        assert result == "Count by month"

    def test_t_returns_french_for_fr_language(self) -> None:
        """t() should return French text when 'fr' is the active language."""
        with patch("i18n.get_language", return_value="fr"):
            result = t("Apple Health Analyzer")
        assert result == "Analyseur de santé Apple"

    def test_t_french_format_kwargs_preserved(self) -> None:
        """t() should interpolate kwargs into French translated strings correctly."""
        with patch("i18n.get_language", return_value="fr"):
            result = t("Count by {period}", period="mois")
        assert result == "Nombre par mois"

    def test_t_falls_back_to_english_when_lang_has_no_mo(self) -> None:
        """t() falls back gracefully when no .mo file exists for the active language."""
        with patch("i18n.get_language", return_value="xx"):  # non-existent language
            result = t("Apple Health Analyzer")
        assert result == "Apple Health Analyzer"

    @pytest.mark.parametrize("lang", list(LANGUAGES.keys()))
    def test_t_never_returns_empty_string_for_known_msgids(self, lang: str) -> None:
        """t() must return a non-empty string for every msgid in every language."""
        msgids = _read_msgids_from_pot()
        with patch("i18n.get_language", return_value=lang):
            for msgid in msgids:
                result = t(msgid)
                assert result, f"t({msgid!r}) returned empty string for language '{lang}'"


class TestLanguageConstants:
    """Tests for the LANGUAGES and DEFAULT_LANGUAGE constants."""

    def test_default_language_is_in_languages(self) -> None:
        """DEFAULT_LANGUAGE must be one of the keys in the LANGUAGES dict."""
        assert DEFAULT_LANGUAGE in LANGUAGES

    def test_languages_contains_english_and_french(self) -> None:
        """At minimum, English and French must be supported."""
        assert "en" in LANGUAGES
        assert "fr" in LANGUAGES


class TestTranslationFallbackInternals:
    """Directly exercise gettext fallback paths used by t()."""

    def test_t_uses_po_fallback_when_compiled_catalog_is_missing(self, tmp_path: Path) -> None:
        """When gettext.translation fails, t() should load .po fallback translations."""
        locale_dir = tmp_path / "locales"
        po_dir = locale_dir / "zz" / "LC_MESSAGES"
        po_dir.mkdir(parents=True)
        po_content = """msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"

msgid "Hello"
msgstr "Salut"
"""
        (po_dir / "messages.po").write_text(po_content, encoding="utf-8")

        get_translation = getattr(i18n_module, "_get_translation")
        get_translation.cache_clear()
        with (
            patch("i18n._LOCALE_DIR", locale_dir),
            patch("i18n.get_language", return_value="zz"),
            patch("i18n.gettext.translation", side_effect=FileNotFoundError),
        ):
            assert t("Hello") == "Salut"
            # Unknown keys should pass through unchanged in _POTranslations.gettext.
            assert t("Unknown key") == "Unknown key"

        get_translation.cache_clear()
