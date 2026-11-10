"""XWeather API client."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from xweather2epw.logcfg import init_logging
from xweather2epw.time_utils import standard_timezone

init_logging()


class XWeatherClient:
    """Client for interacting with XWeather API."""

    BASE_URL = "https://data.api.xweather.com"
    MAX_DAYS_PER_REQUEST = 15

    def __init__(self, api_key: str, api_secret: str, response_log: str | None = None):
        """Initialize XWeather API client.

        :param api_key: XWeather API key (client_id)
        :param api_secret: XWeather API secret (client_secret)
        :param response_log: JSON file for raw responses and credential-free request
            metadata
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.response_log = Path(response_log) if response_log is not None else None
        self.responses = []

    def fetch_conditions(
        self, latitude: float, longitude: float, from_dt: datetime, to_dt: datetime
    ) -> dict[str, Any]:
        """Fetch weather conditions from XWeather API.

        Splits the request into chunks of max 15 days to comply with API limits.

        :param latitude: Latitude of location
        :param longitude: Longitude of location
        :param from_dt: Inclusive start date in local standard time
        :param to_dt: Inclusive end date in local standard time
        :return: dict containing all weather data with metadata
        """
        all_periods = []
        location_info = None
        profile_info = None
        self.responses = []
        self._write_response_log()

        # Public dates are inclusive; API chunks use exclusive end dates.
        end_exclusive = to_dt + timedelta(days=1)
        # Split date range into chunks
        chunks = self._split_date_range(from_dt, end_exclusive)

        for chunk_start, chunk_end in chunks:
            chunk_data = self._fetch_chunk(latitude, longitude, chunk_start, chunk_end)

            response = chunk_data.get("response")
            responses = response if isinstance(response, list) else [response]
            if not responses:
                raise ValueError("API response contains no location data.")

            for response in responses:
                if not isinstance(response, dict):
                    raise ValueError("API response contains invalid location data.")
                # Get location info from first chunk
                if location_info is None:
                    if "place" in response:
                        location_info = response["place"]
                    if "profile" in response:
                        profile_info = response["profile"]
                    elif "loc" in response:
                        # Fallback to basic location data
                        logging.warning("Using fallback location info from 'loc' field.")
                        location_info = {
                            "name": "Unknown",
                            "lat": response["loc"].get("lat", latitude),
                            "long": response["loc"].get("long", longitude),
                        }

                # Collect periods
                if isinstance(response.get("periods"), list):
                    all_periods.extend(response["periods"])
                else:
                    raise ValueError("API response missing 'periods' data.")

        if not all_periods:
            raise ValueError("API response contains no weather periods.")

        zone = standard_timezone(
            profile_info or {}, datetime.fromisoformat(all_periods[0]["dateTimeISO"])
        )
        start = from_dt.replace(tzinfo=zone)
        end = end_exclusive.replace(tzinfo=zone)
        # Summer local midnight precedes standard midnight. The exclusive API
        # end therefore needs one more local day to cover the last standard hour.
        last_local = (end - timedelta(hours=1)).astimezone(
            datetime.fromisoformat(all_periods[-1]["dateTimeISO"]).tzinfo
        )
        if last_local.replace(tzinfo=None) >= end_exclusive:
            extra_data = self._fetch_chunk(
                latitude, longitude, end_exclusive, end_exclusive + timedelta(days=1)
            )
            extra_responses = extra_data.get("response")
            if not isinstance(extra_responses, list):
                extra_responses = [extra_responses]
            if not extra_responses:
                raise ValueError("API response contains no location data.")
            for response in extra_responses:
                if not isinstance(response, dict) or not isinstance(response.get("periods"), list):
                    raise ValueError("API response missing 'periods' data.")
                all_periods.extend(response["periods"])

        periods_by_time = {}
        for period in all_periods:
            dt = datetime.fromisoformat(period["dateTimeISO"])
            if dt.tzinfo is None:
                raise ValueError("API dateTimeISO must include a UTC offset.")
            dt = dt.astimezone(zone)
            if start <= dt < end:
                periods_by_time.setdefault(dt, period)

        missing = []
        current = start
        while current < end:
            if current not in periods_by_time:
                missing.append(current)
            current += timedelta(hours=1)
        if missing:
            dates = ", ".join(sorted({dt.date().isoformat() for dt in missing}))
            raise ValueError(
                f"Missing {len(missing)} hourly periods in local standard time on: {dates}"
            )

        return {
            "place": location_info or {},
            "profile": profile_info or {},
            "periods": [periods_by_time[dt] for dt in sorted(periods_by_time)],
            "loc": {"lat": latitude, "long": longitude},
        }

    def _split_date_range(
        self, from_dt: datetime, to_dt: datetime
    ) -> list[tuple[datetime, datetime]]:
        """Split a half-open date range into contiguous chunks of max 15 days.

        :param from_dt: Start datetime
        :param to_dt: Exclusive end datetime
        :return: List of (start, end) datetime tuples
        """
        chunks = []
        current = from_dt

        while current < to_dt:
            chunk_end = min(current + timedelta(days=self.MAX_DAYS_PER_REQUEST), to_dt)
            chunks.append((current, chunk_end))
            current = chunk_end

        return chunks

    def _fetch_chunk(
        self, latitude: float, longitude: float, start_dt: datetime, end_dt: datetime
    ) -> dict[str, Any]:
        """Fetch a single chunk of weather data.

        :param latitude: Latitude of location
        :param longitude: Longitude of location
        :param start_dt: Start datetime
        :param end_dt: End datetime
        :return: API response dictionary
        """
        # Format location
        location = f"{latitude},{longitude}"

        # Format date range for API
        from_str = start_dt.strftime("%Y-%m-%d")
        to_str = end_dt.strftime("%Y-%m-%d")

        # Build URL
        url = f"{self.BASE_URL}/conditions/{location}"

        # Build parameters
        params = {
            "client_id": self.api_key,
            "client_secret": self.api_secret,
            "from": from_str,
            "to": to_str,
            "filter": "1hr",  # 1-hour interval data
            "format": "json",
        }

        # Make request
        logging.info("Fetching conditions for %s from %s to %s", location, from_str, to_str)
        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            self.responses.append(
                {
                    "request": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "from": from_str,
                        "to": to_str,
                        "filter": "1hr",
                    },
                    "response": data,
                }
            )
            self._write_response_log()
            response.raise_for_status()
        except requests.RequestException:
            # Requests exceptions may contain a URL with credentials.
            raise ValueError(f"XWeather request failed for {from_str} to {to_str}.") from None

        if data["success"] is False:
            raise ValueError(f"API error: {data.get('error', 'Unknown error')}")

        return data

    def _write_response_log(self):
        """Keep a valid JSON report even if a later request fails."""
        if self.response_log is not None:
            with self.response_log.open("w") as f:
                json.dump(self.responses, f, indent=2)
                f.write("\n")
