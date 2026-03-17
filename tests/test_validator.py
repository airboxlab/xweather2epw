"""Tests for input validation."""

import pytest
from datetime import datetime, timedelta
from xweather2epw.validator import validate_inputs


def test_valid_inputs():
    """Test validation with valid inputs."""
    from_dt, to_dt = validate_inputs("2024-01-01", "2024-12-31", 49.4, 0.1)
    assert from_dt == datetime(2024, 1, 1)
    assert to_dt == datetime(2024, 12, 31)


def test_invalid_latitude():
    """Test validation with invalid latitude."""
    with pytest.raises(ValueError, match="Latitude must be between"):
        validate_inputs("2024-01-01", "2024-12-31", 100, 0.1)

    with pytest.raises(ValueError, match="Latitude must be between"):
        validate_inputs("2024-01-01", "2024-12-31", -100, 0.1)


def test_invalid_longitude():
    """Test validation with invalid longitude."""
    with pytest.raises(ValueError, match="Longitude must be between"):
        validate_inputs("2024-01-01", "2024-12-31", 49.4, 200)

    with pytest.raises(ValueError, match="Longitude must be between"):
        validate_inputs("2024-01-01", "2024-12-31", 49.4, -200)


def test_invalid_date_format():
    """Test validation with invalid date format."""
    with pytest.raises(ValueError, match="Invalid from date format"):
        validate_inputs("2024/01/01", "2024-12-31", 49.4, 0.1)

    with pytest.raises(ValueError, match="Invalid to date format"):
        validate_inputs("2024-01-01", "2024/12/31", 49.4, 0.1)


def test_date_range_validation():
    """Test that start date must be before end date."""
    with pytest.raises(ValueError, match="must be before end date"):
        validate_inputs("2024-12-31", "2024-01-01", 49.4, 0.1)


def test_max_duration():
    """Test that date range cannot exceed 365 days."""
    with pytest.raises(ValueError, match="cannot exceed 365 days"):
        validate_inputs("2024-01-01", "2025-12-31", 49.4, 0.1)


def test_future_limit():
    """Test that end date cannot be more than 14 days in the future."""
    from_date = datetime.now().strftime("%Y-%m-%d")
    future_date = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
    with pytest.raises(ValueError, match="cannot be more than 14 days in the future"):
        validate_inputs(from_date, future_date, 49.4, 0.1)
