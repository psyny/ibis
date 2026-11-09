import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from domain.months import today_in
from domain.roles import MIN_ROLE_ADD_TASK
from domain.task_labels import KIND_CATEGORY, KIND_LOCATION
from domain.tasks import latest_occurrence, next_occurrence
from models.task import ASSIGN_SELECTED, RecurringTask
from schemas.task_schemas import RecurringTaskCreate, RecurringTaskRead
from services.context import HouseholdContext
from services.errors import NotFoundError
from services.member_service import MemberService, sort_members
from services.task_label_service import TaskLabelService
from services.task_service import TaskService


def recurring_task_to_read(item: RecurringTask, today: date) -> RecurringTaskRead:
    return RecurringTaskRead(
        id=item.id,
        title=item.title,
        category_id=item.category_id,
        location_id=item.location_id,
        description=item.description,
        start_date=item.start_date,
        interval=item.interval,
        unit=item.unit,
        due_offset_days=item.due_offset_days,
        warn_days=item.warn_days,
        notify_expiring=item.notify_expiring,
        notify_expired=item.notify_expired,
        wait_for_previous=item.wait_for_previous,
        assign_mode=item.assign_mode,
        assignee_ids=[m.id for m in sort_members(item.assignees)],
        is_active=item.is_active,
        last_occurrence_date=item.last_occurrence_date,
        next_date=next_occurrence(item.start_date, item.interval, item.unit, today) if item.is_active else None,
    )


class RecurringTaskService:
    """Definitions of tasks that are created on a schedule. Managers and residents manage them."""

    def __init__(self, db: Session):
        self.db = db
        self.members = MemberService(db)

    def list_items(self, ctx: HouseholdContext) -> list[RecurringTask]:
        ctx.require(MIN_ROLE_ADD_TASK)
        return list(
            self.db.scalars(
                select(RecurringTask)
                .where(RecurringTask.household_id == ctx.household.id)
                .order_by(RecurringTask.is_active.desc(), func.lower(RecurringTask.title))
            ).unique()
        )

    def get(self, ctx: HouseholdContext, item_id: uuid.UUID) -> RecurringTask:
        ctx.require(MIN_ROLE_ADD_TASK)
        item = self.db.get(RecurringTask, item_id)
        if item is None or item.household_id != ctx.household.id:
            raise NotFoundError("Recurring task not found")
        return item

    def create(self, ctx: HouseholdContext, data: RecurringTaskCreate) -> RecurringTask:
        """A start date in the past creates one copy for the latest scheduled date right away."""
        ctx.require(MIN_ROLE_ADD_TASK)
        item = RecurringTask(household_id=ctx.household.id, created_by_user_id=ctx.user.id)
        self._apply(ctx, item, data)
        self.db.add(item)
        self.db.commit()
        TaskService(self.db).sync(ctx.household)  # a schedule starting today creates its first task now
        self.db.refresh(item)
        return item

    def update(self, ctx: HouseholdContext, item_id: uuid.UUID, data: RecurringTaskCreate) -> RecurringTask:
        item = self.get(ctx, item_id)
        schedule = (item.start_date, item.interval, item.unit)
        self._apply(ctx, item, data, current_ids={m.id for m in item.assignees})
        if (item.start_date, item.interval, item.unit) != schedule:
            # New schedule: create copies from today on, without catching up on past dates
            yesterday = today_in(ctx.household.timezone) - timedelta(days=1)
            item.last_occurrence_date = latest_occurrence(item.start_date, item.interval, item.unit, yesterday)
        self.db.commit()
        TaskService(self.db).sync(ctx.household)
        self.db.refresh(item)
        return item

    def delete(self, ctx: HouseholdContext, item_id: uuid.UUID) -> None:
        """Tasks it already created stay."""
        self.db.delete(self.get(ctx, item_id))
        self.db.commit()

    def _apply(self, ctx: HouseholdContext, item: RecurringTask, data: RecurringTaskCreate, current_ids: set = frozenset()) -> None:
        item.title = data.title.strip()
        labels = TaskLabelService(self.db)
        item.category = labels.resolve(ctx.household.id, data.category_id, KIND_CATEGORY)
        item.location = labels.resolve(ctx.household.id, data.location_id, KIND_LOCATION)
        item.description = (data.description or "").strip() or None
        item.start_date = data.start_date
        item.interval = data.interval
        item.unit = data.unit
        item.due_offset_days = data.due_offset_days
        item.warn_days = data.warn_days
        item.notify_expiring = data.notify_expiring
        item.notify_expired = data.notify_expired
        item.wait_for_previous = data.wait_for_previous
        item.assign_mode = data.assign_mode
        item.is_active = data.is_active
        # The fixed list only matters in "selected" mode; "everyone" is resolved when each task is created
        ids = data.assignee_ids if data.assign_mode == ASSIGN_SELECTED else []
        item.assignees = self.members.resolve_assignees(ctx.household.id, ids, current_ids)
