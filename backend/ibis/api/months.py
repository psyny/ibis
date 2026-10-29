from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from api.deps import household_context
from db.session import get_db
from domain.roles import MIN_ROLE_MANAGE, MIN_ROLE_VIEW
from schemas.month_schemas import MonthCreate, MonthRead, MonthSummary
from services.context import HouseholdContext
from services.month_service import MonthService
from services.summary_service import SummaryService

router = APIRouter(prefix="/api/households/{household_id}/months", tags=["months"])

view = household_context(MIN_ROLE_VIEW)
manage = household_context(MIN_ROLE_MANAGE)

Year = Annotated[int, Path(ge=2000, le=2100)]
Month = Annotated[int, Path(ge=1, le=12)]


@router.get("", response_model=list[MonthRead])
def list_months(ctx: HouseholdContext = Depends(view), db: Session = Depends(get_db)):
    service = MonthService(db)
    service.sync(ctx.household)
    return service.list_months(ctx)


@router.post("", response_model=MonthRead, status_code=201)
def create_month(data: MonthCreate, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    """Create a month table (e.g. a future month). The starting-state costs are copied into it."""
    service = MonthService(db)
    month = service.create(ctx, data.year, data.month)
    return _read(service, ctx, month.year, month.month)


@router.get("/{year}/{month}/summary", response_model=MonthSummary)
def month_summary(
    year: Year, month: Month, ctx: HouseholdContext = Depends(view), db: Session = Depends(get_db)
):
    return SummaryService(db).month_summary(ctx, year, month)


@router.post("/{year}/{month}/close", response_model=MonthRead)
def close_month(
    year: Year, month: Month, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)
):
    service = MonthService(db)
    service.close(ctx, year, month)
    return _read(service, ctx, year, month)


@router.post("/{year}/{month}/reopen", response_model=MonthRead)
def reopen_month(
    year: Year, month: Month, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)
):
    service = MonthService(db)
    service.reopen(ctx, year, month)
    return _read(service, ctx, year, month)


@router.post("/{year}/{month}/apply-recurring")
def apply_recurring(
    year: Year, month: Month, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)
):
    """Add starting-state costs that this month is missing (e.g. defined after the month was created)."""
    return {"added": MonthService(db).apply_recurring(ctx, year, month)}


def _read(service: MonthService, ctx: HouseholdContext, year: int, month: int) -> MonthRead:
    return next(m for m in service.list_months(ctx) if m.year == year and m.month == month)
