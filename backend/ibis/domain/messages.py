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


# --- Month-close payments -------------------------------------------------------------------
# Titles match the app's "task.monthPayment.title". The ways to pay are numbered as they are listed.
_PAYMENT_TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Pay {name} {amount}",
        "intro": "Pay {name} {amount} as your part of the split for {month}.",
        "ways": "You can pay with:",
        "key": "A direct transfer to the PIX key: {key}",
        "bank": "A direct transfer: {bank}",
        "link": "The Ibis payment page, with QR code: {url}",
        "code": "The PIX copy-and-paste code in the next message.",
        "none": "{name} has no payment details in Ibis yet. Ask them directly.",
    },
    "pt-BR": {
        "title": "Pagar {amount} para {name}",
        "intro": "Pague {amount} para {name}: sua parte da divisão de {month}.",
        "ways": "Você pode pagar com:",
        "key": "Uma transferência direta para a chave PIX: {key}",
        "bank": "Uma transferência direta: {bank}",
        "link": "A página de pagamento do Ibis, com QR code: {url}",
        "code": "O código PIX copia e cola na próxima mensagem.",
        "none": "{name} ainda não tem dados de pagamento no Ibis. Pergunte diretamente.",
    },
    "de": {
        "title": "{name} {amount} zahlen",
        "intro": "Zahle {name} {amount} als deinen Anteil an der Aufteilung für {month}.",
        "ways": "So kannst du zahlen:",
        "key": "Direkte Überweisung an den PIX-Schlüssel: {key}",
        "bank": "Direkte Überweisung: {bank}",
        "link": "Die Ibis-Zahlungsseite mit QR-Code: {url}",
        "code": "Der PIX-Code zum Kopieren in der nächsten Nachricht.",
        "none": "{name} hat noch keine Zahlungsdaten in Ibis. Frag direkt nach.",
    },
    "fr": {
        "title": "Payer {amount} à {name}",
        "intro": "Payez {amount} à {name} : votre part du partage de {month}.",
        "ways": "Vous pouvez payer avec :",
        "key": "Un virement direct vers la clé PIX : {key}",
        "bank": "Un virement direct : {bank}",
        "link": "La page de paiement Ibis, avec QR code : {url}",
        "code": "Le code PIX copier-coller dans le message suivant.",
        "none": "{name} n'a pas encore de coordonnées de paiement dans Ibis. Demandez-lui directement.",
    },
    "it": {
        "title": "Paga {amount} a {name}",
        "intro": "Paga {amount} a {name}: la tua parte della divisione di {month}.",
        "ways": "Puoi pagare con:",
        "key": "Un bonifico diretto alla chiave PIX: {key}",
        "bank": "Un bonifico diretto: {bank}",
        "link": "La pagina di pagamento di Ibis, con QR code: {url}",
        "code": "Il codice PIX copia e incolla nel prossimo messaggio.",
        "none": "{name} non ha ancora dati di pagamento su Ibis. Chiedi direttamente.",
    },
    "zh-CN": {
        "title": "向 {name} 支付 {amount}",
        "intro": "向 {name} 支付 {amount}，这是你在 {month} 分摊中的份额。",
        "ways": "你可以通过以下方式支付：",
        "key": "直接转账到 PIX 密钥：{key}",
        "bank": "直接转账：{bank}",
        "link": "Ibis 付款页面（含二维码）：{url}",
        "code": "下一条消息中的 PIX 复制粘贴码。",
        "none": "{name} 还没有在 Ibis 中填写付款信息，请直接询问。",
    },
    "ja": {
        "title": "{name} に {amount} を支払う",
        "intro": "{month} の割り勘のあなたの分として、{name} に {amount} を支払ってください。",
        "ways": "支払い方法：",
        "key": "PIX キーへの直接振込：{key}",
        "bank": "直接振込：{bank}",
        "link": "Ibis の支払いページ（QR コード付き）：{url}",
        "code": "次のメッセージの PIX コピー＆ペーストコード。",
        "none": "{name} はまだ Ibis に支払い情報を登録していません。直接確認してください。",
    },
    "ko": {
        "title": "{name}에게 {amount} 보내기",
        "intro": "{month} 정산에서 내 몫으로 {name}에게 {amount}을(를) 보내세요.",
        "ways": "결제 방법:",
        "key": "PIX 키로 직접 이체: {key}",
        "bank": "직접 이체: {bank}",
        "link": "QR 코드가 있는 Ibis 결제 페이지: {url}",
        "code": "다음 메시지의 PIX 복사·붙여넣기 코드.",
        "none": "{name}님은 아직 Ibis에 결제 정보가 없습니다. 직접 물어보세요.",
    },
    "hi": {
        "title": "{name} को {amount} दें",
        "intro": "{month} के बँटवारे में अपने हिस्से के रूप में {name} को {amount} दें।",
        "ways": "आप इनसे भुगतान कर सकते हैं:",
        "key": "PIX की पर सीधा ट्रांसफ़र: {key}",
        "bank": "सीधा ट्रांसफ़र: {bank}",
        "link": "Ibis भुगतान पेज, QR कोड के साथ: {url}",
        "code": "अगले संदेश में PIX कॉपी-पेस्ट कोड।",
        "none": "{name} की भुगतान जानकारी अभी Ibis में नहीं है। सीधे पूछें।",
    },
}

