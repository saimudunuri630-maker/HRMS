import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.notification_service.models import Notification, NotificationType
from app.notification_service import repository
from app.notification_service.schemas import (
    NotificationResponse,
    NotificationListResponse,
    NotificationUnreadCountResponse,
)

logger = logging.getLogger("hrms.notification")


def create_in_app_notification(
    user_id: int,
    title: str,
    message: str,
    category: str = "SYSTEM",
    metadata: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Creates and persists a persistent in-app notification in the database.
    Compatible with calls that provide a Session or omit it.
    """
    meta = metadata or {}
    notif_type = (category or meta.get("notification_type") or "SYSTEM").upper()

    # Determine entity reference
    entity_type = meta.get("entity_type")
    if not entity_type:
        if "project_id" in meta:
            entity_type = "PROJECT"
        elif "announcement_id" in meta:
            entity_type = "ANNOUNCEMENT"
        elif "leave_request_id" in meta:
            entity_type = "LEAVE"
        elif "complaint_id" in meta:
            entity_type = "COMPLAINT"
        else:
            entity_type = notif_type

    entity_id = (
        meta.get("entity_id")
        or meta.get("project_id")
        or meta.get("announcement_id")
        or meta.get("leave_request_id")
        or meta.get("complaint_id")
    )

    data = {
        "user_id": user_id,
        "notification_type": notif_type,
        "title": title,
        "message": message,
        "entity_type": entity_type,
        "entity_id": int(entity_id) if entity_id is not None else None,
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
    }

    def _persist(session: Session) -> Notification:
        return repository.create_notification(session, data)

    created = None
    if db is not None:
        created = _persist(db)
    else:
        with SessionLocal() as standalone_session:
            created = _persist(standalone_session)

    logger.info(f"[NOTIFICATION] Dispatched notification #{created.id} to user {user_id} - '{title}'")
    return {
        "id": created.id,
        "user_id": created.user_id,
        "title": created.title,
        "message": created.message,
        "category": created.notification_type,
        "entity_type": created.entity_type,
        "entity_id": created.entity_id,
        "is_read": created.is_read,
        "created_at": created.created_at.isoformat() if created.created_at else None,
        "metadata": meta,
    }


def list_user_notifications(
    db: Session,
    user_id: int,
    is_read: Optional[bool] = None,
    notification_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    limit: int = 10,
    offset: int = 0,
) -> NotificationListResponse:
    items, total, unread_count = repository.list_user_notifications(
        db,
        user_id=user_id,
        is_read=is_read,
        notification_type=notification_type,
        limit=limit,
        offset=offset,
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return NotificationListResponse(
        total=total,
        unread_count=unread_count,
        items=[NotificationResponse.model_validate(n) for n in items],
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_user_unread_count(db: Session, user_id: int) -> NotificationUnreadCountResponse:
    count = repository.get_unread_count(db, user_id=user_id)
    return NotificationUnreadCountResponse(unread_count=count)


def mark_notification_as_read(
    db: Session,
    user_id: int,
    notification_id: int,
) -> NotificationResponse:
    notif = repository.get_notification_by_id(db, notification_id)
    if not notif or notif.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    updated = repository.mark_as_read(db, notif)
    return NotificationResponse.model_validate(updated)


def mark_all_notifications_as_read(
    db: Session,
    user_id: int,
) -> Dict[str, Any]:
    updated_count = repository.mark_all_as_read(db, user_id=user_id)
    return {
        "success": True,
        "updated_count": updated_count,
        "message": f"Marked {updated_count} notification(s) as read.",
    }
