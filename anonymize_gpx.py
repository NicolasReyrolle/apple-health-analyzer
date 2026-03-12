"""Thin wrapper for the canonical GPX anonymization script.

This repository historically contained two different GPX anonymization implementations:
a random jitter implementation at the repository root (this file) and a spherical
rotation–based implementation in ``tests/fixtures/anonymize_gpx.py`` which is
the documented workflow for generating anonymized GPX data.

To avoid divergence and contributor confusion, this script now simply delegates
execution to the canonical implementation under ``tests/fixtures/``.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    """Delegate GPX anonymization to the canonical script in tests/fixtures.

    This preserves the existing command-line interface while ensuring that there
    is a single source of truth for anonymization behavior.
    """
    repo_root = Path(__file__).resolve().parent
    canonical_script = repo_root / "tests" / "fixtures" / "anonymize_gpx.py"

    if not canonical_script.is_file():
        print(
            "Error: canonical GPX anonymizer not found at "
            f"{canonical_script}. Please ensure tests/fixtures/anonymize_gpx.py exists."
        )
        sys.exit(1)

    # Delegate execution to the canonical script, preserving sys.argv so that
    # command-line arguments are handled there exactly as if it were invoked
    # directly (e.g., `python tests/fixtures/anonymize_gpx.py <directory>`).
    runpy.run_path(str(canonical_script), run_name="__main__")


if __name__ == "__main__":
    main()
