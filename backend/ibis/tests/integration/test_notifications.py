from datetime import timedelta

from domain.months import today_in
from tests.integration.test_household_flow import _cost, _setup_household


def _bar(client, headers):
    response = client.get("/api/notifications/bar", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _box(client, headers, box="inbox"):
    response = client.get(f"/api/notifications?box={box}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _close(client, hid, headers, day, action="close"):
    response = client.post(f"/api/households/{hid}/months/{day.year}/{day.month}/{action}", headers=headers)
    assert response.status_code == 200, response.text


def test_closing_a_month_sends_payment_tasks(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia, rui, gil = (people[p]["headers"] for p in ("mia", "rui", "gil"))
    # Mia paid 90 for Mia, Rui and Gil -> Rui and Gil each pay Mia 30
    client.post(f"/api/households/{hid}/costs", json=_cost(people, "mia", ["mia", "rui", "gil"], 90), headers=mia)
    today = today_in("UTC")
    _close(client, hid, mia, today)

    assert _box(client, mia) == []  # Mia receives, nothing to do
    [task] = _box(client, rui)
    assert task["type"] == "task" and task["kind"] == "month_payment"
    assert task["data"]["to_member_id"] == people["mia"]["member"]["id"]
    assert task["data"]["amount"] == 30 and (task["data"]["year"], task["data"]["month"]) == (today.year, today.month)
    assert _bar(client, rui) == {"items": [task], "unviewed_count": 1}

    # Viewing a task keeps it in the bar until it is completed
    assert client.post(f"/api/notifications/{task['id']}/view", headers=rui).json()["viewed_at"] is not None
    bar = _bar(client, rui)
    assert len(bar["items"]) == 1 and bar["unviewed_count"] == 0

    assert client.post(f"/api/notifications/{task['id']}/complete", headers=rui).status_code == 200
    assert _bar(client, rui)["items"] == []
    assert _box(client, rui) == []
    assert [n["id"] for n in _box(client, rui, "completed")] == [task["id"]]

    # Other users can't touch it
    assert client.post(f"/api/notifications/{task['id']}/delete", headers=gil).status_code == 404

    # Deleting moves it to the Deleted tab; restore brings it back
    assert client.post(f"/api/notifications/{task['id']}/delete", headers=rui).status_code == 200
    assert _box(client, rui, "completed") == [] and len(_box(client, rui, "deleted")) == 1
    assert client.post(f"/api/notifications/{task['id']}/restore", headers=rui).status_code == 200
    assert len(_box(client, rui, "completed")) == 1


def test_reopen_and_close_again_replaces_pending_tasks(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia, rui, gil = (people[p]["headers"] for p in ("mia", "rui", "gil"))
    client.post(f"/api/households/{hid}/costs", json=_cost(people, "mia", ["mia", "rui", "gil"], 90), headers=mia)
    today = today_in("UTC")
    _close(client, hid, mia, today)
    [gil_task] = _box(client, gil)
    client.post(f"/api/notifications/{gil_task['id']}/complete", headers=gil)

    _close(client, hid, mia, today, "reopen")
    assert _box(client, rui) == []  # pending task gone while the month is open again
    client.post(f"/api/households/{hid}/costs", json=_cost(people, "mia", ["rui"], 10), headers=mia)
    _close(client, hid, mia, today)

    [rui_task] = _box(client, rui)
    assert rui_task["data"]["amount"] == 40
    # Gil had already completed the task: it is kept, and a new one arrives
    assert len(_box(client, gil, "completed")) == 1
    assert len(_box(client, gil)) == 1


def test_auto_close_sends_payment_tasks(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia, rui = people["mia"]["headers"], people["rui"]["headers"]
    old = today_in("UTC").replace(day=1) - timedelta(days=40)
    client.post(f"/api/households/{hid}/months", json={"year": old.year, "month": old.month}, headers=mia)
    body = _cost(people, "mia", ["rui"], 25, day=old)
    assert client.post(f"/api/households/{hid}/costs", json=body, headers=mia).status_code == 201

    assert client.put(f"/api/households/{hid}", json={"auto_close_days": 3}, headers=mia).status_code == 200
    client.get(f"/api/households/{hid}/months", headers=mia)  # triggers auto-close
    [task] = _box(client, rui)
    assert task["data"]["amount"] == 25 and task["data"]["month"] == old.month


def test_notes_leave_the_bar_once_viewed(client, admin, login):
    from db.session import SessionLocal
    from models.notification import Notification
    from models.user import User
    from sqlalchemy import select

    hid, people = _setup_household(client, admin, login)
    rui = people["rui"]["headers"]
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.login_name == "rui"))
        db.add(Notification(user_id=user.id, type="note", kind="text", title="Hello", data={}))
        db.commit()
    finally:
        db.close()

    [note] = _bar(client, rui)["items"]
    assert client.post(f"/api/notifications/{note['id']}/complete", headers=rui).status_code == 422
    client.post(f"/api/notifications/{note['id']}/view", headers=rui)
    assert _bar(client, rui)["items"] == []
    assert [n["id"] for n in _box(client, rui)] == [note["id"]]  # still in the inbox
