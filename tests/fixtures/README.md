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

The script `tests/fixtures/anonymize_gpx.py` anonymizes a GPX/XML route file by shifting all `trkpt` coordinates so the first point becomes `lat="0.000000"` and `lon="0.000000"`.

Usage:

```bash
python tests/fixtures/anonymize_gpx.py tests/fixtures/exports/workout-routes/route_2025-09-16_6.15pm.gpx
```

Behavior:

- rewrites the input file in place
- preserves the GPX namespace format (no forced `ns0:` prefixes)
- exits with an error if no track point exists
- exits with an error if the first point is already `0,0` (already anonymized)
