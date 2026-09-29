from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.authentication_service.dependencies import get_current_user
from app.authentication_service.models import User
from app.audit_service import service
from app.audit_service.schemas import (
    AuditLogResponse,
    AuditLogListResponse,
)

def _unwrap_user(auth_data) -> User:
    return auth_data[0] if isinstance(auth_data, tuple) else auth_data

def require_hr_user(current_user=Depends(get_current_user)) -> User:
    user = _unwrap_user(current_user)
    if user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to HR administrators only.",
        )
    return user

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=AuditLogListResponse)
@router.get("/", response_model=AuditLogListResponse)
def list_audit_logs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    module: Optional[str] = Query(None, description="Filter by module"),
    action: Optional[str] = Query(None, description="Filter by action"),
    search: Optional[str] = Query(None, description="Search description or action"),
    start_date: Optional[datetime] = Query(None, description="Filter start timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter end timestamp"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=200, description="Page size"),
    limit: Optional[int] = Query(None, ge=1, le=200, description="Legacy limit parameter"),
    offset: Optional[int] = Query(None, ge=0, description="Legacy offset parameter"),
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    """
    Returns audit log entries. Strictly restricted to HR administrators.
    """
    eff_limit = limit if limit is not None else page_size
    eff_offset = offset if offset is not None else (page - 1) * page_size
    eff_page = page if limit is None else (eff_offset // eff_limit) + 1
    eff_page_size = page_size if limit is None else eff_limit
    return service.list_audit_logs(
        db=db,
        user_id=user_id,
        employee_id=employee_id,
        module=module,
        action=action,
        search=search,
        start_date=start_date,
        end_date=end_date,
        page=eff_page,
        page_size=eff_page_size,
        limit=eff_limit,
        offset=eff_offset,
    )


@router.get("/{audit_id}", response_model=AuditLogResponse)
def get_audit_log_detail(
    audit_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_hr_user),
):
    """
    Returns details for a single audit log entry. Restricted to HR administrators.
    """
    return service.get_audit_log(db=db, audit_id=audit_id)
