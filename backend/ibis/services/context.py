from dataclasses import dataclass
from typing import Optional

from domain.roles import MIN_ROLE_ADD_COST, MIN_ROLE_MANAGE, Role, has_role
from models.household import Household
from models.member import HouseholdMember
from models.user import User
from services.errors import PermissionDeniedError


@dataclass
class HouseholdContext:
    """Who is acting, in which household, with which effective role.

    App admins act as managers in every household. `member` is None when the
    actor is an admin who is not a member of the household.
    """

    user: User
    household: Household
    member: Optional[HouseholdMember]
    role: Role

    @property
    def is_admin(self) -> bool:
        return self.user.is_admin

    @property
    def can_add_cost(self) -> bool:
        return has_role(self.role, MIN_ROLE_ADD_COST)

    @property
    def can_manage(self) -> bool:
        return has_role(self.role, MIN_ROLE_MANAGE)

    def require(self, minimum: Role) -> None:
        if not has_role(self.role, minimum):
            raise PermissionDeniedError(f"This action requires the '{minimum.value}' role")
