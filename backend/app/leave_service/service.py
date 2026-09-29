from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import logging
from app.authentication_service.models import User
from app.employee_service.models import Employee, EmploymentStatus
from app.leave_service.models import LeaveType, LeaveBalance, LeaveRequest, LeaveStatus
from app.leave_service import repository
from app.notification_service.service import create_in_app_notification
from app.audit_service.service import log_audit_event
from app.email_service.service import (
    send_leave_rejection_email,
    send_leave_approval_email,
    send_leave_revoked_email,
)
from app.leave_service.schemas import (
    LeaveTypeCreate,
    LeaveTypeUpdate,
    LeaveTypeResponse,
    LeaveBalanceResponse,
    LeaveRequestCreate,
    LeaveRequestResponse,
    LeaveListResponse,
)

logger = logging.getLogger("hrms.leave")


def seed_default_leave_types_if_empty(db: Session):
    existing = repository.get_all_leave_types(db)
    if not existing:
        defaults = [
            LeaveType(
                name="Annual Leave",
                code="ANNUAL",
                description="Standard annual paid vacation entitlement",
                days_per_year=12.0,
                is_paid=True,
                is_active=True,
            ),
            LeaveType(
                name="Casual Leave",
                code="CASUAL",
                description="Short-term personal or emergency leave",
                days_per_year=8.0,
                is_paid=True,
                is_active=True,
            ),
            LeaveType(
                name="Sick Leave",
                code="SICK",
                description="Medical recovery and illness leave",
                days_per_year=10.0,
                is_paid=True,
                is_active=True,
            ),
        ]
        for dt in defaults:
            db.add(dt)
        db.commit()


def get_employee_for_user(db: Session, user: User) -> Employee:
    employee = db.query(Employee).filter(Employee.user_id == user.id, Employee.deleted_at.is_(None)).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found for this authenticated account.",
        )
    return employee


# ============================================================
# LEAVE TYPE SERVICES
# ============================================================

def list_leave_types(db: Session, active_only: bool = False) -> List[LeaveTypeResponse]:
    seed_default_leave_types_if_empty(db)
    types = repository.get_all_leave_types(db, active_only=active_only)
    return [LeaveTypeResponse.model_validate(t) for t in types]


def create_leave_type(db: Session, data: LeaveTypeCreate, actor_user_id: Optional[int] = None) -> LeaveTypeResponse:
    seed_default_leave_types_if_empty(db)
    clean_code = data.code.strip().upper()
    existing = repository.get_leave_type_by_code(db, clean_code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Leave type code '{clean_code}' already exists.",
        )

    leave_type = LeaveType(
        name=data.name.strip(),
        code=clean_code,
        description=data.description.strip() if data.description else None,
        days_per_year=data.days_per_year,
        is_paid=data.is_paid,
        is_active=data.is_active,
    )
    saved = repository.create_leave_type(db, leave_type)

    if actor_user_id:
        try:
            log_audit_event(
                actor_user_id=actor_user_id,
                action="Leave type created",
                module="LEAVE",
                entity_type="LEAVE_TYPE",
                entity_id=saved.id,
                description=f"Created leave type '{saved.name}' ({saved.code}) with {saved.days_per_year} annual days",
                new_value={"name": saved.name, "code": saved.code, "days": saved.days_per_year, "is_paid": saved.is_paid},
                db=db,
            )
        except Exception as err:
            logger.warning(f"Failed to log audit for create_leave_type: {err}")

    return LeaveTypeResponse.model_validate(saved)


def update_leave_type(db: Session, type_id: int, data: LeaveTypeUpdate, actor_user_id: Optional[int] = None) -> LeaveTypeResponse:
    leave_type = repository.get_leave_type_by_id(db, type_id)
    if not leave_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave type not found.",
        )

    old_state = {"name": leave_type.name, "days": leave_type.days_per_year, "is_active": leave_type.is_active}

    if data.name is not None:
        leave_type.name = data.name.strip()
    if data.description is not None:
        leave_type.description = data.description.strip()
    if data.days_per_year is not None:
        leave_type.days_per_year = data.days_per_year
    if data.is_paid is not None:
        leave_type.is_paid = data.is_paid
    if data.is_active is not None:
        leave_type.is_active = data.is_active

    updated = repository.update_leave_type(db, leave_type)

    if actor_user_id:
        try:
            log_audit_event(
                actor_user_id=actor_user_id,
                action="Leave type updated",
                module="LEAVE",
                entity_type="LEAVE_TYPE",
                entity_id=updated.id,
                description=f"Updated leave type '{updated.name}' ({updated.code})",
                old_value=old_state,
                new_value={"name": updated.name, "days": updated.days_per_year, "is_active": updated.is_active},
                db=db,
            )
        except Exception as err:
            logger.warning(f"Failed to log audit for update_leave_type: {err}")

    return LeaveTypeResponse.model_validate(updated)


