from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.leave_service.models import LeaveStatus


# ============================================================
# LEAVE TYPE SCHEMAS
# ============================================================

class LeaveTypeBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    days_per_year: float = Field(default=12.0, ge=0)
    is_paid: bool = True
    is_active: bool = True


class LeaveTypeCreate(LeaveTypeBase):
    pass


class LeaveTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    days_per_year: Optional[float] = Field(None, ge=0)
    is_paid: Optional[bool] = None
    is_active: Optional[bool] = None


class LeaveTypeResponse(LeaveTypeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# LEAVE BALANCE SCHEMAS
# ============================================================

class LeaveBalanceResponse(BaseModel):
    id: int
    employee_id: int
    leave_type_id: int
    leave_type_name: str
    leave_type_code: str
    year: int
    total_allocated: float
    used_days: float
    pending_days: float
    remaining_days: float
    is_paid: bool

    class Config:
        from_attributes = True


class LeaveBalanceUpdate(BaseModel):
    total_allocated: Optional[float] = Field(None, ge=0)
    used_days: Optional[float] = Field(None, ge=0)
    pending_days: Optional[float] = Field(None, ge=0)


# ============================================================
# LEAVE REQUEST SCHEMAS
# ============================================================

class LeaveRequestCreate(BaseModel):
    employee_id: Optional[int] = None
    employee_code: Optional[str] = None
    leave_type_id: Optional[int] = None
    leave_type_code: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: str = Field(..., min_length=1, max_length=500)


class LeaveRequestAction(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class LeaveRequestResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    leave_type_id: int
    leave_type_name: str
    leave_type_code: str
    start_date: date
    end_date: date
    total_days: float
    reason: str
    status: LeaveStatus
    applied_at: datetime
    action_by_user_id: Optional[int] = None
    action_by_name: Optional[str] = None
    action_reason: Optional[str] = None
    action_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeaveListResponse(BaseModel):
    requests: List[LeaveRequestResponse]
    total: int
