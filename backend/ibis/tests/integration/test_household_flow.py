from datetime import date, timedelta

from domain.months import next_month, today_in
from tests.conftest import ADMIN_LOGIN


def _setup_household(client, admin, login, auto_close_days=None):
    """Household with a manager, a resident, a guest and a viewer."""
    household = client.post(
        "/api/admin/households", json={"name": "Home", "currency": "BRL", "auto_close_days": auto_close_days}, headers=admin
    ).json()
    hid = household["id"]
    people = {}
    for login_name, role in [("mia", "manager"), ("rui", "resident"), ("gil", "guest"), ("val", "viewer")]:
        response = client.post(
            f"/api/households/{hid}/members",
            json={"login_name": login_name, "display_name": login_name.title(), "password": "pass1234", "role": role},
            headers=admin,
        )
        assert response.status_code == 201, response.text
        people[login_name] = {"member": response.json(), "headers": login(login_name, "pass1234")}
    return hid, people


def _cost(people, payer, coverers, amount, day=None, description="Groceries"):
    return {
        "description": description,
        "amount": amount,
        "date": (day or today_in("UTC")).isoformat(),
        "payer_ids": [people[payer]["member"]["id"]],
        "coverer_ids": [people[c]["member"]["id"] for c in coverers],
    }


def _summary(client, hid, headers, day=None):
    day = day or today_in("UTC")
    response = client.get(f"/api/households/{hid}/months/{day.year}/{day.month}/summary", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_first_login_creates_admin(client, admin):
    me = client.get("/api/auth/me", headers=admin).json()
    assert me["login_name"] == ADMIN_LOGIN and me["is_admin"] is True
    # Further unknown logins are rejected
    assert client.post("/api/auth/login", json={"login": "nobody", "password": "x"}).status_code == 401


def test_new_household_gets_current_and_next_month(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    months = client.get(f"/api/households/{hid}/months", headers=people["val"]["headers"]).json()
    today = today_in("UTC")
    assert {(m["year"], m["month"]) for m in months} == {(today.year, today.month), next_month(today.year, today.month)}


def test_members_are_ordered_residents_then_guests(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    names = [m["display_name"] for m in client.get(f"/api/households/{hid}/members", headers=admin).json()]
    assert names == ["Mia", "Rui", "Gil", "Val"]


def test_role_permissions_for_adding_costs(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    body = _cost(people, "rui", ["rui", "mia"], 100)
    assert client.post(f"/api/households/{hid}/costs", json=body, headers=people["val"]["headers"]).status_code == 403
    guest_cost = client.post(f"/api/households/{hid}/costs", json=body, headers=people["gil"]["headers"])
    assert guest_cost.status_code == 201  # guests add costs too
    assert guest_cost.json()["can_edit"] is True  # ...and can edit their own
    assert client.post(f"/api/households/{hid}/costs", json=body, headers=people["rui"]["headers"]).status_code == 201
    assert client.post(f"/api/households/{hid}/costs", json=body, headers=people["mia"]["headers"]).status_code == 201
    # Viewers can't be part of a cost
    bad = _cost(people, "rui", ["val"], 10)
    assert client.post(f"/api/households/{hid}/costs", json=bad, headers=people["rui"]["headers"]).status_code == 422
    # Only managers manage
    assert client.post(
        f"/api/households/{hid}/categories", json={"name": "Food"}, headers=people["rui"]["headers"]
    ).status_code == 403


def test_summary_split_and_categories(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia = people["mia"]["headers"]
    food = client.post(f"/api/households/{hid}/categories", json={"name": "Food"}, headers=mia).json()

    # Mia pays 90 for Mia, Rui, Gil -> Rui and Gil owe Mia 30 each
    body = _cost(people, "mia", ["mia", "rui", "gil"], 90)
    body["category_id"] = food["id"]
    assert client.post(f"/api/households/{hid}/costs", json=body, headers=mia).status_code == 201
    # Rui pays 30 for Gil -> Gil owes Rui 30, so Rui and Gil's debts chain
    assert client.post(
        f"/api/households/{hid}/costs", json=_cost(people, "rui", ["gil"], 30), headers=mia
    ).status_code == 201

    summary = _summary(client, hid, people["val"]["headers"])
    assert summary["total"] == 120
    transfers = {(t["from_member_id"], t["to_member_id"]): t["amount"] for t in summary["transfers"]}
    gil, mia_id = people["gil"]["member"]["id"], people["mia"]["member"]["id"]
    assert transfers == {(gil, mia_id): 60}  # one transfer instead of three
    totals = {c["name"]: c["total"] for c in summary["category_totals"]}
    assert totals == {"Food": 90, "Uncategorized": 30}
    first = next(c for c in summary["costs"] if c["amount"] == 90)
    assert first["cover_share"] == 30
    assert summary["can_add_cost"] is False  # viewer


def test_cost_list_is_oldest_first(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia = people["mia"]["headers"]
    today = today_in("UTC")
    first_day = today.replace(day=1)
    # Added out of order on purpose
    for description, day in [("Middle", today), ("Oldest", first_day), ("Same day, added later", today)]:
        client.post(f"/api/households/{hid}/costs", json=_cost(people, "mia", ["mia"], 10, day=day, description=description), headers=mia)
    descriptions = [c["description"] for c in _summary(client, hid, mia)["costs"]]
    if first_day == today:  # on the 1st all three share a date: order is the order they were added
        assert descriptions == ["Middle", "Oldest", "Same day, added later"]
    else:
        assert descriptions == ["Oldest", "Middle", "Same day, added later"]


def test_closed_month_rejects_changes(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia, rui = people["mia"]["headers"], people["rui"]["headers"]
    cost = client.post(f"/api/households/{hid}/costs", json=_cost(people, "rui", ["rui"], 10), headers=rui).json()
    today = today_in("UTC")

    assert client.post(f"/api/households/{hid}/months/{today.year}/{today.month}/close", headers=rui).status_code == 403
    assert client.post(f"/api/households/{hid}/months/{today.year}/{today.month}/close", headers=mia).status_code == 200

    assert client.post(f"/api/households/{hid}/costs", json=_cost(people, "rui", ["rui"], 10), headers=rui).status_code == 422
    assert client.delete(f"/api/households/{hid}/costs/{cost['id']}", headers=mia).status_code == 422

    assert client.post(f"/api/households/{hid}/months/{today.year}/{today.month}/reopen", headers=mia).status_code == 200
    assert client.delete(f"/api/households/{hid}/costs/{cost['id']}", headers=rui).status_code == 204


def test_resident_can_only_edit_own_costs(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia, rui = people["mia"]["headers"], people["rui"]["headers"]
    by_mia = client.post(f"/api/households/{hid}/costs", json=_cost(people, "mia", ["mia"], 10), headers=mia).json()
    by_rui = client.post(f"/api/households/{hid}/costs", json=_cost(people, "rui", ["rui"], 10), headers=rui).json()
    update = _cost(people, "rui", ["rui", "mia"], 20)
    assert client.put(f"/api/households/{hid}/costs/{by_mia['id']}", json=update, headers=rui).status_code == 403
    assert client.put(f"/api/households/{hid}/costs/{by_rui['id']}", json=update, headers=rui).status_code == 200
    assert client.put(f"/api/households/{hid}/costs/{by_rui['id']}", json=update, headers=mia).status_code == 200


def test_future_month_and_starting_state(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia = people["mia"]["headers"]
    rent = {
        "description": "Rent",
        "amount": 1000,
        "day_of_month": 31,
        "payer_ids": [people["mia"]["member"]["id"]],
        "coverer_ids": [people["mia"]["member"]["id"], people["rui"]["member"]["id"]],
    }
    assert client.post(f"/api/households/{hid}/recurring-costs", json=rent, headers=mia).status_code == 201

    today = today_in("UTC")
    year, month = next_month(*next_month(today.year, today.month))
    future_day = date(year, month, 10)

    # No month table yet -> can't add
    response = client.post(
        f"/api/households/{hid}/costs", json=_cost(people, "mia", ["mia"], 5, day=future_day), headers=mia
    )
    assert response.status_code == 422

    assert client.post(f"/api/households/{hid}/months", json={"year": year, "month": month}, headers=mia).status_code == 201
    summary = _summary(client, hid, mia, future_day)
    assert [c["description"] for c in summary["costs"]] == ["Rent"]  # starting state copied
    assert client.post(
        f"/api/households/{hid}/costs", json=_cost(people, "mia", ["mia"], 5, day=future_day), headers=mia
    ).status_code == 201

    # The current month was created before the template existed: apply it once, no duplicates
    added = client.post(f"/api/households/{hid}/months/{today.year}/{today.month}/apply-recurring", headers=mia).json()
    again = client.post(f"/api/households/{hid}/months/{today.year}/{today.month}/apply-recurring", headers=mia).json()
    assert added["added"] == 1 and again["added"] == 0


def test_add_fixed_costs_never_duplicates(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia = people["mia"]["headers"]
    mia_id, rui_id = people["mia"]["member"]["id"], people["rui"]["member"]["id"]
    today = today_in("UTC")
    apply_url = f"/api/households/{hid}/months/{today.year}/{today.month}/apply-recurring"

    def fixed(description, amount):
        body = {"description": description, "amount": amount, "day_of_month": 1, "payer_ids": [mia_id], "coverer_ids": [mia_id, rui_id]}
        return client.post(f"/api/households/{hid}/recurring-costs", json=body, headers=mia).json()

    def month_costs():
        summary = _summary(client, hid, mia)
        return sorted((c["description"], c["amount"]) for c in summary["costs"])

    rent = fixed("Rent", 3000)
    fixed("Internet", 120)
    # Someone already typed the internet bill by hand (different case/spacing): it counts as present
    client.post(f"/api/households/{hid}/costs", json=_cost(people, "mia", ["mia"], 120, description=" internet "), headers=mia)

    assert client.post(apply_url, headers=mia).json() == {"added": 1}  # only Rent
    assert client.post(apply_url, headers=mia).json() == {"added": 0}  # clicking twice adds nothing
    assert month_costs() == [("Rent", 3000), ("internet", 120)]

    # Rent goes up: the new amount is added, the old one stays
    client.put(
        f"/api/households/{hid}/recurring-costs/{rent['id']}",
        json={"description": "Rent", "amount": 3200, "day_of_month": 1, "payer_ids": [mia_id], "coverer_ids": [mia_id, rui_id]},
        headers=mia,
    )
    assert client.post(apply_url, headers=mia).json() == {"added": 1}
    assert month_costs() == [("Rent", 3000), ("Rent", 3200), ("internet", 120)]

    # Removing a fixed cost never removes what is already in the month
    client.delete(f"/api/households/{hid}/recurring-costs/{rent['id']}", headers=mia)
    assert client.post(apply_url, headers=mia).json() == {"added": 0}
    assert month_costs() == [("Rent", 3000), ("Rent", 3200), ("internet", 120)]

    # Residents can't do it
    assert client.post(apply_url, headers=people["rui"]["headers"]).status_code == 403


def test_auto_close_past_months(client, admin, login):
    hid, people = _setup_household(client, admin, login, auto_close_days=3)
    mia = people["mia"]["headers"]
    old = today_in("UTC").replace(day=1) - timedelta(days=40)
    assert client.post(f"/api/households/{hid}/months", json={"year": old.year, "month": old.month}, headers=mia).status_code == 201
    months = {(m["year"], m["month"]): m for m in client.get(f"/api/households/{hid}/months", headers=mia).json()}
    assert months[(old.year, old.month)]["status"] == "closed"
    today = today_in("UTC")
    assert months[(today.year, today.month)]["status"] == "open"

    # Reopened by a manager -> stays open
    client.post(f"/api/households/{hid}/months/{old.year}/{old.month}/reopen", headers=mia)
    months = {(m["year"], m["month"]): m for m in client.get(f"/api/households/{hid}/months", headers=mia).json()}
    assert months[(old.year, old.month)]["status"] == "open"


def test_disabled_member_cannot_login_but_stays_in_history(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia = people["mia"]["headers"]
    client.post(f"/api/households/{hid}/costs", json=_cost(people, "gil", ["gil", "mia"], 50), headers=mia)
    gil_id = people["gil"]["member"]["id"]

    assert client.put(f"/api/households/{hid}/members/{gil_id}", json={"is_active": False}, headers=mia).status_code == 200
    assert client.post("/api/auth/login", json={"login": "gil", "password": "pass1234"}).status_code == 403
    assert client.get(f"/api/households/{hid}", headers=people["gil"]["headers"]).status_code == 403

    summary = _summary(client, hid, mia)
    assert any(b["member_id"] == gil_id for b in summary["balances"])
    # Disabled people can't be picked for new costs
    response = client.post(f"/api/households/{hid}/costs", json=_cost(people, "gil", ["mia"], 5), headers=mia)
    assert response.status_code == 422


def test_household_keeps_a_manager(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    mia = people["mia"]["headers"]
    mia_id = people["mia"]["member"]["id"]
    rui_id = people["rui"]["member"]["id"]
    assert client.put(f"/api/households/{hid}/members/{mia_id}", json={"role": "resident"}, headers=mia).status_code == 422
    assert client.put(f"/api/households/{hid}/members/{rui_id}", json={"role": "manager"}, headers=mia).status_code == 200
    assert client.put(f"/api/households/{hid}/members/{mia_id}", json={"role": "resident"}, headers=mia).status_code == 200


def test_profile_and_member_contact(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    rui = people["rui"]["headers"]
    qr = "data:image/png;base64,iVBORw0KGgo="
    response = client.put(
        "/api/me",
        json={"whatsapp": "+55 11 99999-0000", "bank_info_type": "pix", "bank_info": "pix@rui.com", "transfer_qr": qr},
        headers=rui,
    )
    assert response.status_code == 200
    detail = client.get(f"/api/households/{hid}/members/{people['rui']['member']['id']}", headers=people["val"]["headers"])
    assert detail.json()["transfer_qr"] == qr
    assert detail.json()["bank_info"] == "pix@rui.com"
    assert detail.json()["bank_info_type"] == "pix"
    assert client.put("/api/me", json={"transfer_qr": "not-an-image"}, headers=rui).status_code == 422
    assert client.put("/api/me", json={"bank_info_type": "crypto"}, headers=rui).status_code == 422


def test_manager_edits_a_person(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    gil_id = people["gil"]["member"]["id"]
    body = {"display_name": "Gilberto", "bank_info_type": "other", "bank_info": "Bank 001 / 1234-5", "email": "gil@x.com"}

    assert client.put(f"/api/households/{hid}/members/{gil_id}", json=body, headers=people["rui"]["headers"]).status_code == 403
    response = client.put(f"/api/households/{hid}/members/{gil_id}", json=body, headers=people["mia"]["headers"])
    assert response.status_code == 200
    edited = response.json()
    assert (edited["display_name"], edited["bank_info_type"], edited["bank_info"], edited["email"]) == (
        "Gilberto", "other", "Bank 001 / 1234-5", "gil@x.com"
    )
    assert edited["role"] == "guest"  # untouched fields stay as they were
    # Clearing a field
    cleared = client.put(f"/api/households/{hid}/members/{gil_id}", json={"email": ""}, headers=people["mia"]["headers"])
    assert cleared.json()["email"] is None


def test_manager_cannot_take_existing_login(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    response = client.post(
        f"/api/households/{hid}/members",
        json={"login_name": "RUI", "password": "x1234", "role": "guest"},
        headers=people["mia"]["headers"],
    )
    assert response.status_code == 409
