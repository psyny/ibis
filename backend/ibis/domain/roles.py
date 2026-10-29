"""Household roles and the permission policy.

All "who can do what" rules live here so they can be changed in one place.
Roles are ordered: viewer < guest < resident < manager. A higher role can do
everything a lower one can.
"""
from enum import Enum


class Role(str, Enum):
    VIEWER = "viewer"
    GUEST = "guest"
    RESIDENT = "resident"
    MANAGER = "manager"


_RANK = {Role.VIEWER: 0, Role.GUEST: 1, Role.RESIDENT: 2, Role.MANAGER: 3}


def has_role(role: Role | str, minimum: Role | str) -> bool:
    return _RANK[Role(role)] >= _RANK[Role(minimum)]


# --- Permission policy -------------------------------------------------------
MIN_ROLE_VIEW = Role.VIEWER
MIN_ROLE_ADD_COST = Role.GUEST  # guests, residents and managers add costs (and edit/delete their own)
MIN_ROLE_MANAGE = Role.MANAGER

# Roles that can appear as "who paid" / "who covers" on a cost.
# Viewers only look at the numbers, so they are not part of the split.
PARTICIPANT_ROLES = frozenset({Role.MANAGER, Role.RESIDENT, Role.GUEST})


def is_participant(role: Role | str) -> bool:
    return Role(role) in PARTICIPANT_ROLES


def member_sort_key(role: Role | str, display_name: str) -> tuple[int, str]:
    """Residents (incl. managers) first, then guests, then viewers; alphabetical in each group."""
    role = Role(role)
    if role in (Role.MANAGER, Role.RESIDENT):
        group = 0
    elif role == Role.GUEST:
        group = 1
    else:
        group = 2
    return group, display_name.casefold()
