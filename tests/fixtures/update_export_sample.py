"""Build tests/fixtures/export_sample.zip from XML fragments in tests/fixtures/exports."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from typing import Iterable

INTERNAL_XML_PATH = "apple_health_export/export.xml"
DEFAULT_EXPORT_DATE = "2026-01-20 22:00:00 +0100"


def build_health_export_xml(workout_fragments: Iterable[str], export_date: str) -> str:
    """Wrap workout fragments in a minimal HealthData document."""
    workouts_xml = "\n".join(workout_fragments)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<HealthData version="11">\n'
        f'    <ExportDate value="{export_date}"/>\n'
        f"{workouts_xml}\n"
        "</HealthData>\n"
    )


def load_fragments(exports_dir: Path) -> list[str]:
    """Load XML fragments from the exports directory in sorted order."""
    fragment_files = sorted(exports_dir.glob("*.xml"))
    if not fragment_files:
        raise FileNotFoundError(f"No XML fragments found in {exports_dir}")
    return [fragment.read_text(encoding="utf-8") for fragment in fragment_files]


def write_export_zip(output_zip: Path, xml_content: str) -> None:
    """Write the export XML into a ZIP at the expected internal path."""
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr(INTERNAL_XML_PATH, xml_content)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Rebuild tests/fixtures/export_sample.zip from XML fragments.",
    )
    parser.add_argument(
        "--exports-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "exports",
        help="Directory containing XML fragments (default: tests/fixtures/exports)",
    )
    parser.add_argument(
        "--output-zip",
        type=Path,
        default=Path(__file__).resolve().parent / "export_sample.zip",
        help="Output zip path (default: tests/fixtures/export_sample.zip)",
    )
    parser.add_argument(
        "--export-date",
        type=str,
        default=DEFAULT_EXPORT_DATE,
        help="ExportDate value written into the XML",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    try:
        fragments = load_fragments(args.exports_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    xml_content = build_health_export_xml(fragments, args.export_date)
    write_export_zip(args.output_zip, xml_content)
    print(f"Wrote {args.output_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
