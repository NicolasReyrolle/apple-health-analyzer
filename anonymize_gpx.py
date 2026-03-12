"""Anonymize GPX coordinates in a directory to small random offsets near (0, 0)."""

import random
import re
import sys
from pathlib import Path


def is_already_anonymized(content: str) -> bool:
    """Check if GPX content is already anonymized (coordinates near 0,0)."""
    # Look for coordinates with magnitude > 1 degree
    if re.search(r'lon="[1-9]\d*\.', content):
        return False
    if re.search(r'lon="-[1-9]\d*\.', content):
        return False
    return True


def anonymize_gpx_file(filepath: Path) -> None:
    """Anonymize GPS coordinates in a single GPX file.

    Replaces real coordinates with small random offsets near (0, 0).
    """
    # Read original content
    original_content = filepath.read_text(encoding="utf-8")

    # Check if already anonymized
    if is_already_anonymized(original_content):
        print(f"Skipped (already anonymized): {filepath.name}")
        return

    # Set seed for deterministic but filename-unique offsets
    random.seed(hash(filepath.name) % (2**32))

    # State for coordinate generation
    state: dict[str, float] = {"base_lat": 0.0, "base_lon": 0.0}

    def replace_trkpt(_: re.Match[str]) -> str:
        """Replace trkpt coordinates with anonymized values."""
        # Generate small offsets
        lat_offset = (random.random() - 0.5) * 0.1
        lon_offset = (random.random() - 0.5) * 0.1

        state["base_lat"] += lat_offset * 0.01
        state["base_lon"] += lon_offset * 0.01

        # Keep values small
        state["base_lat"] = max(-0.05, min(0.05, state["base_lat"]))
        state["base_lon"] = max(-0.05, min(0.05, state["base_lon"]))

        return f'<trkpt lon="{state["base_lon"]:.6f}" lat="{state["base_lat"]:.6f}"'

    # Replace all trkpt coordinates
    trkpt_pattern = r'<trkpt\s+lon="[^"]+"\s+lat="[^"]+"'
    modified_content = re.sub(trkpt_pattern, replace_trkpt, original_content)

    # Write back
    filepath.write_text(modified_content, encoding="utf-8")
    print(f"Anonymized: {filepath.name}")


def anonymize_directory(directory: Path) -> None:
    """Anonymize all GPX files in a directory."""
    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)

    gpx_files = sorted(directory.glob("*.gpx"))

    if not gpx_files:
        print(f"No GPX files found in {directory}")
        return

    print(f"Processing {len(gpx_files)} GPX files in {directory}")

    for filepath in gpx_files:
        try:
            anonymize_gpx_file(filepath)
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error processing {filepath.name}: {e}")

    print("Done!")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python anonymize_gpx.py <directory>")
        sys.exit(1)

    target_dir = Path(sys.argv[1])
    anonymize_directory(target_dir)
