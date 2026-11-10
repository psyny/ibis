"""Settings -> WhatsApp (managers): link the household's number, pick its groups, send a test."""
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.messages import test_message
from domain.phones import default_country_for, whatsapp_number
from domain.roles import MIN_ROLE_MANAGE
from infrastructure import whatsapp
from models.messaging import OutgoingMessage, WhatsAppGroup
from repositories.member_repository import MemberRepository
from schemas.whatsapp_schemas import AvailableGroup, WhatsAppGroupCreate, WhatsAppStatus, WhatsAppTest
from services.context import HouseholdContext
from services.errors import ConflictError, NotFoundError, ServiceUnavailableError, ValidationError

RECENT_MESSAGES = 30


def _call(action, *args):
    """Run a WhatsApp service call, turning its errors into ones the API understands."""
    try:
        return action(*args)
    except whatsapp.WhatsAppError as exc:
        if exc.status in (400, 404, 409):
            raise ValidationError(exc.message) from exc
        raise ServiceUnavailableError(exc.message) from exc


class WhatsAppService:
    def __init__(self, db: Session):
        self.db = db

    # --- Connection ------------------------------------------------------------------------
    def status(self, ctx: HouseholdContext) -> WhatsAppStatus:
        ctx.require(MIN_ROLE_MANAGE)
        if not whatsapp.is_configured():
            return WhatsAppStatus(status="off")
        try:
            return WhatsAppStatus(**whatsapp.status(ctx.household.id))
        except whatsapp.WhatsAppError as exc:
            return WhatsAppStatus(status="unavailable", error=exc.message)

    def connect(self, ctx: HouseholdContext) -> WhatsAppStatus:
        ctx.require(MIN_ROLE_MANAGE)
        return WhatsAppStatus(**_call(whatsapp.connect, ctx.household.id))

    def disconnect(self, ctx: HouseholdContext) -> WhatsAppStatus:
        ctx.require(MIN_ROLE_MANAGE)
        return WhatsAppStatus(**_call(whatsapp.logout, ctx.household.id))

    # --- Household groups ------------------------------------------------------------------
    def list_groups(self, ctx: HouseholdContext) -> list[WhatsAppGroup]:
        ctx.require(MIN_ROLE_MANAGE)
        return list(
            self.db.scalars(
                select(WhatsAppGroup).where(WhatsAppGroup.household_id == ctx.household.id).order_by(WhatsAppGroup.name)
            )
        )

    def available_groups(self, ctx: HouseholdContext) -> list[AvailableGroup]:
        """Groups the linked number is in. Also refreshes the names of the household's saved groups."""
        found = _call(whatsapp.groups, ctx.household.id)
        saved = {g.jid: g for g in self.list_groups(ctx)}
        renamed = False
        for item in found:
            group = saved.get(item["id"])
            if group and item.get("name") and group.name != item["name"]:
                group.name = item["name"][:200]
                renamed = True
        if renamed:
            self.db.commit()
        return sorted(
            (
                AvailableGroup(
                    jid=item["id"],
                    name=item.get("name") or item["id"],
                    participants=item.get("participants", 0),
                    added=item["id"] in saved,
                )
                for item in found
            ),
            key=lambda g: g.name.lower(),
        )

    def add_group(self, ctx: HouseholdContext, data: WhatsAppGroupCreate) -> WhatsAppGroup:
        ctx.require(MIN_ROLE_MANAGE)
        group = WhatsAppGroup(household_id=ctx.household.id, jid=data.jid, name=data.name.strip(), is_active=True)
        self.db.add(group)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("This group is already one of the household groups") from exc
        return group

    def set_group_active(self, ctx: HouseholdContext, group_id: uuid.UUID, active: bool) -> WhatsAppGroup:
        group = self._group(ctx, group_id)
        group.is_active = active
        self.db.commit()
        return group

    def remove_group(self, ctx: HouseholdContext, group_id: uuid.UUID) -> None:
        self.db.delete(self._group(ctx, group_id))
        self.db.commit()

    def _group(self, ctx: HouseholdContext, group_id: uuid.UUID) -> WhatsAppGroup:
        ctx.require(MIN_ROLE_MANAGE)
        group = self.db.get(WhatsAppGroup, group_id)
        if group is None or group.household_id != ctx.household.id:
            raise NotFoundError("Group not found")
        return group

    # --- Testing and the message log ---------------------------------------------------------
    def send_test(self, ctx: HouseholdContext, data: WhatsAppTest) -> None:
        """Sends right away (not queued), so the manager sees at once whether it works."""
        ctx.require(MIN_ROLE_MANAGE)
        if data.group_id:
            to = self._group(ctx, data.group_id).jid
        else:
            member = MemberRepository(self.db).get(ctx.household.id, data.member_id)
            if member is None:
                raise NotFoundError("Member not found")
            to = whatsapp_number(member.user.whatsapp, default_country_for(ctx.household.currency))
            if to is None:
                raise ValidationError(f"{member.user.display_name} has no valid WhatsApp number")
        _call(whatsapp.send, ctx.household.id, to, test_message(ctx.household.language, ctx.household.name))

    def recent_messages(self, ctx: HouseholdContext) -> list[OutgoingMessage]:
        ctx.require(MIN_ROLE_MANAGE)
        return list(
            self.db.scalars(
                select(OutgoingMessage)
                .where(OutgoingMessage.household_id == ctx.household.id)
                .order_by(OutgoingMessage.created_at.desc())
                .limit(RECENT_MESSAGES)
            )
        )
