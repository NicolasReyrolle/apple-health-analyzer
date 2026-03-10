"""Anonymize GPX files by shifting all coordinates so the first point is (0,0)."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET

GPX_NAMESPACE = "http://www.topografix.com/GPX/1/1"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"


def anonymize_gpx(file_path: str) -> None:
    """Rewrite a GPX file in place, shifting all track points by the first point offset."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    namespaces = {"gpx": GPX_NAMESPACE}

    first_pt = root.find(".//gpx:trkpt", namespaces)
    if first_pt is None:
        raise ValueError("No track point found in file")

    lat_value = first_pt.get("lat")
    lon_value = first_pt.get("lon")
    if lat_value is None or lon_value is None:
        raise ValueError("First track point is missing lat/lon attributes")

    offset_lat = float(lat_value)
    offset_lon = float(lon_value)
    if offset_lat == 0.0 and offset_lon == 0.0:
        raise ValueError("File is already anonymized: first point is 0,0")

    for trkpt in root.findall(".//gpx:trkpt", namespaces):
        point_lat = trkpt.get("lat")
        point_lon = trkpt.get("lon")
        if point_lat is None or point_lon is None:
            continue

        new_lat = float(point_lat) - offset_lat
        new_lon = float(point_lon) - offset_lon
        trkpt.set("lat", f"{new_lat:.6f}")
        trkpt.set("lon", f"{new_lon:.6f}")

    # Preserve original namespace style instead of introducing ns0 prefixes.
    ET.register_namespace("", GPX_NAMESPACE)
    ET.register_namespace("xsi", XSI_NAMESPACE)
    tree.write(file_path, encoding="utf-8", xml_declaration=True)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Rewrite a GPX file by shifting coordinates so first point becomes 0,0"
    )
    parser.add_argument("file", help="Path to the GPX/XML file to anonymize in place")
    args = parser.parse_args()

    try:
        anonymize_gpx(args.file)
    except (ET.ParseError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
