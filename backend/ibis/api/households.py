import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import household_context
from db.session import get_db
from domain.roles import MIN_ROLE_MANAGE, MIN_ROLE_VIEW
from schemas.household_schemas import HouseholdRead, HouseholdUpdate, MemberCreate, MemberDetail, MemberRead, MemberUpdate
from schemas.user_schemas import PasswordReset
from services.context import HouseholdContext
from services.household_service import HouseholdService
from services.member_service import MemberService, member_to_read
from services.month_service import MonthService

router = APIRouter(prefix="/api/households/{household_id}", tags=["households"])

view = household_context(MIN_ROLE_VIEW)
manage = household_context(MIN_ROLE_MANAGE)


@router.get("", response_model=HouseholdRead)
def get_household(ctx: HouseholdContext = Depends(view), db: Session = Depends(get_db)):
    MonthService(db).sync(ctx.household)
    return HouseholdService(db).to_read(ctx)


@router.put("", response_model=HouseholdRead)
def update_household(data: HouseholdUpdate, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    service = HouseholdService(db)
    service.update(ctx, data)
    MonthService(db).sync(ctx.household)
    return service.to_read(ctx)


# --- Members ---------------------------------------------------------------------
@router.get("/members", response_model=list[MemberRead])
def list_members(ctx: HouseholdContext = Depends(view), db: Session = Depends(get_db)):
    """Ordered: residents/managers A-Z, then guests A-Z, then viewers A-Z."""
    return [member_to_read(m) for m in MemberService(db).list_members(ctx)]


@router.get("/members/{member_id}", response_model=MemberDetail)
def get_member(member_id: uuid.UUID, ctx: HouseholdContext = Depends(view), db: Session = Depends(get_db)):
    """Contact and payment info (incl. QR code) of a member."""
    return MemberService(db).detail(ctx, member_id)


@router.post("/members", response_model=MemberRead, status_code=201)
def create_member(data: MemberCreate, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    return member_to_read(MemberService(db).create(ctx, data))


@router.put("/members/{member_id}", response_model=MemberRead)
def update_member(
    member_id: uuid.UUID, data: MemberUpdate, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)
):
    """Promote/demote, enable/disable, rename."""
    return member_to_read(MemberService(db).update(ctx, member_id, data))


@router.post("/members/{member_id}/password", status_code=204)
def reset_member_password(
    member_id: uuid.UUID, data: PasswordReset, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)
):
    MemberService(db).reset_password(ctx, member_id, data.new_password)