# ============================================================
# LEAVE BALANCE SERVICES
# ============================================================

def get_employee_balances(
    db: Session, employee_id: int, year: Optional[int] = None
) -> List[LeaveBalanceResponse]:
    seed_default_leave_types_if_empty(db)
    target_year = year or datetime.now(timezone.utc).year
    repository.ensure_employee_balances(db, employee_id, target_year)
    balances = repository.get_all_employee_balances(db, employee_id, target_year)

    results = []
    for b in balances:
        results.append(
            LeaveBalanceResponse(
                id=b.id,
                employee_id=b.employee_id,
                leave_type_id=b.leave_type_id,
                leave_type_name=b.leave_type.name if b.leave_type else "Leave",
                leave_type_code=b.leave_type.code if b.leave_type else "LV",
                year=b.year,
                total_allocated=b.total_allocated,
                used_days=b.used_days,
                pending_days=b.pending_days,
                remaining_days=b.remaining_days,
                is_paid=b.leave_type.is_paid if b.leave_type else True,
            )
        )
    return results


# ============================================================
# LEAVE REQUEST SERVICES
# ============================================================

def _to_request_response(req: LeaveRequest) -> LeaveRequestResponse:
    emp = req.employee
    emp_name = f"{emp.first_name} {emp.last_name}".strip() if emp else "Staff"
    emp_code = emp.employee_code if emp else "EMP"
    lt_name = req.leave_type.name if req.leave_type else "Leave"
    lt_code = req.leave_type.code if req.leave_type else "LV"
    action_name = req.action_by.full_name if req.action_by else None

    return LeaveRequestResponse(
        id=req.id,
        employee_id=req.employee_id,
        employee_name=emp_name,
        employee_code=emp_code,
        leave_type_id=req.leave_type_id,
        leave_type_name=lt_name,
        leave_type_code=lt_code,
        start_date=req.start_date,
        end_date=req.end_date,
        total_days=req.total_days,
        reason=req.reason,
        status=req.status,
        applied_at=req.applied_at,
        action_by_user_id=req.action_by_user_id,
        action_by_name=action_name,
        action_reason=req.action_reason,
        action_at=req.action_at,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


def _get_employee_email(emp: Optional[Employee]) -> Optional[str]:
    if not emp:
        return None
    if getattr(emp, "corporate_email", None) and emp.corporate_email.strip():
        return emp.corporate_email.strip()
    if emp.user and getattr(emp.user, "email", None) and emp.user.email.strip():
        return emp.user.email.strip()
    if getattr(emp, "personal_email", None) and emp.personal_email.strip():
        return emp.personal_email.strip()
    return None


def _get_employee_name(emp: Optional[Employee]) -> str:
    if not emp:
        return "Employee"
    first = getattr(emp, "first_name", "") or ""
    last = getattr(emp, "last_name", "") or ""
    name = f"{first} {last}".strip()
    return name or "Employee"


def apply_for_leave(db: Session, user: User, data: LeaveRequestCreate) -> LeaveRequestResponse:
    seed_default_leave_types_if_empty(db)

    # 1. Identify Target Employee (HR can specify target employee; Employees always get own)
    if user.role == "hr" and (data.employee_id or data.employee_code):
        if data.employee_id:
            employee = db.query(Employee).filter(Employee.id == data.employee_id, Employee.deleted_at.is_(None)).first()
        else:
            employee = db.query(Employee).filter(Employee.employee_code == data.employee_code.strip(), Employee.deleted_at.is_(None)).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected employee was not found in active roster.",
            )
    else:
        employee = get_employee_for_user(db, user)

    # 2. Validate employee is active
    if employee.employment_status != EmploymentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive employees cannot submit leave requests.",
        )

    # 3. Validate date range (default to today if omitted)
    start_date = data.start_date or date.today()
    end_date = data.end_date or start_date
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave start date cannot be after end date.",
        )

    # 4. Resolve standard Leave Type (ANNUAL, CASUAL, SICK)
    leave_type = None
    if data.leave_type_id:
        leave_type = repository.get_leave_type_by_id(db, data.leave_type_id)
    if not leave_type and data.leave_type_code:
        leave_type = repository.get_leave_type_by_code(db, data.leave_type_code.strip().upper())
    if not leave_type and data.reason:
        r_upper = data.reason.strip().upper()
        if "ANNUAL" in r_upper:
            leave_type = repository.get_leave_type_by_code(db, "ANNUAL")
        elif "CASUAL" in r_upper:
            leave_type = repository.get_leave_type_by_code(db, "CASUAL")
        elif "SICK" in r_upper:
            leave_type = repository.get_leave_type_by_code(db, "SICK")
    if not leave_type:
        leave_type = repository.get_leave_type_by_code(db, "ANNUAL")
    if not leave_type:
        active_types = repository.get_all_leave_types(db, active_only=True)
        if active_types:
            leave_type = active_types[0]

    if not leave_type or not leave_type.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or inactive leave type selected.",
        )

    # 5. Check for overlapping approved/pending requests
    overlapping = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
        .first()
    )
    if overlapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An overlapping leave request ({overlapping.start_date} to {overlapping.end_date}, Status: {overlapping.status.value}) already exists.",
        )

    # 6. Calculate total days
    total_days = float((end_date - start_date).days + 1)
    if total_days <= 0:
        total_days = 1.0

    # 7. Check leave balance
    req_year = start_date.year
    balance = repository.create_or_init_balance(db, employee.id, leave_type, req_year)

    if balance.remaining_days < total_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient leave balance for {leave_type.name}. Requested: {total_days:g} day(s), Available: {balance.remaining_days:g} day(s).",
        )

    # 8. Create request in PENDING state
    reason_text = data.reason.strip() if data.reason and data.reason.strip() else f"{leave_type.name} application"
    request = LeaveRequest(
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        reason=reason_text,
        status=LeaveStatus.PENDING,
    )
    saved = repository.create_leave_request(db, request)

    # Reserve pending days on balance (decreases Available/Remaining without increasing Used yet)
    balance.pending_days += total_days
    repository.update_balance(db, balance)

    # 9. Audit record
    try:
        log_audit_event(
            actor_user_id=user.id,
            action="LEAVE_REQUEST_CREATED",
            module="LEAVE",
            entity_type="LEAVE",
            entity_id=saved.id,
            employee_id=employee.id,
            description=f"Submitted {leave_type.name} request for {total_days:g} day(s) from {saved.start_date} to {saved.end_date}",
            new_value={"start_date": str(saved.start_date), "end_date": str(saved.end_date), "days": total_days, "type": leave_type.name},
            db=db,
        )
    except Exception as err:
        logger.warning(f"Failed to log leave creation audit: {err}")

    # 10. Notification
    try:
        emp_name = _get_employee_name(employee)
        if user.role != "hr":
            hr_users = db.query(User).filter(User.role == "hr", User.is_active == True).all()
            for hr in hr_users:
                create_in_app_notification(
                    user_id=hr.id,
                    title="New Leave Request",
                    message=f"{emp_name} has submitted a {leave_type.name} request ({total_days:g} day(s)).",
                    category="LEAVE",
                    metadata={"leave_request_id": saved.id, "entity_type": "LEAVE", "entity_id": saved.id},
                    db=db,
                )
        else:
            if employee.user_id:
                create_in_app_notification(
                    user_id=employee.user_id,
                    title="Leave Request Logged by HR",
                    message=f"A {leave_type.name} request ({total_days:g} day(s)) has been logged for you by HR.",
                    category="LEAVE",
                    metadata={"leave_request_id": saved.id, "entity_type": "LEAVE", "entity_id": saved.id},
                    db=db,
                )
    except Exception as err:
        logger.warning(f"Failed to send leave request notification: {err}")

    return _to_request_response(saved)


