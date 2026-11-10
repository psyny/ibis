from datetime import date

import pytest

from domain.messages import _TEXTS, format_date, task_due_message
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
