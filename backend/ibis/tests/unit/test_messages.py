from datetime import date

import pytest

from domain.messages import _TEXTS, format_date, format_money, month_label, payment_message, task_due_message
from domain.phones import whatsapp_number


@pytest.mark.parametrize(
    "raw, country, expected",
    [
        ("+55 (11) 98765-4321", "55", "5511987654321"),
        ("(11) 98765-4321", "55", "5511987654321"),
        ("011 98765 4321", "55", "5511987654321"),
        ("0055 11 98765 4321", "55", "5511987654321"),
        ("55 11 98765-4321", "55", "5511987654321"),
        ("55 98765-4321", "55", "5555987654321"),  # area code 55 (RS), not the country code
        ("+1 415 555 0100", "55", "14155550100"),
        ("+49 151 23456789", None, "4915123456789"),
        ("not a phone", "55", None),
        ("", "55", None),
        (None, "55", None),
    ],
)
def test_whatsapp_number(raw, country, expected):
    assert whatsapp_number(raw, country) == expected


def test_every_language_has_every_text():
    keys = set(_TEXTS["en"])
    for language, texts in _TEXTS.items():
        assert set(texts) == keys, language


def test_task_due_message():
    due = date(2026, 11, 20)
    assert task_due_message("pt-BR", "expiring", household="Casa", title="Lixo", due=due) == '⏰ Casa: "Lixo" vence em 20/11/2026.'
    group = task_due_message("en", "expired", household="Home", title="Gift", due=due, private=True, people=["Rui"])
    assert "Gift" not in group and "a private task" in group and group.endswith("Assigned to: Rui")
    assert format_date(due, "de") == "20.11.2026"


def test_money_and_month_in_each_language():
    assert format_money(1234.5, "BRL", "pt-BR") == "R$ 1.234,50"
    assert format_money(1234.5, "EUR", "de") == "1.234,50 €"
    assert format_money(1234.5, "USD", "en") == "$1,234.50"
    assert format_money(10, "CHF", "en") == "CHF 10.00"
    assert month_label(2026, 11, "pt-BR") == "novembro de 2026"
    assert month_label(2026, 11, "ja") == "2026年11月"
    assert month_label(2026, 3, "xx") == "March 2026"  # unknown language: English


def test_payment_message_lists_only_the_ways_available():
    common = dict(name="Mia", amount=30, currency="BRL", year=2026, month=11)
    full = payment_message("en", pix_key="mia@x.com", bank_info=None, page_url="https://a/pay", has_code=True, **common)
    assert full.splitlines() == [
        "Pay Mia R$ 30.00 as your part of the split for November 2026.",
        "",
        "You can pay with:",
        "1) A direct transfer to the PIX key: mia@x.com",
        "2) The Ibis payment page, with QR code: https://a/pay",
        "3) The PIX copy-and-paste code in the next message.",
    ]
    nothing = payment_message("en", pix_key=None, bank_info=None, page_url=None, has_code=False, **common)
    assert nothing.endswith("Mia has no payment details in Ibis yet. Ask them directly.")
