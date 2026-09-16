"""Tests for API client."""

from datetime import datetime

from xweather2epw.api_client import XWeatherClient


def test_split_date_range():
    """Test date range splitting."""
    client = XWeatherClient("test_key", "test_secret")

    from_dt = datetime(2024, 1, 1)
    to_dt = datetime(2024, 1, 31)

    chunks = client._split_date_range(from_dt, to_dt)

    # 31 days should be split into 3 chunks (15 + 15 + 1)
    assert len(chunks) == 3
    assert chunks[0] == (datetime(2024, 1, 1), datetime(2024, 1, 15))
    assert chunks[1] == (datetime(2024, 1, 16), datetime(2024, 1, 30))
    assert chunks[2] == (datetime(2024, 1, 31), datetime(2024, 1, 31))


def test_split_date_range_single_chunk():
    """Test date range that fits in single chunk."""
    client = XWeatherClient("test_key", "test_secret")

    from_dt = datetime(2024, 1, 1)
    to_dt = datetime(2024, 1, 10)

    chunks = client._split_date_range(from_dt, to_dt)

    # 10 days should fit in 1 chunk
    assert len(chunks) == 1
    assert chunks[0] == (datetime(2024, 1, 1), datetime(2024, 1, 10))


def test_split_date_range_exactly_15_days():
    """Test date range of exactly 15 days."""
    client = XWeatherClient("test_key", "test_secret")

    from_dt = datetime(2024, 1, 1)
    to_dt = datetime(2024, 1, 15)

    chunks = client._split_date_range(from_dt, to_dt)

    # 15 days should fit in 1 chunk
    assert len(chunks) == 1
    assert chunks[0] == (datetime(2024, 1, 1), datetime(2024, 1, 15))


def test_split_date_range_large():
    """Test splitting large date range."""
    client = XWeatherClient("test_key", "test_secret")

    from_dt = datetime(2024, 1, 1)
    to_dt = datetime(2024, 12, 31)

    chunks = client._split_date_range(from_dt, to_dt)

    # 366 days (leap year) should be split into 25 chunks
    assert len(chunks) == 25

    # First chunk should be 15 days
    assert chunks[0] == (datetime(2024, 1, 1), datetime(2024, 1, 15))

    # Last chunk should end on Dec 31
    assert chunks[-1][1] == datetime(2024, 12, 31)
