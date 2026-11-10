from datetime import timedelta

from domain.months import today_in
from tests.conftest import run_housekeeping
from tests.integration.test_household_flow import _cost, _setup_household


def _bar(client, headers):
    response = client.get("/api/notifications/bar", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _box(client, headers, box="inbox"):
    response = client.get(f"/api/notifications?box={box}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _tasks(client, hid, headers, query=""):
    response = client.get(f"/api/households/{hid}/tasks{query}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _close(client, hid, headers, day, action="close"):
    response = client.post(f"/api/households/{hid}/months/{day.year}/{day.month}/{action}", headers=headers)
    assert response.status_code == 200, response.text


def test_closing_a_month_creates_payment_tasks_and_notes(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia, rui, gil = (people[p]["headers"] for p in ("mia", "rui", "gil"))
    # Mia paid 90 for Mia, Rui and Gil -> Rui and Gil each pay Mia 30
    client.post(f"/api/households/{hid}/costs", json=_cost(people, "mia", ["mia", "rui", "gil"], 90), headers=mia)
    today = today_in("UTC")
    _close(client, hid, mia, today)

    assert _box(client, mia) == []  # Mia receives, nothing to do
    [note] = _box(client, rui)
    assert note["type"] == "note" and note["kind"] == "month_payment" and note["task_id"]
    assert note["data"]["amount"] == 30 and note["data"]["to_member_id"] == people["mia"]["member"]["id"]
    assert _bar(client, rui) == {"items": [note], "unviewed_count": 1}

    # The task is due in 3 days, assigned to Rui
    task = client.get(f"/api/households/{hid}/tasks/{note['task_id']}", headers=rui).json()
    assert task["kind"] == "month_payment" and task["category_name"] == "Bills" and task["assignee_ids"] == [people["rui"]["member"]["id"]]
    assert task["due_date"] == (today + timedelta(days=3)).isoformat() and task["status"] == "expiring"
    assert (task["data"]["year"], task["data"]["month"]) == (today.year, today.month)
    assert len(_tasks(client, hid, mia)) == 2  # Rui's and Gil's

    # Viewing the note takes it out of the bar; it stays in the inbox
    client.post(f"/api/notifications/{note['id']}/view", headers=rui)
    assert _bar(client, rui) == {"items": [], "unviewed_count": 0}
    assert [n["id"] for n in _box(client, rui)] == [note["id"]]

    # Completing Gil's task also marks Gil's note as read
    [gil_note] = _box(client, gil)
    assert client.post(f"/api/households/{hid}/tasks/{gil_note['task_id']}/complete", headers=gil).status_code == 200
    assert _bar(client, gil)["items"] == []

    # Other users can't touch a note
    assert client.post(f"/api/notifications/{note['id']}/delete", headers=gil).status_code == 404
    # Deleting moves it to the Deleted tab; restore brings it back
    assert client.post(f"/api/notifications/{note['id']}/delete", headers=rui).status_code == 200
    assert _box(client, rui) == [] and len(_box(client, rui, "deleted")) == 1
    assert client.post(f"/api/notifications/{note['id']}/restore", headers=rui).status_code == 200
    assert len(_box(client, rui)) == 1


def test_reopen_and_close_again_replaces_open_payment_tasks(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia, rui, gil = (people[p]["headers"] for p in ("mia", "rui", "gil"))
    client.post(f"/api/households/{hid}/costs", json=_cost(people, "mia", ["mia", "rui", "gil"], 90), headers=mia)
    today = today_in("UTC")
    _close(client, hid, mia, today)
    [gil_note] = _box(client, gil)
    client.post(f"/api/households/{hid}/tasks/{gil_note['task_id']}/complete", headers=gil)

    _close(client, hid, mia, today, "reopen")
    assert _box(client, rui) == []  # open task and its note are gone while the month is open again
    assert _tasks(client, hid, mia) == []
    client.post(f"/api/households/{hid}/costs", json=_cost(people, "mia", ["rui"], 10), headers=mia)
    _close(client, hid, mia, today)

    [rui_note] = _box(client, rui)
    assert rui_note["data"]["amount"] == 40
    # Gil had already completed the task: it is kept, and a new one arrives
    assert len(_tasks(client, hid, gil, "?include_completed=true")) == 2
    assert len(_tasks(client, hid, gil)) == 1


def test_auto_close_creates_payment_tasks(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia, rui = people["mia"]["headers"], people["rui"]["headers"]
    old = today_in("UTC").replace(day=1) - timedelta(days=40)
    client.post(f"/api/households/{hid}/months", json={"year": old.year, "month": old.month}, headers=mia)
    body = _cost(people, "mia", ["rui"], 25, day=old)
    assert client.post(f"/api/households/{hid}/costs", json=body, headers=mia).status_code == 201

    assert client.put(f"/api/households/{hid}", json={"auto_close_days": 3}, headers=mia).status_code == 200
    run_housekeeping()  # the scheduler auto-closes the month
    [note] = _box(client, rui)
    assert note["data"]["amount"] == 25 and note["data"]["month"] == old.month
    [task] = _tasks(client, hid, rui)
    assert task["id"] == note["task_id"]


def test_deleting_a_task_removes_its_notes(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia, rui = people["mia"]["headers"], people["rui"]["headers"]
    client.post(f"/api/households/{hid}/costs", json=_cost(people, "mia", ["rui"], 10), headers=mia)
    _close(client, hid, mia, today_in("UTC"))
    [note] = _box(client, rui)
    assert client.delete(f"/api/households/{hid}/tasks/{note['task_id']}", headers=mia).status_code == 204
    assert _box(client, rui) == []
