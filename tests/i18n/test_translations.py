"""Tests for the i18n translations module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from i18n import DEFAULT_LANGUAGE, LANGUAGES, t
from i18n.translations import TRANSLATIONS


class TestTranslationCompleteness:
    """Verify that every translation key present in the default language exists in all others."""

    def test_all_languages_have_same_keys_as_default(self) -> None:
        """All languages must define the same keys as the default (English) language."""
        default_keys = set(TRANSLATIONS[DEFAULT_LANGUAGE].keys())

        for lang_code in LANGUAGES:
            lang_keys = set(TRANSLATIONS[lang_code].keys())
            missing = default_keys - lang_keys
            assert not missing, (
                f"Language '{lang_code}' is missing translation keys: {sorted(missing)}"
            )

    def test_no_language_has_extra_keys(self) -> None:
        """No language should define keys that are not in the default language (avoids drift)."""
        default_keys = set(TRANSLATIONS[DEFAULT_LANGUAGE].keys())

        for lang_code in LANGUAGES:
            if lang_code == DEFAULT_LANGUAGE:
                continue
            lang_keys = set(TRANSLATIONS[lang_code].keys())
            extra = lang_keys - default_keys
            assert not extra, (
                f"Language '{lang_code}' has extra keys not in '{DEFAULT_LANGUAGE}': "
                f"{sorted(extra)}"
            )

    def test_no_empty_translations(self) -> None:
        """No translation value should be an empty string."""
        for lang_code, translations in TRANSLATIONS.items():
            for key, value in translations.items():
                assert value, (
                    f"Language '{lang_code}' has an empty value for key '{key}'"
                )

    def test_all_supported_languages_are_translated(self) -> None:
        """Every language listed in LANGUAGES must have a translations entry."""
        for lang_code in LANGUAGES:
            assert lang_code in TRANSLATIONS, (
                f"Language '{lang_code}' is listed in LANGUAGES but has no TRANSLATIONS entry"
            )


class TestTranslationFunction:
    """Tests for the t() helper function."""

    def test_t_returns_english_by_default(self) -> None:
        """t() should return English text when no language is set in storage."""
        # get_language() falls back to DEFAULT_LANGUAGE when storage is unavailable
        result = t("app.title")
        assert result == TRANSLATIONS[DEFAULT_LANGUAGE]["app.title"]

    def test_t_returns_key_for_unknown_keys(self) -> None:
        """t() should return the key itself when it is not found in any language."""
        unknown_key = "this.key.does.not.exist"
        result = t(unknown_key)
        assert result == unknown_key

    def test_t_supports_format_kwargs(self) -> None:
        """t() should interpolate keyword arguments into the translated string."""
        result = t("chart.count_by_period", period="month")
        assert "month" in result

    def test_t_uses_selected_language(self) -> None:
        """t() should use the language stored in NiceGUI user storage when available."""
        with patch("i18n.get_language", return_value="fr"):
            result = t("app.title")
        assert result == TRANSLATIONS["fr"]["app.title"]

    def test_t_falls_back_to_english_for_missing_key_in_language(self) -> None:
        """t() should fall back to English if a key is missing in the active language."""
        # Temporarily add a key only to English
        english_only_key = "_test_english_only_key_"
        TRANSLATIONS[DEFAULT_LANGUAGE][english_only_key] = "English Only"
        try:
            with patch("i18n.get_language", return_value="fr"):
                result = t(english_only_key)
            assert result == "English Only"
        finally:
            del TRANSLATIONS[DEFAULT_LANGUAGE][english_only_key]

    @pytest.mark.parametrize("lang_code", list(LANGUAGES.keys()))
    def test_t_returns_non_empty_string_for_all_keys_in_all_languages(
        self, lang_code: str
    ) -> None:
        """t() must return a non-empty string for every key in every language."""
        with patch("i18n.get_language", return_value=lang_code):
            for key in TRANSLATIONS[DEFAULT_LANGUAGE]:
                result = t(key)
                assert result, (
                    f"t('{key}') returned empty string for language '{lang_code}'"
                )


class TestLanguageConstants:
    """Tests for the LANGUAGES and DEFAULT_LANGUAGE constants."""

    def test_default_language_is_in_languages(self) -> None:
        """DEFAULT_LANGUAGE must be one of the keys in the LANGUAGES dict."""
        assert DEFAULT_LANGUAGE in LANGUAGES

    def test_languages_contains_english_and_french(self) -> None:
        """At minimum, English and French must be supported."""
        assert "en" in LANGUAGES
        assert "fr" in LANGUAGES
