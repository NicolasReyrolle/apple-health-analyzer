"""Translation dictionaries for supported languages."""

DEFAULT_LANGUAGE = "en"

LANGUAGES: dict[str, str] = {
    "en": "English",
    "fr": "Français",
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # App title
        "app.title": "Apple Health Analyzer",
        # Header
        "header.language_selector": "Language",
        # Left drawer
        "drawer.activities": "Activities",
        "drawer.activity_type": "Activity Type",
        "drawer.date_range": "Date range",
        "drawer.export_data": "Export data",
        "drawer.export_to_json": "to JSON",
        "drawer.export_to_csv": "to CSV",
        # Main body
        "body.input_file_label": "Apple Health export file",
        "body.input_file_placeholder": "Select an Apple Health export file...",
        "body.btn_browse": "Browse",
        "body.btn_load": "Load",
        # Tabs
        "tab.overview": "Overview",
        "tab.activities": "Activities",
        "tab.trends": "Trends",
        "tab.health_data": "Health Data",
        # Stat cards
        "stat.count": "Count",
        "stat.distance": "Distance",
        "stat.duration": "Duration",
        "stat.elevation": "Elevation",
        "stat.calories": "Calories",
        # Notifications
        "notify.no_file_selected": "No file selected",
        "notify.select_file_first": "Please select an Apple Health export file first.",
        "notify.file_parsed": "File parsed successfully.",
        "notify.error_parsing": "Error parsing file: {error}",
        # Trends
        "trends.aggregate_by": "Aggregate by:",
        "period.W": "Week",
        "period.M": "Month",
        "period.Q": "Quarter",
        "period.Y": "Year",
        # Period labels (lowercase, for chart titles)
        "period_label.W": "week",
        "period_label.M": "month",
        "period_label.Q": "quarter",
        "period_label.Y": "year",
        # Activity charts
        "chart.count_by_activity": "Count by activity",
        "chart.distance_by_activity": "Distance by activity",
        "chart.calories_by_activity": "Calories by activity",
        "chart.duration_by_activity": "Duration by activity",
        "chart.elevation_by_activity": "Elevation by activity",
        # Trends charts (use {period} placeholder)
        "chart.count_by_period": "Count by {period}",
        "chart.distance_by_period": "Distance by {period}",
        "chart.calories_by_period": "Calories by {period}",
        "chart.duration_by_period": "Duration by {period}",
        "chart.elevation_by_period": "Elevation by {period}",
        # Health data charts
        "chart.resting_hr": "Resting HR frequency over time",
        "chart.body_mass": "Body Mass over time",
        "chart.vo2_max": "VO2 Max over time",
    },
    "fr": {
        # App title
        "app.title": "Analyseur de santé Apple",
        # Header
        "header.language_selector": "Langue",
        # Left drawer
        "drawer.activities": "Activités",
        "drawer.activity_type": "Type d'activité",
        "drawer.date_range": "Plage de dates",
        "drawer.export_data": "Exporter les données",
        "drawer.export_to_json": "en JSON",
        "drawer.export_to_csv": "en CSV",
        # Main body
        "body.input_file_label": "Fichier d'export Apple Health",
        "body.input_file_placeholder": "Sélectionner un fichier d'export Apple Health...",
        "body.btn_browse": "Parcourir",
        "body.btn_load": "Charger",
        # Tabs
        "tab.overview": "Vue d'ensemble",
        "tab.activities": "Activités",
        "tab.trends": "Tendances",
        "tab.health_data": "Données de santé",
        # Stat cards
        "stat.count": "Nombre",
        "stat.distance": "Distance",
        "stat.duration": "Durée",
        "stat.elevation": "Dénivelé",
        "stat.calories": "Calories",
        # Notifications
        "notify.no_file_selected": "Aucun fichier sélectionné",
        "notify.select_file_first": "Veuillez d'abord sélectionner un fichier d'export Apple Health.",
        "notify.file_parsed": "Fichier analysé avec succès.",
        "notify.error_parsing": "Erreur lors de l'analyse : {error}",
        # Trends
        "trends.aggregate_by": "Agréger par :",
        "period.W": "Semaine",
        "period.M": "Mois",
        "period.Q": "Trimestre",
        "period.Y": "Année",
        # Period labels (lowercase, for chart titles)
        "period_label.W": "semaine",
        "period_label.M": "mois",
        "period_label.Q": "trimestre",
        "period_label.Y": "année",
        # Activity charts
        "chart.count_by_activity": "Nombre par activité",
        "chart.distance_by_activity": "Distance par activité",
        "chart.calories_by_activity": "Calories par activité",
        "chart.duration_by_activity": "Durée par activité",
        "chart.elevation_by_activity": "Dénivelé par activité",
        # Trends charts (use {period} placeholder)
        "chart.count_by_period": "Nombre par {period}",
        "chart.distance_by_period": "Distance par {period}",
        "chart.calories_by_period": "Calories par {period}",
        "chart.duration_by_period": "Durée par {period}",
        "chart.elevation_by_period": "Dénivelé par {period}",
        # Health data charts
        "chart.resting_hr": "Fréquence cardiaque au repos au fil du temps",
        "chart.body_mass": "Masse corporelle au fil du temps",
        "chart.vo2_max": "VO2 Max au fil du temps",
    },
}
