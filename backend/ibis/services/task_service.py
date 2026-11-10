import calendar
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.money import from_cents
from domain.months import last_day, today_in
from domain.roles import MIN_ROLE_ADD_TASK, MIN_ROLE_COMPLETE_ANY_TASK, Role, has_role
from domain.task_labels import KEY_BILLS, KIND_CATEGORY, KIND_LOCATION
from domain.tasks import PAYMENT_TASK_DAYS, is_expiring_window, latest_occurrence, task_status
from models.household import Household
from models.member import HouseholdMember
from models.month import HouseholdMonth
from models.notification import KIND_MONTH_PAYMENT, KIND_TASK_EXPIRED, KIND_TASK_EXPIRING
from models.task import (
    ASSIGN_EVERYONE,
    ASSIGN_EVERYONE_GUESTS,
    KIND_MANUAL,
    KIND_MONTH_PAYMENT as TASK_KIND_MONTH_PAYMENT,
    KIND_RECURRING,
    SHARED_FLAGS,
    RecurringTask,
    Task,
    task_assignees,
)
from models.user import User
from repositories.cost_repository import CostRepository
from repositories.member_repository import MemberRepository
from schemas.task_schemas import TaskCreate, TaskRead, TaskUpdate
from services.context import HouseholdContext
from services.errors import NotFoundError, PermissionDeniedError
from services.member_service import MemberService, sort_members
from services.messaging_service import MessagingService
from services.notification_service import NotificationService
from services.split import split_costs
from services.task_label_service import TaskLabelService


def _now() -> datetime:
    return datetime.now(timezone.utc)


def month_group_key(month: HouseholdMonth) -> str:
    return f"month_payment:{month.household_id}:{month.year:04d}-{month.month:02d}"


def _wants(event: str):
    """SQL: the task asks for any notification (in-app or another channel) on this event."""
    columns = [getattr(Task, f"notify_{event}{suffix}") for suffix in ("", "_whatsapp", "_email", "_groups")]
    return or_(*columns)


def _active(members: list[HouseholdMember]) -> list[HouseholdMember]:
    return [m for m in members if m.is_active and m.user.is_active]


