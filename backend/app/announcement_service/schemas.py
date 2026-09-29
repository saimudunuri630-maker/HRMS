from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

from app.announcement_service.models import AnnouncementPriority, AnnouncementStatus


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=5)
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    status: Optional[AnnouncementStatus] = AnnouncementStatus.DRAFT


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    content: Optional[str] = Field(None, min_length=5)
    priority: Optional[AnnouncementPriority] = None
    status: Optional[AnnouncementStatus] = None


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    priority: AnnouncementPriority
    status: AnnouncementStatus
    published_at: Optional[datetime] = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    creator_name: Optional[str] = None


class AnnouncementListResponse(BaseModel):
    total: int
    items: List[AnnouncementResponse]
