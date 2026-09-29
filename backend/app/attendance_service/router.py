from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.attendance_service import service
from app.attendance_service.models import AttendanceStatus
from app.attendance_service.schemas import (
    AttendanceCheckIn,
    AttendanceCheckOut,
    AttendanceListResponse,
    AttendanceResponse,
    AttendanceDailySummary,
)
from app.authentication_service.dependencies import get_current_user
from app.core.database import get_db

router = APIRouter(
    prefix="/api/attendance",
    tags=["Attendance"],
)


def _unwrap_user(auth_data):
    return auth_data[0] if isinstance(auth_data, tuple) else auth_data


def require_hr_user(current_user=Depends(get_current_user)):
    user = _unwrap_user(current_user)
    if user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR administrators are authorized to access this operation.",
        )
    return user


# =========================
# EMPLOYEE & HR OWN ATTENDANCE
# =========================

@router.post(
    "/check-in",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def check_in(
    data: AttendanceCheckIn = AttendanceCheckIn(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.check_in(
        db=db,
        user=user,
        remarks=data.remarks,
    )


@router.post(
    "/check-out",
    response_model=AttendanceResponse,
)
def check_out(
    data: AttendanceCheckOut = AttendanceCheckOut(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.check_out(
        db=db,
        user=user,
        remarks=data.remarks,
    )


@router.get(
    "/me",
    response_model=AttendanceListResponse,
)
def get_my_attendance(
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    status_filter: Optional[AttendanceStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.get_my_attendance(
        db=db,
        user=user,
        start_date=start_date,
        end_date=end_date,
        status_filter=status_filter,
    )


@router.get(
    "/me/history",
    response_model=AttendanceListResponse,
)
def get_my_attendance_history(
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    status_filter: Optional[AttendanceStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.get_my_attendance(
        db=db,
        user=user,
        start_date=start_date,
        end_date=end_date,
        status_filter=status_filter,
    )


@router.get(
    "/me/today",
    response_model=Optional[AttendanceResponse],
)
def get_my_today_attendance(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.get_my_today_attendance(
        db=db,
        user=user,
    )


# =========================
# HR ATTENDANCE ENDPOINTS
# =========================

@router.get(
    "/hr/daily-summary",
    response_model=AttendanceDailySummary,
)
def get_hr_daily_summary(
    summary_date: Optional[date] = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    return service.get_hr_daily_summary(db=db, target_date=summary_date)


@router.get(
    "/hr",
    response_model=AttendanceListResponse,
)
def get_all_attendance_for_hr(
    attendance_date: Optional[date] = Query(default=None, alias="date"),
    employee_id: Optional[int] = Query(default=None),
    status_filter: Optional[AttendanceStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    return service.get_hr_attendance_list(
        db=db,
        target_date=attendance_date,
        employee_id=employee_id,
        status_filter=status_filter,
    )


@router.get(
    "/hr/employee/{employee_id}",
    response_model=AttendanceListResponse,
)
def get_employee_attendance_for_hr(
    employee_id: int,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    status_filter: Optional[AttendanceStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    records = repository.get_employee_attendance(
        db=db,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        status=status_filter,
    )
    return {
        "total": len(records),
        "attendance": [service._format_attendance_response(r) for r in records],
    }


# Backwards compatibility routes
@router.get(
    "",
    response_model=AttendanceListResponse,
)
def get_all_attendance_compat(
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    status_filter: Optional[AttendanceStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    return service.get_hr_attendance_list(
        db=db,
        target_date=start_date or date.today(),
        status_filter=status_filter,
    )