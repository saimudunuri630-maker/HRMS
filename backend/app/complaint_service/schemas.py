from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

from app.complaint_service.models import ComplaintType, ComplaintPriority, ComplaintStatus


class ComplaintCreate(BaseModel):
    complaint_type: ComplaintType = ComplaintType.OTHER
    project_id: Optional[int] = None
    subject: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=5)
    priority: ComplaintPriority = ComplaintPriority.MEDIUM


class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    hr_response: Optional[str] = None


class ComplaintFeedbackRequest(BaseModel):
    feedback: Optional[str] = None
    hr_response: Optional[str] = None
    status: Optional[ComplaintStatus] = None

    def model_post_init(self, __context):
        if not self.feedback and self.hr_response:
            self.feedback = self.hr_response
        elif not self.hr_response and self.feedback:
            self.hr_response = self.feedback


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    complaint_type: ComplaintType
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    project_code: Optional[str] = None
    subject: str
    description: str
    priority: ComplaintPriority
    status: ComplaintStatus
    hr_response: Optional[str] = None
    assigned_hr_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ComplaintListResponse(BaseModel):
    total: int
    items: List[ComplaintResponse]
