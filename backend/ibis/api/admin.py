import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import require_admin
from db.session import get_db
from models.user import User
from schemas.household_schemas import HouseholdCreate
from schemas.user_schemas import AdminUserCreate, AdminUserUpdate, UserRead
from services.household_service import HouseholdService
from services.month_service import MonthService
from services.user_service import UserService

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminHouseholdRead(BaseModel):
    id: uuid.UUID
    name: str
    currency: str
    timezone: str
    auto_close_days: int | None = None
    member_count: int


def _to_read(service: HouseholdService, household) -> AdminHouseholdRead:
    return AdminHouseholdRead(
        id=household.id,
        name=household.name,
        currency=household.currency,
        timezone=household.timezone,
        auto_close_days=household.auto_close_days,
        member_count=service.member_count(household.id),
    )


@router.get("/households", response_model=list[AdminHouseholdRead])
def list_households(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    service = HouseholdService(db)
    return [_to_read(service, h) for h in service.list_all()]


@router.post("/households", response_model=AdminHouseholdRead, status_code=201)
def create_household(data: HouseholdCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    service = HouseholdService(db)
    household = service.create(data)
    MonthService(db).sync(household)
    return _to_read(service, household)


@router.delete("/households/{household_id}", status_code=204)
def delete_household(household_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    HouseholdService(db).delete(household_id)


@router.get("/users", response_model=list[UserRead])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return UserService(db).list_users()


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(data: AdminUserCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return UserService(db).create_user(data)


@router.put("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID, data: AdminUserUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    return UserService(db).admin_update_user(admin, user_id, data)
