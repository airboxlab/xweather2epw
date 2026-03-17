"""XWeather API client."""

import logging
from datetime import datetime, timedelta
from typing import Any

import requests

from xweather2epw.logcfg import init_logging

init_logging()


class XWeatherClient:
    """Client for interacting with XWeather API."""

    BASE_URL = "https://data.api.xweather.com"
    MAX_DAYS_PER_REQUEST = 15

    def __init__(self, api_key: str, api_secret: str):
        """Initialize XWeather API client.

        :param api_key: XWeather API key (client_id)
        :param api_secret: XWeather API secret (client_secret)
        """
        self.api_key = api_key
        self.api_secret = api_secret

    def fetch_conditions(
        self, latitude: float, longitude: float, from_dt: datetime, to_dt: datetime
    ) -> dict[str, Any]:
        """Fetch weather conditions from XWeather API.

        Splits the request into chunks of max 15 days to comply with API limits.

        :param latitude: Latitude of location
        :param longitude: Longitude of location
        :param from_dt: Start datetime
        :param to_dt: End datetime
        :return: dict containing all weather data with metadata
        """
        all_periods = []
        location_info = None
        profile_info = None

        # XWeather API treats 'to' date as exclusive, so we adjust it by adding 1 day
        to_dt += timedelta(days=1)
        # Split date range into chunks
        chunks = self._split_date_range(from_dt, to_dt)

        for chunk_start, chunk_end in chunks:
            chunk_data = self._fetch_chunk(latitude, longitude, chunk_start, chunk_end)

            if chunk_data and "response" in chunk_data:
                response = chunk_data["response"]
                if isinstance(response, list) and len(response) > 0:
                    response = response[0]

                # Get location info from first chunk
                if location_info is None and isinstance(response, dict):
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
                if "periods" in response:
                    all_periods.extend(response["periods"])
                else:
                    raise ValueError("API response missing 'periods' data.")

        return {
            "place": location_info or {},
            "profile": profile_info or {},
            "periods": all_periods,
            "loc": {"lat": latitude, "long": longitude},
        }

    def _split_date_range(
        self, from_dt: datetime, to_dt: datetime
    ) -> list[tuple[datetime, datetime]]:
        """Split date range into chunks of max 15 days.

        :param from_dt: Start datetime
        :param to_dt: End datetime
        :return: List of (start, end) datetime tuples
        """
        chunks = []
        current = from_dt

        while current <= to_dt:
            chunk_end = min(current + timedelta(days=self.MAX_DAYS_PER_REQUEST - 1), to_dt)
            chunks.append((current, chunk_end))
            current = chunk_end + timedelta(days=1)

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
        logging.info(f"Fetching data with params: {params}")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        response = response.json()

        if response["success"] is False:
            raise ValueError(f"API error: {response.get('error', 'Unknown error')}")

        return response
