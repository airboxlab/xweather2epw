# XWeather to EPW Converter

A tool that fetches data from the [XWeather API](https://www.xweather.com/docs/weather-api/) and generates a full year AMY (Actual Meteorological Year) EnergyPlus Weather file (EPW).

The tool takes care of fetching the necessary data from the API, processing it, and formatting it into the EPW format. It's designed for fast and efficient data retrieval.

# Installation

## Prerequisites

You need to have a XWeather API access. Note that at hourly frequency (which is used for EPW generation), each day of data costs 1 API request.

## Install the package

### PyPi

```
pip install xweather2epw
```

### From source

Clone the current repository and install the required dependencies using [Poetry](https://python-poetry.org/):

```bash
git clone https://github.com/airboxlab/xweather2epw.git
cd xweather2epw
poetry install
```

# Usage

Example usage:

```bash
# using poetry, execute in local repository
poetry run xweather2epw fetch --from '2025-01-01' --to '2025-12-31' --latitude 49.4 --longitude 0.1 --api-key YOUR_KEY --api-secret YOUR_SECRET

# specify a custom output file
poetry run xweather2epw fetch --from '2025-01-01' --to '2025-12-31' --latitude 49.4 --longitude 0.1 --api-key YOUR_KEY --api-secret YOUR_SECRET --output my_weather.epw
```

Use `--help` to have a list of available options:

```bash
poetry run xweather2epw --help
poetry run xweather2epw fetch --help
```

## Development

### Running Tests

To run the test suite:

```bash
poetry run test
```

This will execute all unit tests with verbose output.

## Features

- **Date Range Validation**: Validates input parameters (latitude, longitude, date range)
- **Smart Chunking**: Automatically splits requests into 15-day chunks to comply with API limits
- **Date Range Limits**: 
  - Maximum duration: 1 year (365 days)
  - Forecast limit: Up to 14 days in the future
- **Missing Data Handling**: Uses safe default values for missing weather data
- **Unit Conversion**: Automatically converts units to comply with EPW format (SI units)
- **EPW Header Generation**: Populates EPW headers with location information from API response
- **Solar Radiation Data**: Extracts solar radiation data from XWeather API's `solrad` field (GHI, DNI, DHI)
- **Sequential Processing**: Processes data chunks sequentially for reliability

## Limitations

- Ground/soil temperatures cannot be calculated from XWeather API data, so the `GROUND TEMPERATURES` header is set to `0`
- Some advanced EPW fields (like extraterrestrial radiation and illuminance) are not available from the XWeather conditions endpoint and are filled with missing data indicators
- Historical data availability depends on your XWeather API subscription

## Documentation

- [XWeather API Documentation](https://www.xweather.com/docs/weather-api/)
- [XWeather Conditions Endpoint](https://www.xweather.com/docs/weather-api/endpoints/conditions)
- [EPW Format Specification](https://designbuilder.co.uk/cahelp/Content/EnergyPlusWeatherFileFormat.htm)

