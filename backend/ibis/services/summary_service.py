from collections import defaultdict

from sqlalchemy.orm import Session

from domain.money import from_cents, to_cents
from domain.settlement import CostShares, compute_totals, settle
from repositories.cost_repository import CostRepository
from repositories.member_repository import MemberRepository
from schemas.month_schemas import BalanceRead, CategoryTotalRead, MonthSummary, TransferRead
from services.catalog_service import CatalogService, category_to_read
from services.context import HouseholdContext
from services.cost_service import CostService
from services.member_service import member_to_read, sort_members
from services.month_service import MonthService

UNCATEGORIZED = "Uncategorized"


class SummaryService:
    """Everything the main screen needs for one month: split, category totals, cost list."""

    def __init__(self, db: Session):
        self.db = db
        self.months = MonthService(db)
        self.costs = CostRepository(db)
        self.members = MemberRepository(db)
        self.cost_service = CostService(db)
        self.catalog = CatalogService(db)

    def month_summary(self, ctx: HouseholdContext, year: int, month: int) -> MonthSummary:
        household = ctx.household
        self.months.sync(household)
        month_row = self.months.get(household, year, month)
        costs = self.costs.list_for_month(month_row.id)
        members = self.members.list_ordered(household.id)

        totals = compute_totals(
            CostShares(
                amount_cents=to_cents(cost.amount),
                payers=[m.id for m in sort_members(cost.payers)],
                coverers=[m.id for m in sort_members(cost.coverers)],
            )
            for cost in costs
        )
        order = {m.id: index for index, m in enumerate(members)}
        balances = [
            BalanceRead(member_id=member_id, paid=from_cents(t.paid), covered=from_cents(t.covered), net=from_cents(t.net))
            for member_id, t in sorted(totals.items(), key=lambda item: order.get(item[0], len(order)))
        ]
        transfers = [
            TransferRead(from_member_id=t.debtor, to_member_id=t.creditor, amount=from_cents(t.amount_cents))
            for t in settle({member_id: t.net for member_id, t in totals.items()})
        ]

        by_category: dict = defaultdict(int)
        category_info: dict = {}
        for cost in costs:
            key = cost.category_id
            by_category[key] += to_cents(cost.amount)
            if key is not None and cost.category is not None:
                category_info[key] = cost.category
        category_totals = sorted(
            (
                CategoryTotalRead(
                    category_id=key,
                    name=category_info[key].name if key in category_info else UNCATEGORIZED,
                    color=category_info[key].color if key in category_info else None,
                    total=from_cents(cents),
                )
                for key, cents in by_category.items()
            ),
            key=lambda c: -c.total,
        )

        stats = (len(costs), sum((cost.amount for cost in costs), start=0))
        return MonthSummary(
            month=self.months.to_read(household, month_row, stats),
            currency=household.currency,
            total=from_cents(sum(to_cents(cost.amount) for cost in costs)),
            members=[member_to_read(m) for m in members],
            balances=balances,
            transfers=transfers,
            category_totals=category_totals,
            categories=[category_to_read(c) for c in self.catalog.list_categories(household.id, include_archived=True)],
            costs=[self.cost_service.to_read(ctx, cost, month_row.is_open) for cost in costs],
            can_add_cost=ctx.can_add_cost and month_row.is_open,
            can_manage=ctx.can_manage,
        )
