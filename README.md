# 🏃‍♂️ Apple Health Analyzer

A modern, graphical tool to parse, analyze, and export your Apple Health data. Originally a CLI, this project now features a clean **NiceGUI** interface for easier interaction with your workout history. Of course this is still a work-in-progress, so feel free to contribute.

[![codecov](https://codecov.io/gh/NicolasReyrolle/apple-health-analyzer/graph/badge.svg?token=2yKEc6OOkx)](https://codecov.io/gh/NicolasReyrolle/apple-health-analyzer)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=NicolasReyrolle_apple-health-analyzer&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=NicolasReyrolle_apple-health-analyzer)

## 👩‍💻 For Contributors

If you are contributing or maintaining the project, see [MAINTAINERS.md](MAINTAINERS.md).

## ✨ Features

- **ZIP Parsing**: Directly select and parse your `export.zip` file from Apple Health.
- **Workout Extraction**: Focused on running workouts with detailed metrics (distance, duration, METs, heart rate, power, etc.).
- **Visual Statistics**: Real-time summary of total activities, distance, duration, elevation, and calories with interactive charts (pie/rose charts for activity breakdown, bar charts with trend lines for time-based analysis).
- **Health Data Insights**: Dedicated Health Data tab with period-based trends for resting heart rate, body mass, and VO2 max.
- **Best Segments Tab**: Computes and displays best running segments from 100m to 100km with expandable runner-up rows, formatted durations, and localized labels.
- **Activity Filtering**: Filter your workout data by activity type (Running, Cycling, Walking, etc.).
- **Date Range Filtering**: Analyze specific time periods using the date range picker to focus on your desired date ranges.
- **Trends Period Aggregation**: Switch the Trends tab aggregation between week, month, quarter, or year.
- **Gap-Aware Time Series**: Missing periods are preserved in health-data charts, so the x-axis remains continuous and missing measurements are explicit (not coerced to zero).
- **Route Parts Merging**: Workouts with multiple GPX route files are merged into a single continuous route for analysis.
- **Multilingual UI (EN/FR)**: gettext-based translations for labels, tabs, date picker locale labels, notifications, and loading/progress status messages.
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
1. View the statistics in the **Overview** tab.
1. Explore your data in the **Activities** tab (pie/rose charts grouped by activity type), **Trends** tab (weekly/monthly/quarterly/yearly bar charts with moving average trend lines), **Health Data** tab (line charts for resting heart rate, body mass, and VO2 max), and **Best Segments** tab (standard race distances with expandable runner-ups).
1. Use the **Activity filter** in the left drawer to focus on specific workout types.
1. Use the **Date range picker** to analyze specific time periods.
1. Use the **Aggregate by** selector in the **Trends** tab to change the period.
1. Export your data using the **Export data** menu to download CSV or JSON files.

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

Maintainer and contributor documentation has moved to [MAINTAINERS.md](MAINTAINERS.md).

If you are here to use the app, you can skip directly to the sections above.

## 🔒 Security

This application uses **streaming XML parsing** (`iterparse`) to remain memory-efficient even with large exports (GBs of data) and `defusedxml.ElementTree` to mitigate risks associated with untrusted XML data.

## 📄 License

This project is licensed under the **GPL-3.0 License**. See the [LICENSE](LICENSE) file for details.
