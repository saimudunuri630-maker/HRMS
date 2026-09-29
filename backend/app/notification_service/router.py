from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.authentication_service.dependencies import get_current_user
from app.authentication_service.models import User
from app.notification_service import service
from app.notification_service.schemas import (
    NotificationResponse,
    NotificationListResponse,
    NotificationUnreadCountResponse,
)

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


def _unwrap_user(auth_data) -> User:
    return auth_data[0] if isinstance(auth_data, tuple) else auth_data


@router.get("", response_model=NotificationListResponse)
@router.get("/", response_model=NotificationListResponse)
def list_my_notifications(
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    notification_type: Optional[str] = Query(None, alias="type", description="Filter by category/type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Page size"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Legacy limit parameter"),
    offset: Optional[int] = Query(None, ge=0, description="Legacy offset parameter"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    eff_limit = limit if limit is not None else page_size
    eff_offset = offset if offset is not None else (page - 1) * page_size
    eff_page = page if limit is None else (eff_offset // eff_limit) + 1
    eff_page_size = page_size if limit is None else eff_limit
    return service.list_user_notifications(
        db=db,
        user_id=user.id,
        is_read=is_read,
        notification_type=notification_type,
        page=eff_page,
        page_size=eff_page_size,
        limit=eff_limit,
        offset=eff_offset,
    )


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.get_user_unread_count(db=db, user_id=user.id)


@router.put("/read-all")
@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.mark_all_notifications_as_read(db=db, user_id=user.id)


@router.put("/{notification_id}/read", response_model=NotificationResponse)
@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.mark_notification_as_read(
        db=db,
        user_id=user.id,
        notification_id=notification_id,
    )
