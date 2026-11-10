"""The scheduler (time-based work) and the household's month-close payment task settings."""
import asyncio
from datetime import timedelta

from domain.months import today_in
from scheduler import Job, Scheduler
from scheduler.runner import find_job, run_job
from tests.conftest import run_housekeeping
from tests.integration.test_household_flow import _cost, _setup_household
from tests.integration.test_notifications import _box, _close, _tasks
from tests.integration.test_tasks import TODAY, _create, _days_later, _task

ALL_ON = {
    "notify_expiring": True,
    "notify_expired": True,
    "notify_expiring_whatsapp": True,
    "notify_expiring_email": True,
    "notify_expiring_groups": True,
    "notify_expired_whatsapp": True,
    "notify_expired_email": True,
    "notify_expired_groups": True,
}


def test_jobs_are_registered():
    assert find_job("housekeeping").run_at_start is True
    assert find_job("deliver_messages").enabled() is False  # no WhatsApp service in tests
    assert find_job("nope") is None


def test_scheduler_runs_jobs_on_their_interval():
    runs: list[str] = []
    fast = Job(name="fast", run=lambda _db: runs.append("fast"), interval_seconds=lambda: 0.01, run_at_start=True)
    off = Job(name="off", run=lambda _db: runs.append("off"), interval_seconds=lambda: 0.01, enabled=lambda: False)

    def boom(_db):
        raise RuntimeError("job failed")

    failing = Job(name="failing", run=boom, interval_seconds=lambda: 0.01, run_at_start=True)

    async def scenario():
        scheduler = Scheduler([fast, off, failing])
        scheduler.start()
        await asyncio.sleep(0.2)
        await scheduler.stop()

    asyncio.run(scenario())
    assert runs.count("fast") >= 2  # kept running, even though another job keeps failing
    assert "off" not in runs
    assert run_job(fast) is True


def test_opening_the_household_no_longer_runs_time_based_work(client, admin, login, monkeypatch):
    hid, people = _setup_household(client, admin, login)
    mia, rui = people["mia"]["headers"], people["rui"]["headers"]
    _create(client, hid, mia, _task(people, "Later", due=TODAY + timedelta(days=5), assignees=["rui"], notify_expiring=True))
    _days_later(monkeypatch, 3)
    client.get(f"/api/households/{hid}", headers=rui)
    assert _box(client, rui) == []  # opening the household doesn't send it...
    run_housekeeping()
    assert [n["kind"] for n in _box(client, rui)] == ["task_expiring"]  # ...the scheduler does


def _close_with_debt(client, hid, people, settings=None):
    """Mia paid 90 for everyone, so Rui and Gil each owe Mia 30. Closes the current month."""
    mia = people["mia"]["headers"]
    if settings is not None:
        response = client.put(f"/api/households/{hid}", json={"payment_task": settings}, headers=mia)
        assert response.status_code == 200, response.text
    client.post(f"/api/households/{hid}/costs", json=_cost(people, "mia", ["mia", "rui", "gil"], 90), headers=mia)
    _close(client, hid, mia, today_in("UTC"))


def test_payment_task_settings_defaults(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    settings = client.get(f"/api/households/{hid}", headers=people["mia"]["headers"]).json()["payment_task"]
    assert settings == {"enabled": True, "due_days": 3, "warn_days": 3, **{flag: False for flag in ALL_ON}}
    bad = client.put(f"/api/households/{hid}", json={"payment_task": {"due_days": -1}}, headers=people["mia"]["headers"])
    assert bad.status_code == 422
    assert client.put(f"/api/households/{hid}", json={"payment_task": {}}, headers=people["rui"]["headers"]).status_code == 403


def test_payment_tasks_can_be_turned_off(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    _close_with_debt(client, hid, people, {"enabled": False})
    assert _tasks(client, hid, people["mia"]["headers"]) == []
    assert _box(client, people["rui"]["headers"]) == []


def test_payment_task_uses_the_household_settings(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    rui = people["rui"]["headers"]
    _close_with_debt(client, hid, people, {"enabled": True, "due_days": 10, "warn_days": 2, **ALL_ON})
    [task] = _tasks(client, hid, rui, f"?assignee_id={people['rui']['member']['id']}")
    assert task["due_date"] == (today_in("UTC") + timedelta(days=10)).isoformat()  # counted from the close
    assert task["warn_days"] == 2 and task["status"] == "pending"
    assert all(task[flag] for flag in ALL_ON)
    assert [n["kind"] for n in _box(client, rui)] == ["month_payment"]  # not expiring yet: only the close note


def test_payment_task_already_expiring_notifies_right_away(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    rui = people["rui"]["headers"]
    # Defaults: due in 3 days, yellow 3 days before -> it starts inside its warning window
    _close_with_debt(client, hid, people, {"notify_expiring": True})
    assert sorted(n["kind"] for n in _box(client, rui)) == ["month_payment", "task_expiring"]
    run_housekeeping()
    assert len(_box(client, rui)) == 2  # not sent twice
