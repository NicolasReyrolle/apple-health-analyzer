# Apple Health Analyzer - AI Coding Agent Instructions

## Architecture

**Purpose**: NiceGUI-based graphical application for parsing and analyzing Apple Health export files (ZIP archives containing XML).

**Core Components**:
- `src/apple_health_analyzer.py` - NiceGUI page definition and main GUI entry point with `@ui.page` decorator
- `src/export_parser.py` - `ExportParser` class (context manager) for ZIP/XML processing
- `src/local_file_picker.py` - `LocalFilePicker` class extending `ui.dialog` for file selection UI
- `src/assets.py` - Static assets (icons, images) for the GUI
- `tests/` - pytest suite with fixture-based tests and NiceGUI testing integration

**Data Flow**: NiceGUI app loads → `@ui.page` creates welcome page → user clicks "Browse" → `pick_file()` opens `LocalFilePicker` → user selects file → `load_file()` parses with `ExportParser` → results displayed in UI

## Development Workflow

**Setup**: Python 3.10+ with virtual environment (`.\.venv\Scripts\Activate.ps1` on Windows)

**Running the App**: `python -m nicegui src.apple_health_analyzer`

**Testing**: `pytest --cov=src tests/`
- Uses `pytest-asyncio` with `asyncio_mode = "auto"` (configured in `pyproject.toml`)
- Uses NiceGUI testing plugin with user fixture (`nicegui.testing.user_plugin`)
- Tests gracefully skip if `tests/fixtures/` missing sample files
- Integration tests may use mock fixtures from `tests/conftest.py`

**Code Quality** (all configured in `pyproject.toml`):
```bash
black src tests --line-length=100
isort src tests --profile=black
mypy src tests
pylint src tests
```

**Linting & Type Checking**: 
- Pylint is configured with: init-hook to add src to path, win32api in extension allow list
- Mypy configured with: `disallow_untyped_defs = false`, Python 3.14 target
- All Pylance and Pylint warnings MUST be resolved (see "Code Quality Standards" section below)

CI validates code quality and tests on push/PR to main/develop (`.github/workflows/tests.yml`).

## Critical Patterns

**Context Manager Pattern**: `ExportParser` implements `__enter__`/`__exit__` for resource cleanup.
- Always use: `with ExportParser(file_path) as parser: parser.parse()`
- `zipfile` attribute is `None` until `parse()` explicitly called
- Safely processes large files with streaming (iterparse) and element clearing

**Security**: Uses **defusedxml** (not ElementTree) for XXE protection—maintain for all XML additions.

**Data Processing**: Streaming XML iteration with `defusedxml.ElementTree.iterparse()` and `elem.clear()` for memory efficiency.

## Key Files

| File | Responsibility |
|------|---|
| `src/apple_health_analyzer.py` | NiceGUI page definition, main GUI entry point, file/data handling |
| `src/export_parser.py` | ZIP/XML parsing, extraction logic |
| `src/local_file_picker.py` | File picker UI component |
| `src/assets.py` | Static assets (base64-encoded icons/images) |
| `tests/conftest.py` | Shared pytest fixtures and mock helpers |
| `tests/test_*.py` | Parser, file picker, and GUI component tests |
| `pyproject.toml` | Build config, tool configs (Black 100-char, Pylint, mypy, pytest) |

## Before Coding

- **Pylance & Pylint warnings**: All Pylance and Pylint warnings MUST be resolved. Do not add code that creates new warnings. Use `# pylint: disable=...` or `# type: ignore` comments only when absolutely necessary and with clear justification.
- **Type hints**: Maintain consistency with existing code (mypy: `disallow_untyped_defs = false`)
- **NiceGUI components**: Familiarize with `@ui.page` decorator, `ui.dialog`, async/await patterns, and testing plugin usage
- **Async/await patterns**: NiceGUI operations are async; always use `async def` and `await` where required. Tests must wait for async operations with `asyncio.sleep()` or similar.
- **Mocking for tests**: Use centralized mock factories from `tests/conftest.py` (e.g., `mock_file_picker_context`) rather than inline mocks. When mocking NiceGUI components, use module-level lookups (e.g., `import apple_health_analyzer as _module; _module.LocalFilePicker`) to enable runtime patching.
- **Test fixtures**: Add to `tests/fixtures/` (tests auto-skip if missing). Use pytest fixtures with `@pytest.fixture` decorator for setup/teardown. Never modify any file in `tests/fixtures/exports` unless adding new sample export files for testing. They are real export samples and should not be altered.
- **Dependencies**: Check GPL-3.0 license compatibility for additions. NiceGUI and defusedxml are core dependencies.
- **Entry point**: Sync entry point in `pyproject.toml` with `main()` function in `src/apple_health_analyzer.py`
- **Memory efficiency**: Use iterparse + `.clear()` pattern for large XML files (see `_load_running_workouts()` in `export_parser.py`)
- **Data types**: Convert numeric strings to `int`/`float` when parsing XML attributes
- **Security**: Uses **defusedxml** (not ElementTree) for XXE protection—maintain for all XML additions
- **Documentation**: Update README.md for new features or changes
- **Development workflow**: Use TDD approach. Write tests first, ensure they fail, then implement the code to pass tests
- **Code reviews**: All Pylint/Pylance issues must be addressed before code is reviewed