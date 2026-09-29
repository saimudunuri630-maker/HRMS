from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.authentication_service.dependencies import get_current_user
from app.complaint_service.models import ComplaintType, ComplaintPriority, ComplaintStatus
from app.complaint_service.schemas import (
    ComplaintCreate,
    ComplaintUpdate,
    ComplaintFeedbackRequest,
    ComplaintResponse,
    ComplaintListResponse,
)
from app.complaint_service import service

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])


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
# EMPLOYEE COMPLAINT ROUTES
# ============================================================

@router.post("", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
def raise_complaint(
    payload: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.create_complaint(db=db, user=user, data=payload.model_dump())


@router.get("/me", response_model=ComplaintListResponse)
def list_my_complaints(
    complaint_type: Optional[ComplaintType] = Query(None, alias="type"),
    priority: Optional[ComplaintPriority] = None,
    status_filter: Optional[ComplaintStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.list_my_complaints(
        db=db,
        user=user,
        complaint_type=complaint_type,
        priority=priority,
        status_filter=status_filter,
    )


@router.get("/me/{complaint_id}", response_model=ComplaintResponse)
def get_my_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = _unwrap_user(current_user)
    return service.get_my_complaint(db=db, complaint_id=complaint_id, user=user)


# ============================================================
# HR COMPLAINT ROUTES
# ============================================================

@router.get("/hr", response_model=ComplaintListResponse)
def list_all_complaints(
    employee_id: Optional[int] = None,
    complaint_type: Optional[ComplaintType] = Query(None, alias="type"),
    project_id: Optional[int] = None,
    priority: Optional[ComplaintPriority] = None,
    status_filter: Optional[ComplaintStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    return service.list_hr_complaints(
        db=db,
        employee_id=employee_id,
        complaint_type=complaint_type,
        project_id=project_id,
        priority=priority,
        status_filter=status_filter,
    )


@router.get("/hr/{complaint_id}", response_model=ComplaintResponse)
def get_complaint_detail_for_hr(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    return service.get_hr_complaint(db=db, complaint_id=complaint_id)


@router.post("/hr/{complaint_id}/feedback", response_model=ComplaintResponse)
def add_hr_feedback(
    complaint_id: int,
    payload: ComplaintFeedbackRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    return service.add_hr_feedback(
        db=db,
        complaint_id=complaint_id,
        feedback=payload.feedback or payload.hr_response or "",
        status_val=payload.status,
        hr_user_id=current_user.id,
    )


@router.put("/hr/{complaint_id}", response_model=ComplaintResponse)
def update_complaint_by_hr(
    complaint_id: int,
    payload: ComplaintUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    return service.update_complaint_by_hr(
        db=db,
        complaint_id=complaint_id,
        data=payload.model_dump(exclude_unset=True),
        hr_user_id=current_user.id,
    )
