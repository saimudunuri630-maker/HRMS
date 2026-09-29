from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.authentication_service.dependencies import get_current_user
from app.announcement_service.models import AnnouncementPriority, AnnouncementStatus
from app.announcement_service.schemas import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
    AnnouncementListResponse,
)
from app.announcement_service import service

router = APIRouter(prefix="/api/announcements", tags=["Announcements"])


def _unwrap_user(auth_data):
    return auth_data[0] if isinstance(auth_data, tuple) else auth_data


def require_hr_user(current_user=Depends(get_current_user)):
    user = _unwrap_user(current_user)
    if user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR administrators are authorized to perform this operation.",
        )
    return user


@router.post("", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
def create_announcement(
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    status_val = payload.status or AnnouncementStatus.DRAFT
    return service.create_announcement(
        db=db,
        title=payload.title,
        content=payload.content,
        priority=payload.priority,
        status_val=status_val,
        user_id=current_user.id,
    )


@router.get("", response_model=AnnouncementListResponse)
def list_announcements(
    priority: Optional[AnnouncementPriority] = None,
    status_filter: Optional[AnnouncementStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    is_hr = user.role == "hr"
    return service.list_announcements(
        db=db,
        is_hr=is_hr,
        priority=priority,
        status_filter=status_filter,
    )


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
def get_announcement_details(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    is_hr = user.role == "hr"
    return service.get_announcement_by_id(db, announcement_id, is_hr=is_hr)


@router.put("/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: int,
    payload: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    return service.update_announcement(
        db=db,
        announcement_id=announcement_id,
        data=payload.model_dump(exclude_unset=True),
        user_id=current_user.id,
    )


@router.post("/{announcement_id}/publish", response_model=AnnouncementResponse)
def publish_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    return service.publish_announcement(db, announcement_id, user_id=current_user.id)


@router.post("/{announcement_id}/archive", response_model=AnnouncementResponse)
def archive_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    return service.archive_announcement(db, announcement_id, user_id=current_user.id)
