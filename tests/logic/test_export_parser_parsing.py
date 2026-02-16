"""Tests for parsing and value conversion functionality."""

from xml.etree.ElementTree import Element

import pytest

import logic.export_parser as ep


class TestParseValue:
    """Test cases for the _parse_value static method."""

    # pylint: disable=protected-access
    @pytest.mark.parametrize(
        "input_str, expected_val, expected_unit",
        [
            # --- 1. Boolean Rules (0 or 1 without unit) ---
            ("0", False, None),  # "0" -> False
            ("1", True, None),  # "1" -> True
            ("0.0", False, None),  # "0.0" -> False (mathematically 0)
            ("1.0", True, None),  # "1.0" -> True
            # --- 2. String Rules (Text without unit) ---
            ("Europe/Luxembourg", "Europe/Luxembourg", None),  # Standard string
            ("Running", "Running", None),  # Activity name
            (
                "String with spaces",
                "String with spaces",
                None,
            ),  # String containing spaces but no number at start
            # --- 3. Number without unit (others) ---
            ("2", 2.0, None),  # Integer other than 0/1
            ("123.45", 123.45, None),  # Float
            ("-5", -5.0, None),  # Negative number
            # --- 4. Standard Unit Conversions (unchanged) ---
            ("860 cm", 8.6, "m"),  # cm to meters
            ("10586 cm", 105.86, "m"),  # cm to meters
            ("8500 %", 85.0, "%"),  # Percentage scaling
            ("10 km", 10.0, "km"),  # Unknown unit passthrough
        ],
    )
    def test_parse_value_logic_rules(self, input_str: str, expected_val: str, expected_unit: str):
        """
        Tests the routing logic: Booleans, Strings, Numbers, and Unit conversion.
        """
        val, unit = ep.ExportParser._parse_value(input_str)  # type: ignore[misc]
        assert val == expected_val
        assert unit == expected_unit

    def test_parse_value_fahrenheit(self):
        """
        Tests Fahrenheit conversion with float precision.
        """
        val, unit = ep.ExportParser._parse_value("52.0326 degF")  # type: ignore[misc]
        assert unit == "degC"
        assert val == pytest.approx(11.12922, abs=0.0001)  # type: ignore[misc]

    def test_parse_value_zero_with_unit(self):
        """
        Edge case: "0 cm".
        Should NOT be boolean False, but 0.0 meters.
        """
        val, unit = ep.ExportParser._parse_value("0 cm")  # type: ignore[misc]
        assert val == pytest.approx(0.0)  # type: ignore[misc]
        assert val is not False  # Explicit type check (optional but strict)
        assert unit == "m"

    @pytest.mark.parametrize("input_val", [None, ""])
    def test_parse_value_empty(self, input_val: str):
        """Tests handling of empty or None values."""
        val, unit = ep.ExportParser._parse_value(input_val)  # type: ignore[misc]
        assert val is None
        assert unit is None


class TestParseValueEdgeCases:
    """Additional edge case tests for _parse_value."""

    # pylint: disable=protected-access
    def test_parse_value_with_negative_fahrenheit(self) -> None:
        """Test Fahrenheit conversion with negative temperature."""
        val, unit = ep.ExportParser._parse_value("-40 degF")  # type: ignore[misc]
        assert unit == "degC"
        assert val == pytest.approx(-40.0, abs=0.0001)  # type: ignore[misc]

    def test_parse_value_with_very_large_number(self) -> None:
        """Test parsing very large numbers."""
        val, unit = ep.ExportParser._parse_value("999999999.99")  # type: ignore[misc]
        assert val == pytest.approx(999999999.99)  # type: ignore[misc]
        assert unit is None

    def test_parse_value_with_scientific_notation(self) -> None:
        """Test parsing numbers in scientific notation."""
        val, unit = ep.ExportParser._parse_value("1.5e-3")  # type: ignore[misc]
        assert val == pytest.approx(0.0015, abs=0.00001)  # type: ignore[misc]
        assert unit is None

    def test_parse_value_with_unit_percent_conversion(self) -> None:
        """Test percentage unit conversion."""
        val, unit = ep.ExportParser._parse_value("50.5 %")  # type: ignore[misc]
        assert val == pytest.approx(0.505, abs=0.001)  # type: ignore[misc]
        assert unit == "%"

    def test_parse_value_handles_multiple_spaces(self) -> None:
        """Test that multiple spaces between value and unit are handled."""
        val, _ = ep.ExportParser._parse_value("100  cm")  # type: ignore[misc]
        assert val is not None


# pylint: disable=protected-access
class TestExtractActivityType:
    """Test the _extract_activity_type method."""

    def test_extract_activity_type_running(self):
        """Test extracting running activity type."""
        elem = Element("Workout", attrib={"workoutActivityType": "HKWorkoutActivityTypeRunning"})
        parser = ep.ExportParser()
        result = parser._extract_activity_type(elem)  # type: ignore[misc]
        assert result == "Running"

    def test_extract_activity_type_cycling(self):
        """Test extracting cycling activity type."""
        elem = Element("Workout", attrib={"workoutActivityType": "HKWorkoutActivityTypeCycling"})
        parser = ep.ExportParser()
        result = parser._extract_activity_type(elem)  # type: ignore[misc]
        assert result == "Cycling"

    def test_extract_activity_type_missing_attribute(self):
        """Test extracting activity type when attribute is missing."""
        elem = Element("Workout")
        parser = ep.ExportParser()
        result = parser._extract_activity_type(elem)  # type: ignore[misc]
        assert result == ""
