"""Messages that leave the app (WhatsApp now, email later).

Producers queue `OutgoingMessage` rows inside their own transaction; `deliver_pending` (run by a
loop in the API process, see main.py) sends them, retrying a few times when the service is down.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from domain.messages import MessageEvent, payment_message, payment_test_intro, payment_title, task_due_message
from domain.months import today_in
from domain.phones import default_country_for, whatsapp_number
from domain.pix import payment_details, payment_page_url
from infrastructure import whatsapp
from infrastructure.config.settings import settings
from models.household import Household
from models.messaging import (
    CHANNEL_WHATSAPP,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_SENT,
    OutgoingMessage,
    WhatsAppGroup,
)
from models.task import KIND_MONTH_PAYMENT, Task
from services.member_service import sort_members

log = logging.getLogger("ibis.messaging")

# Wait this long before each retry; after the last one the message is marked failed
RETRY_DELAYS = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30), timedelta(hours=2))
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1
PAYMENT_EXAMPLE_AMOUNT = 10.0  # the sample payment in Settings -> WhatsApp "Send test"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MessagingService:
    def __init__(self, db: Session):
        self.db = db
        self._last_queued: Optional[datetime] = None

    def _next_queue_time(self) -> datetime:
        """Messages are sent oldest first, so ones queued together must not share a time (the database's
        now() is the same for a whole transaction, and the Windows clock often repeats too)."""
        now = _now()
        if self._last_queued is not None and now <= self._last_queued:
            now = self._last_queued + timedelta(microseconds=1)
        self._last_queued = now
        return now

    # --- Producers (they flush; the caller commits) ------------------------------------
    def task_due(self, household: Household, task: Task, event: MessageEvent) -> None:
        """Queue what the task's flags ask for when it starts expiring / is past due."""
        assignees = [m for m in sort_members(task.assignees) if m.is_active and m.user.is_active]
        text_for = lambda people=None: task_due_message(  # noqa: E731
            household.language,
            event,
            household=household.name,
            title=task.title,
            due=task.due_date,
            private=task.is_private and people is not None,  # only group messages hide the title
            people=people,
        )
        payment = task.data if task.kind == KIND_MONTH_PAYMENT else None

        def with_payment(text: str) -> list[str]:
            """Payment tasks add how to pay; the copy-and-paste code goes alone in its own message
            so it copies cleanly. Groups get it too: the household chose to send these to groups."""
            if not payment:
                return [text]
            texts = [text + "\n\n" + self._payment_text(household, payment)]
            if payment.get("pix_code"):
                texts.append(payment["pix_code"])
            return texts

        if getattr(task, f"notify_{event}_whatsapp") and whatsapp.is_configured():
            country = default_country_for(household.currency)
            texts = with_payment(text_for())
            for member in assignees:
                number = whatsapp_number(member.user.whatsapp, country)
                if number:
                    for text in texts:
                        self.queue_whatsapp(household.id, number, member.user.display_name, text)
        if getattr(task, f"notify_{event}_groups") and whatsapp.is_configured():
            texts = with_payment(text_for([m.user.display_name for m in assignees]))
            for group in self.active_groups(household.id):
                for text in texts:
                    self.queue_whatsapp(household.id, group.jid, group.name, text)
        if getattr(task, f"notify_{event}_email"):
            self._queue_email(household, task, event)
        self.db.flush()

    def payment_example(self, household: Household, receiver_name: str, bank_info_type: str, bank_info: str) -> list[str]:
        """A sample payment reminder (R$ 10 to `receiver_name`, due in 3 days), marked as a test, plus
        its PIX code: what a payer gets when a month closes. Used by Settings -> WhatsApp "Send test"."""
        today = today_in(household.timezone)
        amount = PAYMENT_EXAMPLE_AMOUNT
        data = {
            "to_name": receiver_name,
            "amount": amount,
            "currency": household.currency,
            "year": today.year,
            "month": today.month,
            **payment_details(bank_info_type, bank_info, receiver_name, amount, household.currency),
        }
        reminder = task_due_message(
            household.language,
            "expiring",
            household=household.name,
            title=payment_title(household.language, name=receiver_name, amount=amount, currency=household.currency),
            due=today + timedelta(days=3),
        )
        texts = [f"{payment_test_intro(household.language)}\n\n{reminder}\n\n{self._payment_text(household, data)}"]
        if data["pix_code"]:
            texts.append(data["pix_code"])
        return texts

    @staticmethod
    def _payment_text(household: Household, data: dict) -> str:
        """The ways to pay a month-close payment task (see domain/messages.py payment_message)."""
        page_url = None
        if data.get("pix_code") and settings.app_url:
            page_url = payment_page_url(settings.app_url, data["pix_key"], data["to_name"], data["amount"], household.language)
        return payment_message(
            household.language,
            name=data["to_name"],
            amount=data["amount"],
            currency=data["currency"],
            year=data["year"],
            month=data["month"],
            pix_key=data.get("pix_key"),
            bank_info=data.get("bank_info"),
            page_url=page_url,
            has_code=bool(data.get("pix_code")),
        )

    def queue_whatsapp(self, household_id, recipient: str, label: str, text: str) -> OutgoingMessage:
        message = OutgoingMessage(
            household_id=household_id,
            channel=CHANNEL_WHATSAPP,
            recipient=recipient,
            recipient_label=label[:200],
            text=text,
            status=STATUS_PENDING,
            attempts=0,
            created_at=self._next_queue_time(),
        )
        self.db.add(message)
        return message

    def _queue_email(self, household: Household, task: Task, event: MessageEvent) -> None:
        """Placeholder: email isn't set up yet. The task flags are stored, so this is the only piece to fill in."""

    def active_groups(self, household_id) -> list[WhatsAppGroup]:
        return list(
            self.db.scalars(
                select(WhatsAppGroup)
                .where(WhatsAppGroup.household_id == household_id, WhatsAppGroup.is_active.is_(True))
                .order_by(WhatsAppGroup.name)
            )
        )

    # --- Delivery ----------------------------------------------------------------------------
    def deliver_pending(self, limit: int = 20) -> int:
        """Send queued WhatsApp messages that are due. Returns how many were sent."""
        if not whatsapp.is_configured():
            return 0
        now = _now()
        due = list(
            self.db.scalars(
                select(OutgoingMessage)
                .where(
                    OutgoingMessage.channel == CHANNEL_WHATSAPP,
                    OutgoingMessage.status == STATUS_PENDING,
                    or_(OutgoingMessage.next_attempt_at.is_(None), OutgoingMessage.next_attempt_at <= now),
                )
                .order_by(OutgoingMessage.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        sent = 0
        for message in due:
            try:
                whatsapp.send(message.household_id, message.recipient, message.text)
            except whatsapp.WhatsAppError as exc:
                message.attempts += 1
                message.last_error = exc.message[:1000]
                if message.attempts >= MAX_ATTEMPTS or exc.status in (400, 404):
                    # 400/404: bad number or unknown group; retrying won't help
                    message.status = STATUS_FAILED
                else:
                    message.next_attempt_at = _now() + RETRY_DELAYS[message.attempts - 1]
                log.warning("WhatsApp message %s not sent: %s", message.id, exc.message)
            else:
                message.attempts += 1
                message.status = STATUS_SENT
                message.sent_at = _now()
                message.last_error = None
                sent += 1
        self.db.commit()
        return sent
