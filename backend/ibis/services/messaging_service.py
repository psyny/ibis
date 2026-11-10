"""Messages that leave the app (WhatsApp now, email later).

Producers queue `OutgoingMessage` rows inside their own transaction; `deliver_pending` (run by a
loop in the API process, see main.py) sends them, retrying a few times when the service is down.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from domain.messages import MessageEvent, task_due_message
from domain.phones import default_country_for, whatsapp_number
from infrastructure import whatsapp
from models.household import Household
from models.messaging import (
    CHANNEL_WHATSAPP,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_SENT,
    OutgoingMessage,
    WhatsAppGroup,
)
from models.task import Task
from services.member_service import sort_members

log = logging.getLogger("ibis.messaging")

# Wait this long before each retry; after the last one the message is marked failed
RETRY_DELAYS = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30), timedelta(hours=2))
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MessagingService:
    def __init__(self, db: Session):
        self.db = db

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
        if getattr(task, f"notify_{event}_whatsapp") and whatsapp.is_configured():
            country = default_country_for(household.currency)
            text = text_for()
            for member in assignees:
                number = whatsapp_number(member.user.whatsapp, country)
                if number:
                    self.queue_whatsapp(household.id, number, member.user.display_name, text)
        if getattr(task, f"notify_{event}_groups") and whatsapp.is_configured():
            text = text_for([m.user.display_name for m in assignees])
            for group in self.active_groups(household.id):
                self.queue_whatsapp(household.id, group.jid, group.name, text)
        if getattr(task, f"notify_{event}_email"):
            self._queue_email(household, task, event)
        self.db.flush()

    def queue_whatsapp(self, household_id, recipient: str, label: str, text: str) -> OutgoingMessage:
        message = OutgoingMessage(
            household_id=household_id,
            channel=CHANNEL_WHATSAPP,
            recipient=recipient,
            recipient_label=label[:200],
            text=text,
            status=STATUS_PENDING,
            attempts=0,
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
