from datetime import datetime, timezone, timedelta

from sqlalchemy import func


def now_utc() -> datetime:
    """
    Returns current UTC time as timezone-aware datetime.

    This is the replacement for deprecated datetime.utcnow().
    All timestamps in the system should use this function.

    Returns:
        datetime: Current time in UTC with tzinfo set to timezone.utc
    """
    return datetime.now(timezone.utc)

def now_utc_func():
    """
    Returns current UTC time as timezone-aware datetime.

    This is the replacement for deprecated datetime.utcnow().
    All timestamps in the system should use this function.

    Returns:
        datetime: Current time in UTC with tzinfo set to timezone.utc
    """
    return func.now()


def ensure_utc(dt: datetime) -> datetime:
    """
    Ensures datetime is timezone-aware and in UTC.

    If datetime is naive (no tzinfo), assumes it's UTC and adds timezone info.
    If datetime has timezone info, converts to UTC.

    Args:
        dt: datetime object (naive or aware)

    Returns:
        datetime: Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_utc(dt_str: str) -> datetime:
    """
    Parses ISO-8601 datetime string and ensures UTC timezone.

    Args:
        dt_str: ISO-8601 formatted datetime string

    Returns:
        datetime: Timezone-aware datetime in UTC
    """
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    return ensure_utc(dt)


def end_of_day_utc(dt: datetime) -> datetime:
    """
    Returns end of day (23:59:59) for given datetime in UTC.

    Args:
        dt: datetime object (will be converted to UTC if needed)

    Returns:
        datetime: End of day (23:59:59) in UTC
    """
    dt_utc = ensure_utc(dt)
    return dt_utc.replace(hour=23, minute=59, second=59, microsecond=0)


def build_events_window(period_days: int) -> tuple[str, str]:
    """
    Build events window (from, to) for The Odds API requests.

    Computes:
    - from: now_utc() (current UTC time)
    - to: end_of_day_utc(now_utc() + period_days) (23:59:59Z)

    Args:
        period_days: Period in days (must be between 7 and 60)

    Returns:
        tuple[str, str]: (from_iso, to_iso) in ISO-8601 format with Z suffix

    Raises:
        ValueError: If period_days is not in valid range (7-60)
    """
    # Validate period
    if not (7 <= period_days <= 60):
        raise ValueError(
            f"period_days must be between 7 and 60, got {period_days}"
        )

    # Compute from = now_utc()
    from_dt = now_utc()

    # Compute to = end_of_day_utc(now_utc() + period_days)
    to_dt = end_of_day_utc(from_dt + timedelta(days=period_days))

    # Format as ISO-8601 with Z suffix
    from_iso = from_dt.isoformat().replace("+00:00", "Z")
    to_iso = to_dt.isoformat().replace("+00:00", "Z")

    return (from_iso, to_iso)
