import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models.user import User
from schemas.notification_schemas import NotificationBar, NotificationBox, NotificationRead
from services.notification_service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    box: NotificationBox = "inbox", user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """inbox: not deleted; deleted: deleted items (can be restored)."""
    return NotificationService(db).list_box(user, box)


@router.get("/bar", response_model=NotificationBar)
def notification_bar(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, unviewed = NotificationService(db).bar(user)
    return NotificationBar(items=[NotificationRead.model_validate(n) for n in items], unviewed_count=unviewed)


@router.post("/{notification_id}/view", response_model=NotificationRead)
def view(notification_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return NotificationService(db).view(user, notification_id)


@router.post("/{notification_id}/delete", response_model=NotificationRead)
def delete(notification_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Soft delete: the item moves to the Deleted tab."""
    return NotificationService(db).delete(user, notification_id, True)


@router.post("/{notification_id}/restore", response_model=NotificationRead)
def restore(notification_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return NotificationService(db).delete(user, notification_id, False)
