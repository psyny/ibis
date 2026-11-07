import calendar
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from domain.money import from_cents
from models.household import Household
from models.month import HouseholdMonth
from models.notification import KIND_MONTH_PAYMENT, TYPE_NOTE, TYPE_TASK, Notification
from models.user import User
from repositories.cost_repository import CostRepository
from repositories.member_repository import MemberRepository
from schemas.notification_schemas import NotificationBox
from services.errors import NotFoundError, ValidationError
from services.split import split_costs

BAR_LIMIT = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def month_group_key(month: HouseholdMonth) -> str:
    return f"month_payment:{month.household_id}:{month.year:04d}-{month.month:02d}"


class NotificationService:
    """Per-user inbox. Producers (e.g. closing a month) add items; the user views, completes or deletes them."""

    def __init__(self, db: Session):
        self.db = db

    # --- Producers (they flush; the caller commits) ------------------------------------
    def month_closed(self, household: Household, month: HouseholdMonth) -> None:
        """Send each person who has to pay something a task with their transfer.

        Replaces the open tasks of an earlier close of the same month (amounts may have changed);
        completed ones are kept.
        """
        group = month_group_key(month)
        self._drop_open(group)
        _, transfers = split_costs(CostRepository(self.db).list_for_month(month.id))
        members = {m.id: m for m in MemberRepository(self.db).list_ordered(household.id)}
        label = f"{calendar.month_name[month.month]} {month.year}"
        for transfer in transfers:
            debtor, creditor = members.get(transfer.debtor), members.get(transfer.creditor)
            if debtor is None or creditor is None or not debtor.is_active or not debtor.user.is_active:
                continue
            amount = from_cents(transfer.amount_cents)
            self.db.add(
                Notification(
                    user_id=debtor.user_id,
                    household_id=household.id,
                    type=TYPE_TASK,
                    kind=KIND_MONTH_PAYMENT,
                    title=f"Pay {creditor.user.display_name} {household.currency} {amount:.2f} for {label}",
                    data={
                        "household_name": household.name,
                        "year": month.year,
                        "month": month.month,
                        "to_member_id": str(creditor.id),
                        "to_name": creditor.user.display_name,
                        "amount": amount,
                        "currency": household.currency,
                    },
                    group_key=group,
                )
            )
        self.db.flush()

    def month_reopened(self, month: HouseholdMonth) -> None:
        """Amounts can change again, so the month's pending payment tasks go away until it closes again."""
        self._drop_open(month_group_key(month))
        self.db.flush()

    def _drop_open(self, group_key: str) -> None:
        self.db.execute(
            delete(Notification).where(Notification.group_key == group_key, Notification.completed_at.is_(None))
        )

    # --- Reading ---------------------------------------------------------------------------
    def list_box(self, user: User, box: NotificationBox) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user.id)
        if box == "deleted":
            query = query.where(Notification.deleted_at.is_not(None))
        elif box == "completed":
            query = query.where(Notification.deleted_at.is_(None), Notification.completed_at.is_not(None))
        else:
            query = query.where(Notification.deleted_at.is_(None), Notification.completed_at.is_(None))
        return list(self.db.scalars(query.order_by(Notification.created_at.desc())))

    def bar(self, user: User) -> tuple[list[Notification], int]:
        """Latest notes not viewed yet and tasks not completed yet (up to 5), plus the inbox's unviewed count."""
        pending = and_(
            Notification.user_id == user.id,
            Notification.deleted_at.is_(None),
            or_(
                and_(Notification.type == TYPE_NOTE, Notification.viewed_at.is_(None)),
                and_(Notification.type == TYPE_TASK, Notification.completed_at.is_(None)),
            ),
        )
        items = list(
            self.db.scalars(select(Notification).where(pending).order_by(Notification.created_at.desc()).limit(BAR_LIMIT))
        )
        unviewed = self.db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user.id,
                Notification.deleted_at.is_(None),
                Notification.completed_at.is_(None),
                Notification.viewed_at.is_(None),
            )
        )
        return items, unviewed or 0

    # --- User actions ----------------------------------------------------------------------
    def view(self, user: User, notification_id: uuid.UUID) -> Notification:
        found = self._get(user, notification_id)
        if found.viewed_at is None:
            found.viewed_at = _now()
            self.db.commit()
        return found

    def complete(self, user: User, notification_id: uuid.UUID, completed: bool = True) -> Notification:
        found = self._get(user, notification_id)
        if not found.is_task:
            raise ValidationError("Only tasks can be completed")
        found.completed_at = (found.completed_at or _now()) if completed else None
        found.viewed_at = found.viewed_at or _now()
        self.db.commit()
        return found

    def delete(self, user: User, notification_id: uuid.UUID, deleted: bool = True) -> Notification:
        """Soft delete (or restore with deleted=False)."""
        found = self._get(user, notification_id)
        found.deleted_at = (found.deleted_at or _now()) if deleted else None
        self.db.commit()
        return found

    def _get(self, user: User, notification_id: uuid.UUID) -> Notification:
        found = self.db.get(Notification, notification_id)
        if found is None or found.user_id != user.id:
            raise NotFoundError("Notification not found")
        return found
