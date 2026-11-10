"""Texts of messages sent outside the app (WhatsApp; email later), in the household's language.

Pure functions, no database code. The app's own screens are translated in the frontend; these are
the only server-side translations, because the text leaves the app as-is.
"""
from datetime import date
from typing import Literal, Optional

MessageEvent = Literal["expiring", "expired"]

# {household}, {title}, {date}; group messages also get {people}
_TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "expiring": '⏰ {household}: "{title}" is due on {date}.',
        "expired": '⚠️ {household}: "{title}" is overdue (it was due on {date}).',
        "people": "Assigned to: {people}",
        "private": "a private task",
        "nobody": "nobody",
        "test": "✅ Ibis: WhatsApp messages from {household} are working.",
    },
    "pt-BR": {
        "expiring": '⏰ {household}: "{title}" vence em {date}.',
        "expired": '⚠️ {household}: "{title}" está atrasada (venceu em {date}).',
        "people": "Responsáveis: {people}",
        "private": "uma tarefa privada",
        "nobody": "ninguém",
        "test": "✅ Ibis: as mensagens de WhatsApp de {household} estão funcionando.",
    },
    "de": {
        "expiring": '⏰ {household}: „{title}“ ist am {date} fällig.',
        "expired": '⚠️ {household}: „{title}“ ist überfällig (fällig am {date}).',
        "people": "Zugewiesen an: {people}",
        "private": "eine private Aufgabe",
        "nobody": "niemanden",
        "test": "✅ Ibis: WhatsApp-Nachrichten von {household} funktionieren.",
    },
    "fr": {
        "expiring": "⏰ {household} : « {title} » est à faire pour le {date}.",
        "expired": "⚠️ {household} : « {title} » est en retard (à faire pour le {date}).",
        "people": "Assignée à : {people}",
        "private": "une tâche privée",
        "nobody": "personne",
        "test": "✅ Ibis : les messages WhatsApp de {household} fonctionnent.",
    },
    "it": {
        "expiring": '⏰ {household}: "{title}" scade il {date}.',
        "expired": '⚠️ {household}: "{title}" è in ritardo (scadeva il {date}).',
        "people": "Assegnata a: {people}",
        "private": "un'attività privata",
        "nobody": "nessuno",
        "test": "✅ Ibis: i messaggi WhatsApp di {household} funzionano.",
    },
    "zh-CN": {
        "expiring": "⏰ {household}：“{title}” 将于 {date} 到期。",
        "expired": "⚠️ {household}：“{title}” 已逾期（截止日期 {date}）。",
        "people": "负责人：{people}",
        "private": "一项私密任务",
        "nobody": "无",
        "test": "✅ Ibis：{household} 的 WhatsApp 消息运行正常。",
    },
    "ja": {
        "expiring": "⏰ {household}：「{title}」の期限は {date} です。",
        "expired": "⚠️ {household}：「{title}」は期限切れです（期限 {date}）。",
        "people": "担当：{people}",
        "private": "非公開のタスク",
        "nobody": "なし",
        "test": "✅ Ibis：{household} の WhatsApp メッセージは正常に届いています。",
    },
    "ko": {
        "expiring": '⏰ {household}: "{title}" 마감일은 {date}입니다.',
        "expired": '⚠️ {household}: "{title}" 기한이 지났습니다 (마감일 {date}).',
        "people": "담당: {people}",
        "private": "비공개 작업",
        "nobody": "없음",
        "test": "✅ Ibis: {household}의 WhatsApp 메시지가 정상 작동합니다.",
    },
    "hi": {
        "expiring": '⏰ {household}: "{title}" की अंतिम तिथि {date} है।',
        "expired": '⚠️ {household}: "{title}" की तिथि निकल गई ({date})।',
        "people": "ज़िम्मेदार: {people}",
        "private": "एक निजी काम",
        "nobody": "कोई नहीं",
        "test": "✅ Ibis: {household} के WhatsApp संदेश काम कर रहे हैं।",
    },
}

_DATE_FORMATS = {
    "en": "{y}-{m:02d}-{d:02d}",
    "de": "{d:02d}.{m:02d}.{y}",
    "zh-CN": "{y}-{m:02d}-{d:02d}",
    "ja": "{y}/{m:02d}/{d:02d}",
    "ko": "{y}.{m:02d}.{d:02d}",
}


def _texts(language: str) -> dict[str, str]:
    return _TEXTS.get(language, _TEXTS["en"])


def format_date(day: date, language: str) -> str:
    pattern = _DATE_FORMATS.get(language, "{d:02d}/{m:02d}/{y}")
    return pattern.format(y=day.year, m=day.month, d=day.day)


def task_due_message(
    language: str,
    event: MessageEvent,
    *,
    household: str,
    title: str,
    due: date,
    private: bool = False,
    people: Optional[list[str]] = None,
) -> str:
    """The text for a task that is about to expire / has expired.

    `people` is given for group messages (which list the assignees). A private task's title is
    replaced by "a private task", since a group includes people who aren't assigned.
    """
    texts = _texts(language)
    shown = texts["private"] if private else title
    text = texts[event].format(household=household, title=shown, date=format_date(due, language))
    if people is not None:
        text += "\n" + texts["people"].format(people=", ".join(people) or texts["nobody"])
    return text


def test_message(language: str, household: str) -> str:
    return _texts(language)["test"].format(household=household)
