import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from domain.money import to_cents
from models.cost import Cost


def cost_key(description: str, amount) -> tuple[str, int]:
    """Identity used to spot duplicate costs: description (trimmed, case-insensitive) + amount in cents."""
    return " ".join(description.split()).casefold(), to_cents(amount)


class CostRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, household_id: uuid.UUID, cost_id: uuid.UUID) -> Optional[Cost]:
        cost = self.db.get(Cost, cost_id)
        if cost is None or cost.household_id != household_id:
            return None
        return cost

    def list_for_month(self, month_id: uuid.UUID) -> list[Cost]:
        """Oldest first: by date, then by when it was added."""
        return list(
            self.db.scalars(
                select(Cost)
                .where(Cost.month_id == month_id)
                .order_by(Cost.date.asc(), Cost.created_at.asc(), Cost.id.asc())
            ).unique()
        )

    def list_for_household(self, household_id: uuid.UUID) -> list[Cost]:
        return list(self.db.scalars(select(Cost).where(Cost.household_id == household_id)).unique())

    def stats_by_month(self, household_id: uuid.UUID) -> dict[uuid.UUID, tuple[int, Decimal]]:
        rows = self.db.execute(
            select(Cost.month_id, func.count(Cost.id), func.coalesce(func.sum(Cost.amount), 0))
            .where(Cost.household_id == household_id)
            .group_by(Cost.month_id)
        )
        return {month_id: (count, Decimal(total)) for month_id, count, total in rows}

    def description_amount_keys(self, month_id: uuid.UUID) -> set[tuple[str, int]]:
        """(description, amount) of every cost in the month, used to avoid adding duplicates."""
        rows = self.db.execute(select(Cost.description, Cost.amount).where(Cost.month_id == month_id))
        return {cost_key(description, amount) for description, amount in rows}

    def is_category_used(self, category_id: uuid.UUID) -> bool:
        return self.db.scalar(select(func.count()).select_from(Cost).where(Cost.category_id == category_id)) > 0
