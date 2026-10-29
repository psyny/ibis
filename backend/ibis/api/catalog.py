import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import household_context
from db.session import get_db
from domain.roles import MIN_ROLE_MANAGE, MIN_ROLE_VIEW
from schemas.catalog_schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    PresetCreate,
    PresetRead,
    PresetUpdate,
)
from services.catalog_service import CatalogService, category_to_read, preset_to_read
from services.context import HouseholdContext

router = APIRouter(prefix="/api/households/{household_id}", tags=["catalog"])

view = household_context(MIN_ROLE_VIEW)
manage = household_context(MIN_ROLE_MANAGE)


@router.get("/categories", response_model=list[CategoryRead])
def list_categories(
    include_archived: bool = False, ctx: HouseholdContext = Depends(view), db: Session = Depends(get_db)
):
    return [category_to_read(c) for c in CatalogService(db).list_categories(ctx.household.id, include_archived)]


@router.post("/categories", response_model=CategoryRead, status_code=201)
def create_category(data: CategoryCreate, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    return category_to_read(CatalogService(db).create_category(ctx, data))


@router.put("/categories/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: uuid.UUID, data: CategoryUpdate, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)
):
    return category_to_read(CatalogService(db).update_category(ctx, category_id, data))


@router.delete("/categories/{category_id}")
def delete_category(category_id: uuid.UUID, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    """Deletes the category, or archives it when costs already use it."""
    deleted = CatalogService(db).delete_category(ctx, category_id)
    return {"deleted": deleted, "archived": not deleted}


@router.get("/presets", response_model=list[PresetRead])
def list_presets(ctx: HouseholdContext = Depends(view), db: Session = Depends(get_db)):
    return [preset_to_read(p) for p in CatalogService(db).list_presets(ctx.household.id)]


@router.post("/presets", response_model=PresetRead, status_code=201)
def create_preset(data: PresetCreate, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    return preset_to_read(CatalogService(db).create_preset(ctx, data))


@router.put("/presets/{preset_id}", response_model=PresetRead)
def update_preset(
    preset_id: uuid.UUID, data: PresetUpdate, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)
):
    return preset_to_read(CatalogService(db).update_preset(ctx, preset_id, data))


@router.delete("/presets/{preset_id}", status_code=204)
def delete_preset(preset_id: uuid.UUID, ctx: HouseholdContext = Depends(manage), db: Session = Depends(get_db)):
    CatalogService(db).delete_preset(ctx, preset_id)
