import uuid
from typing import Iterable

from sqlalchemy.orm import Session

from domain.roles import MIN_ROLE_MANAGE, Role, is_participant, member_sort_key
from models.member import HouseholdMember
from repositories.member_repository import MemberRepository
from repositories.user_repository import UserRepository
from schemas.household_schemas import MemberCreate, MemberDetail, MemberRead, MemberUpdate
from services.context import HouseholdContext
from services.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from services.user_service import apply_contact_fields


def member_to_read(member: HouseholdMember) -> MemberRead:
    user = member.user
    return MemberRead(
        id=member.id,
        user_id=user.id,
        login_name=user.login_name,
        display_name=user.display_name,
        role=member.role,
        is_active=member.is_active,
        is_participant=is_participant(member.role),
        email=user.email,
        whatsapp=user.whatsapp,
        bank_info_type=user.bank_info_type or "pix",
        bank_info=user.bank_info,
        has_transfer_qr=bool(user.transfer_qr),
    )


def sort_members(members: Iterable[HouseholdMember]) -> list[HouseholdMember]:
    return sorted(members, key=lambda m: member_sort_key(m.role, m.user.display_name))


class MemberService:
    def __init__(self, db: Session):
        self.db = db
        self.members = MemberRepository(db)
        self.users = UserRepository(db)

    def list_members(self, ctx: HouseholdContext) -> list[HouseholdMember]:
        return self.members.list_ordered(ctx.household.id)

    def get(self, ctx: HouseholdContext, member_id: uuid.UUID) -> HouseholdMember:
        member = self.members.get(ctx.household.id, member_id)
        if member is None:
            raise NotFoundError("Member not found")
        return member

    def detail(self, ctx: HouseholdContext, member_id: uuid.UUID) -> MemberDetail:
        member = self.get(ctx, member_id)
        return MemberDetail(**member_to_read(member).model_dump(), transfer_qr=member.user.transfer_qr)

    def create(self, ctx: HouseholdContext, data: MemberCreate) -> HouseholdMember:
        ctx.require(MIN_ROLE_MANAGE)
        user = self.users.get_by_login_name(data.login_name)
        if user is not None:
            # Only app admins may pull an existing account into another household.
            if not ctx.is_admin:
                raise ConflictError("This login is already taken. Pick another one.")
            if self.members.get_for_user(ctx.household.id, user.id):
                raise ConflictError("This user is already a member of the household")
        else:
            if not data.password:
                raise ValidationError("A password is required for a new user")
            user = self.users.create(
                data.login_name,
                data.password,
                (data.display_name or data.login_name).strip(),
                email=(data.email or "").strip() or None,
                whatsapp=(data.whatsapp or "").strip() or None,
            )

        member = HouseholdMember(household_id=ctx.household.id, user_id=user.id, role=data.role.value, is_active=True)
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def update(self, ctx: HouseholdContext, member_id: uuid.UUID, data: MemberUpdate) -> HouseholdMember:
        ctx.require(MIN_ROLE_MANAGE)
        member = self.get(ctx, member_id)

        new_role = data.role.value if data.role else member.role
        new_active = member.is_active if data.is_active is None else data.is_active
        losing_manager = member.role == Role.MANAGER.value and member.is_active and (
            new_role != Role.MANAGER.value or not new_active
        )
        if losing_manager and not ctx.is_admin and self._active_manager_count(ctx.household.id) <= 1:
            raise ValidationError("A household needs at least one active manager")

        member.role = new_role
        member.is_active = new_active
        apply_contact_fields(member.user, data)
        self.db.commit()
        self.db.refresh(member)
        return member

    def reset_password(self, ctx: HouseholdContext, member_id: uuid.UUID, new_password: str) -> None:
        ctx.require(MIN_ROLE_MANAGE)
        member = self.get(ctx, member_id)
        user = member.user
        if not ctx.is_admin:
            other_households = [m for m in self.members.list_for_user(user.id) if m.household_id != ctx.household.id]
            if user.is_admin or other_households:
                raise PermissionDeniedError("Only an app admin can reset this user's password")
        self.users.set_password(user, new_password)
        self.db.commit()

    def resolve_participants(
        self,
        household_id: uuid.UUID,
        member_ids: list[uuid.UUID],
        label: str,
        already_allowed: Iterable[uuid.UUID] = (),
    ) -> list[HouseholdMember]:
        """Load payers/coverers, checking they can take part in costs.

        `already_allowed` lets an edit keep people already on the cost even if
        they were disabled since.
        """
        allowed = set(already_allowed)
        result: list[HouseholdMember] = []
        for member_id in dict.fromkeys(member_ids):  # de-duplicate, keep order
            member = self.members.get(household_id, member_id)
            if member is None:
                raise ValidationError(f"Unknown member in '{label}'")
            if member.id not in allowed:
                if not member.is_active:
                    raise ValidationError(f"{member.user.display_name} is disabled")
                if not is_participant(member.role):
                    raise ValidationError(f"{member.user.display_name} is a viewer and can't be in '{label}'")
            result.append(member)
        if not result:
            raise ValidationError(f"Pick at least one person in '{label}'")
        return sort_members(result)

    def _active_manager_count(self, household_id: uuid.UUID) -> int:
        return sum(
            1 for m in self.members.list_ordered(household_id) if m.is_active and m.role == Role.MANAGER.value
        )
