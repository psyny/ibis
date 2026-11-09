import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from domain.roles import MIN_ROLE_MANAGE
from domain.task_labels import default_labels
from models.household import Household
from models.task import TaskLabel
from schemas.task_schemas import TaskLabelCreate, TaskLabelUpdate
from services.context import HouseholdContext
from services.errors import ConflictError, NotFoundError, ValidationError


class TaskLabelService:
    """The household's task categories and locations. Everyone reads them; managers edit them."""

    def __init__(self, db: Session):
        self.db = db

    def list_labels(self, household_id: uuid.UUID) -> list[TaskLabel]:
        return list(
            self.db.scalars(
                select(TaskLabel)
                .where(TaskLabel.household_id == household_id)
                .order_by(TaskLabel.kind, TaskLabel.position, func.lower(TaskLabel.name))
            )
        )

    def seed_defaults(self, household: Household) -> None:
        """The initial lists of a new household (flushes; the caller commits)."""
        for position, (kind, key, name) in enumerate(default_labels(household.language)):
            self.db.add(TaskLabel(household_id=household.id, kind=kind, key=key, name=name, position=position))
        self.db.flush()

    def by_key(self, household_id: uuid.UUID, kind: str, key: str) -> Optional[TaskLabel]:
        return self.db.scalar(
            select(TaskLabel).where(TaskLabel.household_id == household_id, TaskLabel.kind == kind, TaskLabel.key == key)
        )

    def resolve(self, household_id: uuid.UUID, label_id: Optional[uuid.UUID], kind: str) -> Optional[TaskLabel]:
        """Check a category/location picked for a task belongs to this household's list."""
        if label_id is None:
            return None
        label = self.db.get(TaskLabel, label_id)
        if label is None or label.household_id != household_id or label.kind != kind:
            raise ValidationError(f"Unknown task {kind}")
        return label

    def create(self, ctx: HouseholdContext, data: TaskLabelCreate) -> TaskLabel:
        ctx.require(MIN_ROLE_MANAGE)
        name = data.name.strip()
        self._check_unique(ctx.household.id, data.kind, name)
        last = self.db.scalar(
            select(func.max(TaskLabel.position)).where(
                TaskLabel.household_id == ctx.household.id, TaskLabel.kind == data.kind
            )
        )
        label = TaskLabel(household_id=ctx.household.id, kind=data.kind, name=name, position=(last or 0) + 1)
        self.db.add(label)
        self.db.commit()
        self.db.refresh(label)
        return label

    def update(self, ctx: HouseholdContext, label_id: uuid.UUID, data: TaskLabelUpdate) -> TaskLabel:
        ctx.require(MIN_ROLE_MANAGE)
        label = self._get(ctx, label_id)
        name = data.name.strip()
        self._check_unique(ctx.household.id, label.kind, name, except_id=label.id)
        label.name = name
        self.db.commit()
        self.db.refresh(label)
        return label

    def delete(self, ctx: HouseholdContext, label_id: uuid.UUID) -> None:
        """Tasks that used it keep everything else; their category/location becomes empty."""
        ctx.require(MIN_ROLE_MANAGE)
        self.db.delete(self._get(ctx, label_id))
        self.db.commit()
        self.db.expire_all()  # the database cleared it from tasks (ON DELETE SET NULL)

    def _get(self, ctx: HouseholdContext, label_id: uuid.UUID) -> TaskLabel:
        label = self.db.get(TaskLabel, label_id)
        if label is None or label.household_id != ctx.household.id:
            raise NotFoundError("Not found")
        return label

    def _check_unique(self, household_id: uuid.UUID, kind: str, name: str, except_id: Optional[uuid.UUID] = None) -> None:
        clash = self.db.scalar(
            select(TaskLabel.id).where(
                TaskLabel.household_id == household_id,
                TaskLabel.kind == kind,
                func.lower(TaskLabel.name) == name.lower(),
            )
        )
        if clash is not None and clash != except_id:
            raise ConflictError(f"'{name}' is already in the list")
