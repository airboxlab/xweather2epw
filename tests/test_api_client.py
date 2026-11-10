"""Tests for API client."""

import json
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pytest
import requests

from xweather2epw.api_client import XWeatherClient
from xweather2epw.epw_writer import EPWWriter


def test_split_date_range():
    """Test date range splitting."""
    client = XWeatherClient("test_key", "test_secret")

    from_dt = datetime(2024, 1, 1)
    to_dt = datetime(2024, 2, 1)

    chunks = client._split_date_range(from_dt, to_dt)

    # 31 days should be split into 3 chunks (15 + 15 + 1)
    assert len(chunks) == 3
    assert chunks[0] == (datetime(2024, 1, 1), datetime(2024, 1, 16))
    assert chunks[1] == (datetime(2024, 1, 16), datetime(2024, 1, 31))
    assert chunks[2] == (datetime(2024, 1, 31), datetime(2024, 2, 1))


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
    to_dt = datetime(2024, 1, 16)

    chunks = client._split_date_range(from_dt, to_dt)

    # 15 days should fit in 1 chunk
    assert len(chunks) == 1
    assert chunks[0] == (datetime(2024, 1, 1), datetime(2024, 1, 16))


def test_split_date_range_large():
    """Test splitting large date range."""
    client = XWeatherClient("test_key", "test_secret")

    from_dt = datetime(2024, 1, 1)
    to_dt = datetime(2025, 1, 1)

    chunks = client._split_date_range(from_dt, to_dt)

    # 366 days (leap year) should be split into 25 chunks
    assert len(chunks) == 25

    # First chunk should be 15 days
    assert chunks[0] == (datetime(2024, 1, 1), datetime(2024, 1, 16))

    assert chunks[-1][1] == datetime(2025, 1, 1)
    assert all(left[1] == right[0] for left, right in zip(chunks, chunks[1:]))


def hourly_response(start, end, zone_name="Europe/Paris"):
    """Emulate exclusive local-date API bounds, including real DST transitions."""
    zone = ZoneInfo(zone_name)
    current = start.replace(tzinfo=zone).astimezone(timezone.utc)
    stop = end.replace(tzinfo=zone).astimezone(timezone.utc)
    periods = []
    while current < stop:
        periods.append({"dateTimeISO": current.astimezone(zone).isoformat()})
        current += timedelta(hours=1)
    return {
        "success": True,
        "response": [
            {
                "place": {"name": "Test"},
                "profile": {"tz": zone_name, "tzoffset": 3600, "elevM": 160},
                "periods": periods,
            }
        ],
    }


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (datetime(2026, 10, 1), datetime(2026, 11, 11)),
        (datetime(2026, 7, 1), datetime(2026, 7, 1)),
        (datetime(2026, 3, 29), datetime(2026, 3, 29)),
        (datetime(2026, 10, 25), datetime(2026, 10, 25)),
    ],
)
def test_fetch_complete_standard_time_range(start, end, tmp_path):
    """Fetch every standard-time hour, including chunk boundaries and DST."""
    report = tmp_path / "responses.json"
    client = XWeatherClient("test_key", "test_secret", str(report))

    def get_response(url, params, timeout):
        body = hourly_response(
            datetime.fromisoformat(params["from"]), datetime.fromisoformat(params["to"])
        )
        return Mock(json=Mock(return_value=body))

    with patch("xweather2epw.api_client.requests.get", side_effect=get_response) as get:
        result = client.fetch_conditions(49.48, 1.11, start, end)

    fixed_zone = timezone(timedelta(hours=1))
    actual = [
        datetime.fromisoformat(period["dateTimeISO"]).astimezone(fixed_zone)
        for period in result["periods"]
    ]
    expected = [
        start.replace(tzinfo=fixed_zone) + timedelta(hours=hour)
        for hour in range(((end - start).days + 1) * 24)
    ]
    assert actual == expected
    epw = tmp_path / "weather.epw"
    EPWWriter(result, 49.48, 1.11).write(str(epw))
    records = [line.split(",")[:5] for line in epw.read_text().splitlines()[8:]]
    assert records == [
        [str(dt.year), str(dt.month), str(dt.day), str(dt.hour + 1), "0"] for dt in expected
    ]
    requests_made = [call.kwargs["params"] for call in get.call_args_list]
    assert all(left["to"] == right["from"] for left, right in zip(requests_made, requests_made[1:]))
    saved = json.loads(report.read_text())
    assert len(saved) == len(requests_made)
    assert saved[0]["response"]["success"] is True
    assert "test_key" not in report.read_text()
    assert "test_secret" not in report.read_text()


def test_missing_day_is_reported():
    """Do not silently produce a successful EPW when an API day is absent."""
    body = hourly_response(datetime(2026, 10, 1), datetime(2026, 10, 17))
    body["response"][0]["periods"] = [
        p for p in body["response"][0]["periods"] if not p["dateTimeISO"].startswith("2026-10-15")
    ]
    client = XWeatherClient("test_key", "test_secret")
    with patch.object(client, "_fetch_chunk", return_value=body):
        with pytest.raises(ValueError, match=r"Missing 24 hourly periods.*2026-10-1[45]"):
            client.fetch_conditions(49.48, 1.11, datetime(2026, 10, 1), datetime(2026, 10, 15))


def test_empty_response_is_reported():
    client = XWeatherClient("test_key", "test_secret")
    with patch.object(client, "_fetch_chunk", return_value={"response": []}):
        with pytest.raises(ValueError, match="no location data"):
            client.fetch_conditions(0, 0, datetime(2026, 1, 1), datetime(2026, 1, 1))


def test_duplicate_boundary_periods_and_dictionary_response():
    body = hourly_response(datetime(2026, 1, 1), datetime(2026, 1, 2))
    location = body["response"][0]
    location["periods"].insert(1, location["periods"][0])
    body["response"] = location
    client = XWeatherClient("test_key", "test_secret")
    with patch.object(client, "_fetch_chunk", return_value=body):
        result = client.fetch_conditions(49.48, 1.11, datetime(2026, 1, 1), datetime(2026, 1, 1))
    assert len(result["periods"]) == 24


def test_error_response_is_saved_and_previous_responses_retained(tmp_path, caplog):
    report = tmp_path / "responses.json"
    client = XWeatherClient("test_key", "test_secret", str(report))
    first = hourly_response(datetime(2026, 10, 1), datetime(2026, 10, 16))
    error = {"success": False, "error": {"code": "test_error"}}
    with patch(
        "xweather2epw.api_client.requests.get",
        side_effect=[Mock(json=Mock(return_value=first)), Mock(json=Mock(return_value=error))],
    ):
        with caplog.at_level(logging.INFO):
            with pytest.raises(ValueError, match="API error"):
                client.fetch_conditions(49.48, 1.11, datetime(2026, 10, 1), datetime(2026, 11, 1))
    saved = json.loads(report.read_text())
    assert [entry["response"] for entry in saved] == [first, error]
    assert "test_key" not in caplog.text
    assert "test_secret" not in caplog.text


def test_http_error_does_not_expose_credentials(tmp_path):
    client = XWeatherClient("test_key", "test_secret", str(tmp_path / "responses.json"))
    response = Mock(
        json=Mock(return_value={"success": False}),
        raise_for_status=Mock(side_effect=requests.HTTPError("url?client_secret=test_secret")),
    )
    with patch("xweather2epw.api_client.requests.get", return_value=response):
        with pytest.raises(ValueError, match="XWeather request failed") as error:
            client.fetch_conditions(0, 0, datetime(2026, 1, 1), datetime(2026, 1, 1))
    assert "test_secret" not in str(error.value)
