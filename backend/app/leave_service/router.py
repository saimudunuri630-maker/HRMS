from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.authentication_service.dependencies import get_current_user
from app.authentication_service.models import User
from app.leave_service.models import LeaveStatus
from app.leave_service import service
from app.leave_service.schemas import (
    LeaveTypeCreate,
    LeaveTypeUpdate,
    LeaveTypeResponse,
    LeaveBalanceResponse,
    LeaveRequestCreate,
    LeaveRequestAction,
    LeaveRequestResponse,
    LeaveListResponse,
)

router = APIRouter(
    prefix="/api/leave",
    tags=["Leave Management"],
)


def _unwrap_user(auth_data) -> User:
    return auth_data[0] if isinstance(auth_data, tuple) else auth_data


# ============================================================
# LEAVE TYPES (HR MANAGES, EMPLOYEES VIEW)
# ============================================================

@router.get("/types", response_model=List[LeaveTypeResponse])
def get_leave_types(
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    return service.list_leave_types(db, active_only=True)


@router.post("/types", response_model=LeaveTypeResponse, status_code=status.HTTP_201_CREATED)
def create_leave_type(
    data: LeaveTypeCreate,
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    if user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only HR administrators can create leave types.",
        )
    return service.create_leave_type(db, data, actor_user_id=user.id)


@router.put("/types/{type_id}", response_model=LeaveTypeResponse)
def update_leave_type(
    type_id: int,
    data: LeaveTypeUpdate,
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    if user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only HR administrators can modify leave types.",
        )
    return service.update_leave_type(db, type_id, data, actor_user_id=user.id)


@router.put("/types/{type_id}/status", response_model=LeaveTypeResponse)
def update_leave_type_status(
    type_id: int,
    is_active: bool = Query(..., description="Active status flag"),
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    if user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only HR administrators can modify leave types.",
        )
    update_data = LeaveTypeUpdate(is_active=is_active)
    return service.update_leave_type(db, type_id, update_data, actor_user_id=user.id)


# ============================================================
# LEAVE BALANCES
# ============================================================

@router.get("/balances", response_model=List[LeaveBalanceResponse])
@router.get("/balances/me", response_model=List[LeaveBalanceResponse])
def get_my_leave_balances(
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    emp = service.get_employee_for_user(db, user)
    return service.get_employee_balances(db, emp.id)


@router.get("/balances/{employee_id}", response_model=List[LeaveBalanceResponse])
def get_employee_balances(
    employee_id: int,
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    if user.role != "hr":
        emp = service.get_employee_for_user(db, user)
        if emp.id != employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only view your own leave balance.",
            )
    return service.get_employee_balances(db, employee_id, year)


# ============================================================
# LEAVE REQUESTS
# ============================================================

@router.get("/requests/me", response_model=LeaveListResponse)
def list_my_leave_requests(
    status_filter: Optional[LeaveStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    emp = service.get_employee_for_user(db, user)
    return service.list_leave_requests(
        db=db,
        user=user,
        employee_id=emp.id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get("/requests/me/{request_id}", response_model=LeaveRequestResponse)
def get_my_leave_request(
    request_id: int,
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    return service.get_leave_request(db=db, user=user, request_id=request_id)


@router.get("/requests", response_model=LeaveListResponse)
def list_leave_requests(
    employee_id: Optional[int] = Query(None),
    status_filter: Optional[LeaveStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    return service.list_leave_requests(
        db=db,
        user=user,
        employee_id=employee_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post("/requests", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
def apply_leave_request(
    data: LeaveRequestCreate,
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    return service.apply_for_leave(db=db, user=user, data=data)


@router.get("/requests/{request_id}", response_model=LeaveRequestResponse)
def get_leave_request(
    request_id: int,
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    return service.get_leave_request(db=db, user=user, request_id=request_id)


@router.put("/requests/{request_id}/approve", response_model=LeaveRequestResponse)
@router.post("/requests/{request_id}/approve", response_model=LeaveRequestResponse)
@router.patch("/requests/{request_id}/approve", response_model=LeaveRequestResponse)
def approve_leave(
    request_id: int,
    action: Optional[LeaveRequestAction] = None,
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    if user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only HR administrators can approve leave requests.",
        )
    return service.approve_leave_request(
        db=db,
        hr_user=user,
        request_id=request_id,
        reason=action.reason if action else None,
    )


@router.put("/requests/{request_id}/reject", response_model=LeaveRequestResponse)
@router.post("/requests/{request_id}/reject", response_model=LeaveRequestResponse)
@router.patch("/requests/{request_id}/reject", response_model=LeaveRequestResponse)
def reject_leave(
    request_id: int,
    action: Optional[LeaveRequestAction] = None,
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    if user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only HR administrators can reject leave requests.",
        )
    return service.reject_leave_request(
        db=db,
        hr_user=user,
        request_id=request_id,
        reason=action.reason if action else None,
    )


@router.put("/requests/{request_id}/revoke", response_model=LeaveRequestResponse)
@router.post("/requests/{request_id}/revoke", response_model=LeaveRequestResponse)
@router.patch("/requests/{request_id}/revoke", response_model=LeaveRequestResponse)
def revoke_leave(
    request_id: int,
    action: Optional[LeaveRequestAction] = None,
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    if user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only HR administrators can revoke leave requests.",
        )
    return service.revoke_leave_request(
        db=db,
        hr_user=user,
        request_id=request_id,
        reason=action.reason if action else None,
    )



@router.put("/requests/{request_id}/cancel", response_model=LeaveRequestResponse)
@router.post("/requests/{request_id}/cancel", response_model=LeaveRequestResponse)
@router.patch("/requests/{request_id}/cancel", response_model=LeaveRequestResponse)
def cancel_leave(
    request_id: int,
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    return service.cancel_leave_request(
        db=db,
        user=user,
        request_id=request_id,
    )