class TaskService:
    """Household tasks: the list, adding/editing/completing, payment tasks for closed months,
    recurring copies and due-date notifications (the last two run lazily in `sync`)."""

    def __init__(self, db: Session):
        self.db = db
        self.members = MemberService(db)
        self.notifications = NotificationService(db)
        self.messaging = MessagingService(db)
        self.labels = TaskLabelService(db)

    # --- Permissions -----------------------------------------------------------------------
    @staticmethod
    def is_assigned(ctx: HouseholdContext, task: Task) -> bool:
        return ctx.member is not None and any(m.id == ctx.member.id for m in task.assignees)

    def can_see(self, ctx: HouseholdContext, task: Task) -> bool:
        return ctx.sees_all_tasks or self.is_assigned(ctx, task)

    def is_hidden(self, ctx: HouseholdContext, task: Task) -> bool:
        """A private task's title and description are only for the people assigned to it."""
        return task.is_private and not self.is_assigned(ctx, task)

    def can_edit(self, ctx: HouseholdContext, task: Task) -> bool:
        """Managers edit any task; residents the ones they added. Nobody edits a task they can't read."""
        return not self.is_hidden(ctx, task) and self.can_delete(ctx, task)

    @staticmethod
    def can_delete(ctx: HouseholdContext, task: Task) -> bool:
        """Managers delete any task; residents the ones they added."""
        if ctx.can_manage:
            return True
        return ctx.can_add_task and task.created_by_user_id == ctx.user.id

    def can_complete(self, ctx: HouseholdContext, task: Task) -> bool:
        if has_role(ctx.role, MIN_ROLE_COMPLETE_ANY_TASK):
            return True
        return ctx.role == Role.GUEST and self.is_assigned(ctx, task)

    # --- Reading ---------------------------------------------------------------------------
    def list_tasks(
        self,
        ctx: HouseholdContext,
        include_completed: bool = False,
        assignee_id: Optional[uuid.UUID] = None,
        due_month: Optional[tuple[int, int]] = None,
        category_id: Optional[uuid.UUID] = None,
        location_id: Optional[uuid.UUID] = None,
    ) -> list[Task]:
        """Ordered by due date (oldest first; no due date last), then by when they were added."""
        query = select(Task).where(Task.household_id == ctx.household.id)
        if not include_completed:
            query = query.where(Task.completed_at.is_(None))
        if category_id:
            query = query.where(Task.category_id == category_id)
        if location_id:
            query = query.where(Task.location_id == location_id)
        if due_month:
            year, month = due_month
            query = query.where(Task.due_date >= date(year, month, 1), Task.due_date <= last_day(year, month))
        must_include = [assignee_id] if assignee_id else []
        if not ctx.sees_all_tasks:
            must_include.append(ctx.member.id)  # guests: only their own tasks
        for member_id in must_include:
            alias = task_assignees.alias()
            query = query.join(alias, alias.c.task_id == Task.id).where(alias.c.member_id == member_id)
        query = query.order_by(Task.due_date.is_(None), Task.due_date, Task.created_at)
        return list(self.db.scalars(query).unique())

    def get(self, ctx: HouseholdContext, task_id: uuid.UUID) -> Task:
        task = self.db.get(Task, task_id)
        if task is None or task.household_id != ctx.household.id or not self.can_see(ctx, task):
            raise NotFoundError("Task not found")
        return task

    def to_read(self, ctx: HouseholdContext, task: Task, today: Optional[date] = None) -> TaskRead:
        today = today or today_in(ctx.household.timezone)
        hidden = self.is_hidden(ctx, task)
        return TaskRead(
            id=task.id,
            title="" if hidden else task.title,
            category_id=task.category_id,
            category_name=task.category.name if task.category else None,
            location_id=task.location_id,
            location_name=task.location.name if task.location else None,
            description=None if hidden else task.description,
            kind=task.kind,
            data={} if hidden else (task.data or {}),
            due_date=task.due_date,
            warn_days=task.warn_days,
            **{flag: getattr(task, flag) for flag in SHARED_FLAGS},
            is_hidden=hidden,
            status=task_status(task.due_date, task.is_completed, today, task.warn_days),
            assignee_ids=[m.id for m in sort_members(task.assignees)],
            recurring_task_id=task.recurring_task_id,
            created_by_user_id=task.created_by_user_id,
            created_by_name=self._user_name(task.created_by_user_id),
            created_at=task.created_at,
            completed_at=task.completed_at,
            completed_by_name=self._user_name(task.completed_by_user_id),
            can_edit=self.can_edit(ctx, task),
            can_delete=self.can_delete(ctx, task),
            can_complete=self.can_complete(ctx, task),
        )

    def _user_name(self, user_id: Optional[uuid.UUID]) -> Optional[str]:
        user = self.db.get(User, user_id) if user_id else None
        return user.display_name if user else None

    # --- User actions ----------------------------------------------------------------------
    def create(self, ctx: HouseholdContext, data: TaskCreate) -> Task:
        ctx.require(MIN_ROLE_ADD_TASK)
        task = Task(household_id=ctx.household.id, kind=KIND_MANUAL, created_by_user_id=ctx.user.id, data={})
        self._apply(ctx, task, data)
        self.db.add(task)
        self.db.flush()
        self._send_due_notifications(ctx.household, [task])
        self.db.commit()
        self.db.refresh(task)
        return task

    def update(self, ctx: HouseholdContext, task_id: uuid.UUID, data: TaskUpdate) -> Task:
        task = self.get(ctx, task_id)
        if not self.can_edit(ctx, task):
            raise PermissionDeniedError("You can only edit tasks you added")
        timing = (task.due_date, task.warn_days)
        self._apply(ctx, task, data, current_ids={m.id for m in task.assignees})
        if (task.due_date, task.warn_days) != timing:
            # New timing: the due-date notifications can go out again
            task.expiring_notified_at = None
            task.expired_notified_at = None
        self._send_due_notifications(ctx.household, [task])
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete(self, ctx: HouseholdContext, task_id: uuid.UUID) -> None:
        task = self.get(ctx, task_id)
        if not self.can_delete(ctx, task):
            raise PermissionDeniedError("You can only delete tasks you added")
        self.notifications.drop_for_tasks([task.id])
        self.db.delete(task)
        self.db.commit()

    def complete(self, ctx: HouseholdContext, task_id: uuid.UUID, completed: bool = True) -> Task:
        task = self.get(ctx, task_id)
        if not self.can_complete(ctx, task):
            raise PermissionDeniedError("Only the people assigned to this task can complete it")
        if completed and task.completed_at is None:
            task.completed_at = _now()
            task.completed_by_user_id = ctx.user.id
            self.notifications.mark_task_viewed(task.id)
        elif not completed:
            task.completed_at = None
            task.completed_by_user_id = None
        self.db.commit()
        self.db.refresh(task)
        return task

    def _apply(self, ctx: HouseholdContext, task: Task, data: TaskCreate, current_ids: set = frozenset()) -> None:
        task.title = data.title.strip()
        task.category = self.labels.resolve(ctx.household.id, data.category_id, KIND_CATEGORY)
        task.location = self.labels.resolve(ctx.household.id, data.location_id, KIND_LOCATION)
        task.description = (data.description or "").strip() or None
        task.due_date = data.due_date
        task.warn_days = data.warn_days
        for flag in SHARED_FLAGS:
            setattr(task, flag, getattr(data, flag))
        task.assignees = self.members.resolve_assignees(ctx.household.id, data.assignee_ids, current_ids)

    # --- Closing months: one payment task per transfer -------------------------------------
    def month_closed(self, household: Household, month: HouseholdMonth) -> None:
        """Give each person who has to pay a task (due in 3 days) and a note linking to it.

        Replaces the open payment tasks of an earlier close of the same month (amounts may have
        changed); completed ones are kept. Flushes; the caller commits.
        """
        group = month_group_key(month)
        self._drop_open_group(group)
        _, transfers = split_costs(CostRepository(self.db).list_for_month(month.id))
        members = {m.id: m for m in MemberRepository(self.db).list_ordered(household.id)}
        label = f"{calendar.month_name[month.month]} {month.year}"
        due = today_in(household.timezone) + timedelta(days=PAYMENT_TASK_DAYS)
        bills = self.labels.by_key(household.id, KIND_CATEGORY, KEY_BILLS)  # None if a manager deleted it
        for transfer in transfers:
            debtor, creditor = members.get(transfer.debtor), members.get(transfer.creditor)
            if debtor is None or creditor is None or not _active([debtor]):
                continue
            amount = from_cents(transfer.amount_cents)
            data = {
                "household_name": household.name,
                "year": month.year,
                "month": month.month,
                "to_member_id": str(creditor.id),
                "to_name": creditor.user.display_name,
                "amount": amount,
                "currency": household.currency,
            }
            title = f"Pay {creditor.user.display_name} {household.currency} {amount:.2f} for {label}"
            task = Task(
                household_id=household.id,
                kind=TASK_KIND_MONTH_PAYMENT,
                title=title,
                category=bills,
                data=data,
                group_key=group,
                due_date=due,
                assignees=[debtor],
            )
            self.db.add(task)
            self.db.flush()
            self.notifications.add_note(
                [debtor.user_id],
                household_id=household.id,
                kind=KIND_MONTH_PAYMENT,
                title=title,
                data={**data, "due_date": due.isoformat()},
                task_id=task.id,
                group_key=group,
            )

    def month_reopened(self, month: HouseholdMonth) -> None:
        """Amounts can change again, so the month's open payment tasks go away until it closes again."""
        self._drop_open_group(month_group_key(month))
        self.db.flush()

    def _drop_open_group(self, group_key: str) -> None:
        open_tasks = list(
            self.db.scalars(select(Task).where(Task.group_key == group_key, Task.completed_at.is_(None))).unique()
        )
        self.notifications.drop_for_tasks([t.id for t in open_tasks])
        for task in open_tasks:
            self.db.delete(task)
        self.db.flush()

    # --- Housekeeping (no worker: runs whenever the household is opened) ------------------
    def sync(self, household: Household) -> None:
        """Create due copies of recurring tasks, then send due-date notifications."""
        today = today_in(household.timezone)
        changed = self._create_recurring(household, today)
        pending = list(
            self.db.scalars(
                select(Task).where(
                    Task.household_id == household.id,
                    Task.completed_at.is_(None),
                    Task.due_date.is_not(None),
                    (_wants("expiring") & Task.expiring_notified_at.is_(None))
                    | (_wants("expired") & Task.expired_notified_at.is_(None)),
                )
            ).unique()
        )
        changed |= self._send_due_notifications(household, pending, today)
        if changed:
            self.db.commit()

    def _send_due_notifications(self, household: Household, tasks: list[Task], today: Optional[date] = None) -> bool:
        """'Expiring' when a task enters its warning window, 'expired' once it is past due (each sent once).

        Each event goes to whatever the task's flags ask for: an in-app note to the assignees, and/or
        WhatsApp (assignees, household groups) and email (placeholder) through MessagingService.
        """
        today = today or today_in(household.timezone)
        changed = False
        for task in tasks:
            if task.is_completed or task.due_date is None:
                continue
            event = None
            if task.due_date < today:
                if task.notify_any("expired") and task.expired_notified_at is None:
                    event = "expired"
                    task.expired_notified_at = _now()
                if task.expiring_notified_at is None:
                    task.expiring_notified_at = _now()  # its warning window has passed
                    changed = True
            elif task.notify_any("expiring") and task.expiring_notified_at is None and is_expiring_window(
                task.due_date, today, task.warn_days
            ):
                event = "expiring"
                task.expiring_notified_at = _now()
            if event is None:
                continue
            changed = True
            self.messaging.task_due(household, task, event)
            if not getattr(task, f"notify_{event}"):
                continue  # no in-app note asked for
            kind = KIND_TASK_EXPIRED if event == "expired" else KIND_TASK_EXPIRING
            word = "is overdue" if kind == KIND_TASK_EXPIRED else "is due soon"
            self.notifications.add_note(
                [m.user_id for m in _active(task.assignees)],
                household_id=household.id,
                kind=kind,
                title=f"{task.title} {word} ({task.due_date.isoformat()})",
                data={"household_name": household.name, "task_title": task.title, "due_date": task.due_date.isoformat()},
                task_id=task.id,
            )
        return changed

    def _create_recurring(self, household: Household, today: date) -> bool:
        """For each active recurring task whose latest scheduled date hasn't been handled yet, create
        one copy (missed dates never pile up). With "wait for the previous one", a date that arrives
        while the last copy is still open is skipped."""
        definitions = self.db.scalars(
            select(RecurringTask).where(RecurringTask.household_id == household.id, RecurringTask.is_active.is_(True))
        ).unique()
        changed = False
        for item in definitions:
            scheduled = latest_occurrence(item.start_date, item.interval, item.unit, today)
            if scheduled is None or (item.last_occurrence_date and scheduled <= item.last_occurrence_date):
                continue
            changed = True
            item.last_occurrence_date = scheduled
            self.db.flush()  # outside the savepoint below, so a lost race can't roll it back
            if item.wait_for_previous and self._has_open_copy(item):
                continue
            try:
                with self.db.begin_nested():
                    self.db.add(
                        Task(
                            household_id=household.id,
                            kind=KIND_RECURRING,
                            title=item.title,
                            category_id=item.category_id,
                            location_id=item.location_id,
                            description=item.description,
                            data={},
                            warn_days=item.warn_days,
                            **{flag: getattr(item, flag) for flag in SHARED_FLAGS},
                            due_date=scheduled + timedelta(days=item.due_offset_days),
                            recurring_task_id=item.id,
                            occurrence_date=scheduled,
                            created_by_user_id=item.created_by_user_id,
                            assignees=self._recurring_assignees(item),
                        )
                    )
                    self.db.flush()
            except IntegrityError:
                pass  # someone opening the household at the same moment already created it
        return changed

    def _has_open_copy(self, item: RecurringTask) -> bool:
        return (
            self.db.scalar(
                select(Task.id).where(Task.recurring_task_id == item.id, Task.completed_at.is_(None)).limit(1)
            )
            is not None
        )

    def _recurring_assignees(self, item: RecurringTask) -> list[HouseholdMember]:
        """"Everyone" is resolved when each copy is created, so it follows who lives there now."""
        if item.assign_mode in (ASSIGN_EVERYONE, ASSIGN_EVERYONE_GUESTS):
            roles = {Role.MANAGER.value, Role.RESIDENT.value}
            if item.assign_mode == ASSIGN_EVERYONE_GUESTS:
                roles.add(Role.GUEST.value)
            return [m for m in _active(MemberRepository(self.db).list_ordered(item.household_id)) if m.role in roles]
        return sort_members(m for m in _active(item.assignees) if m.role != Role.VIEWER.value)
