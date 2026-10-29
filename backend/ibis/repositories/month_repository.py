import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.month import HouseholdMonth


class MonthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, household_id: uuid.UUID, year: int, month: int) -> Optional[HouseholdMonth]:
        return self.db.scalar(
            select(HouseholdMonth).where(
                HouseholdMonth.household_id == household_id,
                HouseholdMonth.year == year,
                HouseholdMonth.month == month,
            )
        )

    def list_for_household(self, household_id: uuid.UUID) -> list[HouseholdMonth]:
        return list(
            self.db.scalars(
                select(HouseholdMonth)
                .where(HouseholdMonth.household_id == household_id)
                .order_by(HouseholdMonth.year.desc(), HouseholdMonth.month.desc())
            )
        )
