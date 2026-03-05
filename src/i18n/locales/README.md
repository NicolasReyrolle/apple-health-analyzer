# Translation Maintenance Guide

This folder contains gettext catalogs used by the app:

- `messages.pot`: source template (all translatable English msgids)
- `<lang>/LC_MESSAGES/messages.po`: editable translations for each language
- `<lang>/LC_MESSAGES/messages.mo`: compiled binary catalogs used at runtime

Current language example:

- `fr/LC_MESSAGES/messages.po`
- `fr/LC_MESSAGES/messages.mo`

## Prerequisites

Activate your virtual environment, then ensure dependencies are installed:

```bash
pip install -r requirements.txt
```

`Babel` is required and already pinned in `requirements.txt`.

## Update Translations After UI/Text Changes

When you add or change calls like `t("...")` in Python code:

1. Rebuild the POT template from source:

```bash
pybabel extract -k t -o src/i18n/locales/messages.pot src
```

1. Update existing language files from the new template (example for French):

```bash
pybabel update -i src/i18n/locales/messages.pot -d src/i18n/locales -D messages -l fr
```

1. Open `src/i18n/locales/fr/LC_MESSAGES/messages.po` and translate any new/changed entries.

1. Compile the `.po` into `.mo`:

```bash
pybabel compile -d src/i18n/locales -D messages -l fr
```

## Add a New Language

Example: Spanish (`es`).

1. Initialize the new language from the template:

```bash
pybabel init -i src/i18n/locales/messages.pot -d src/i18n/locales -D messages -l es
```

1. Translate entries in:

- `src/i18n/locales/es/LC_MESSAGES/messages.po`

1. Compile the catalog:

```bash
pybabel compile -d src/i18n/locales -D messages -l es
```

1. Register the new language in `src/i18n/__init__.py`:

- Add it to the `LANGUAGES` dict, for example: `"es": "Espanol"`

## Compile All Languages

```bash
pybabel compile -d src/i18n/locales -D messages
```

## Verify Before Commit

Run translation consistency tests:

```bash
pytest tests/i18n/test_translations.py
```

Make sure these files are committed:

- `src/i18n/locales/messages.pot`
- `src/i18n/locales/<lang>/LC_MESSAGES/messages.po`
- `src/i18n/locales/<lang>/LC_MESSAGES/messages.mo`
