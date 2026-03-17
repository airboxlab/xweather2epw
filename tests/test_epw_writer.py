"""Tests for EPW writer."""

import os
import tempfile
from datetime import datetime

from xweather2epw.epw_writer import EPWWriter


def test_epw_writer_with_sample_data():
    """Test EPW writer with sample weather data."""
    sample_data = {
        "place": {"name": "Minneapolis", "state": "MN", "country": "US"},
        "profile": {"tz": -6, "elevM": 250},
        "periods": [
            {
                "dateTimeISO": "2024-01-01T00:00:00-06:00",
                "tempC": -10.0,
                "dewpointC": -15.0,
                "humidity": 70,
                "pressureMB": 1013.25,
                "windSpeedKPH": 18.0,
                "windDirDEG": 270,
                "cloudsCovered": 50,
                "visibilityKM": 10.0,
                "precipMM": 0.0,
                "snowDepthCM": 5.0,
            },
            {
                "dateTimeISO": "2024-01-01T01:00:00-06:00",
                "tempC": -11.0,
                "dewpointC": -16.0,
                "humidity": 72,
                "pressureMB": 1013.0,
                "windSpeedKPH": 20.0,
                "windDirDEG": 280,
                "cloudsCovered": 60,
                "visibilityKM": 8.0,
                "precipMM": 1.5,
                "snowDepthCM": 6.0,
            },
        ],
        "loc": {"lat": 44.9778, "long": -93.2650},
    }

    writer = EPWWriter(sample_data, 44.9778, -93.2650)

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".epw") as f:
        temp_path = f.name

    try:
        writer.write(temp_path)

        # Verify file was created
        assert os.path.exists(temp_path)

        # Read and verify content
        with open(temp_path) as f:
            content = f.read()
            lines = content.split("\n")

        # Check headers
        assert lines[0].startswith("LOCATION,Minneapolis/MN")
        assert "DESIGN CONDITIONS" in lines[1]
        assert "TYPICAL/EXTREME PERIODS" in lines[2]
        assert "GROUND TEMPERATURES,0" in lines[3]
        assert "HOLIDAYS/DAYLIGHT SAVING" in lines[4]
        assert "xweather2epw" in lines[5]
        assert "XWeather API" in lines[6]
        assert "DATA PERIODS" in lines[7]

        # Check weather data records
        assert len(lines) > 8  # Should have at least header + 2 data records

        # Verify first data record
        first_record = lines[8].split(",")
        assert first_record[0] == "2024"  # Year
        assert first_record[1] == "1"  # Month
        assert first_record[2] == "1"  # Day

    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_epw_writer_missing_data():
    """Test EPW writer handles missing data properly."""
    sample_data = {
        "place": {},
        "profile": {},
        "periods": [
            {
                "dateTimeISO": "2024-01-01T00:00:00Z",
                # Minimal data, most fields missing
                "tempC": 20.0,
            }
        ],
        "loc": {"lat": 0.0, "long": 0.0},
    }

    writer = EPWWriter(sample_data, 0.0, 0.0)

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".epw") as f:
        temp_path = f.name

    try:
        # Should not raise an error
        writer.write(temp_path)

        # Verify file was created
        assert os.path.exists(temp_path)

        with open(temp_path) as f:
            content = f.read()

        # Should have default values for missing data
        assert "999" in content or "9999" in content

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_parse_iso_datetime():
    """Test ISO datetime parsing."""
    writer = EPWWriter({}, 0.0, 0.0)

    # Test with timezone
    dt1 = writer._parse_iso_datetime("2024-01-01T12:00:00-06:00")
    assert dt1 == datetime(2024, 1, 1, 12, 0, 0)

    # Test without timezone
    dt2 = writer._parse_iso_datetime("2024-01-01T12:00:00")
    assert dt2 == datetime(2024, 1, 1, 12, 0, 0)

    # Test with Z timezone (UTC)
    dt3 = writer._parse_iso_datetime("2024-01-01T12:00:00Z")
    assert dt3 == datetime(2024, 1, 1, 12, 0, 0)

    # Test invalid string
    dt4 = writer._parse_iso_datetime("invalid")
    assert dt4 is None


def test_epw_writer_with_solar_radiation():
    """Test EPW writer extracts solar radiation data from solrad field."""
    sample_data = {
        "place": {"name": "Test City", "state": "ST", "country": "US"},
        "profile": {"tz": 0, "elevM": 100},
        "periods": [
            {
                "dateTimeISO": "2024-06-15T12:00:00Z",
                "tempC": 25.0,
                "dewpointC": 15.0,
                "humidity": 60,
                "pressureMB": 1013.25,
                "windSpeedKPH": 10.0,
                "windDirDEG": 180,
                "cloudsCovered": 20,
                "visibilityKM": 15.0,
                "precipMM": 0.0,
                "snowDepthCM": 0.0,
                "solrad": {
                    "ghiWM2": 346.77,
                    "dniWM2": 165.75,
                    "dhiWM2": 249.02,
                },
            }
        ],
        "loc": {"lat": 40.0, "long": -100.0},
    }

    writer = EPWWriter(sample_data, 40.0, -100.0)

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".epw") as f:
        temp_path = f.name

    try:
        writer.write(temp_path)

        # Verify file was created
        assert os.path.exists(temp_path)

        # Read and verify content
        with open(temp_path) as f:
            content = f.read()
            lines = content.split("\n")

        # Check that there's weather data
        assert len(lines) > 8

        # Get the first weather data record (line 8, 0-indexed)
        weather_record = lines[8].split(",")

        # Verify solar radiation values are present
        # Field indices in EPW format (0-based):
        # 13: Global Horizontal Radiation
        # 14: Direct Normal Radiation
        # 15: Diffuse Horizontal Radiation
        global_horizontal = float(weather_record[13])
        direct_normal = float(weather_record[14])
        diffuse_horizontal = float(weather_record[15])

        # Check that values match the input (approximately)
        assert abs(global_horizontal - 346.77) < 0.1
        assert abs(direct_normal - 165.75) < 0.1
        assert abs(diffuse_horizontal - 249.02) < 0.1

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
