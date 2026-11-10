"""Tests for fetch reports and output paths."""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from tests.test_api_client import hourly_response
from xweather2epw.cli import cli


def fetch_args():
    return [
        "fetch",
        "--from",
        "2026-01-01",
        "--to",
        "2026-01-01",
        "--latitude",
        "49.48",
        "--longitude",
        "1.11",
        "--api-key",
        "test_key",
        "--api-secret",
        "test_secret",
    ]


@pytest.mark.parametrize("custom_report", [False, True])
def test_fetch_writes_report(tmp_path, custom_report):
    output = tmp_path / "weather.epw"
    report = tmp_path / ("inspection.json" if custom_report else "weather.xweather.json")
    args = fetch_args() + ["--output", str(output)]
    if custom_report:
        args += ["--response-log", str(report)]
    body = hourly_response(datetime(2026, 1, 1), datetime(2026, 1, 2))
    with patch("xweather2epw.api_client.requests.get", return_value=Mock(json=lambda: body)):
        result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    assert json.loads(report.read_text())[0]["response"] == body
    lines = output.read_text().splitlines()
    assert len(lines) == 8 + 24
    assert [line.split(",")[3] for line in lines[8:]] == [str(h) for h in range(1, 25)]
    assert str(report) in result.output


def test_fetch_rejects_same_report_and_output_path(tmp_path):
    output = str(tmp_path / "weather.epw")
    with patch("xweather2epw.api_client.requests.get") as get:
        result = CliRunner().invoke(
            cli, fetch_args() + ["--output", output, "--response-log", output]
        )
    assert result.exit_code == 1
    assert "different paths" in result.output
    get.assert_not_called()
