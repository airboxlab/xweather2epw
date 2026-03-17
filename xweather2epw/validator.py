"""Input validation for xweather2epw."""

from datetime import datetime, timedelta


def validate_inputs(from_date_str, to_date_str, latitude, longitude):
    """Validate command line inputs.

    :param from_date_str: Start date string in ISO format (YYYY-MM-DD)
    :param to_date_str: End date string in ISO format (YYYY-MM-DD)
    :param latitude: Latitude value (-90 to 90)
    :param longitude: Longitude value (-180 to 180)
    :return: tuple: (from_datetime, to_datetime)
    :raises: ValueError: If any validation fails
    """
    # Validate latitude
    if not -90 <= latitude <= 90:
        raise ValueError(f"Latitude must be between -90 and 90, got {latitude}")

    # Validate longitude
    if not -180 <= longitude <= 180:
        raise ValueError(f"Longitude must be between -180 and 180, got {longitude}")

    # Parse dates
    try:
        from_dt = datetime.strptime(from_date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid from date format: {from_date_str}. Use YYYY-MM-DD")

    try:
        to_dt = datetime.strptime(to_date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid to date format: {to_date_str}. Use YYYY-MM-DD")

    # Validate date range
    if from_dt > to_dt:
        raise ValueError(f"Start date {from_date_str} must be before end date {to_date_str}")

    # Calculate duration
    duration = (to_dt - from_dt).days

    # Check maximum duration (1 year = 365 days)
    if duration > 365:
        raise ValueError(f"Date range cannot exceed 365 days. Current range: {duration} days")

    # Check forecast limit (14 days from now)
    now = datetime.now()
    max_future_date = now + timedelta(days=14)

    if to_dt > max_future_date:
        raise ValueError(
            f"End date cannot be more than 14 days in the future. "
            f"Maximum allowed date: {max_future_date.strftime('%Y-%m-%d')}"
        )

    return from_dt, to_dt
