import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.announcement_service import repository
from app.announcement_service.models import Announcement, AnnouncementStatus, AnnouncementPriority
from app.employee_service.models import Employee, EmploymentStatus
from app.notification_service.service import create_in_app_notification
from app.email_service.service import send_announcement_published_email
from app.audit_service.service import log_audit_event

logger = logging.getLogger("hrms.announcements")


def _format_announcement_response(a: Announcement) -> dict:
    creator_name = None
    if a.creator:
        creator_name = a.creator.full_name if hasattr(a.creator, "full_name") else f"{a.creator.first_name or ''} {a.creator.last_name or ''}".strip() or a.creator.email
    return {
        "id": a.id,
        "title": a.title,
        "content": a.content,
        "priority": a.priority,
        "status": a.status,
        "published_at": a.published_at,
        "created_by": a.created_by,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
        "creator_name": creator_name,
    }


def create_announcement(
    db: Session,
    title: str,
    content: str,
    priority: AnnouncementPriority,
    status_val: AnnouncementStatus,
    user_id: int,
) -> dict:
    clean_title = title.strip()
    if not clean_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Announcement title cannot be empty.",
        )

    now = datetime.now(timezone.utc)
    published_at = now if status_val == AnnouncementStatus.PUBLISHED else None

    data = {
        "title": clean_title,
        "content": content.strip(),
        "priority": priority,
        "status": status_val,
        "published_at": published_at,
        "created_by": user_id,
        "created_at": now,
        "updated_at": now,
    }
    announcement = repository.create_announcement(db, data)

    log_audit_event(
        actor_user_id=user_id,
        action="Announcement created",
        entity_type="Announcement",
        entity_id=announcement.id,
        details={"title": clean_title, "status": status_val.value, "priority": priority.value},
    )

    if status_val == AnnouncementStatus.PUBLISHED:
        _broadcast_announcement(db, announcement, user_id)

    return _format_announcement_response(announcement)


def update_announcement(
    db: Session,
    announcement_id: int,
    data: dict,
    user_id: int,
) -> dict:
    announcement = repository.get_announcement_by_id(db, announcement_id)
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    was_published = announcement.status == AnnouncementStatus.PUBLISHED
    target_status = data.get("status")

    if "title" in data and data["title"] is not None:
        data["title"] = data["title"].strip()
        if not data["title"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Announcement title cannot be empty.",
            )

    data["updated_at"] = datetime.now(timezone.utc)
    if target_status == AnnouncementStatus.PUBLISHED and not announcement.published_at:
        data["published_at"] = datetime.now(timezone.utc)

    updated = repository.update_announcement(db, announcement, data)

    log_audit_event(
        actor_user_id=user_id,
        action="Announcement updated",
        entity_type="Announcement",
        entity_id=updated.id,
        details={"updated_fields": list(data.keys())},
    )

    # If transitioning to PUBLISHED, broadcast to active employees
    if not was_published and updated.status == AnnouncementStatus.PUBLISHED:
        _broadcast_announcement(db, updated, user_id)

    return _format_announcement_response(updated)


def publish_announcement(db: Session, announcement_id: int, user_id: int) -> dict:
    announcement = repository.get_announcement_by_id(db, announcement_id)
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    now = datetime.now(timezone.utc)
    updated = repository.update_announcement(
        db,
        announcement,
        {"status": AnnouncementStatus.PUBLISHED, "published_at": now, "updated_at": now},
    )

    log_audit_event(
        actor_user_id=user_id,
        action="Announcement published",
        entity_type="Announcement",
        entity_id=updated.id,
        details={"title": updated.title, "priority": updated.priority.value},
    )

    _broadcast_announcement(db, updated, user_id)
    return _format_announcement_response(updated)


def archive_announcement(db: Session, announcement_id: int, user_id: int) -> dict:
    announcement = repository.get_announcement_by_id(db, announcement_id)
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    now = datetime.now(timezone.utc)
    updated = repository.update_announcement(
        db,
        announcement,
        {"status": AnnouncementStatus.ARCHIVED, "updated_at": now},
    )

    log_audit_event(
        actor_user_id=user_id,
        action="Announcement archived",
        entity_type="Announcement",
        entity_id=updated.id,
        details={"title": updated.title},
    )
    return _format_announcement_response(updated)


def get_announcement_by_id(db: Session, announcement_id: int, is_hr: bool = False) -> dict:
    announcement = repository.get_announcement_by_id(db, announcement_id)
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    # Non-HR employees can only view published announcements
    if not is_hr and announcement.status != AnnouncementStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found or not published yet.",
        )

    return _format_announcement_response(announcement)


def list_announcements(
    db: Session,
    is_hr: bool = False,
    priority: Optional[AnnouncementPriority] = None,
    status_filter: Optional[AnnouncementStatus] = None,
) -> dict:
    # Non-HR employees see only published announcements
    effective_status = status_filter if is_hr else AnnouncementStatus.PUBLISHED
    items = repository.list_announcements(db, status=effective_status, priority=priority)
    return {
        "total": len(items),
        "items": [_format_announcement_response(a) for a in items],
    }


def _broadcast_announcement(db: Session, announcement: Announcement, actor_user_id: int):
    """
    Finds all ACTIVE employees and:
    1. Creates an in-app notification
    2. Sends an email notification
    Does not crash if an individual email fails.
    """
    active_employees = (
        db.query(Employee)
        .filter(Employee.employment_status == EmploymentStatus.ACTIVE)
        .all()
    )

    pub_date_str = str(announcement.published_at.date()) if announcement.published_at else str(datetime.now(timezone.utc).date())

    for emp in active_employees:
        user = emp.user
        if not user:
            continue

        # 1. In-App Notification
        try:
            create_in_app_notification(
                user_id=user.id,
                title="New Announcement",
                message=f'A new company announcement has been published: "{announcement.title}"',
                category="ANNOUNCEMENT",
                metadata={"announcement_id": announcement.id, "entity_type": "ANNOUNCEMENT", "entity_id": announcement.id, "priority": announcement.priority.value},
                db=db,
            )
        except Exception as err:
            logger.warning(f"Failed to create announcement in-app notification for user {user.id}: {err}")

        # 2. Email Notification
        if user.email:
            try:
                send_announcement_published_email(
                    recipient_email=user.email,
                    first_name=emp.first_name or "Colleague",
                    title=announcement.title,
                    content=announcement.content,
                    priority=announcement.priority.value,
                    published_date=pub_date_str,
                    entity_id=announcement.id,
                    db=db,
                )
            except Exception as err:
                logger.warning(f"Could not deliver announcement email to {user.email}: {err}")
