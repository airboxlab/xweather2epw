"""Command line interface for xweather2epw."""

import sys
from pathlib import Path

import click

from .api_client import XWeatherClient
from .epw_writer import EPWWriter
from .validator import validate_inputs


@click.group()
@click.version_option()
def cli():
    """XWeather to EPW Converter - Fetch weather data and generate EPW files."""
    pass


@cli.command()
@click.option(
    "--from",
    "from_date",
    required=True,
    type=str,
    help="Start date in ISO format (YYYY-MM-DD)",
)
@click.option(
    "--to",
    "to_date",
    required=True,
    type=str,
    help="End date in ISO format (YYYY-MM-DD, inclusive)",
)
@click.option(
    "--latitude",
    required=True,
    type=float,
    help="Latitude of the location (-90 to 90)",
)
@click.option(
    "--longitude",
    required=True,
    type=float,
    help="Longitude of the location (-180 to 180)",
)
@click.option(
    "--api-key",
    required=True,
    type=str,
    help="XWeather API key",
)
@click.option(
    "--api-secret",
    required=True,
    type=str,
    help="XWeather API secret",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output EPW file path (default: weather_<lat>_<lon>.epw)",
)
@click.option(
    "--response-log",
    type=click.Path(dir_okay=False),
    default=None,
    help="Raw API JSON report path (default: <output stem>.xweather.json)",
)
def fetch(from_date, to_date, latitude, longitude, api_key, api_secret, output, response_log):
    """Fetch weather data from XWeather API and generate an EPW file."""
    try:
        # Validate inputs
        from_dt, to_dt = validate_inputs(from_date, to_date, latitude, longitude)

        # Set default output filename
        if output is None:
            output = f"weather_{latitude}_{longitude}.epw"
        if response_log is None:
            response_log = str(Path(output).with_suffix(".xweather.json"))
        if Path(response_log).resolve() == Path(output).resolve():
            raise ValueError("Response log and EPW output must use different paths.")

        click.echo(f"Fetching weather data for ({latitude}, {longitude})")
        click.echo(f"Date range: {from_date} to {to_date}")

        # Create API client
        client = XWeatherClient(api_key, api_secret, response_log=response_log)

        # Fetch weather data
        click.echo("Fetching data from XWeather API...")
        click.echo(f"Saving API responses to {response_log}")
        weather_data = client.fetch_conditions(latitude, longitude, from_dt, to_dt)

        if not weather_data:
            click.echo("Error: No weather data received from API", err=True)
            sys.exit(1)

        # Write EPW file
        click.echo(f"Writing EPW file to {output}...")
        writer = EPWWriter(weather_data, latitude, longitude)
        writer.write(output)

        click.echo(f"Successfully generated EPW file: {output}")

    except ValueError as e:
        click.echo(f"Validation error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
