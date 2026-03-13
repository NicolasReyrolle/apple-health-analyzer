# Apple Health Analyzer - AI Coding Agent Instructions

## Rule precedence

When instructions conflict, apply this order:
1. Explicit user request for the current task
2. Safety and platform policy
3. This repository instruction file
4. General style preferences

If two rules at the same level conflict, choose the simpler option and state the assumption.

## Project overview

**Purpose**: NiceGUI app that parses Apple Health exports (ZIP containing XML/GPX) and presents workout analytics.

**Core modules**:
- `src/apple_health_analyzer.py` - app entrypoint and `@ui.page` registration
- `src/app_state.py` - shared UI/data singleton state
- `src/ui/layout.py` - UI composition (header, drawer, tabs, charts)
- `src/ui/local_file_picker.py` - local file picker dialog
- `src/ui/helpers.py` - label/date/duration/distance formatters
- `src/logic/export_parser.py` - ZIP/XML/GPX parsing (`ExportParser`)
- `src/logic/workout_manager/` - workout aggregations/export/segment features
- `src/logic/workout_route.py` - `WorkoutRoute`/`RoutePoint`, route metrics, segment search
- `tests/` - unit tests for logic, UI, i18n

**Data flow**: page load → file selection → `load_workouts_from_file()` → parse with `ExportParser` → store in `AppState` → refresh tabs/views.

## Development commands

- Setup (Windows): `.\.venv\Scripts\Activate.ps1`
- Run app: `python -m nicegui src.apple_health_analyzer`
- Tests: `pytest --cov=src tests/`
- Quality: `black src tests --line-length=100`, `isort src tests --profile=black`, `mypy src tests`, `pylint src tests`

## Mandatory engineering constraints

### Parsing and security
- Keep XML parsing on `defusedxml` (never switch to stdlib `ElementTree` for untrusted XML parsing).
- Preserve streaming parsing patterns (`iterparse` + `elem.clear()`) for large files.
- `ExportParser` remains a context manager and should be used with `with ExportParser() as ep:`.

### Test fixtures and mocking
- Never modify existing files under `tests/fixtures/exports`.
- For new scenarios, add new fixture files or construct data in tests.
- Prefer centralized fixtures/helpers in `tests/conftest.py` instead of ad-hoc inline mocks.
- For patching NiceGUI objects, patch module-level lookups to support runtime patching.

### Data and numeric handling
- Convert numeric XML attributes/values to `int`/`float` at parse time.
- In tests, never compare floating-point values with `==`; use `pytest.approx`.

## Coding workflow

### Before coding
- Identify impacted files and adjacent tests.
- Reuse existing patterns and naming.
- Prefer minimal, targeted changes over broad refactors.

### During coding
- Fix root cause; avoid cosmetic unrelated edits.
- Keep public APIs stable unless the task explicitly requests API changes. Do not use compatibility layers unless absolutely necessary.
- Use `# pylint: disable=...` or `# type: ignore` only when necessary and scoped to the smallest expression/line.
- Keep cognitive complexity low; break down complex functions into smaller helpers. Maximum complexity of 15 per function.

### Validation scope (default)
- Validate changed files and directly affected tests first.
- Run wider suites (`tests/`, full lint, full type-check) only when:
	- requested by the user, or
	- risk is high (cross-cutting parser/model/UI changes).

### TDD policy
- Use TDD for bug fixes and new logic where practical.
- For trivial refactors/renames/doc-only changes, add or update tests only if behavior meaningfully changes.

## Definition of done

A task is complete when all of the following are true:
1. Requested behavior is implemented.
2. Changed files are lint/type clean (or existing unrelated issues are explicitly called out).
3. Relevant tests pass.
4. Any new assumptions, trade-offs, or follow-ups are clearly reported.

## Key file map

| File | Responsibility |
|---|---|
| `src/apple_health_analyzer.py` | App entrypoint, page registration, CLI args |
| `src/app_state.py` | Shared application state |
| `src/ui/layout.py` | Main UI rendering/composition |
| `src/ui/local_file_picker.py` | Local file picker dialog UI |
| `src/ui/helpers.py` | UI formatting utilities |
| `src/logic/export_parser.py` | Health export parsing, route loading |
| `src/logic/workout_manager/` | Aggregations and reporting utilities |
| `src/logic/workout_route.py` | Route models and route computations |
| `tests/conftest.py` | Shared fixtures and test helpers |
| `pyproject.toml` | Tooling configuration (pytest/mypy/pylint/formatters) |

## CI expectations

CI validates tests and quality checks on PRs. Keep local changes aligned with configured tooling and avoid introducing new warnings in touched code.

## Example responses

### Small fix (single file)
"Updated `src/logic/workout_route.py` to avoid float equality in the segment guard. Ran `pytest tests/logic/test_workout_route.py -q` (all passing). No API changes."

### Multi-file change
"Implemented the requested metric in `src/logic/workout_manager/` and wired it in `src/ui/layout.py`, with tests in `tests/logic/test_workout_manager_totals.py`. Validated changed tests and ran targeted lint/type checks for touched files."

### Blocked case
"I could not complete the change because the required fixture is missing and must be provided by a human (`tests/fixtures/exports/...`). I made no destructive edits. If you add the fixture, I can finish by adding parser handling and tests in one pass."
