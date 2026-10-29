import calendar
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.months import auto_close_date, clamp_day, next_month, today_in
from domain.roles import MIN_ROLE_MANAGE
from models.cost import SOURCE_RECURRING, Cost, RecurringCost
from models.household import Household
from models.month import MONTH_CLOSED, MONTH_OPEN, HouseholdMonth
from repositories.cost_repository import CostRepository, cost_key
from repositories.month_repository import MonthRepository
from schemas.month_schemas import MonthRead
from services.context import HouseholdContext
from services.errors import ConflictError, NotFoundError, ValidationError


def month_label(year: int, month: int) -> str:
    return f"{calendar.month_name[month]} {year}"


class MonthService:
    def __init__(self, db: Session):
        self.db = db
        self.months = MonthRepository(db)
        self.costs = CostRepository(db)

    # --- Automatic housekeeping -------------------------------------------------
    def sync(self, household: Household) -> None:
        """Make sure the current and next month exist, and auto-close months past their deadline.

        Called lazily whenever a household is read, so no background worker is needed.
        """
        today = today_in(household.timezone)
        current = (today.year, today.month)
        changed = False
        for year, month in (current, next_month(*current)):
            if self.months.get(household.id, year, month) is None:
                changed |= self._create_with_recurring(household, year, month) is not None

        if household.auto_close_days is not None:
            for month in self.months.list_for_household(household.id):
                if month.status != MONTH_OPEN or month.auto_close_exempt:
                    continue
                close_on = auto_close_date(month.year, month.month, household.auto_close_days)
                if close_on is not None and today >= close_on:
                    month.status = MONTH_CLOSED
                    month.closed_at = datetime.now(timezone.utc)
                    month.closed_by_user_id = None
                    changed = True
        if changed:
            self.db.commit()

    def sync_all(self) -> None:
        for household in self.db.scalars(select(Household)):
            self.sync(household)

    # --- Use cases ----------------------------------------------------------------
    def get(self, household: Household, year: int, month: int) -> HouseholdMonth:
        found = self.months.get(household.id, year, month)
        if found is None:
            raise NotFoundError(f"{month_label(year, month)} has not been created yet")
        return found

    def list_months(self, ctx: HouseholdContext) -> list[MonthRead]:
        stats = self.costs.stats_by_month(ctx.household.id)
        return [self.to_read(ctx.household, m, stats.get(m.id)) for m in self.months.list_for_household(ctx.household.id)]

    def create(self, ctx: HouseholdContext, year: int, month: int) -> HouseholdMonth:
        ctx.require(MIN_ROLE_MANAGE)
        if self.months.get(ctx.household.id, year, month) is not None:
            raise ConflictError(f"{month_label(year, month)} already exists")
        created = self._create_with_recurring(ctx.household, year, month)
        if created is None:
            raise ConflictError(f"{month_label(year, month)} already exists")
        self.db.commit()
        return created

    def close(self, ctx: HouseholdContext, year: int, month: int) -> HouseholdMonth:
        ctx.require(MIN_ROLE_MANAGE)
        found = self.get(ctx.household, year, month)
        found.status = MONTH_CLOSED
        found.closed_at = datetime.now(timezone.utc)
        found.closed_by_user_id = ctx.user.id
        self.db.commit()
        return found

    def reopen(self, ctx: HouseholdContext, year: int, month: int) -> HouseholdMonth:
        ctx.require(MIN_ROLE_MANAGE)
        found = self.get(ctx.household, year, month)
        found.status = MONTH_OPEN
        found.closed_at = None
        found.closed_by_user_id = None
        found.auto_close_exempt = True  # don't let auto-close undo the manager's decision
        self.db.commit()
        return found

    def apply_recurring(self, ctx: HouseholdContext, year: int, month: int) -> int:
        """Add the fixed costs this month doesn't have yet (e.g. after the fixed costs were adjusted).

        A fixed cost is skipped when the month already has a cost with the same description
        and amount, so clicking twice never duplicates anything. Costs already in the month
        are never removed, even if their fixed cost was deleted or changed since.
        Returns how many were added.
        """
        ctx.require(MIN_ROLE_MANAGE)
        found = self.get(ctx.household, year, month)
        # Lock the month row so two simultaneous clicks run one after the other (Postgres).
        self.db.execute(select(HouseholdMonth.id).where(HouseholdMonth.id == found.id).with_for_update())
        self.require_open(found)
        added = self._copy_recurring(ctx.household, found, skip_keys=self.costs.description_amount_keys(found.id))
        self.db.commit()
        return added

    def open_month_for_date(self, household: Household, day: date) -> HouseholdMonth:
        """The month a cost on `day` belongs to; it must exist and be open."""
        self.sync(household)
        found = self.months.get(household.id, day.year, day.month)
        if found is None:
            raise ValidationError(
                f"{month_label(day.year, day.month)} has not been created yet. A manager can create it in Settings."
            )
        self.require_open(found)
        return found

    @staticmethod
    def require_open(month: HouseholdMonth) -> None:
        if not month.is_open:
            raise ValidationError(f"{month_label(month.year, month.month)} is closed")

    def to_read(self, household: Household, month: HouseholdMonth, stats=None) -> MonthRead:
        count, total = stats if stats else (0, 0)
        return MonthRead(
            id=month.id,
            year=month.year,
            month=month.month,
            status=month.status,
            closed_at=month.closed_at,
            auto_close_on=None
            if month.auto_close_exempt
            else auto_close_date(month.year, month.month, household.auto_close_days),
            cost_count=count,
            total=float(total),
        )

    # --- Internals --------------------------------------------------------------------
    def _create_with_recurring(self, household: Household, year: int, month: int) -> HouseholdMonth | None:
        """Create a month and copy the starting-state costs into it. None if it already existed (race)."""
        try:
            with self.db.begin_nested():
                created = HouseholdMonth(household_id=household.id, year=year, month=month, status=MONTH_OPEN)
                self.db.add(created)
                self.db.flush()
                self._copy_recurring(household, created, skip_keys=set())
        except IntegrityError:
            return None
        return created

    def _copy_recurring(self, household: Household, month: HouseholdMonth, skip_keys: set[tuple[str, int]]) -> int:
        """Copy active fixed costs into `month`, skipping any whose (description, amount) is in skip_keys."""
        templates = self.db.scalars(
            select(RecurringCost).where(RecurringCost.household_id == household.id, RecurringCost.is_active.is_(True))
        ).unique()
        added = 0
        for template in templates:
            key = cost_key(template.description, template.amount)
            if key in skip_keys:
                continue
            payers = [m for m in template.payers if m.is_active]
            coverers = [m for m in template.coverers if m.is_active]
            if not payers or not coverers:
                continue
            self.db.add(
                Cost(
                    household_id=household.id,
                    month_id=month.id,
                    description=template.description,
                    category_id=template.category_id,
                    amount=template.amount,
                    date=clamp_day(month.year, month.month, template.day_of_month),
                    source=SOURCE_RECURRING,
                    recurring_cost_id=template.id,
                    payers=payers,
                    coverers=coverers,
                )
            )
            skip_keys.add(key)  # two identical fixed costs are added once
            added += 1
        self.db.flush()
        return added
