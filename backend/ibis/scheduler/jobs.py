"""The scheduled jobs. Each one is a plain function taking a database session.

To add one: write `def my_job(db: Session) -> None`, then add a `Job(...)` to JOBS below.
"""
import logging
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from infrastructure import whatsapp
from infrastructure.config.settings import settings
from models.household import Household
from services.messaging_service import MessagingService
from services.month_service import MonthService
from services.task_service import TaskService

log = logging.getLogger("ibis.scheduler")


@dataclass(frozen=True)
class Job:
    name: str
    run: Callable[[Session], None]
    interval_seconds: Callable[[], float]  # read when needed, so settings can change in tests
    enabled: Callable[[], bool] = lambda: True
    run_at_start: bool = False  # also run once as soon as the API starts


# --- Jobs ------------------------------------------------------------------------------------
def housekeeping(db: Session) -> None:
    """Time-based household work, for every household:

    - create the current and next month (a new month starts in the household's timezone)
    - auto-close months past their deadline (which creates the payment tasks)
    - create the copies of recurring tasks whose date has come
    - send the "about to expire" / "expired" notifications of tasks (in-app, WhatsApp, email)

    One household failing doesn't stop the others.
    """
    for household_id in db.scalars(select(Household.id)).all():
        household = db.get(Household, household_id)
        try:
            MonthService(db).sync(household)
            TaskService(db).sync(household)
        except Exception:
            db.rollback()
            log.exception("Housekeeping failed for household %s", household_id)


def deliver_messages(db: Session) -> None:
    """Send queued WhatsApp messages (retries included)."""
    MessagingService(db).deliver_pending()


JOBS: list[Job] = [
    Job(
        name="housekeeping",
        run=housekeeping,
        interval_seconds=lambda: settings.housekeeping_interval_minutes * 60,
        run_at_start=True,
    ),
    Job(
        name="deliver_messages",
        run=deliver_messages,
        interval_seconds=lambda: settings.whatsapp_send_interval_seconds,
        enabled=whatsapp.is_configured,
    ),
]
