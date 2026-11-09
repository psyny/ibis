from datetime import date

from domain.tasks import latest_occurrence, next_occurrence, task_status

TODAY = date(2026, 11, 8)


def test_status_colors():
    assert task_status(None, True, TODAY, 3) == "completed"
    assert task_status(date(2026, 11, 7), False, TODAY, 3) == "overdue"
    assert task_status(TODAY, False, TODAY, 3) == "expiring"
    assert task_status(date(2026, 11, 11), False, TODAY, 3) == "expiring"
    assert task_status(date(2026, 11, 12), False, TODAY, 3) == "pending"
    assert task_status(date(2026, 11, 9), False, TODAY, 0) == "pending"
    assert task_status(None, False, TODAY, 3) == "pending"


def test_weekly_and_daily_schedules():
    start = date(2026, 11, 2)
    assert latest_occurrence(start, 1, "week", date(2026, 11, 1)) is None
    assert latest_occurrence(start, 1, "week", start) == start
    assert latest_occurrence(start, 1, "week", date(2026, 11, 15)) == date(2026, 11, 9)
    assert latest_occurrence(start, 2, "week", date(2026, 11, 15)) == date(2026, 11, 2)
    assert latest_occurrence(start, 3, "day", date(2026, 11, 7)) == date(2026, 11, 5)
    assert next_occurrence(start, 1, "week", date(2026, 11, 9)) == date(2026, 11, 16)
    assert next_occurrence(start, 1, "week", date(2026, 10, 1)) == start


def test_monthly_schedule_keeps_the_day_and_clamps():
    start = date(2026, 1, 31)
    assert latest_occurrence(start, 1, "month", date(2026, 2, 27)) == date(2026, 1, 31)
    assert latest_occurrence(start, 1, "month", date(2026, 2, 28)) == date(2026, 2, 28)
    assert latest_occurrence(start, 1, "month", date(2026, 3, 30)) == date(2026, 2, 28)
    assert latest_occurrence(start, 1, "month", date(2026, 3, 31)) == date(2026, 3, 31)
    assert latest_occurrence(start, 3, "month", date(2026, 6, 1)) == date(2026, 4, 30)
    assert next_occurrence(start, 1, "month", date(2026, 2, 28)) == date(2026, 3, 31)
    assert next_occurrence(start, 12, "month", date(2026, 2, 1)) == date(2027, 1, 31)
