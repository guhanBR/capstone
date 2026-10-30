from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Indian Standard Time (IST, UTC+05:30)
IST = ZoneInfo("Asia/Kolkata")


def to_ist(dt):
    """
    Safely converts a datetime object to Asia/Kolkata (IST, UTC+05:30).
    - If dt is None, returns None.
    - If dt is a string (e.g. ISO format), parses it first.
    - If dt is naive, assumes UTC (the application's storage standard) and converts to IST.
    - If dt is already timezone-aware, converts directly to IST.
      If it is already in IST, it remains in IST without double-converting.
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def format_ist(dt, fmt='%Y-%m-%d %H:%M'):
    """
    Converts a datetime to IST and formats it with strftime.
    Returns '—' if dt is None.
    """
    if dt is None:
        return '—'
    dt_ist = to_ist(dt)
    if dt_ist is None:
        return '—'
    return dt_ist.strftime(fmt)


def now_utc():
    """Returns current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def now_ist():
    """Returns current IST datetime (timezone-aware)."""
    return datetime.now(IST)
