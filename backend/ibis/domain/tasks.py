"""Pure task rules: status colors and recurring schedules. No database code here."""
from datetime import date, timedelta
from typing import Literal, Optional

from domain.months import clamp_day

TaskStatus = Literal["completed", "overdue", "expiring", "pending"]
FrequencyUnit = Literal["day", "week", "month"]

DEFAULT_WARN_DAYS = 3


def task_status(due: Optional[date], completed: bool, today: date, warn_days: int) -> TaskStatus:
    """completed (green), overdue (red: past due), expiring (yellow: due within warn_days), else pending."""
    if completed:
        return "completed"
    if due is None:
        return "pending"
    if due < today:
        return "overdue"
    if (due - today).days <= warn_days:
        return "expiring"
    return "pending"


def is_expiring_window(due: date, today: date, warn_days: int) -> bool:
    return today <= due and (due - today).days <= warn_days


def _add_months(start: date, months: int) -> date:
    total = start.year * 12 + (start.month - 1) + months
    return clamp_day(total // 12, total % 12 + 1, start.day)


def occurrence(start: date, interval: int, unit: FrequencyUnit, index: int) -> date:
    """The index-th scheduled date (0 = start). Monthly dates keep start's day (31 -> last day)."""
    if unit == "month":
        return _add_months(start, interval * index)
    days = interval * (7 if unit == "week" else 1)
    return start + timedelta(days=days * index)


def _latest_index(start: date, interval: int, unit: FrequencyUnit, today: date) -> Optional[int]:
    if today < start:
        return None
    if unit == "month":
        months = (today.year - start.year) * 12 + (today.month - start.month)
        index = months // interval
        while index > 0 and occurrence(start, interval, unit, index) > today:
            index -= 1
        return index
    step = interval * (7 if unit == "week" else 1)
    return (today - start).days // step


def latest_occurrence(start: date, interval: int, unit: FrequencyUnit, today: date) -> Optional[date]:
    """The last scheduled date on or before today, or None if the schedule hasn't started."""
    index = _latest_index(start, interval, unit, today)
    return None if index is None else occurrence(start, interval, unit, index)


def next_occurrence(start: date, interval: int, unit: FrequencyUnit, after: date) -> date:
    """The first scheduled date strictly after `after` (dates only ever increase, even when clamped)."""
    index = _latest_index(start, interval, unit, after)
    return start if index is None else occurrence(start, interval, unit, index + 1)