def list_leave_requests(
    db: Session,
    user: User,
    employee_id: Optional[int] = None,
    status_filter: Optional[LeaveStatus] = None,
    limit: int = 50,
    offset: int = 0,
) -> LeaveListResponse:
    # Role-based restriction: Employees can ONLY view their own leave requests
    if user.role != "hr":
        emp = get_employee_for_user(db, user)
        employee_id = emp.id

    items, total = repository.list_leave_requests(
        db,
        employee_id=employee_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return LeaveListResponse(
        requests=[_to_request_response(r) for r in items],
        total=total,
    )


def get_leave_request(db: Session, user: User, request_id: int) -> LeaveRequestResponse:
    req = repository.get_leave_request_by_id(db, request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave request not found.",
        )

    if user.role != "hr":
        emp = get_employee_for_user(db, user)
        if req.employee_id != emp.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot view another employee's leave request.",
            )

    return _to_request_response(req)


def approve_leave_request(
    db: Session, hr_user: User, request_id: int, reason: Optional[str] = None
) -> LeaveRequestResponse:
    if hr_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only HR administrators can approve leave requests.",
        )

    req = repository.get_leave_request_by_id(db, request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave request not found.",
        )

    # State Machine: Only PENDING requests can be approved
    if req.status != LeaveStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve leave request with status '{req.status.value}'. Only PENDING requests can be approved.",
        )

    # Fetch and update balance: move pending_days -> used_days
    balance = repository.get_employee_balance(
        db, req.employee_id, req.leave_type_id, req.start_date.year
    )
    if balance:
        # Check that used + pending does not exceed allocation
        new_used = balance.used_days + req.total_days
        if new_used > balance.total_allocated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve: Employee has insufficient leave balance ({balance.remaining_days:g} days available).",
            )
        balance.pending_days = max(0.0, balance.pending_days - req.total_days)
        balance.used_days = new_used
        repository.update_balance(db, balance)

    req.status = LeaveStatus.APPROVED
    req.action_by_user_id = hr_user.id
    req.action_reason = reason.strip() if reason and reason.strip() else "Approved by HR"
    req.action_at = datetime.now(timezone.utc)
    updated = repository.update_leave_request(db, req)

    emp = updated.employee
    emp_name = _get_employee_name(emp)
    emp_email = _get_employee_email(emp)
    lt_name = updated.leave_type.name if updated.leave_type else "Leave"

    # Audit log
    try:
        log_audit_event(
            actor_user_id=hr_user.id,
            action="LEAVE APPROVED",
            module="LEAVE",
            entity_type="LEAVE",
            entity_id=updated.id,
            employee_id=updated.employee_id,
            description=f"Approved leave request #{updated.id} for employee {emp_name}",
            new_value={"status": "APPROVED", "remarks": req.action_reason, "days": updated.total_days},
            db=db,
        )
    except Exception as err:
        logger.warning(f"Failed to log leave approval audit: {err}")

    # In-app notification to employee
    if emp and emp.user_id:
        try:
            start_str = updated.start_date.strftime("%d %b %Y")
            end_str = updated.end_date.strftime("%d %b %Y")
            date_range_str = f"from {start_str} to {end_str}" if start_str != end_str else f"for {start_str}"
            create_in_app_notification(
                user_id=emp.user_id,
                title="Leave Request Approved",
                message=f"Your {lt_name} request ({updated.total_days:g} day(s)) {date_range_str} has been approved.",
                category="LEAVE",
                metadata={"leave_request_id": updated.id, "entity_type": "LEAVE", "entity_id": updated.id},
                db=db,
            )
        except Exception as err:
            logger.warning(f"Failed to notify employee of leave approval: {err}")

    # Email notification to employee
    if emp_email:
        try:
            send_leave_approval_email(
                recipient_email=emp_email,
                employee_name=emp_name,
                leave_type_name=lt_name,
                start_date=str(updated.start_date),
                end_date=str(updated.end_date),
                total_days=updated.total_days,
                approval_reason=req.action_reason,
                entity_id=updated.id,
                db=db,
            )
        except Exception as err:
            logger.warning(f"Failed to send leave approval email: {err}")

    return _to_request_response(updated)


