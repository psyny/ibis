from datetime import timedelta

import pytest

import services.task_service as task_service
from domain.months import today_in
from tests.conftest import run_housekeeping
from tests.integration.test_household_flow import _setup_household

TODAY = today_in("UTC")


def _task(people, title="Clean kitchen", assignees=(), due=None, **extra):
    return {
        "title": title,
        "due_date": due.isoformat() if due else None,
        "assignee_ids": [people[p]["member"]["id"] for p in assignees],
        **extra,
    }


def _create(client, hid, headers, body, status=201):
    response = client.post(f"/api/households/{hid}/tasks", json=body, headers=headers)
    assert response.status_code == status, response.text
    return response.json()


def _list(client, hid, headers, query=""):
    response = client.get(f"/api/households/{hid}/tasks{query}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _notes(client, headers):
    return client.get("/api/notifications", headers=headers).json()


def _labels(client, hid, headers):
    """{(kind, name): id} of the household's task categories and locations."""
    response = client.get(f"/api/households/{hid}/task-labels", headers=headers)
    assert response.status_code == 200, response.text
    return {(label["kind"], label["name"]): label["id"] for label in response.json()}


def _days_later(monkeypatch, days):
    """Pretend today is `days` from now (for recurring tasks and due-date notes)."""
    monkeypatch.setattr(task_service, "today_in", lambda _tz: TODAY + timedelta(days=days))


@pytest.fixture()
def home(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    return hid, people, {name: p["headers"] for name, p in people.items()}


def test_who_can_add_edit_delete(client, home):
    hid, people, h = home
    _create(client, hid, h["val"], _task(people), status=403)  # viewer
    _create(client, hid, h["gil"], _task(people), status=403)  # guest
    labels = _labels(client, hid, h["rui"])
    repair, kitchen = labels[("category", "Repair")], labels[("location", "Kitchen")]
    mine = _create(client, hid, h["rui"], _task(people, "By Rui", category_id=repair, location_id=kitchen))
    managers = _create(client, hid, h["mia"], _task(people, "By Mia"))
    assert mine["can_edit"] and mine["can_delete"] and mine["created_by_name"] == "Rui"
    assert (mine["category_name"], mine["location_name"]) == ("Repair", "Kitchen") and managers["category_id"] is None
    _create(client, hid, h["rui"], _task(people, category_id=kitchen), status=422)  # a location is not a category

    # Residents edit/delete only their own; managers any
    def put(task_id, who):
        return client.put(f"/api/households/{hid}/tasks/{task_id}", json=_task(people, "x"), headers=h[who])

    assert put(managers["id"], "rui").status_code == 403
    assert put(mine["id"], "rui").status_code == 200
    assert client.delete(f"/api/households/{hid}/tasks/{managers['id']}", headers=h["rui"]).status_code == 403
    assert client.delete(f"/api/households/{hid}/tasks/{mine['id']}", headers=h["mia"]).status_code == 204

    # Viewers can't be assigned
    _create(client, hid, h["mia"], _task(people, assignees=["val"]), status=422)


def test_guests_see_and_complete_only_their_tasks(client, home):
    hid, people, h = home
    theirs = _create(client, hid, h["mia"], _task(people, "For Gil", assignees=["gil", "rui"]))
    other = _create(client, hid, h["mia"], _task(people, "For Rui", assignees=["rui"]))

    assert [t["id"] for t in _list(client, hid, h["gil"])] == [theirs["id"]]
    assert len(_list(client, hid, h["val"])) == 2  # viewers see everything
    assert client.get(f"/api/households/{hid}/tasks/{other['id']}", headers=h["gil"]).status_code == 404

    def complete(task_id, who):
        return client.post(f"/api/households/{hid}/tasks/{task_id}/complete", headers=h[who])

    assert complete(other["id"], "val").status_code == 403
    done = complete(theirs["id"], "gil").json()
    assert done["status"] == "completed" and done["completed_by_name"] == "Gil"
    assert complete(other["id"], "rui").status_code == 200  # residents complete any task
    assert _list(client, hid, h["mia"]) == []  # completed are hidden by default
    assert len(_list(client, hid, h["mia"], "?include_completed=true")) == 2
    undone = client.post(f"/api/households/{hid}/tasks/{theirs['id']}/uncomplete", headers=h["gil"]).json()
    assert undone["completed_at"] is None


def test_order_status_and_filters(client, home):
    hid, people, h = home
    later = _create(client, hid, h["mia"], _task(people, "Later", due=TODAY + timedelta(days=10), assignees=["rui"]))
    soon = _create(client, hid, h["mia"], _task(people, "Soon", due=TODAY + timedelta(days=3), assignees=["mia"]))
    late = _create(client, hid, h["mia"], _task(people, "Late", due=TODAY - timedelta(days=1)))
    undated = _create(client, hid, h["mia"], _task(people, "Whenever"))
    wide = _create(client, hid, h["mia"], _task(people, "Wide", due=TODAY + timedelta(days=10), warn_days=14))

    tasks = _list(client, hid, h["mia"])
    assert [t["title"] for t in tasks] == ["Late", "Soon", "Later", "Wide", "Whenever"]
    status = {t["title"]: t["status"] for t in tasks}
    assert status == {"Late": "overdue", "Soon": "expiring", "Later": "pending", "Wide": "expiring", "Whenever": "pending"}

    rui_id = people["rui"]["member"]["id"]
    assert [t["id"] for t in _list(client, hid, h["mia"], f"?assignee_id={rui_id}")] == [later["id"]]
    month = f"{TODAY.year:04d}-{TODAY.month:02d}"
    in_month = {t["id"] for t in _list(client, hid, h["mia"], f"?due_month={month}")}
    expected = {t["id"] for t in (later, soon, late, wide) if t["due_date"].startswith(month)}
    assert in_month == expected and undated["id"] not in in_month


def test_due_date_notifications(client, home, monkeypatch):
    hid, people, h = home
    # Off by default: nothing is sent
    _create(client, hid, h["mia"], _task(people, "Quiet", due=TODAY + timedelta(days=1), assignees=["rui"]))
    assert _notes(client, h["rui"]) == []

    body = _task(
        people, "Soon", due=TODAY + timedelta(days=5), assignees=["rui", "gil"], notify_expiring=True, notify_expired=True
    )
    soon = _create(client, hid, h["mia"], body)
    assert _notes(client, h["rui"]) == []  # not in its 3-day window yet

    _days_later(monkeypatch, 2)
    run_housekeeping()  # the scheduler runs the checks
    [note] = _notes(client, h["rui"])
    assert note["kind"] == "task_expiring" and note["task_id"] == soon["id"]
    assert len(_notes(client, h["gil"])) == 1
    run_housekeeping()
    assert len(_notes(client, h["rui"])) == 1  # sent once

    _days_later(monkeypatch, 6)
    run_housekeeping()
    assert [n["kind"] for n in _notes(client, h["rui"])] == ["task_expired", "task_expiring"]

    # Completed tasks never notify
    body = _task(people, "Done", due=TODAY + timedelta(days=7), assignees=["rui"], notify_expired=True)
    done = _create(client, hid, h["mia"], body)
    client.post(f"/api/households/{hid}/tasks/{done['id']}/complete", headers=h["rui"])
    _days_later(monkeypatch, 30)
    run_housekeeping()
    assert all(n["task_id"] != done["id"] for n in _notes(client, h["rui"]))


def _recurring(people, **extra):
    body = {
        "title": "Take out trash",
        "start_date": TODAY.isoformat(),
        "interval": 1,
        "unit": "week",
        "assign_mode": "selected",
        "assignee_ids": [people["rui"]["member"]["id"]],
    }
    body.update(extra)
    return body


def _create_recurring(client, hid, headers, body, status=201):
    response = client.post(f"/api/households/{hid}/recurring-tasks", json=body, headers=headers)
    assert response.status_code == status, response.text
    return response.json()


def test_recurring_permissions(client, home):
    hid, people, h = home
    for who in ("gil", "val"):
        _create_recurring(client, hid, h[who], _recurring(people), status=403)
        assert client.get(f"/api/households/{hid}/recurring-tasks", headers=h[who]).status_code == 403
    item = _create_recurring(client, hid, h["rui"], _recurring(people))
    assert item["next_date"] == (TODAY + timedelta(days=7)).isoformat()
    assert client.get(f"/api/households/{hid}/recurring-tasks", headers=h["mia"]).json()[0]["id"] == item["id"]


def test_recurring_creates_copies_and_waits_for_previous(client, home, monkeypatch):
    hid, people, h = home
    cleaning = _labels(client, hid, h["mia"])[("category", "Cleaning")]
    item = _create_recurring(client, hid, h["mia"], _recurring(people, due_offset_days=2, category_id=cleaning))
    [first] = _list(client, hid, h["mia"])  # starts today: the first copy is created right away
    assert first["recurring_task_id"] == item["id"] and first["kind"] == "recurring"
    assert item["category_id"] == cleaning and first["category_name"] == "Cleaning"
    assert first["due_date"] == (TODAY + timedelta(days=2)).isoformat()
    assert first["assignee_ids"] == [people["rui"]["member"]["id"]]

    # A week later the first copy is still open: that date is skipped
    _days_later(monkeypatch, 7)
    run_housekeeping()
    assert len(_list(client, hid, h["mia"])) == 1

    # Once it's done, the next scheduled date creates a new one (only one, even after several weeks)
    client.post(f"/api/households/{hid}/tasks/{first['id']}/complete", headers=h["rui"])
    _days_later(monkeypatch, 30)
    run_housekeeping()
    run_housekeeping()
    [second] = _list(client, hid, h["mia"])
    assert second["due_date"] == (TODAY + timedelta(days=28 + 2)).isoformat()


def test_recurring_without_waiting_and_everyone(client, home, monkeypatch):
    hid, people, h = home
    daily = dict(unit="day", wait_for_previous=False)
    _create_recurring(client, hid, h["mia"], _recurring(people, **daily, assign_mode="everyone", assignee_ids=[]))
    _create_recurring(client, hid, h["mia"], _recurring(people, **daily, title="Guests too", assign_mode="everyone_guests"))
    # A new resident joins: "everyone" is resolved when each copy is created
    response = client.post(
        f"/api/households/{hid}/members",
        json={"login_name": "ana", "display_name": "Ana", "password": "pass1234", "role": "resident"},
        headers=h["mia"],
    )
    ana = response.json()["id"]
    _days_later(monkeypatch, 1)
    run_housekeeping()

    tasks = _list(client, hid, h["mia"])
    trash = [t for t in tasks if t["title"] == "Take out trash"]
    guests = [t for t in tasks if t["title"] == "Guests too"]
    assert len(trash) == 2 and len(guests) == 2  # yesterday's copy is still open, a new one came anyway

    def ids(*names):
        return {people[n]["member"]["id"] for n in names}

    assert set(trash[0]["assignee_ids"]) == ids("mia", "rui")
    assert set(trash[1]["assignee_ids"]) == ids("mia", "rui") | {ana}
    assert set(guests[1]["assignee_ids"]) == ids("mia", "rui", "gil") | {ana}
    assert [t["title"] for t in _list(client, hid, h["gil"])] == ["Guests too", "Guests too"]


def test_editing_the_schedule_does_not_backfill(client, home):
    hid, people, h = home
    item = _create_recurring(client, hid, h["mia"], _recurring(people, start_date=(TODAY + timedelta(days=3)).isoformat()))
    assert _list(client, hid, h["mia"]) == []
    body = _recurring(people, start_date=(TODAY - timedelta(days=3)).isoformat(), unit="month")
    assert client.put(f"/api/households/{hid}/recurring-tasks/{item['id']}", json=body, headers=h["mia"]).status_code == 200
    assert _list(client, hid, h["mia"]) == []  # the past date is not created after an edit

    # Deleting a definition keeps the tasks it already created
    now = _create_recurring(client, hid, h["mia"], _recurring(people, title="Now"))
    [copy] = _list(client, hid, h["mia"])
    assert client.delete(f"/api/households/{hid}/recurring-tasks/{now['id']}", headers=h["rui"]).status_code == 204
    assert [t["id"] for t in _list(client, hid, h["mia"])] == [copy["id"]]


def test_households_start_with_default_lists(client, admin, home):
    hid, people, h = home
    labels = _labels(client, hid, h["val"])  # everyone can read them
    assert ("location", "Garden") in labels and ("category", "Garden") not in labels
    assert ("category", "Bills") in labels and ("location", "Living room") in labels
    # A new household gets them in its language
    other = client.post("/api/admin/households", json={"name": "Casa", "language": "pt-BR"}, headers=admin).json()
    assert ("location", "Cozinha") in _labels(client, other["id"], admin)


def test_managers_edit_the_lists(client, home):
    hid, people, h = home
    url = f"/api/households/{hid}/task-labels"
    assert client.post(url, json={"kind": "location", "name": "Attic"}, headers=h["rui"]).status_code == 403
    attic = client.post(url, json={"kind": "location", "name": "Attic"}, headers=h["mia"]).json()
    assert client.post(url, json={"kind": "location", "name": "attic"}, headers=h["mia"]).status_code == 409
    renamed = client.put(f"{url}/{attic['id']}", json={"name": "Loft"}, headers=h["mia"]).json()
    assert renamed["name"] == "Loft" and list(_labels(client, hid, h["mia"]))[-1] == ("location", "Loft")

    # Deleting one clears it from tasks; the task stays
    task = _create(client, hid, h["mia"], _task(people, "Fix roof", location_id=attic["id"]))
    assert client.delete(f"{url}/{attic['id']}", headers=h["mia"]).status_code == 204
    again = client.get(f"/api/households/{hid}/tasks/{task['id']}", headers=h["mia"]).json()
    assert again["location_id"] is None and again["title"] == "Fix roof"


def test_filter_by_category_and_location(client, home):
    hid, people, h = home
    labels = _labels(client, hid, h["mia"])
    cleaning, repair = labels[("category", "Cleaning")], labels[("category", "Repair")]
    kitchen, garden = labels[("location", "Kitchen")], labels[("location", "Garden")]
    a = _create(client, hid, h["mia"], _task(people, "A", category_id=cleaning, location_id=kitchen))
    b = _create(client, hid, h["mia"], _task(people, "B", category_id=repair, location_id=kitchen))
    _create(client, hid, h["mia"], _task(people, "C", category_id=cleaning, location_id=garden))

    def titles(query):
        return [t["title"] for t in _list(client, hid, h["mia"], query)]

    assert titles(f"?category_id={cleaning}") == ["A", "C"]
    assert titles(f"?location_id={kitchen}") == ["A", "B"]
    assert titles(f"?category_id={cleaning}&location_id={kitchen}") == [a["title"]]
    assert b["category_name"] == "Repair"
