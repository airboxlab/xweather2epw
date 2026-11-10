"""Time handling shared by API collection and EPW output."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo


def standard_timezone(profile: dict[str, Any], reference: datetime | None) -> timezone:
    """Resolve the location's fixed standard-time offset, excluding DST."""
    zone_name = profile.get("tz")
    if isinstance(zone_name, str):
        zone = ZoneInfo(zone_name)
        local = (
            reference.astimezone(zone)
            if reference is not None and reference.tzinfo is not None
            else (reference or datetime.now()).replace(tzinfo=zone)
        )
        return timezone(local.utcoffset() - local.dst())

    if profile.get("isDST"):
        raise ValueError("API profile must include an IANA timezone to remove DST.")

    offset = profile.get("tzoffset")
    if isinstance(offset, (int, float)):
        return timezone(timedelta(seconds=offset))

    logging.warning("No timezone profile available; using the first period's fixed UTC offset.")
    if reference is not None and reference.utcoffset() is not None:
        return timezone(reference.utcoffset())
    return timezone.utc
