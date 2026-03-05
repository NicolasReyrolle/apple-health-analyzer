"""Tests for top-level package metadata."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def test_package_version_is_defined() -> None:
    """Top-level package should expose a non-empty __version__."""
    init_path = Path(__file__).resolve().parents[1] / "src" / "__init__.py"
    spec = spec_from_file_location("package_init", init_path)
    assert spec is not None and spec.loader is not None

    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    version = getattr(module, "__version__", "")
    assert isinstance(version, str)
    assert version
