"""Fixtures for testing Apple Health Analyzer."""

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Callable, Generator

import pytest

# Centralized default XML structure
DEFAULT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData version="11">
    <ExportDate value="2026-01-20 22:00:00 +0100"/>
    <Me HKCharacteristicTypeIdentifierDateOfBirth="1990-01-01" 
        HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexMale"/>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" 
             duration="119.2710362156232" durationUnit="min" 
             sourceName="Apple Watch" sourceVersion="26.2" 
             creationDate="2025-12-20 14:51:19 +0100" 
             startDate="2025-12-20 12:51:00 +0100" 
             endDate="2025-12-20 14:50:16 +0100">
        <MetadataEntry key="HKIndoorWorkout" value="0"/>
        <MetadataEntry key="HKTimeZone" value="Europe/Paris"/>
        <MetadataEntry key="HKWeatherHumidity" value="9400 %"/>
        <MetadataEntry key="HKWeatherTemperature" value="47.6418 degF"/>
        <MetadataEntry key="HKAverageMETs" value="9.66668 kcal/hr·kg"/>
        <WorkoutEvent type="HKWorkoutEventTypeSegment" date="2025-12-20 12:51:00 +0100" duration="8.048923822244008" durationUnit="min"/>
        <WorkoutActivity uuid="936B9E1D-52B9-41CA-BCA9-9654D43F004E" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" duration="119.2710362156232" durationUnit="min">
            <WorkoutStatistics type="HKQuantityTypeIdentifierStepCount" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" sum="17599" unit="count"/>
            <MetadataEntry key="HKElevationAscended" value="45443 cm"/>
        </WorkoutActivity>
        <WorkoutStatistics type="HKQuantityTypeIdentifierStepCount" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" sum="17599" unit="count"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierRunningGroundContactTime" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" average="323.718" minimum="224" maximum="369" unit="ms"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierRunningPower" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" average="222.789" minimum="61" maximum="479" unit="W"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" sum="1389.98" unit="kcal"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" sum="16.1244" unit="km"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" average="140.139" minimum="75" maximum="157" unit="count/min"/>
    </Workout>
</HealthData>
"""


@pytest.fixture
def create_health_zip() -> Generator[Callable[[str], str], None, None]:
    """
    Factory fixture to generate a health export ZIP file.
    Usage: zip_path = create_health_zip([optional_xml_string])
    """
    temp_dirs: list[str] = []

    def _generate(xml_content: str = DEFAULT_XML) -> str:
        # Create a unique temp directory for this specific file
        temp_dir = tempfile.mkdtemp()
        temp_dirs.append(temp_dir)

        zip_path = Path(temp_dir) / "export.zip"
        internal_path = "apple_health_export/export.xml"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr(internal_path, xml_content)

        return str(zip_path)

    yield _generate

    # Cleanup after the test is finished
    for d in temp_dirs:
        shutil.rmtree(d, ignore_errors=True)