def reject_leave_request(
    db: Session, hr_user: User, request_id: int, reason: Optional[str] = None
) -> LeaveRequestResponse:
    if hr_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only HR administrators can reject leave requests.",
        )

    # Mandatory rejection reason validation (Backend enforcement)
    if not reason or not reason.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is mandatory.",
        )

    req = repository.get_leave_request_by_id(db, request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave request not found.",
        )

    # State Machine: Only PENDING requests can be rejected
    if req.status != LeaveStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject leave request with status '{req.status.value}'. Only PENDING requests can be rejected.",
        )

    # Restore pending days without deducting from balance or altering used days
    balance = repository.get_employee_balance(
        db, req.employee_id, req.leave_type_id, req.start_date.year
    )
    if balance:
        balance.pending_days = max(0.0, balance.pending_days - req.total_days)
        repository.update_balance(db, balance)

    req.status = LeaveStatus.REJECTED
    req.action_by_user_id = hr_user.id
    req.action_reason = reason.strip()
    req.action_at = datetime.now(timezone.utc)
    updated = repository.update_leave_request(db, req)

    emp = updated.employee
    emp_name = _get_employee_name(emp)
    emp_email = _get_employee_email(emp)
    lt_name = updated.leave_type.name if updated.leave_type else "Leave"

    # Audit log
    try:
        log_audit_event(
            actor_user_id=hr_user.id,
            action="LEAVE_REJECTED",
            module="LEAVE",
            entity_type="LEAVE",
            entity_id=updated.id,
            employee_id=updated.employee_id,
            description=f"Rejected leave request #{updated.id}: {req.action_reason}",
            new_value={"status": "REJECTED", "remarks": req.action_reason},
            db=db,
        )
    except Exception as err:
        logger.warning(f"Failed to log leave rejection audit: {err}")

    # In-app notification to employee
    if emp and emp.user_id:
        try:
            create_in_app_notification(
                user_id=emp.user_id,
                title="Leave Request Rejected",
                message=f"Your {lt_name} request has been rejected. Reason: {req.action_reason}",
                category="LEAVE",
                metadata={"leave_request_id": updated.id, "entity_type": "LEAVE", "entity_id": updated.id},
                db=db,
            )
        except Exception as err:
            logger.warning(f"Failed to notify employee of leave rejection: {err}")

    # Email notification to employee with mandatory rejection reason
    if emp_email:
        try:
            send_leave_rejection_email(
                recipient_email=emp_email,
                employee_name=emp_name,
                leave_type_name=lt_name,
                start_date=str(updated.start_date),
                end_date=str(updated.end_date),
                total_days=updated.total_days,
                rejection_reason=req.action_reason,
                entity_id=updated.id,
                db=db,
            )
        except Exception as err:
            logger.warning(f"Failed to send leave rejection email: {err}")

    return _to_request_response(updated)


