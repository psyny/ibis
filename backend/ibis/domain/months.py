"""Month/date helpers."""
import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def today_in(timezone_name: str) -> date:
    try:
        tz = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("UTC")
    return datetime.now(tz).date()


def is_valid_timezone(timezone_name: str) -> bool:
    try:
        ZoneInfo(timezone_name)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


def last_day(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def clamp_day(year: int, month: int, day: int) -> date:
    """Date in (year, month) with `day` clamped to the month's length (e.g. 31 -> 28 in Feb)."""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def auto_close_date(year: int, month: int, days_after_end: int | None) -> date | None:
    """First day on which the month is auto-closed, or None when auto-close is off."""
    if days_after_end is None:
        return None
    return last_day(year, month) + timedelta(days=days_after_end + 1)
