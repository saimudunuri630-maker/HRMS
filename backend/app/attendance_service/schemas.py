from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

from app.attendance_service.models import AttendanceStatus


class AttendanceCheckIn(BaseModel):
    remarks: Optional[str] = Field(
        default=None,
        max_length=500,
    )


class AttendanceCheckOut(BaseModel):
    remarks: Optional[str] = Field(
        default=None,
        max_length=500,
    )


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    department: Optional[str] = None
    attendance_date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    working_hours: Optional[str] = None
    working_hours_decimal: Optional[float] = None
    status: AttendanceStatus
    remarks: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AttendanceListResponse(BaseModel):
    total: int
    attendance: List[AttendanceResponse]
    items: Optional[List[AttendanceResponse]] = None

    def model_post_init(self, __context):
        if self.items is None:
            self.items = self.attendance


class AttendanceDailySummary(BaseModel):
    date: date
    total_active_employees: int
    present_count: int
    absent_count: int
    half_day_count: int
    on_leave_count: int
    present: Optional[int] = None
    absent: Optional[int] = None
    half_day: Optional[int] = None
    on_leave: Optional[int] = None

    def model_post_init(self, __context):
        if self.present is None:
            self.present = self.present_count
        if self.absent is None:
            self.absent = self.absent_count
        if self.half_day is None:
            self.half_day = self.half_day_count
        if self.on_leave is None:
            self.on_leave = self.on_leave_count


class AttendanceDateFilter(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[AttendanceStatus] = None