def revoke_leave_request(
    db: Session, hr_user: User, request_id: int, reason: Optional[str] = None
) -> LeaveRequestResponse:
    if hr_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only HR administrators can revoke leave requests.",
        )

    req = repository.get_leave_request_by_id(db, request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave request not found.",
        )

    # State Machine Validation:
    # Once REVOKED, no more actions are allowed
    if req.status == LeaveStatus.REVOKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke request: Leave request is already in REVOKED state.",
        )

    # Only APPROVED or REJECTED can be revoked
    if req.status not in [LeaveStatus.APPROVED, LeaveStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot revoke leave request with status '{req.status.value}'. Only APPROVED or REJECTED requests can be revoked.",
        )

    prev_status = req.status.value

    # If previously APPROVED, restore the consumed leave balance
    if req.status == LeaveStatus.APPROVED:
        balance = repository.get_employee_balance(
            db, req.employee_id, req.leave_type_id, req.start_date.year
        )
        if balance:
            balance.used_days = max(0.0, balance.used_days - req.total_days)
            repository.update_balance(db, balance)

    # If previously REJECTED:
    # Balance was never consumed, so do not alter used or pending days.

    # Transition to terminal REVOKED state
    req.status = LeaveStatus.REVOKED
    req.action_by_user_id = hr_user.id
    revoke_reason = reason.strip() if reason and reason.strip() else f"Revoked by HR (previously {prev_status})"
    req.action_reason = revoke_reason
    req.action_at = datetime.now(timezone.utc)
    updated = repository.update_leave_request(db, req)

    emp = updated.employee
    emp_name = _get_employee_name(emp)
    emp_email = _get_employee_email(emp)
    lt_name = updated.leave_type.name if updated.leave_type else "Leave"

    # Audit log
    try:
        log_audit_event(
            actor_user_id=hr_user.id,
            action="LEAVE_REVOKED",
            module="LEAVE",
            entity_type="LEAVE",
            entity_id=updated.id,
            employee_id=updated.employee_id,
            description=f"Revoked {prev_status} leave request #{updated.id} for employee {emp_name}",
            new_value={"status": "REVOKED", "previous_status": prev_status, "remarks": revoke_reason},
            db=db,
        )
    except Exception as err:
        logger.warning(f"Failed to log leave revocation audit: {err}")

    # In-app notification to employee
    if emp and emp.user_id:
        try:
            create_in_app_notification(
                user_id=emp.user_id,
                title="Leave Request Revoked",
                message=f"Your {lt_name} request ({updated.total_days:g} day(s)) has been revoked by HR (previously {prev_status}).",
                category="LEAVE",
                metadata={"leave_request_id": updated.id, "entity_type": "LEAVE", "entity_id": updated.id},
                db=db,
            )
        except Exception as err:
            logger.warning(f"Failed to notify employee of leave revoke: {err}")

    # Email notification to employee
    if emp_email:
        try:
            send_leave_revoked_email(
                recipient_email=emp_email,
                employee_name=emp_name,
                leave_type_name=lt_name,
                start_date=str(updated.start_date),
                end_date=str(updated.end_date),
                total_days=updated.total_days,
                previous_status=prev_status,
                entity_id=updated.id,
                db=db,
            )
        except Exception as err:
            logger.warning(f"Failed to send leave revoked email: {err}")

    return _to_request_response(updated)


