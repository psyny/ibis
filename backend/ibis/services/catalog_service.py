import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from domain.roles import MIN_ROLE_MANAGE
from models.category import Category, CostPreset
from models.cost import RecurringCost
from repositories.cost_repository import CostRepository
from schemas.catalog_schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    PresetCreate,
    PresetRead,
    PresetUpdate,
)
from services.context import HouseholdContext
from services.errors import ConflictError, NotFoundError, ValidationError

# Used, in this fixed order, when a category is created without a color.
# Validated for colorblind separation and contrast on the app's dark surface.
DEFAULT_COLORS = [
    "#3987e5", "#d95926", "#199e70", "#c98500",
    "#d55181", "#008300", "#9085e9", "#e66767",
]


def category_to_read(category: Category) -> CategoryRead:
    return CategoryRead(id=category.id, name=category.name, color=category.color, is_archived=category.is_archived)


def preset_to_read(preset: CostPreset) -> PresetRead:
    return PresetRead(
        id=preset.id,
        name=preset.name,
        category_id=preset.category_id,
        default_amount=float(preset.default_amount) if preset.default_amount is not None else None,
    )


class CatalogService:
    def __init__(self, db: Session):
        self.db = db

    # --- Categories -------------------------------------------------------------
    def list_categories(self, household_id: uuid.UUID, include_archived: bool = False) -> list[Category]:
        query = select(Category).where(Category.household_id == household_id)
        if not include_archived:
            query = query.where(Category.is_archived.is_(False))
        return list(self.db.scalars(query.order_by(func.lower(Category.name))))

    def get_category(self, household_id: uuid.UUID, category_id: uuid.UUID) -> Category:
        category = self.db.get(Category, category_id)
        if category is None or category.household_id != household_id:
            raise NotFoundError("Category not found")
        return category

    def resolve_category(
        self, household_id: uuid.UUID, category_id: Optional[uuid.UUID], allow_archived_id: Optional[uuid.UUID] = None
    ) -> Optional[Category]:
        """Validate a category chosen for a cost. Archived ones are only kept if already set."""
        if category_id is None:
            return None
        category = self.get_category(household_id, category_id)
        if category.is_archived and category.id != allow_archived_id:
            raise ValidationError(f"Category '{category.name}' is archived")
        return category

    def create_category(self, ctx: HouseholdContext, data: CategoryCreate) -> Category:
        ctx.require(MIN_ROLE_MANAGE)
        self._check_unique_name(ctx.household.id, data.name)
        existing = self.list_categories(ctx.household.id, include_archived=True)
        color = data.color or DEFAULT_COLORS[len(existing) % len(DEFAULT_COLORS)]
        category = Category(household_id=ctx.household.id, name=data.name.strip(), color=color)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def update_category(self, ctx: HouseholdContext, category_id: uuid.UUID, data: CategoryUpdate) -> Category:
        ctx.require(MIN_ROLE_MANAGE)
        category = self.get_category(ctx.household.id, category_id)
        if data.name and data.name.strip() != category.name:
            self._check_unique_name(ctx.household.id, data.name, exclude_id=category.id)
            category.name = data.name.strip()
        if data.color:
            category.color = data.color
        if data.is_archived is not None:
            category.is_archived = data.is_archived
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete_category(self, ctx: HouseholdContext, category_id: uuid.UUID) -> bool:
        """Delete an unused category; archive it if costs use it. Returns True if deleted."""
        ctx.require(MIN_ROLE_MANAGE)
        category = self.get_category(ctx.household.id, category_id)
        used_by_recurring = self.db.scalar(
            select(func.count()).select_from(RecurringCost).where(RecurringCost.category_id == category.id)
        )
        if CostRepository(self.db).is_category_used(category.id) or used_by_recurring:
            category.is_archived = True
            self.db.commit()
            return False
        self.db.delete(category)
        self.db.commit()
        return True

    def _check_unique_name(self, household_id: uuid.UUID, name: str, exclude_id: Optional[uuid.UUID] = None) -> None:
        for category in self.list_categories(household_id, include_archived=True):
            if category.id != exclude_id and category.name.casefold() == name.strip().casefold():
                raise ConflictError(f"A category named '{category.name}' already exists")

    # --- Presets (premade cost descriptions) ------------------------------------
    def list_presets(self, household_id: uuid.UUID) -> list[CostPreset]:
        return list(
            self.db.scalars(
                select(CostPreset).where(CostPreset.household_id == household_id).order_by(func.lower(CostPreset.name))
            ).unique()
        )

    def get_preset(self, household_id: uuid.UUID, preset_id: uuid.UUID) -> CostPreset:
        preset = self.db.get(CostPreset, preset_id)
        if preset is None or preset.household_id != household_id:
            raise NotFoundError("Preset not found")
        return preset

    def create_preset(self, ctx: HouseholdContext, data: PresetCreate) -> CostPreset:
        ctx.require(MIN_ROLE_MANAGE)
        category = self.resolve_category(ctx.household.id, data.category_id)
        preset = CostPreset(
            household_id=ctx.household.id,
            name=data.name.strip(),
            category_id=category.id if category else None,
            default_amount=data.default_amount,
        )
        self.db.add(preset)
        self.db.commit()
        self.db.refresh(preset)
        return preset

    def update_preset(self, ctx: HouseholdContext, preset_id: uuid.UUID, data: PresetUpdate) -> CostPreset:
        ctx.require(MIN_ROLE_MANAGE)
        preset = self.get_preset(ctx.household.id, preset_id)
        if data.name:
            preset.name = data.name.strip()
        if data.clear_category:
            preset.category_id = None
        elif data.category_id is not None:
            preset.category_id = self.resolve_category(ctx.household.id, data.category_id).id
        if data.clear_default_amount:
            preset.default_amount = None
        elif data.default_amount is not None:
            preset.default_amount = data.default_amount
        self.db.commit()
        self.db.refresh(preset)
        return preset

    def delete_preset(self, ctx: HouseholdContext, preset_id: uuid.UUID) -> None:
        ctx.require(MIN_ROLE_MANAGE)
        self.db.delete(self.get_preset(ctx.household.id, preset_id))
        self.db.commit()
