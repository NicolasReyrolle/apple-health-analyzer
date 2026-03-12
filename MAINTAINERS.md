# Maintainers Guide

This document contains development, testing, and maintenance notes for `apple-health-analyzer`.

## Development Setup

### Run tests

```bash
pytest --cov=src tests/
```

### Dev mode (preloaded file)

Preferred entry point:

```bash
apple-health-analyzer --dev-file tests/fixtures/export_sample.zip
```

Alternative module run:

```bash
python src/apple_health_analyzer.py --dev-file tests/fixtures/export_sample.zip
```

### Debug logging for dev-file loading

```bash
apple-health-analyzer --dev-file tests/fixtures/export_sample.zip --log-level DEBUG
```

or:

```bash
python src/apple_health_analyzer.py --dev-file tests/fixtures/export_sample.zip --log-level DEBUG
```

In normal mode logs are written to console and `logs/apple_health_analyzer.log`.
In `--dev-file` mode logs are console-only to avoid reload loops.

Available log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`).

### Rebuild test fixture zip

```bash
python tests/fixtures/update_export_sample.py
```

This rebuilds `tests/fixtures/export_sample.zip` from `tests/fixtures/exports/`.

## Code Quality

Run before opening a PR:

```bash
black src tests --line-length=100
isort src tests --profile=black
mypy src tests
pylint src tests
```

## Route Parsing and Segment Semantics

The parser and segment logic intentionally use window-bounded route behavior:

- Each XML `WorkoutRoute` block is treated as an independent time window.
- GPX points are clipped to that window (`startDate` to `endDate`).
- Windows with no matching GPX points are skipped.
- Parsed route windows are stored in `route_parts`.
- `route` is kept as a backward-compatible merged representation.
- Best-segment analysis uses `route_parts` traces so segment windows do not cross disjoint route windows.

This behavior prevents unrealistic artifacts (for example impossible `100m` durations) when exports contain reused GPX file references or missing points in specific windows.

## Translations

Translation workflows are documented in [src/i18n/locales/README.md](src/i18n/locales/README.md).

Runtime notes:

- Language is session-based and changeable from the header menu.
- Loading/progress messages are localized in UI.
- Date picker labels are sourced from gettext catalogs.
- `.mo` files are auto-generated at startup when missing/outdated.

## Windows-specific testing note

`tests/conftest.py` includes workarounds for `WinError 32` (PermissionError) during teardown by isolating storage and patching cleanup behavior.