def cancel_leave_request(db: Session, user: User, request_id: int) -> LeaveRequestResponse:
    req = repository.get_leave_request_by_id(db, request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave request not found.",
        )

    # Permission check: employee can cancel own; HR can also cancel
    emp = get_employee_for_user(db, user) if user.role != "hr" else None
    if user.role != "hr" and req.employee_id != emp.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only cancel your own leave requests.",
        )

    was_approved = req.status == LeaveStatus.APPROVED
    if req.status not in [LeaveStatus.PENDING, LeaveStatus.APPROVED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel leave request with status '{req.status.value}'.",
        )

    if user.role != "hr" and req.status != LeaveStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employees can only cancel PENDING leave requests. Please contact HR for approved leaves.",
        )

    # Restore days to balance
    balance = repository.get_employee_balance(
        db, req.employee_id, req.leave_type_id, req.start_date.year
    )
    if balance:
        if was_approved:
            balance.used_days = max(0.0, balance.used_days - req.total_days)
        else:
            balance.pending_days = max(0.0, balance.pending_days - req.total_days)
        repository.update_balance(db, balance)

    req.status = LeaveStatus.CANCELLED
    req.action_by_user_id = user.id
    req.action_reason = "Cancelled by applicant" if user.role != "hr" else "Cancelled by HR"
    req.action_at = datetime.now(timezone.utc)
    updated = repository.update_leave_request(db, req)

    # Audit log
    try:
        log_audit_event(
            actor_user_id=user.id,
            action="Leave cancelled",
            module="LEAVE",
            entity_type="LEAVE",
            entity_id=updated.id,
            employee_id=updated.employee_id,
            description=f"Cancelled leave request #{updated.id}",
            new_value={"status": "CANCELLED"},
            db=db,
        )
    except Exception as err:
        logger.warning(f"Failed to log leave cancellation audit: {err}")

    # If cancelled by HR, notify employee
    if user.role == "hr" and updated.employee and updated.employee.user_id:
        try:
            create_in_app_notification(
                user_id=updated.employee.user_id,
                title="Leave Request Cancelled",
                message="Your leave request has been cancelled by HR.",
                category="LEAVE",
                metadata={"leave_request_id": updated.id, "entity_type": "LEAVE", "entity_id": updated.id},
                db=db,
            )
        except Exception as err:
            logger.warning(f"Failed to notify employee of leave cancellation: {err}")

    return _to_request_response(updated)
