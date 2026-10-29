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

    @property
    def is_shielded(self) -> bool:
        """A guest in a household that shields costs from guests: sees only what involves them."""
        return (
            self.household.shield_costs_from_guests
            and self.role == Role.GUEST
            and not self.user.is_admin
            and self.member is not None
        )

    def involves_me(self, cost) -> bool:
        """True if the acting member paid, covers, or added this cost (or fixed cost)."""
        if self.member is None:
            return False
        if getattr(cost, "created_by_user_id", None) == self.user.id:
            return True
        return any(m.id == self.member.id for m in [*cost.payers, *cost.coverers])

    def can_see(self, cost) -> bool:
        return not self.is_shielded or self.involves_me(cost)

    def require(self, minimum: Role) -> None:
        if not has_role(self.role, minimum):
            raise PermissionDeniedError(f"This action requires the '{minimum.value}' role")
