import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from domain.roles import MIN_ROLE_MANAGE
from models.cost import RecurringCost
from schemas.cost_schemas import RecurringCostCreate, RecurringCostRead, RecurringCostUpdate
from services.catalog_service import CatalogService
from services.context import HouseholdContext
from services.errors import NotFoundError
from services.member_service import MemberService, sort_members


def recurring_to_read(item: RecurringCost) -> RecurringCostRead:
    return RecurringCostRead(
        id=item.id,
        description=item.description,
        category_id=item.category_id,
        category_name=item.category.name if item.category else None,
        amount=float(item.amount),
        day_of_month=item.day_of_month,
        payer_ids=[m.id for m in sort_members(item.payers)],
        coverer_ids=[m.id for m in sort_members(item.coverers)],
        is_active=item.is_active,
    )


class RecurringCostService:
    """The household's "starting state": costs copied into every new month."""

    def __init__(self, db: Session):
        self.db = db
        self.members = MemberService(db)
        self.catalog = CatalogService(db)

    def list_items(self, ctx: HouseholdContext) -> list[RecurringCost]:
        items = self.db.scalars(
            select(RecurringCost)
            .where(RecurringCost.household_id == ctx.household.id)
            .order_by(RecurringCost.day_of_month, func.lower(RecurringCost.description))
        ).unique()
        return [item for item in items if ctx.can_see(item)]

    def get(self, ctx: HouseholdContext, item_id: uuid.UUID) -> RecurringCost:
        item = self.db.get(RecurringCost, item_id)
        if item is None or item.household_id != ctx.household.id:
            raise NotFoundError("Recurring cost not found")
        return item

    def create(self, ctx: HouseholdContext, data: RecurringCostCreate) -> RecurringCost:
        ctx.require(MIN_ROLE_MANAGE)
        item = RecurringCost(household_id=ctx.household.id)
        self._apply(ctx, item, data, current_ids=set())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, ctx: HouseholdContext, item_id: uuid.UUID, data: RecurringCostUpdate) -> RecurringCost:
        ctx.require(MIN_ROLE_MANAGE)
        item = self.get(ctx, item_id)
        current_ids = {m.id for m in item.payers} | {m.id for m in item.coverers}
        self._apply(ctx, item, data, current_ids)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, ctx: HouseholdContext, item_id: uuid.UUID) -> None:
        ctx.require(MIN_ROLE_MANAGE)
        self.db.delete(self.get(ctx, item_id))
        self.db.commit()

    def _apply(self, ctx: HouseholdContext, item: RecurringCost, data: RecurringCostCreate, current_ids: set) -> None:
        household_id = ctx.household.id
        category = self.catalog.resolve_category(household_id, data.category_id, allow_archived_id=item.category_id)
        item.description = data.description.strip()
        item.category_id = category.id if category else None
        item.amount = data.amount
        item.day_of_month = data.day_of_month
        item.is_active = data.is_active
        item.payers = self.members.resolve_participants(household_id, data.payer_ids, "Who paid", current_ids)
        item.coverers = self.members.resolve_participants(household_id, data.coverer_ids, "Who covers", current_ids)