_MONTHS: dict[str, tuple[str, ...]] = {
    "en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"),
    "pt-BR": ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
              "novembro", "dezembro"),
    "de": ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
           "November", "Dezember"),
    "fr": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
           "novembre", "décembre"),
    "it": ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre",
           "novembre", "dicembre"),
    "hi": ("जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्तूबर", "नवंबर", "दिसंबर"),
}
_MONTH_FORMATS = {"pt-BR": "{name} de {y}", "zh-CN": "{y}年{m}月", "ja": "{y}年{m}月", "ko": "{y}년 {m}월"}

_SYMBOLS = {"BRL": "R$", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥", "KRW": "₩", "INR": "₹"}
_THOUSANDS = {"pt-BR": ".", "de": ".", "it": ".", "fr": "\u202f"}  # languages with comma decimals -> thousands separator
_SYMBOL_AFTER = {"de", "fr", "it"}


def _payment_texts(language: str) -> dict[str, str]:
    return _PAYMENT_TEXTS.get(language, _PAYMENT_TEXTS["en"])


def month_label(year: int, month: int, language: str) -> str:
    """E.g. "November 2026", "novembro de 2026", "2026年11月"."""
    names = _MONTHS.get(language, _MONTHS["en"])
    pattern = _MONTH_FORMATS.get(language, "{name} {y}")
    return pattern.format(name=names[month - 1], y=year, m=month)


def format_money(amount: float, currency: str, language: str) -> str:
    """E.g. "R$ 1.234,56" (pt-BR), "1.234,56 €" (de), "$1,234.56" (en)."""
    number = f"{amount:,.2f}"
    thousands = _THOUSANDS.get(language)
    if thousands:
        number = number.replace(",", "_").replace(".", ",").replace("_", thousands)
    symbol = _SYMBOLS.get(currency.upper())
    if symbol is None:
        return f"{currency.upper()} {number}"
    if language in _SYMBOL_AFTER:
        return f"{number} {symbol}"
    return f"{symbol} {number}" if len(symbol) > 1 else f"{symbol}{number}"


def payment_title(language: str, *, name: str, amount: float, currency: str) -> str:
    return _payment_texts(language)["title"].format(name=name, amount=format_money(amount, currency, language))


def payment_message(
    language: str,
    *,
    name: str,
    amount: float,
    currency: str,
    year: int,
    month: int,
    pix_key: Optional[str],
    bank_info: Optional[str],
    page_url: Optional[str],
    has_code: bool,
) -> str:
    """How to pay a month's transfer: a direct transfer (PIX key or bank details), the Ibis payment
    page, and the copy-and-paste code (sent as its own message, so it copies cleanly)."""
    texts = _payment_texts(language)
    money = format_money(amount, currency, language)
    ways = []
    if pix_key:
        ways.append(texts["key"].format(key=pix_key))
    elif bank_info:
        ways.append(texts["bank"].format(bank=bank_info))
    if page_url:
        ways.append(texts["link"].format(url=page_url))
    if has_code:
        ways.append(texts["code"])
    lines = [texts["intro"].format(name=name, amount=money, month=month_label(year, month, language)), ""]
    if ways:
        lines.append(texts["ways"])
        lines += [f"{i}) {way}" for i, way in enumerate(ways, start=1)]
    else:
        lines.append(texts["none"].format(name=name))
    return "\n".join(lines)
