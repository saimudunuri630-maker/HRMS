from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.audit_service.models import AuditLog


def create_audit_log(db: Session, data: dict) -> AuditLog:
    log_entry = AuditLog(**data)
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


def get_audit_log_by_id(db: Session, audit_id: int) -> Optional[AuditLog]:
    return db.query(AuditLog).filter(AuditLog.id == audit_id).first()


def list_audit_logs(
    db: Session,
    user_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    module: Optional[str] = None,
    action: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[AuditLog], int]:
    query = db.query(AuditLog)

    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if employee_id is not None:
        query = query.filter(AuditLog.employee_id == employee_id)
    if module:
        query = query.filter(AuditLog.module == module.upper())
    if action:
        query = query.filter(AuditLog.action == action.upper())
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                AuditLog.description.ilike(pattern),
                AuditLog.action.ilike(pattern),
                AuditLog.module.ilike(pattern),
            )
        )

    total = query.count()
    items = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()
    return items, total
