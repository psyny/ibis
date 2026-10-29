import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from domain.months import is_valid_timezone, today_in
from models.household import Household
from models.member import HouseholdMember
from schemas.household_schemas import HouseholdCreate, HouseholdPermissions, HouseholdRead, HouseholdUpdate
from services.context import HouseholdContext
from services.errors import NotFoundError, ValidationError


class HouseholdService:
    def __init__(self, db: Session):
        self.db = db

    def get(self, household_id: uuid.UUID) -> Household:
        household = self.db.get(Household, household_id)
        if household is None:
            raise NotFoundError("Household not found")
        return household

    def list_all(self) -> list[Household]:
        return list(self.db.scalars(select(Household).order_by(func.lower(Household.name))))

    def member_count(self, household_id: uuid.UUID) -> int:
        return self.db.scalar(
            select(func.count()).select_from(HouseholdMember).where(HouseholdMember.household_id == household_id)
        ) or 0

    def create(self, data: HouseholdCreate) -> Household:
        if not is_valid_timezone(data.timezone):
            raise ValidationError(f"Unknown timezone '{data.timezone}'")
        household = Household(
            name=data.name.strip(),
            currency=data.currency.upper(),
            timezone=data.timezone,
            auto_close_days=data.auto_close_days,
        )
        self.db.add(household)
        self.db.commit()
        self.db.refresh(household)
        return household

    def update(self, ctx: HouseholdContext, data: HouseholdUpdate) -> Household:
        household = ctx.household
        if data.name:
            household.name = data.name.strip()
        if data.currency:
            household.currency = data.currency.upper()
        if data.timezone:
            if not is_valid_timezone(data.timezone):
                raise ValidationError(f"Unknown timezone '{data.timezone}'")
            household.timezone = data.timezone
        if data.disable_auto_close:
            household.auto_close_days = None
        elif data.auto_close_days is not None:
            household.auto_close_days = data.auto_close_days
        self.db.commit()
        self.db.refresh(household)
        return household

    def delete(self, household_id: uuid.UUID) -> None:
        self.db.delete(self.get(household_id))
        self.db.commit()

    def to_read(self, ctx: HouseholdContext) -> HouseholdRead:
        household = ctx.household
        return HouseholdRead(
            id=household.id,
            name=household.name,
            currency=household.currency,
            timezone=household.timezone,
            auto_close_days=household.auto_close_days,
            today=today_in(household.timezone),
            my_role=ctx.role.value,
            my_member_id=ctx.member.id if ctx.member else None,
            permissions=HouseholdPermissions(can_add_cost=ctx.can_add_cost, can_manage=ctx.can_manage),
            member_count=self.member_count(household.id),
        )
