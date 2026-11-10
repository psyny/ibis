"""PIX "copia e cola" codes, built on the server so messages can carry them.

A port of the frontend's utils/pixKey.ts (key cleanup) and utils/pix.ts (the code itself, the same
fields the react-qrcode-pix library writes). Both sides must produce the same code for the same
input: tests/unit/test_pix.py checks codes made by the frontend.

Pure functions, no database code.
"""
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

PIX_CITY = "BRASIL"  # required by the format; banks don't check it for person-to-person transfers
_MAX_NAME = 25
_MAX_CITY = 15
_INVISIBLE = re.compile("[​-‍﻿ ]")


@dataclass(frozen=True)
class PixKey:
    kind: str  # email, cpf, cnpj, phone or random
    key: str  # canonical form


# --- Keys (utils/pixKey.ts) ---------------------------------------------------------------
def is_valid_cpf(digits: str) -> bool:
    if not re.fullmatch(r"\d{11}", digits) or len(set(digits)) == 1:
        return False

    def check(length: int) -> int:
        total = sum(int(digits[i]) * (length + 1 - i) for i in range(length))
        rest = (total * 10) % 11
        return 0 if rest == 10 else rest

    return check(9) == int(digits[9]) and check(10) == int(digits[10])


def is_valid_cnpj(digits: str) -> bool:
    if not re.fullmatch(r"\d{14}", digits) or len(set(digits)) == 1:
        return False

    def check(length: int) -> int:
        weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if length == 12 else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        rest = sum(w * int(digits[i]) for i, w in enumerate(weights)) % 11
        return 0 if rest < 2 else 11 - rest

    return check(12) == int(digits[12]) and check(13) == int(digits[13])


def _national_phone_ok(national: str) -> bool:
    """Area code (11-99) plus an 8-digit landline or a 9-digit mobile starting with 9."""
    if not 10 <= len(national) <= 11:
        return False
    if not re.match(r"[1-9][1-9]", national):
        return False
    return len(national) == 10 or national[2] == "9"


def parse_pix_key(raw: Optional[str]) -> Optional[PixKey]:
    """The canonical PIX key for whatever people typed, or None if it can't be used."""
    text = _INVISIBLE.sub(" ", raw or "").strip()
    if not text:
        return None

    if "@" in text:
        email = re.sub(r"^mailto:", "", re.sub(r"\s+", "", text), flags=re.I).lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 77:
            return None
        return PixKey("email", email)

    hexa = re.sub(r"[\s-]", "", text)
    if re.fullmatch(r"[0-9a-fA-F]{32}", hexa) and re.search(r"[a-fA-F]", hexa):
        h = hexa.lower()
        return PixKey("random", f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}")

    if not re.fullmatch(r"\+?[\d\s.\-/()]+", text):
        return None
    has_plus = text.startswith("+")
    looks_like_phone = has_plus or bool(re.search(r"[()]", text))
    looks_like_document = bool(re.search(r"[./]", text))
    digits = re.sub(r"\D", "", text)

    def phone(national: str) -> Optional[PixKey]:
        return PixKey("phone", f"+55{national}") if _national_phone_ok(national) else None

    if has_plus:
        return phone(digits[2:]) if digits.startswith("55") else None

    if len(digits) == 14:
        return PixKey("cnpj", digits) if is_valid_cnpj(digits) else None

    if len(digits) == 11 and not looks_like_phone:
        if is_valid_cpf(digits):
            return PixKey("cpf", digits)
        if looks_like_document or not _national_phone_ok(digits):
            return None
        return PixKey("phone", f"+55{digits}")

    if len(digits) == 12 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) in (12, 13) and digits.startswith("55"):
        return phone(digits[2:])
    if looks_like_phone or len(digits) in (10, 11):
        return phone(digits)
    return None


# --- The code (utils/pix.ts + react-qrcode-pix) ---------------------------------------------
def _plain_name(name: str, limit: int) -> str:
    text = unicodedata.normalize("NFD", name)
    text = re.sub("[̀-ͯ]", "", text)
    text = re.sub(r"[^a-zA-Z\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()[:limit].strip()


def crc16(text: str) -> str:
    """CRC16-CCITT (0xFFFF), as the PIX/EMV QR format uses."""
    crc = 0xFFFF
    for char in text:
        crc ^= ord(char) << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def _field(field_id: int, content: str) -> str:
    if len(content) > 99:
        raise ValueError("PIX field too long")
    return f"{field_id:02d}{len(content):02d}{content}"


def pix_code(key: PixKey, name: str, amount: Optional[float]) -> str:
    """The "copia e cola" code that pays `amount` (None: the payer types it) to `name` at `key`."""
    merchant = _plain_name(name, _MAX_NAME) or "RECEBEDOR"
    city = _plain_name(PIX_CITY, _MAX_CITY)
    value = round(amount, 2) if amount and amount > 0 else None
    body = "".join(
        [
            _field(0, "01"),
            _field(26, _field(0, "BR.GOV.BCB.PIX") + _field(1, re.sub(r"\s", "", key.key)[:77])),
            _field(52, "0000"),
            _field(53, "986"),  # BRL
            _field(54, f"{value:.2f}") if value else "",
            _field(58, "BR"),
            _field(59, merchant),
            _field(60, city),
            _field(62, _field(5, "***")),
            "6304",
        ]
    )
    return body + crc16(body)


def payment_details(bank_info_type: str, bank_info: Optional[str], name: str, amount: float, currency: str) -> dict:
    """How to pay `name`, saved with a month's payment task (a snapshot: the amount and key of the close).

    - pix_key: the canonical PIX key, if they have a usable one
    - pix_code: the copy-and-paste code for the exact amount (PIX is BRL only)
    - bank_info: what they wrote, when there is no usable PIX key (e.g. bank account details)
    """
    key = parse_pix_key(bank_info) if bank_info_type == "pix" else None
    return {
        "pix_key": key.key if key else None,
        "pix_code": pix_code(key, name, amount) if key and currency.upper() == "BRL" else None,
        "bank_info": None if key else ((bank_info or "").strip() or None),
    }


def payment_page_url(base_url: str, key: str, name: str, amount: float, language: str) -> str:
    """The app's public payment page (QR + code) for this transfer; no sign-in needed."""
    query = urlencode({"key": key, "name": name, "amount": f"{amount:.2f}", "lang": language})
    return f"{base_url.rstrip('/')}/pay?{query}"
