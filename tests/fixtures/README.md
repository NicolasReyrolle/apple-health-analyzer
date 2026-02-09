# Test Fixtures

## export_sample.zip

The file tests/fixtures/export_sample.zip is a convenience fixture for UI tests. It is generated from the XML fragment files in tests/fixtures/exports.

To regenerate it on demand, run:

```bash
python tests/fixtures/update_export_sample.py
```

This will overwrite tests/fixtures/export_sample.zip with a ZIP that contains apple_health_export/export.xml built from all \*.xml files in tests/fixtures/exports (sorted by file name).

Optional arguments:

```bash
python tests/fixtures/update_export_sample.py --exports-dir tests/fixtures/exports --output-zip tests/fixtures/export_sample.zip --export-date "2026-01-20 22:00:00 +0100"
```
