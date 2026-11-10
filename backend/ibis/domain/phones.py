"""Turn the free-text WhatsApp number people type into what WhatsApp expects. No database code."""
import re
from typing import Optional


def whatsapp_number(raw: Optional[str], default_country: Optional[str] = None) -> Optional[str]:
    """Digits with the country code (e.g. "5511987654321"), or None if it can't be a phone number.

    "+55 (11) 98765-4321", "0055 11 98765 4321" and "55 11 987654321" all give the same result.
    Without a country code (no "+" or "00"), `default_country` is added when the number looks local
    (10-11 digits for Brazil). The WhatsApp service then checks the number really is on WhatsApp.
    """
    if not raw:
        return None
    text = raw.strip()
    digits = re.sub(r"\D", "", text)
    if text.startswith("+"):
        pass
    elif digits.startswith("00"):
        digits = digits[2:]
    elif default_country and not digits.startswith(default_country):
        digits = default_country + digits.lstrip("0")
    elif default_country == "55" and digits.startswith("55") and len(digits) in (10, 11):
        # e.g. "55 9876-5432": a local number from area code 55 (RS), not the country code
        digits = default_country + digits
    if not 8 <= len(digits) <= 15:
        return None
    return digits


def default_country_for(currency: str) -> Optional[str]:
    """A household's likely country calling code, used for numbers typed without one."""
    return {"BRL": "55"}.get(currency)
