import json
import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.audit_service.models import AuditLog
from app.audit_service import repository
from app.audit_service.schemas import (
    AuditLogResponse,
    AuditLogListResponse,
)

logger = logging.getLogger("hrms.audit")


def _format_audit_response(log: AuditLog) -> AuditLogResponse:
    user_name = None
    user_email = None
    user_role = None
    if log.user:
        user_name = log.user.full_name or log.user.email.split("@")[0]
        user_email = log.user.email
        user_role = log.user.role.upper() if log.user.role else None

    employee_code = None
    if log.employee:
        employee_code = log.employee.employee_code

    return AuditLogResponse(
        id=log.id,
        user_id=log.user_id,
        user_name=user_name,
        user_email=user_email,
        user_role=user_role,
        employee_id=log.employee_id,
        employee_code=employee_code,
        action=log.action,
        module=log.module,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        description=log.description,
        old_value=log.old_value,
        new_value=log.new_value,
        ip_address=log.ip_address,
        created_at=log.created_at,
    )


def log_audit_event(
    actor_user_id: Optional[int],
    action: str,
    entity_type: str = "SYSTEM",
    entity_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
    module: Optional[str] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    ip_address: Optional[str] = None,
    employee_id: Optional[int] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Persists an immutable audit log entry in the database.
    Compatible with existing call signatures.
    """
    # Auto-derive module from entity_type if not passed
    derived_module = module
    if not derived_module:
        e_upper = (entity_type or "").upper()
        if "AUTH" in e_upper or "USER" in e_upper:
            derived_module = "AUTHENTICATION"
        elif "PROJECT" in e_upper:
            derived_module = "PROJECTS"
        elif "ANNOUNCEMENT" in e_upper:
            derived_module = "ANNOUNCEMENTS"
        elif "COMPLAINT" in e_upper:
            derived_module = "COMPLAINTS"
        elif "ATTENDANCE" in e_upper:
            derived_module = "ATTENDANCE"
        elif "LEAVE" in e_upper:
            derived_module = "LEAVE"
        elif "EMPLOYEE" in e_upper:
            derived_module = "EMPLOYEE"
        elif "WORK_REPORT" in e_upper:
            derived_module = "WORK_REPORTS"
        else:
            derived_module = "SYSTEM"

    # Auto-derive description
    desc = description
    if not desc:
        if details and "title" in details:
            desc = f"{action}: {details['title']}"
        elif details and "status" in details:
            desc = f"{action} (Status: {details['status']})"
        elif entity_id:
            desc = f"{action} on {entity_type} #{entity_id}"
        else:
            desc = f"{action} on {entity_type}"

    old_val_str = json.dumps(old_value) if isinstance(old_value, (dict, list)) else (str(old_value) if old_value is not None else None)
    new_val_str = json.dumps(new_value) if isinstance(new_value, (dict, list)) else (str(new_value) if new_value is not None else None)

    data = {
        "user_id": actor_user_id,
        "employee_id": employee_id,
        "action": action.upper(),
        "module": derived_module.upper(),
        "entity_type": entity_type.upper() if entity_type else None,
        "entity_id": entity_id,
        "description": desc,
        "old_value": old_val_str,
        "new_value": new_val_str,
        "ip_address": ip_address,
        "created_at": datetime.now(timezone.utc),
    }

    def _persist(session: Session) -> AuditLog:
        return repository.create_audit_log(session, data)

    created = None
    if db is not None:
        created = _persist(db)
    else:
        with SessionLocal() as standalone_session:
            created = _persist(standalone_session)

    logger.info(f"[AUDIT] {data['action']} logged in {data['module']} by user {actor_user_id}")
    return {
        "id": created.id,
        "timestamp": created.created_at.isoformat() if created.created_at else None,
        "actor_user_id": created.user_id,
        "action": created.action,
        "module": created.module,
        "entity_type": created.entity_type,
        "entity_id": created.entity_id,
        "description": created.description,
        "details": details or {},
    }


def list_audit_logs(
    db: Session,
    user_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    module: Optional[str] = None,
    action: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 10,
    limit: int = 10,
    offset: int = 0,
) -> AuditLogListResponse:
    items, total = repository.list_audit_logs(
        db,
        user_id=user_id,
        employee_id=employee_id,
        module=module,
        action=action,
        search=search,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return AuditLogListResponse(
        total=total,
        items=[_format_audit_response(item) for item in items],
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_audit_log(db: Session, audit_id: int) -> AuditLogResponse:
    log_entry = repository.get_audit_log_by_id(db, audit_id)
    if not log_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log record not found.",
        )
    return _format_audit_response(log_entry)
