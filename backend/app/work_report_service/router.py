from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.authentication_service.dependencies import get_current_user
from app.work_report_service.models import ReportStatus
from app.work_report_service.schemas import (
    WorkReportCreate,
    WorkReportUpdate,
    WorkReportResponse,
    WorkReportListResponse,
)
from app.work_report_service import service

router = APIRouter(prefix="/api/work-reports", tags=["Work Reports"])


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


# ============================================================
# EMPLOYEE & HR PERSONAL WORK REPORT ROUTES
# ============================================================

@router.post("", response_model=WorkReportResponse, status_code=status.HTTP_201_CREATED)
def create_daily_report(
    payload: WorkReportCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.create_work_report(
        db=db,
        user=user,
        data=payload.model_dump(),
    )


@router.get("/me", response_model=WorkReportListResponse)
def list_my_work_reports(
    project_id: Optional[int] = None,
    report_date: Optional[date] = Query(None, alias="date"),
    status_filter: Optional[ReportStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.list_my_reports(
        db=db,
        user=user,
        project_id=project_id,
        report_date=report_date,
        status_filter=status_filter,
    )


@router.get("/me/{report_id}", response_model=WorkReportResponse)
def get_my_work_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.get_my_report(db=db, report_id=report_id, user=user)


@router.put("/me/{report_id}", response_model=WorkReportResponse)
def update_my_work_report(
    report_id: int,
    payload: WorkReportUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.update_work_report(
        db=db,
        report_id=report_id,
        user=user,
        data=payload.model_dump(exclude_unset=True),
    )


@router.delete("/me/{report_id}")
def delete_my_work_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.delete_work_report(db=db, report_id=report_id, user=user)


@router.post("/me/{report_id}/submit", response_model=WorkReportResponse)
def submit_my_work_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.update_work_report(
        db=db,
        report_id=report_id,
        user=user,
        data={"status": ReportStatus.SUBMITTED},
    )


# ============================================================
# HR WORK REPORT ROUTES
# ============================================================

@router.get("/hr", response_model=WorkReportListResponse)
def list_employee_work_reports(
    employee_id: Optional[int] = None,
    project_id: Optional[int] = None,
    report_date: Optional[date] = Query(None, alias="date"),
    status_filter: Optional[ReportStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    return service.list_hr_reports(
        db=db,
        employee_id=employee_id,
        project_id=project_id,
        report_date=report_date,
        status_filter=status_filter,
    )


@router.get("/hr/{report_id}", response_model=WorkReportResponse)
def get_employee_work_report_detail(
    report_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    return service.get_hr_report_by_id(db=db, report_id=report_id)
