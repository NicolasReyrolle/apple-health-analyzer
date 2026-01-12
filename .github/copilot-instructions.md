# Apple Health Analyzer - AI Coding Agent Instructions

## Architecture

**Purpose**: CLI tool for parsing and analyzing Apple Health export files (ZIP archives containing XML).

**Core Components**:
- `src/apple_health_analyzer.py` - CLI entry point with `argparse` argument parsing
- `src/export_parser.py` - `ExportParser` class (context manager) for ZIP/XML processing
- `tests/` - pytest suite with fixture-based tests

**Data Flow**: CLI args → `parse_cli_arguments()` → `main()` → `ExportParser.__enter__()` → `.parse()` method

## Development Workflow

**Setup**: Python 3.9+ with virtual environment (`.\.venv\Scripts\Activate.ps1` on Windows)

**Testing**: `pytest --cov=src tests/`
- Tests gracefully skip if `tests/fixtures/` missing sample files
- Integration tests expect `export_sample.zip` in fixtures directory

**Code Quality** (all configured in `pyproject.toml`):
```bash
black src tests --line-length=100
isort src tests --profile=black
flake8 src tests --max-complexity=10
mypy src tests
```

CI validates all checks on push/PR to main/develop (`.github/workflows/tests.yml`).

## Critical Patterns

**Context Manager Pattern**: `ExportParser` implements `__enter__`/`__exit__` for resource cleanup.
- Always use: `with ExportParser(file_path) as parser: parser.parse()`
- `zipfile` attribute is `None` until `parse()` explicitly called
- Safely processes large files with streaming (iterparse) and element clearing

**Security**: Uses **defusedxml** (not ElementTree) for XXE protection—maintain for all XML additions.

**CLI Convention**: `parse_cli_arguments()` returns `Dict[str, Any]`, not argparse Namespace.

**Data Processing**: Streaming XML iteration with `defusedxml.ElementTree.iterparse()` and `elem.clear()` for memory efficiency.

## Key Files

| File | Responsibility |
|------|---|
| `src/export_parser.py` | ZIP/XML parsing, extraction logic |
| `src/apple_health_analyzer.py` | CLI interface, entry point |
| `tests/test_*.py` | Parser and CLI tests |
| `pyproject.toml` | Build, tool configs (Black 100-char, isort Black profile) |

## Before Coding

- **Type hints**: Maintain consistency with existing code (mypy: `disallow_untyped_defs = false`)
- **Test fixtures**: Add to `tests/fixtures/` (tests auto-skip if missing)
- **Dependencies**: Check GPL-3.0 license compatibility for additions
- **Entry point**: Sync CLI script name `apple-health-analyzer` in `pyproject.toml` with `main()` function
- **Memory**: Use iterparse + `.clear()` pattern for large XML files (see `_load_running_workouts()`)
- **Data types**: Convert numeric strings to `int`/`float` when parsing XML attributes (see recent changes in `test_export_parser_workout.py` and `export_parser.py`)
- **Documentation**: Update README.md for new features or changes
- **Development**: Use a TDD approach. First write the tests, ensure they fail, then adapt the code
