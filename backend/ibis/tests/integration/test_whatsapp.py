"""WhatsApp: household groups, task notifications queued and delivered, private tasks.

The WhatsApp service itself is replaced by a fake (see `fake_whatsapp`).
"""
from datetime import timedelta

import pytest

from db.session import SessionLocal
from domain.months import today_in
from infrastructure import whatsapp
from infrastructure.config.settings import settings
from models.messaging import OutgoingMessage
from services.messaging_service import MessagingService
from tests.conftest import run_housekeeping
from tests.integration.test_household_flow import _cost, _setup_household
from tests.integration.test_notifications import _close
from tests.integration.test_tasks import TODAY, _create, _days_later, _list, _task

GROUP_JID = "120363000000000001@g.us"


class FakeWhatsApp:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []
        self.fail_with: whatsapp.WhatsAppError | None = None

    def status(self, _hid):
        return {"status": "connected", "phone": "5511900000000", "name": "Home"}

    def groups(self, _hid):
        return [{"id": GROUP_JID, "name": "Family", "participants": 4}]

    def send(self, _hid, to, text):
        if self.fail_with:
            raise self.fail_with
        self.sent.append((to, text))
        return {"id": "msg"}


@pytest.fixture()
def fake_whatsapp(monkeypatch):
    fake = FakeWhatsApp()
    monkeypatch.setattr(settings, "whatsapp_service_url", "http://whatsapp.test")
    for name in ("status", "groups", "send"):
        monkeypatch.setattr(whatsapp, name, getattr(fake, name))
    return fake


@pytest.fixture()
def home(client, admin, login):
    hid, people = _setup_household(client, admin, login)
    headers = {name: p["headers"] for name, p in people.items()}
    # Rui has a Brazilian number typed without the country code (the household uses BRL)
    rui = people["rui"]["member"]["id"]
    response = client.put(f"/api/households/{hid}/members/{rui}", json={"whatsapp": "(11) 98765-4321"}, headers=admin)
    assert response.status_code == 200, response.text
    return hid, people, headers


def _deliver() -> int:
    db = SessionLocal()
    try:
        return MessagingService(db).deliver_pending()
    finally:
        db.close()


