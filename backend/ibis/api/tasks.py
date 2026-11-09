import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import household_context
from db.session import get_db
from domain.months import today_in
from domain.roles import MIN_ROLE_ADD_TASK, MIN_ROLE_MANAGE, MIN_ROLE_VIEW
from schemas.task_schemas import (
    RecurringTaskCreate,
    RecurringTaskRead,
    RecurringTaskUpdate,
    TaskCreate,
    TaskLabelCreate,
    TaskLabelRead,
    TaskLabelUpdate,
    TaskRead,
    TaskUpdate,
)
from services.context import HouseholdContext
from services.recurring_task_service import RecurringTaskService, recurring_task_to_read
from services.task_label_service import TaskLabelService
from services.task_service import TaskService

router = APIRouter(prefix="/api/households/{household_id}", tags=["tasks"])

view = household_context(MIN_ROLE_VIEW)
add_task = household_context(MIN_ROLE_ADD_TASK)
manage = household_context(MIN_ROLE_MANAGE)


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(
    include_completed: bool = False,
    assignee_id: Optional[uuid.UUID] = None,
    due_month: Optional[str] = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    category_id: Optional[uuid.UUID] = None,
    location_id: Optional[uuid.UUID] = None,
    ctx: HouseholdContext = Depends(view),
    db: Session = Depends(get_db),
):
    """Pending tasks by due date (oldest first). Guests only get the tasks assigned to them."""
    service = TaskService(db)
    month = (int(due_month[:4]), int(due_month[5:])) if due_month else None
    today = today_in(ctx.household.timezone)
    tasks = service.list_tasks(ctx, include_completed, assignee_id, month, category_id, location_id)
    return [service.to_read(ctx, t, today) for t in tasks]


@router.post("/tasks", response_model=TaskRead, status_code=201)
def create_task(data: TaskCreate, ctx: HouseholdContext = Depends(add_task), db: Session = Depends(get_db)):
    service = TaskService(db)
    return service.to_read(ctx, service.create(ctx, data))


@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: uuid.UUID, ctx: HouseholdContext = Depends(view), db: Session = Depends(get_db)):
    service = TaskService(db)
    return service.to_read(ctx, service.get(ctx, task_id))


@router.put("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: uuid.UUID, data: TaskUpdate, ctx: HouseholdContext = Depends(add_task), db: Session = Depends(get_db)):
    service = TaskService(db)
    return service.to_read(ctx, service.update(ctx, task_id, data))


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: uuid.UUID, ctx: HouseholdContext = Depends(add_task), db: Session = Depends(get_db)):
    TaskService(db).delete(ctx, task_id)


@router.post("/tasks/{task_id}/complete", response_model=TaskRead)
def complete_task(task_id: uuid.UUID, ctx: HouseholdContext = Depends(view), db: Session = Depends(get_db)):
    """Managers and residents complete any task; guests only the ones assigned to them."""
    service = TaskService(db)
    return service.to_read(ctx, service.complete(ctx, task_id, True))


@router.post("/tasks/{task_id}/uncomplete", response_model=TaskRead)
def uncomplete_task(task_id: uuid.UUID, ctx: HouseholdContext = Depends(view), db: Session = Depends(get_db)):
    service = TaskService(db)
    return service.to_read(ctx, service.complete(ctx, task_id, False))


# --- Recurring tasks (managers and residents) -------------------------------------
@router.get("/recurring-tasks", response_model=list[RecurringTaskRead])
def list_recurring_tasks(ctx: HouseholdContext = Depends(add_task), db: Session = Depends(get_db)):
    today = today_in(ctx.household.timezone)
    return [recurring_task_to_read(r, today) for r in RecurringTaskService(db).list_items(ctx)]


@router.post("/recurring-tasks", response_model=RecurringTaskRead, status_code=201)
def create_recurring_task(data: RecurringTaskCreate, ctx: HouseholdContext = Depends(add_task), db: Session = Depends(get_db)):
    item = RecurringTaskService(db).create(ctx, data)
    return recurring_task_to_read(item, today_in(ctx.household.timezone))


@router.put("/recurring-tasks/{item_id}", response_model=RecurringTaskRead)
def update_recurring_task(
    item_id: uuid.UUID, data: RecurringTaskUpdate, ctx: HouseholdContext = Depends(add_task), db: Session = Depends(get_db)
):
    item = RecurringTaskService(db).update(ctx, item_id, data)
    return recurring_task_to_read(item, today_in(ctx.household.timezone))


@router.delete("/recurring-tasks/{item_id}", status_code=204)
def delete_recurring_task(item_id: uuid.UUID, ctx: HouseholdContext = Depends(add_task), db: Session = Depends(get_db)):
    """Tasks it already created stay."""
    RecurringTaskService(db).delete(ctx, item_id)


# --- Task categories and locations (everyone reads; managers edit) -----------------
@router.get("/task-labels", response_model=list[TaskLabelRead])
def list_task_labels(ctx: HouseholdContext = Depends(view), db: Session = Depends(get_db)):
    """Both lists, each in its order: kind = category | location."""
    return TaskLabelService(db).list_labels(ctx.household.id)


@router.post("/task-labels", response_model=TaskLabelRead, status_code=201)
def create_task_label(data: TaskLabelCreate, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    return TaskLabelService(db).create(ctx, data)


@router.put("/task-labels/{label_id}", response_model=TaskLabelRead)
def update_task_label(
    label_id: uuid.UUID, data: TaskLabelUpdate, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)
):
    return TaskLabelService(db).update(ctx, label_id, data)


@router.delete("/task-labels/{label_id}", status_code=204)
def delete_task_label(label_id: uuid.UUID, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    """Tasks that used it lose their category/location."""
    TaskLabelService(db).delete(ctx, label_id)
