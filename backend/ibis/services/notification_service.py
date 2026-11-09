import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from models.notification import TYPE_NOTE, Notification
from models.user import User
from schemas.notification_schemas import NotificationBox
from services.errors import NotFoundError

BAR_LIMIT = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


class NotificationService:
    """Per-user inbox of notes. Producers (e.g. tasks) add notes; the user views (reads) or deletes them."""

    def __init__(self, db: Session):
        self.db = db

    # --- Producers (they flush; the caller commits) ------------------------------------
    def add_note(
        self,
        user_ids: Iterable[uuid.UUID],
        *,
        household_id: Optional[uuid.UUID],
        kind: str,
        title: str,
        data: dict[str, Any],
        task_id: Optional[uuid.UUID] = None,
        group_key: Optional[str] = None,
    ) -> None:
        for user_id in dict.fromkeys(user_ids):  # one note per person
            self.db.add(
                Notification(
                    user_id=user_id,
                    household_id=household_id,
                    type=TYPE_NOTE,
                    kind=kind,
                    title=title,
                    data=data,
                    task_id=task_id,
                    group_key=group_key,
                )
            )
        self.db.flush()

    def drop_for_tasks(self, task_ids: list[uuid.UUID]) -> None:
        """Remove the notes about tasks that are being deleted."""
        if task_ids:
            self.db.execute(delete(Notification).where(Notification.task_id.in_(task_ids)))

    def mark_task_viewed(self, task_id: uuid.UUID) -> None:
        """A completed task's notes no longer need attention: take them out of everyone's bar."""
        self.db.execute(
            update(Notification)
            .where(Notification.task_id == task_id, Notification.viewed_at.is_(None))
            .values(viewed_at=_now())
        )

    # --- Reading ---------------------------------------------------------------------------
    def list_box(self, user: User, box: NotificationBox) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user.id)
        if box == "deleted":
            query = query.where(Notification.deleted_at.is_not(None))
        else:
            query = query.where(Notification.deleted_at.is_(None))
        return list(self.db.scalars(query.order_by(Notification.created_at.desc())))

    def bar(self, user: User) -> tuple[list[Notification], int]:
        """Latest notes not viewed yet (up to 5), plus how many there are."""
        unread = (
            Notification.user_id == user.id,
            Notification.deleted_at.is_(None),
            Notification.viewed_at.is_(None),
        )
        items = list(
            self.db.scalars(select(Notification).where(*unread).order_by(Notification.created_at.desc()).limit(BAR_LIMIT))
        )
        unviewed = self.db.scalar(select(func.count(Notification.id)).where(*unread))
        return items, unviewed or 0

    # --- User actions ----------------------------------------------------------------------
    def view(self, user: User, notification_id: uuid.UUID) -> Notification:
        found = self._get(user, notification_id)
        if found.viewed_at is None:
            found.viewed_at = _now()
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
