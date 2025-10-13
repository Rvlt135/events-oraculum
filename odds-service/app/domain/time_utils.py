from datetime import datetime, timezone

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
