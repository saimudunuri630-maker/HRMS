from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.announcement_service.models import Announcement, AnnouncementStatus, AnnouncementPriority


def create_announcement(db: Session, data: dict) -> Announcement:
    announcement = Announcement(**data)
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


def get_announcement_by_id(db: Session, announcement_id: int) -> Optional[Announcement]:
    return db.query(Announcement).filter(Announcement.id == announcement_id).first()


def list_announcements(
    db: Session,
    status: Optional[AnnouncementStatus] = None,
    priority: Optional[AnnouncementPriority] = None,
) -> List[Announcement]:
    query = db.query(Announcement)
    if status:
        query = query.filter(Announcement.status == status)
    if priority:
        query = query.filter(Announcement.priority == priority)
    return query.order_by(desc(Announcement.created_at)).all()


def update_announcement(db: Session, announcement: Announcement, data: dict) -> Announcement:
    for key, value in data.items():
        if value is not None:
            setattr(announcement, key, value)
    db.commit()
    db.refresh(announcement)
    return announcement


def delete_announcement(db: Session, announcement: Announcement) -> None:
    db.delete(announcement)
    db.commit()
