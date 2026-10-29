import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.roles import member_sort_key
from models.member import HouseholdMember


class MemberRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, household_id: uuid.UUID, member_id: uuid.UUID) -> Optional[HouseholdMember]:
        member = self.db.get(HouseholdMember, member_id)
        if member is None or member.household_id != household_id:
            return None
        return member

    def get_for_user(self, household_id: uuid.UUID, user_id: uuid.UUID) -> Optional[HouseholdMember]:
        return self.db.scalar(
            select(HouseholdMember).where(
                HouseholdMember.household_id == household_id, HouseholdMember.user_id == user_id
            )
        )

    def list_ordered(self, household_id: uuid.UUID) -> list[HouseholdMember]:
        """Residents/managers A-Z, then guests A-Z, then viewers A-Z."""
        members = list(self.db.scalars(select(HouseholdMember).where(HouseholdMember.household_id == household_id)))
        return sorted(members, key=lambda m: member_sort_key(m.role, m.user.display_name))

    def list_for_user(self, user_id: uuid.UUID) -> list[HouseholdMember]:
        return list(self.db.scalars(select(HouseholdMember).where(HouseholdMember.user_id == user_id)))
