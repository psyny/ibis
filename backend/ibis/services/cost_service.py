import uuid

from sqlalchemy.orm import Session

from domain.money import from_cents, split_cents, to_cents
from domain.roles import MIN_ROLE_ADD_COST
from models.cost import SOURCE_WEB, Cost
from models.month import HouseholdMonth
from repositories.cost_repository import CostRepository
from schemas.cost_schemas import CostCreate, CostRead, CostUpdate
from services.catalog_service import CatalogService
from services.context import HouseholdContext
from services.errors import NotFoundError, PermissionDeniedError
from services.member_service import MemberService, sort_members
from services.month_service import MonthService


class CostService:
    """Adding, editing and removing costs.

    `source` records where a cost came from ("web" today; future WhatsApp or
    voice integrations pass their own value and reuse the same rules).
    """

    def __init__(self, db: Session):
        self.db = db
        self.costs = CostRepository(db)
        self.months = MonthService(db)
        self.members = MemberService(db)
        self.catalog = CatalogService(db)

    def get(self, ctx: HouseholdContext, cost_id: uuid.UUID) -> Cost:
        cost = self.costs.get(ctx.household.id, cost_id)
        if cost is None:
            raise NotFoundError("Cost not found")
        return cost

    def can_edit(self, ctx: HouseholdContext, cost: Cost) -> bool:
        if ctx.can_manage:
            return True
        return ctx.can_add_cost and cost.created_by_user_id == ctx.user.id

    def create(self, ctx: HouseholdContext, data: CostCreate, source: str = SOURCE_WEB) -> Cost:
        ctx.require(MIN_ROLE_ADD_COST)
        household_id = ctx.household.id
        month = self.months.open_month_for_date(ctx.household, data.date)
        category = self.catalog.resolve_category(household_id, data.category_id)
        cost = Cost(
            household_id=household_id,
            month_id=month.id,
            description=data.description.strip(),
            category_id=category.id if category else None,
            amount=data.amount,
            date=data.date,
            source=source,
            created_by_user_id=ctx.user.id,
            payers=self.members.resolve_participants(household_id, data.payer_ids, "Who paid"),
            coverers=self.members.resolve_participants(household_id, data.coverer_ids, "Who covers"),
        )
        self.db.add(cost)
        self.db.commit()
        self.db.refresh(cost)
        return cost

    def update(self, ctx: HouseholdContext, cost_id: uuid.UUID, data: CostUpdate) -> Cost:
        cost = self.get(ctx, cost_id)
        if not self.can_edit(ctx, cost):
            raise PermissionDeniedError("You can only edit costs you added")
        household_id = ctx.household.id
        self.months.require_open(self.db.get(HouseholdMonth, cost.month_id))
        target_month = self.months.open_month_for_date(ctx.household, data.date)

        category = self.catalog.resolve_category(household_id, data.category_id, allow_archived_id=cost.category_id)
        current_ids = {m.id for m in cost.payers} | {m.id for m in cost.coverers}
        cost.payers = self.members.resolve_participants(household_id, data.payer_ids, "Who paid", current_ids)
        cost.coverers = self.members.resolve_participants(household_id, data.coverer_ids, "Who covers", current_ids)
        cost.description = data.description.strip()
        cost.category_id = category.id if category else None
        cost.amount = data.amount
        cost.date = data.date
        cost.month_id = target_month.id
        self.db.commit()
        self.db.refresh(cost)
        return cost

    def delete(self, ctx: HouseholdContext, cost_id: uuid.UUID) -> None:
        cost = self.get(ctx, cost_id)
        if not self.can_edit(ctx, cost):
            raise PermissionDeniedError("You can only delete costs you added")
        self.months.require_open(self.db.get(HouseholdMonth, cost.month_id))
        self.db.delete(cost)
        self.db.commit()

    def to_read(self, ctx: HouseholdContext, cost: Cost, month_open: bool) -> CostRead:
        cents = to_cents(cost.amount)
        payers = sort_members(cost.payers)
        coverers = sort_members(cost.coverers)
        return CostRead(
            id=cost.id,
            description=cost.description,
            category_id=cost.category_id,
            category_name=cost.category.name if cost.category else None,
            amount=from_cents(cents),
            date=cost.date,
            payer_ids=[m.id for m in payers],
            coverer_ids=[m.id for m in coverers],
            paid_share=from_cents(split_cents(cents, len(payers))[0]) if payers else 0,
            cover_share=from_cents(split_cents(cents, len(coverers))[0]) if coverers else 0,
            source=cost.source,
            recurring_cost_id=cost.recurring_cost_id,
            created_by_user_id=cost.created_by_user_id,
            created_at=cost.created_at,
            can_edit=month_open and self.can_edit(ctx, cost),
        )
