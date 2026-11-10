import uuid
from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from domain.task_labels import LabelKind
from domain.tasks import DEFAULT_WARN_DAYS, FrequencyUnit, TaskStatus

AssignMode = Literal["selected", "everyone", "everyone_guests"]


class _TaskSettingsIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    # From the household's task categories / locations (Settings -> Tasks)
    category_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    description: Optional[str] = Field(None, max_length=5000)
    warn_days: int = Field(DEFAULT_WARN_DAYS, ge=0, le=365)
    notify_expiring: bool = False
    notify_expired: bool = False
    # Outside the app: assignees on WhatsApp / email, the household's WhatsApp groups
    notify_expiring_whatsapp: bool = False
    notify_expiring_email: bool = False
    notify_expiring_groups: bool = False
    notify_expired_whatsapp: bool = False
    notify_expired_email: bool = False
    notify_expired_groups: bool = False
    # Only the assignees see the title and description
    is_private: bool = False
    assignee_ids: list[uuid.UUID] = Field(default_factory=list)


class TaskCreate(_TaskSettingsIn):
    due_date: Optional[date] = None


class TaskUpdate(TaskCreate):
    pass


class TaskRead(BaseModel):
    id: uuid.UUID
    title: str
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    location_id: Optional[uuid.UUID] = None
    location_name: Optional[str] = None
    description: Optional[str] = None
    kind: str
    data: dict[str, Any]
    due_date: Optional[date] = None
    warn_days: int
    notify_expiring: bool
    notify_expired: bool
    notify_expiring_whatsapp: bool = False
    notify_expiring_email: bool = False
    notify_expiring_groups: bool = False
    notify_expired_whatsapp: bool = False
    notify_expired_email: bool = False
    notify_expired_groups: bool = False
    is_private: bool = False
    # A private task seen by someone not assigned: title and description are blanked
    is_hidden: bool = False
    status: TaskStatus
    assignee_ids: list[uuid.UUID]
    recurring_task_id: Optional[uuid.UUID] = None
    created_by_user_id: Optional[uuid.UUID] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    completed_by_name: Optional[str] = None
    can_edit: bool = False
    can_delete: bool = False
    can_complete: bool = False


class RecurringTaskCreate(_TaskSettingsIn):
    start_date: date
    interval: int = Field(1, ge=1, le=365)
    unit: FrequencyUnit = "week"
    due_offset_days: int = Field(0, ge=0, le=365)
    wait_for_previous: bool = True
    assign_mode: AssignMode = "selected"
    is_active: bool = True


class RecurringTaskUpdate(RecurringTaskCreate):
    pass


class RecurringTaskRead(BaseModel):
    id: uuid.UUID
    title: str
    category_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    start_date: date
    interval: int
    unit: str
    due_offset_days: int
    warn_days: int
    notify_expiring: bool
    notify_expired: bool
    notify_expiring_whatsapp: bool = False
    notify_expiring_email: bool = False
    notify_expiring_groups: bool = False
    notify_expired_whatsapp: bool = False
    notify_expired_email: bool = False
    notify_expired_groups: bool = False
    is_private: bool = False
    wait_for_previous: bool
    assign_mode: str
    assignee_ids: list[uuid.UUID]
    is_active: bool
    last_occurrence_date: Optional[date] = None
    # The next scheduled date from today (None when paused)
    next_date: Optional[date] = None


class TaskLabelCreate(BaseModel):
    kind: LabelKind
    name: str = Field(..., min_length=1, max_length=100)


class TaskLabelUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class TaskLabelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    name: str
