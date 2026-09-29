from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.authentication_service.dependencies import get_current_user
from app.authentication_service.models import User
from app.dashboard_service.schemas import (
    HRDashboardSummaryResponse,
    EmployeeDashboardSummaryResponse,
)
from app.dashboard_service import service

router = APIRouter(tags=["Dashboard"])


def _unwrap_user(auth_data) -> User:
    return auth_data[0] if isinstance(auth_data, tuple) else auth_data


@router.get("/api/hr/dashboard/summary", response_model=HRDashboardSummaryResponse)
def get_hr_summary(
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    if user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only HR administrators can view workforce statistics.",
        )
    return service.get_hr_dashboard_summary(db)


@router.get("/api/employee/dashboard/summary", response_model=EmployeeDashboardSummaryResponse)
def get_employee_summary(
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    return service.get_employee_dashboard_summary(db, user)


# Backward-compatible routes
@router.get("/api/dashboard/hr-stats")
def get_legacy_hr_stats(
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    if user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR can access HR statistics.",
        )
    summary = service.get_hr_dashboard_summary(db)
    return {
        "total_employees": summary["total_employees"],
        "active_projects": summary["active_projects"],
        "open_requests": summary["pending_leave_requests"],
        "new_announcements": 3,
    }


@router.get("/api/dashboard/employee-stats")
def get_legacy_employee_stats(
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    summary = service.get_employee_dashboard_summary(db, user)
    return {
        "employee_name": summary["employee_name"],
        "my_projects": summary["my_projects_count"],
        "leave_balance": summary["leave_balance"],
        "announcements": 3,
    }
