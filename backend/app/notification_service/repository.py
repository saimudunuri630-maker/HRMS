from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.notification_service.models import Notification


def create_notification(db: Session, data: dict) -> Notification:
    notif = Notification(**data)
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def get_notification_by_id(db: Session, notification_id: int) -> Optional[Notification]:
    return db.query(Notification).filter(Notification.id == notification_id).first()


def get_unread_count(db: Session, user_id: int) -> int:
    return (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .count()
    )


def list_user_notifications(
    db: Session,
    user_id: int,
    is_read: Optional[bool] = None,
    notification_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Notification], int, int]:
    base_query = db.query(Notification).filter(Notification.user_id == user_id)
    unread_count = base_query.filter(Notification.is_read.is_(False)).count()

    filtered_query = db.query(Notification).filter(Notification.user_id == user_id)
    if is_read is not None:
        filtered_query = filtered_query.filter(Notification.is_read == is_read)
    if notification_type:
        filtered_query = filtered_query.filter(Notification.notification_type == notification_type.upper())

    total = filtered_query.count()
    items = (
        filtered_query.order_by(desc(Notification.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total, unread_count


def mark_as_read(db: Session, notification: Notification) -> Notification:
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return notification


def mark_all_as_read(db: Session, user_id: int) -> int:
    now = datetime.now(timezone.utc)
    updated_rows = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .update(
            {"is_read": True, "read_at": now},
            synchronize_session="fetch",
        )
    )
    db.commit()
    return updated_rows
