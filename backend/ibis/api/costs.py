import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import household_context
from db.session import get_db
from domain.roles import MIN_ROLE_ADD_COST, MIN_ROLE_MANAGE, MIN_ROLE_VIEW
from models.month import HouseholdMonth
from schemas.cost_schemas import (
    CostCreate,
    CostRead,
    CostUpdate,
    RecurringCostCreate,
    RecurringCostRead,
    RecurringCostUpdate,
)
from services.context import HouseholdContext
from services.cost_service import CostService
from services.recurring_service import RecurringCostService, recurring_to_read

router = APIRouter(prefix="/api/households/{household_id}", tags=["costs"])

view = household_context(MIN_ROLE_VIEW)
add_cost = household_context(MIN_ROLE_ADD_COST)
manage = household_context(MIN_ROLE_MANAGE)


def _read(service: CostService, ctx: HouseholdContext, cost, db: Session) -> CostRead:
    month = db.get(HouseholdMonth, cost.month_id)
    return service.to_read(ctx, cost, month.is_open)


@router.post("/costs", response_model=CostRead, status_code=201)
def create_cost(data: CostCreate, ctx: HouseholdContext = Depends(add_cost), db: Session = Depends(get_db)):
    service = CostService(db)
    return _read(service, ctx, service.create(ctx, data), db)


@router.get("/costs/{cost_id}", response_model=CostRead)
def get_cost(cost_id: uuid.UUID, ctx: HouseholdContext = Depends(view), db: Session = Depends(get_db)):
    service = CostService(db)
    return _read(service, ctx, service.get(ctx, cost_id), db)


@router.put("/costs/{cost_id}", response_model=CostRead)
def update_cost(
    cost_id: uuid.UUID, data: CostUpdate, ctx: HouseholdContext = Depends(add_cost), db: Session = Depends(get_db)
):
    service = CostService(db)
    return _read(service, ctx, service.update(ctx, cost_id, data), db)


@router.delete("/costs/{cost_id}", status_code=204)
def delete_cost(cost_id: uuid.UUID, ctx: HouseholdContext = Depends(add_cost), db: Session = Depends(get_db)):
    CostService(db).delete(ctx, cost_id)


# --- Starting state (recurring costs) -------------------------------------------
@router.get("/recurring-costs", response_model=list[RecurringCostRead])
def list_recurring(ctx: HouseholdContext = Depends(view), db: Session = Depends(get_db)):
    return [recurring_to_read(r) for r in RecurringCostService(db).list_items(ctx)]


@router.post("/recurring-costs", response_model=RecurringCostRead, status_code=201)
def create_recurring(data: RecurringCostCreate, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    return recurring_to_read(RecurringCostService(db).create(ctx, data))


@router.put("/recurring-costs/{item_id}", response_model=RecurringCostRead)
def update_recurring(
    item_id: uuid.UUID,
    data: RecurringCostUpdate,
    ctx: HouseholdContext = Depends(manage),
    db: Session = Depends(get_db),
):
    return recurring_to_read(RecurringCostService(db).update(ctx, item_id, data))


@router.delete("/recurring-costs/{item_id}", status_code=204)
def delete_recurring(item_id: uuid.UUID, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    RecurringCostService(db).delete(ctx, item_id)
