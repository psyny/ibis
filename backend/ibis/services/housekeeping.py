"""Lazy housekeeping: there is no worker, so this runs whenever a household is opened (and at startup)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.household import Household
from services.month_service import MonthService
from services.task_service import TaskService


def sync_household(db: Session, household: Household) -> None:
    """Create the current/next month, auto-close months, create recurring tasks, send due-date notes."""
    MonthService(db).sync(household)
    TaskService(db).sync(household)


def sync_all(db: Session) -> None:
    for household in db.scalars(select(Household)):
        sync_household(db, household)