def _messages(client, hid, headers):
    response = client.get(f"/api/households/{hid}/whatsapp/messages", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_status_is_off_without_a_service(client, home):
    hid, _people, h = home
    assert client.get(f"/api/households/{hid}/whatsapp", headers=h["mia"]).json()["status"] == "off"
    assert client.get(f"/api/households/{hid}/whatsapp", headers=h["rui"]).status_code == 403  # managers only
    assert client.post(f"/api/households/{hid}/whatsapp/connect", headers=h["mia"]).status_code == 503


def test_household_groups(client, home, fake_whatsapp):
    hid, _people, h = home
    base = f"/api/households/{hid}/whatsapp"
    [available] = client.get(f"{base}/available-groups", headers=h["mia"]).json()
    assert available == {"jid": GROUP_JID, "name": "Family", "participants": 4, "added": False}

    group = client.post(f"{base}/groups", json={"jid": GROUP_JID, "name": "Family"}, headers=h["mia"]).json()
    assert client.post(f"{base}/groups", json={"jid": GROUP_JID, "name": "Again"}, headers=h["mia"]).status_code == 409
    assert client.post(f"{base}/groups", json={"jid": "not-a-group", "name": "x"}, headers=h["mia"]).status_code == 422
    assert client.get(f"{base}/available-groups", headers=h["mia"]).json()[0]["added"] is True

    assert client.post(f"{base}/test", json={"group_id": group["id"]}, headers=h["mia"]).status_code == 204
    assert fake_whatsapp.sent[-1][0] == GROUP_JID

    paused = client.put(f"{base}/groups/{group['id']}", json={"is_active": False}, headers=h["mia"]).json()
    assert paused["is_active"] is False
    assert client.delete(f"{base}/groups/{group['id']}", headers=h["mia"]).status_code == 204
    assert client.get(f"{base}/groups", headers=h["mia"]).json() == []


def test_test_message_to_a_member(client, home, fake_whatsapp):
    hid, people, h = home
    base = f"/api/households/{hid}/whatsapp"
    rui, gil = people["rui"]["member"]["id"], people["gil"]["member"]["id"]
    assert client.post(f"{base}/test", json={"member_id": rui}, headers=h["mia"]).status_code == 204
    assert fake_whatsapp.sent[-1][0] == "5511987654321"
    assert client.post(f"{base}/test", json={"member_id": gil}, headers=h["mia"]).status_code == 422  # no number


def test_expiring_task_notifies_on_whatsapp(client, home, fake_whatsapp, monkeypatch):
    hid, people, h = home
    client.post(f"/api/households/{hid}/whatsapp/groups", json={"jid": GROUP_JID, "name": "Family"}, headers=h["mia"])
    body = _task(
        people,
        title="Pay rent",
        assignees=["rui", "gil"],
        due=TODAY + timedelta(days=10),
        notify_expiring_whatsapp=True,
        notify_expiring_groups=True,
        notify_expiring_email=True,  # placeholder: nothing is sent yet
    )
    _create(client, hid, h["mia"], body)
    assert _messages(client, hid, h["mia"]) == []  # not in its warning window yet

    _days_later(monkeypatch, 8)
    run_housekeeping()  # the scheduler runs the due-date checks
    queued = _messages(client, hid, h["mia"])
    assert sorted(m["recipient_label"] for m in queued) == ["Family", "Rui"]  # Gil has no number
    assert all(m["status"] == "pending" for m in queued)
    group_text = next(m["text"] for m in queued if m["recipient_label"] == "Family")
    assert '"Pay rent"' in group_text and "Rui, Gil" in group_text
    assert client.get("/api/notifications", headers=h["rui"]).json() == []  # no in-app note asked for

    assert _deliver() == 2
    assert {to for to, _ in fake_whatsapp.sent} == {"5511987654321", GROUP_JID}
    assert all(m["status"] == "sent" for m in _messages(client, hid, h["mia"]))

    run_housekeeping()  # sent once only
    assert len(_messages(client, hid, h["mia"])) == 2


def test_private_task_group_message_hides_the_title(client, home, fake_whatsapp, monkeypatch):
    hid, people, h = home
    client.post(f"/api/households/{hid}/whatsapp/groups", json={"jid": GROUP_JID, "name": "Family"}, headers=h["mia"])
    body = _task(
        people, title="Surprise party", assignees=["rui"], due=TODAY, is_private=True,
        notify_expiring_whatsapp=True, notify_expiring_groups=True,
    )
    _create(client, hid, h["mia"], body)
    texts = {m["recipient_label"]: m["text"] for m in _messages(client, hid, h["mia"])}
    assert "Surprise party" in texts["Rui"]  # Rui is assigned
    assert "Surprise party" not in texts["Family"] and "a private task" in texts["Family"]


def test_failed_messages_are_retried_then_given_up(client, home, fake_whatsapp):
    hid, people, h = home
    body = _task(people, assignees=["rui"], due=TODAY, notify_expiring_whatsapp=True)
    _create(client, hid, h["mia"], body)
    fake_whatsapp.fail_with = whatsapp.WhatsAppError("service down", 503)
    assert _deliver() == 0
    [message] = _messages(client, hid, h["mia"])
    assert message["status"] == "pending" and message["attempts"] == 1 and message["last_error"] == "service down"
    assert _deliver() == 0  # waits before retrying
    assert _messages(client, hid, h["mia"])[0]["attempts"] == 1

    fake_whatsapp.fail_with = whatsapp.WhatsAppError("not on WhatsApp", 400)
    db = SessionLocal()
    try:
        db.query(OutgoingMessage).update({OutgoingMessage.next_attempt_at: None})
        db.commit()
    finally:
        db.close()
    _deliver()
    assert _messages(client, hid, h["mia"])[0]["status"] == "failed"  # a bad number won't get better


def test_private_tasks_are_hidden_from_people_not_assigned(client, home):
    hid, people, h = home
    task = _create(
        client, hid, h["mia"], _task(people, title="Gift for Mia", description="Shh", assignees=["rui"], is_private=True)
    )
    assert task["is_hidden"] is True and task["title"] == ""  # Mia created it but isn't assigned

    [mine] = _list(client, hid, h["rui"])
    assert mine["title"] == "Gift for Mia" and mine["description"] == "Shh" and mine["is_hidden"] is False

    [theirs] = _list(client, hid, h["mia"])
    assert theirs["title"] == "" and theirs["description"] is None and theirs["is_hidden"] is True
    assert theirs["can_edit"] is False and theirs["can_delete"] is True  # managers can still remove it
    response = client.put(f"/api/households/{hid}/tasks/{task['id']}", json=_task(people, title="x"), headers=h["mia"])
    assert response.status_code == 403


def _close_with_debt(client, hid, people, h):
    """Mia paid 90 for everyone, so Rui and Gil each owe Mia 30. Closes the current month."""
    settings_body = {"payment_task": {"notify_expiring_whatsapp": True}}  # due in 3 days: expiring at once
    assert client.put(f"/api/households/{hid}", json=settings_body, headers=h["mia"]).status_code == 200
    client.post(f"/api/households/{hid}/costs", json=_cost(people, "mia", ["mia", "rui", "gil"], 90), headers=h["mia"])
    _close(client, hid, h["mia"], today_in("UTC"))


def test_payment_reminder_carries_the_pix_code(client, home, fake_whatsapp, monkeypatch):
    hid, people, h = home
    monkeypatch.setattr(settings, "frontend_url", "https://ibis.example.com")
    client.put(f"/api/households/{hid}", json={"language": "pt-BR"}, headers=h["mia"])
    client.put("/api/me", json={"bank_info_type": "pix", "bank_info": "Mia@Example.com"}, headers=h["mia"])
    _close_with_debt(client, hid, people, h)

    [task] = _list(client, hid, h["rui"], f"?assignee_id={people['rui']['member']['id']}")
    assert task["title"] == "Pagar R$ 30,00 para Mia"  # in the household's language
    assert task["data"]["pix_key"] == "mia@example.com"
    assert task["data"]["pix_code"].startswith("00020126") and "54" "0530.00" in task["data"]["pix_code"]

    code, details = [m["text"] for m in _messages(client, hid, h["mia"]) if m["recipient_label"] == "Rui"]  # newest first
    assert details.startswith('⏰ ') and '"Pagar R$ 30,00 para Mia"' in details
    assert "1) Uma transferência direta para a chave PIX: mia@example.com" in details
    assert "2) A página de pagamento do Ibis, com QR code: https://ibis.example.com/pay?key=mia%40example.com" in details
    assert "3) O código PIX copia e cola na próxima mensagem." in details
    assert code == task["data"]["pix_code"]  # alone, so it copies cleanly

    assert _deliver() == 2
    assert [text for _to, text in fake_whatsapp.sent] == [details, code]  # in that order


def test_payment_reminder_without_a_pix_key(client, home, fake_whatsapp):
    hid, people, h = home
    client.put("/api/me", json={"bank_info_type": "other", "bank_info": "Bank 001 / 1234-5"}, headers=h["mia"])
    _close_with_debt(client, hid, people, h)
    [details] = [m["text"] for m in _messages(client, hid, h["mia"]) if m["recipient_label"] == "Rui"]
    assert "1) A direct transfer: Bank 001 / 1234-5" in details
    assert "payment page" not in details and "2)" not in details  # no PIX key: no code, no page
