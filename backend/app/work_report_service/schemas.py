from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

from app.work_report_service.models import ReportStatus


class WorkReportCreate(BaseModel):
    project_id: int
    report_date: date
    work_summary: str = Field(..., min_length=3)
    tasks_completed: Optional[str] = None
    hours_worked: float = Field(default=8.0, ge=0.0, le=24.0)
    achievements: Optional[str] = None
    blockers: Optional[str] = None
    next_day_plan: Optional[str] = None
    status: Optional[ReportStatus] = ReportStatus.DRAFT


class WorkReportUpdate(BaseModel):
    project_id: Optional[int] = None
    report_date: Optional[date] = None
    work_summary: Optional[str] = Field(None, min_length=3)
    tasks_completed: Optional[str] = None
    hours_worked: Optional[float] = Field(None, ge=0.0, le=24.0)
    achievements: Optional[str] = None
    blockers: Optional[str] = None
    next_day_plan: Optional[str] = None
    status: Optional[ReportStatus] = None


class WorkReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    project_id: int
    project_name: Optional[str] = None
    project_code: Optional[str] = None
    report_date: date
    work_summary: str
    tasks_completed: Optional[str] = None
    hours_worked: float
    achievements: Optional[str] = None
    blockers: Optional[str] = None
    next_day_plan: Optional[str] = None
    status: ReportStatus
    created_at: datetime
    updated_at: datetime


class WorkReportListResponse(BaseModel):
    total: int
    items: List[WorkReportResponse]
