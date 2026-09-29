from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.leave_service.models import LeaveType, LeaveBalance, LeaveRequest, LeaveStatus
from app.employee_service.models import Employee


# ============================================================
# LEAVE TYPES REPOSITORY
# ============================================================

def get_all_leave_types(db: Session, active_only: bool = False) -> List[LeaveType]:
    query = db.query(LeaveType)
    if active_only:
        query = query.filter(LeaveType.is_active.is_(True))
    return query.order_by(LeaveType.id.asc()).all()


def get_leave_type_by_id(db: Session, type_id: int) -> Optional[LeaveType]:
    return db.query(LeaveType).filter(LeaveType.id == type_id).first()


def get_leave_type_by_code(db: Session, code: str) -> Optional[LeaveType]:
    return db.query(LeaveType).filter(LeaveType.code == code).first()


def create_leave_type(db: Session, leave_type: LeaveType) -> LeaveType:
    db.add(leave_type)
    db.commit()
    db.refresh(leave_type)
    return leave_type


def update_leave_type(db: Session, leave_type: LeaveType) -> LeaveType:
    leave_type.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(leave_type)
    return leave_type


# ============================================================
# LEAVE BALANCES REPOSITORY
# ============================================================

def get_employee_balance(
    db: Session, employee_id: int, leave_type_id: int, year: int
) -> Optional[LeaveBalance]:
    return (
        db.query(LeaveBalance)
        .filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.year == year,
        )
        .first()
    )


def get_all_employee_balances(
    db: Session, employee_id: int, year: Optional[int] = None
) -> List[LeaveBalance]:
    query = db.query(LeaveBalance).filter(LeaveBalance.employee_id == employee_id)
    if year:
        query = query.filter(LeaveBalance.year == year)
    return query.order_by(LeaveBalance.leave_type_id.asc()).all()


def create_or_init_balance(
    db: Session, employee_id: int, leave_type: LeaveType, year: int
) -> LeaveBalance:
    balance = get_employee_balance(db, employee_id, leave_type.id, year)
    if not balance:
        balance = LeaveBalance(
            employee_id=employee_id,
            leave_type_id=leave_type.id,
            year=year,
            total_allocated=leave_type.days_per_year,
            used_days=0.0,
            pending_days=0.0,
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)
    return balance


def ensure_employee_balances(db: Session, employee_id: int, year: int) -> List[LeaveBalance]:
    active_types = get_all_leave_types(db, active_only=True)
    results = []
    for lt in active_types:
        bal = create_or_init_balance(db, employee_id, lt, year)
        results.append(bal)
    return results


def update_balance(db: Session, balance: LeaveBalance) -> LeaveBalance:
    balance.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(balance)
    return balance


# ============================================================
# LEAVE REQUESTS REPOSITORY
# ============================================================

def get_leave_request_by_id(db: Session, request_id: int) -> Optional[LeaveRequest]:
    return db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()


def list_leave_requests(
    db: Session,
    employee_id: Optional[int] = None,
    status_filter: Optional[LeaveStatus] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[LeaveRequest], int]:
    query = db.query(LeaveRequest)
    if employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter)

    total = query.count()
    items = query.order_by(LeaveRequest.applied_at.desc()).offset(offset).limit(limit).all()
    return items, total


def create_leave_request(db: Session, request: LeaveRequest) -> LeaveRequest:
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def update_leave_request(db: Session, request: LeaveRequest) -> LeaveRequest:
    request.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(request)
    return request
