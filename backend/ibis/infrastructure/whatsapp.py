"""HTTP client for the WhatsApp service (../../whatsapp, a small Node app around Baileys).

One WhatsApp session per household: the session id is the household id. Standard library only.
"""
import json
import urllib.error
import urllib.request
from typing import Any, Optional

from infrastructure.config.settings import settings

TIMEOUT_SECONDS = 15


class WhatsAppError(Exception):
    """The service is not configured, can't be reached, or refused the request."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status = status


def is_configured() -> bool:
    return bool(settings.whatsapp_service_url)


def _request(method: str, path: str, body: Optional[dict] = None) -> Any:
    if not is_configured():
        raise WhatsAppError("WhatsApp is not set up on this server (WHATSAPP_SERVICE_URL)")
    url = settings.whatsapp_service_url.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {settings.whatsapp_service_token}")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read() or b"{}").get("error")
        except ValueError:
            detail = None
        raise WhatsAppError(detail or f"WhatsApp service error ({exc.code})", exc.code) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise WhatsAppError(f"Can't reach the WhatsApp service: {exc}") from exc
    return json.loads(raw) if raw else None


def _session(household_id) -> str:
    return f"/sessions/{household_id}"


def status(household_id) -> dict:
    """{status: disconnected | connecting | qr | connected, qr: data URL or null, phone, name, error}"""
    return _request("GET", _session(household_id))


def connect(household_id) -> dict:
    """Start the session. Until it is linked, status() returns a QR code to scan."""
    return _request("POST", _session(household_id) + "/connect")


def logout(household_id) -> dict:
    """Unlink the number and forget the session."""
    return _request("POST", _session(household_id) + "/logout")


def groups(household_id) -> list[dict]:
    """Groups the connected number is in: [{id (jid), name, participants}]"""
    return _request("GET", _session(household_id) + "/groups")


def send(household_id, to: str, text: str) -> dict:
    """`to` is a group jid ("...@g.us") or a phone number with country code (digits)."""
    return _request("POST", _session(household_id) + "/messages", {"to": to, "text": text})
