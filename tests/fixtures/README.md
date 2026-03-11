# Test Fixtures

## export_sample.zip

The file tests/fixtures/export_sample.zip is a convenience fixture for UI tests. It is generated from top-level XML fragment files in tests/fixtures/exports and includes all files found in any exports subfolder.

To regenerate it on demand, run:

```bash
python tests/fixtures/update_export_sample.py
```

This will overwrite tests/fixtures/export_sample.zip with a ZIP that contains:

- apple_health_export/export.xml built from all top-level \*.xml files in tests/fixtures/exports (sorted by file name)
- all files inside subfolders of tests/fixtures/exports (for example workout-routes/), preserved under the same relative paths in apple_health_export/

Optional arguments:

```bash
python tests/fixtures/update_export_sample.py --exports-dir tests/fixtures/exports --output-zip tests/fixtures/export_sample.zip --export-date "2026-01-20 22:00:00 +0100"
```

## GPX anonymization script

The script `tests/fixtures/anonymize_gpx.py` anonymizes GPX/XML route files by applying a spherical rotation so geometry/distances are preserved while the first point is moved to `lat="0.000000"` and `lon="0.000000"`.

Usage:

```bash
python tests/fixtures/anonymize_gpx.py tests/fixtures/exports/workout-routes/route_2025-09-16_6.15pm.gpx
```

Single-track mode for split route files (continuity preserved between files):

```bash
python tests/fixtures/anonymize_gpx.py --single-track tests/fixtures/exports/workout-routes/route_2025-09-16_6.15pm.gpx tests/fixtures/exports/workout-routes/route_2025-09-16_6.25pm.gpx
```

Select all route files for one date:

```bash
python tests/fixtures/anonymize_gpx.py --date 16/09/2025 --single-track
```

Write anonymized copies to another folder instead of in-place:

```bash
python tests/fixtures/anonymize_gpx.py --single-track --output-dir tests/fixtures/output tests/fixtures/exports/workout-routes/route_2025-09-16_6.15pm.gpx
```

Behavior:

- rewrites the input file in place
- supports multiple input files in batch mode
- supports date-based auto-selection with `--date` and `--routes-dir`
- in `--single-track` mode, enforces continuity: first point of file N+1 equals last point of file N
- optionally writes output to another directory with `--output-dir`
- preserves the GPX namespace format (no forced `ns0:` prefixes)
- exits with an error if no track point exists
- exits with an error if the first point is already `0,0` (already anonymized)
