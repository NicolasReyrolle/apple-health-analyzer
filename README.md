# 🏃‍♂️ Apple Health Analyzer

A modern, graphical tool to parse, analyze, and export your Apple Health data. Originally a CLI, this project now features a clean **NiceGUI** interface for easier interaction with your workout history. Of course this is still a work-in-progress, so feel free to contribute.

[![codecov](https://codecov.io/gh/NicolasReyrolle/apple-health-analyzer/graph/badge.svg?token=2yKEc6OOkx)](https://codecov.io/gh/NicolasReyrolle/apple-health-analyzer)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=NicolasReyrolle_apple-health-analyzer&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=NicolasReyrolle_apple-health-analyzer)

## ✨ Features

- **ZIP Parsing**: Directly select and parse your `export.zip` file from Apple Health.
- **Workout Extraction**: Focused on running workouts with detailed metrics (distance, duration, METs, heart rate, power, etc.).
- **Visual Statistics**: Real-time summary of total activities, distance, and time (WIP)
- **Data Export**: Convert your data into clean **CSV** or **JSON** formats for further analysis in Excel, Python, or other tools.
- All processing happens locally on your machine.
- **Modern UI**: Dark/Light mode support with a responsive layout.

## 🚀 Installation

### Prerequisites

- Python 3.10 or higher.
- An Apple Health export file (`export.zip`).

### Setup

#### Clone the repository

```bash
git clone https://github.com/NicolasReyrolle/apple-health-analyzer.git
cd apple-health-analyzer
```

#### Create a virtual environment

```bash
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate
```

#### Install the dependencies

```bash
pip install -r requirements.txt
```

## 🖥️ Usage

Start the application using the following command:

```bash
python -m nicegui src.apple_health_analyzer
```

1. Open your browser to `http://localhost:8080`.
1. Click **Browse** to select your Apple Health `export.zip`.
1. Click **Load** to parse the data.
1. View the statistics and use the **Export data** menu to download your CSV or JSON files.

> **Tip**: You can set a permanent storage secret for sessions by using an environment variable:
> `set STORAGE_SECRET=your_custom_secret` (Windows)

### 📱 How to Get Your Export File

To analyze your data, you first need to export it from your iPhone:

1. Open the **Health app** on your iPhone.
1. Tap your **Profile Picture** or icon in the top-right corner.
1. Scroll to the bottom and tap **Export All Health Data**.
1. Tap **Export** to confirm. This process may take a few minutes depending on the amount of data.
1. Once the export is ready, share the `export.zip` file to your computer (via AirDrop, iCloud Drive, OneDrive, GoogleDrive or any other mean).
1. Use this file in the **Apple Health Analyzer** app.

## 🛠️ Development & Testing

### Running Tests

The project uses `pytest` with specific configurations for asynchronous NiceGUI testing.

```bash
pytest --cov=src tests/
```

### Developer Mode: Quick UI Testing

For rapid UI development and testing, you can launch the app with a pre-loaded Apple Health export file:

```bash
python src/apple_health_analyzer.py --dev-file tests/fixtures/export_sample.zip
```

This is especially useful for:

- Testing UI rendering with actual data without manual file selection
- Quick iteration on UI components
- Verifying data visualization and metrics display

The app will automatically load the specified file on startup, skipping the file picker dialog.

#### Enable Debug Logging

To see detailed debug information about the dev file loading process:

```bash
python src/apple_health_analyzer.py --dev-file tests/fixtures/export_sample.zip --log-level DEBUG
```

Debug logs are written to:

- **Console**: Printed to stdout
- **File**: `logs/apple_health_analyzer.log` (size-based rotation: 10MB max per file, 3 backup files)

**Note**: When running with `--dev-file`, file logging is disabled to prevent reload loops. Logs are only written to the console in dev mode.

Available log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)

**Note**: First, generate the test fixture with:

```bash
python tests/fixtures/update_export_sample.py
```

### Code Quality

We maintain strict coding standards. Before submitting a PR, ensure your code passes:

- **Formatting**: `black` & `isort`.
- **Linting**: `pylint` (configured for Windows compatibility).
- **Typing**: `mypy` & `Pylance` (Strict mode).

```bash
# Run all checks
black src tests --line-length=100
isort src tests --profile=black
mypy src tests
pylint src tests
```

### Windows-Specific Notes

The test suite includes a specialized `conftest.py` that handles Windows "WinError 32" (PermissionError) by isolating storage and patching file locks during teardown.

## 🔒 Security

This application uses **streaming XML parsing** (`iterparse`) to remain memory-efficient even with large exports (GBs of data) and `defusedxml.ElementTree` to mitigate risks associated with untrusted XML data.

## 📄 License

This project is licensed under the **GPL-3.0 License**. See the [LICENSE](LICENSE) file for details.
