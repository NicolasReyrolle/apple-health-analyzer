"""Anonymize GPX files by shifting all coordinates so the first point is (0,0)."""

from __future__ import annotations

import argparse
import math
import sys
import xml.etree.ElementTree as ET

GPX_NAMESPACE = "http://www.topografix.com/GPX/1/1"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"


def _lat_lon_to_vector(latitude: float, longitude: float) -> tuple[float, float, float]:
    """Convert latitude/longitude in degrees to a 3D unit vector on the sphere."""
    lat_rad = math.radians(latitude)
    lon_rad = math.radians(longitude)
    cos_lat = math.cos(lat_rad)
    return (
        cos_lat * math.cos(lon_rad),
        cos_lat * math.sin(lon_rad),
        math.sin(lat_rad),
    )


def _vector_to_lat_lon(vector: tuple[float, float, float]) -> tuple[float, float]:
    """Convert a 3D unit vector to latitude/longitude in degrees."""
    x_coord, y_coord, z_coord = vector
    latitude = math.degrees(math.atan2(z_coord, math.sqrt(x_coord * x_coord + y_coord * y_coord)))
    longitude = math.degrees(math.atan2(y_coord, x_coord))
    return latitude, longitude


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(vector: tuple[float, float, float]) -> float:
    return math.sqrt(_dot(vector, vector))


def _normalize(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    vector_norm = _norm(vector)
    if vector_norm == 0.0:
        raise ValueError("Cannot normalize a zero vector")
    return (vector[0] / vector_norm, vector[1] / vector_norm, vector[2] / vector_norm)


def _rotate_with_axis_angle(
    vector: tuple[float, float, float],
    axis: tuple[float, float, float],
    angle: float,
) -> tuple[float, float, float]:
    """Rotate a vector around a unit axis using Rodrigues' formula."""
    axis_unit = _normalize(axis)
    cos_angle = math.cos(angle)
    sin_angle = math.sin(angle)
    axis_dot_vector = _dot(axis_unit, vector)
    axis_cross_vector = _cross(axis_unit, vector)
    return (
        vector[0] * cos_angle
        + axis_cross_vector[0] * sin_angle
        + axis_unit[0] * axis_dot_vector * (1.0 - cos_angle),
        vector[1] * cos_angle
        + axis_cross_vector[1] * sin_angle
        + axis_unit[1] * axis_dot_vector * (1.0 - cos_angle),
        vector[2] * cos_angle
        + axis_cross_vector[2] * sin_angle
        + axis_unit[2] * axis_dot_vector * (1.0 - cos_angle),
    )


def _build_rotation(
    source_vector: tuple[float, float, float],
    target_vector: tuple[float, float, float],
):
    """Return a rotation function mapping source_vector onto target_vector on the sphere."""
    source_unit = _normalize(source_vector)
    target_unit = _normalize(target_vector)
    cross_vec = _cross(source_unit, target_unit)
    cross_norm = _norm(cross_vec)
    dot_value = max(-1.0, min(1.0, _dot(source_unit, target_unit)))

    if cross_norm < 1e-12:
        if dot_value > 0.0:
            return lambda vector: vector

        # 180-degree rotation: pick any axis orthogonal to source.
        fallback_axis = _cross(source_unit, (0.0, 0.0, 1.0))
        if _norm(fallback_axis) < 1e-12:
            fallback_axis = _cross(source_unit, (0.0, 1.0, 0.0))
        return lambda vector: _rotate_with_axis_angle(vector, fallback_axis, math.pi)

    axis = (cross_vec[0] / cross_norm, cross_vec[1] / cross_norm, cross_vec[2] / cross_norm)
    angle = math.atan2(cross_norm, dot_value)
    return lambda vector: _rotate_with_axis_angle(vector, axis, angle)


def anonymize_gpx(file_path: str) -> None:
    """Rewrite a GPX file in place while preserving route geometry and distances."""
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

    first_lat = float(lat_value)
    first_lon = float(lon_value)
    if abs(first_lat) < 1e-12 and abs(first_lon) < 1e-12:
        raise ValueError("File is already anonymized: first point is 0,0")

    source_vector = _lat_lon_to_vector(first_lat, first_lon)
    target_vector = _lat_lon_to_vector(0.0, 0.0)
    rotate = _build_rotation(source_vector, target_vector)

    for trkpt in root.findall(".//gpx:trkpt", namespaces):
        point_lat = trkpt.get("lat")
        point_lon = trkpt.get("lon")
        if point_lat is None or point_lon is None:
            continue

        point_vector = _lat_lon_to_vector(float(point_lat), float(point_lon))
        rotated_vector = rotate(point_vector)
        new_lat, new_lon = _vector_to_lat_lon(rotated_vector)
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
