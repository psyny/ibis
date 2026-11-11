import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import household_context
from db.session import get_db
from domain.roles import MIN_ROLE_MANAGE
from schemas.whatsapp_schemas import (
    AvailableGroup,
    OutgoingMessageRead,
    WhatsAppGroupCreate,
    WhatsAppGroupRead,
    WhatsAppGroupUpdate,
    WhatsAppStatus,
    WhatsAppTest,
    WhatsAppTestResult,
)
from services.context import HouseholdContext
from services.whatsapp_service import WhatsAppService

router = APIRouter(prefix="/api/households/{household_id}/whatsapp", tags=["whatsapp"])

manage = household_context(MIN_ROLE_MANAGE)


@router.get("", response_model=WhatsAppStatus)
def get_status(ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    """The household's WhatsApp link (poll it while showing the QR code)."""
    return WhatsAppService(db).status(ctx)


@router.post("/connect", response_model=WhatsAppStatus)
def connect(ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    return WhatsAppService(db).connect(ctx)


@router.post("/disconnect", response_model=WhatsAppStatus)
def disconnect(ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    return WhatsAppService(db).disconnect(ctx)


@router.get("/available-groups", response_model=list[AvailableGroup])
def available_groups(ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    """Groups the linked number is in, to pick household groups from."""
    return WhatsAppService(db).available_groups(ctx)


@router.get("/groups", response_model=list[WhatsAppGroupRead])
def list_groups(ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    return WhatsAppService(db).list_groups(ctx)


@router.post("/groups", response_model=WhatsAppGroupRead, status_code=201)
def add_group(data: WhatsAppGroupCreate, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    return WhatsAppService(db).add_group(ctx, data)


@router.put("/groups/{group_id}", response_model=WhatsAppGroupRead)
def update_group(
    group_id: uuid.UUID, data: WhatsAppGroupUpdate, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)
):
    return WhatsAppService(db).set_group_active(ctx, group_id, data.is_active)


@router.delete("/groups/{group_id}", status_code=204)
def remove_group(group_id: uuid.UUID, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    WhatsAppService(db).remove_group(ctx, group_id)


@router.post("/test", response_model=WhatsAppTestResult)
def send_test(data: WhatsAppTest, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    """Send a test message now to a household group or a member, plus a sample payment reminder."""
    return WhatsAppTestResult(payment_receiver=WhatsAppService(db).send_test(ctx, data))


@router.get("/messages", response_model=list[OutgoingMessageRead])
def recent_messages(ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    """The latest messages Ibis queued or sent for this household (WhatsApp and, later, email)."""
    return WhatsAppService(db).recent_messages(ctx)
