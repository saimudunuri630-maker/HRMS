import logging
from datetime import date, datetime, timezone
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.attendance_service import repository
from app.attendance_service.models import Attendance, AttendanceStatus
from app.employee_service.models import Employee, EmploymentStatus
from app.leave_service.models import LeaveRequest, LeaveStatus
from app.audit_service.service import log_audit_event

logger = logging.getLogger("hrms.attendance")


def get_or_ensure_employee(db: Session, user) -> Employee:
    emp = (
        db.query(Employee)
        .filter(Employee.user_id == user.id, Employee.deleted_at.is_(None))
        .first()
    )
    if emp:
        return emp

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Employee profile not found for this account. Please contact HR.",
    )


def _calc_working_hours(
    check_in: Optional[datetime], check_out: Optional[datetime]
) -> Tuple[Optional[str], Optional[float]]:
    if not check_in or not check_out:
        return None, None
    diff = check_out - check_in
    total_seconds = max(0, int(diff.total_seconds()))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    formatted = f"{hours:02d}h {minutes:02d}m"
    decimal_hours = round(total_seconds / 3600.0, 2)
    return formatted, decimal_hours


def _format_attendance_response(a: Attendance, emp: Optional[Employee] = None) -> dict:
    employee = emp or getattr(a, "employee", None)
    emp_name = (
        f"{employee.first_name} {employee.last_name}".strip()
        if employee
        else "Unknown"
    )
    emp_code = employee.employee_code if employee else ""
    dept = "General Operations"

    wh_str, wh_dec = _calc_working_hours(a.check_in, a.check_out)

    return {
        "id": a.id,
        "employee_id": a.employee_id,
        "employee_name": emp_name,
        "employee_code": emp_code,
        "department": dept,
        "attendance_date": a.attendance_date,
        "check_in": a.check_in,
        "check_out": a.check_out,
        "working_hours": wh_str,
        "working_hours_decimal": wh_dec,
        "status": a.status,
        "remarks": a.remarks,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


def check_in(
    db: Session,
    user,
    remarks: Optional[str] = None,
) -> dict:
    employee = get_or_ensure_employee(db, user)
    if employee.employment_status != EmploymentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive employees cannot mark attendance.",
        )

    today = date.today()

    # Check if employee has approved leave today
    approved_leave = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.start_date <= today,
            LeaveRequest.end_date >= today,
        )
        .first()
    )
    if approved_leave:
        lt_name = approved_leave.leave_type.name if approved_leave.leave_type else "Leave"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You are on approved leave today ({lt_name}). Check-in is not required.",
        )

    existing = repository.get_attendance_by_employee_and_date(db, employee.id, today)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attendance already marked for today.",
        )

    now = datetime.now(timezone.utc)
    attendance = Attendance(
        employee_id=employee.id,
        attendance_date=today,
        check_in=now,
        status=AttendanceStatus.PRESENT,
        remarks=remarks,
    )
    created = repository.create_attendance(db, attendance)

    log_audit_event(
        actor_user_id=user.id,
        action="Attendance login",
        entity_type="Attendance",
        entity_id=created.id,
        details={"date": str(today), "login_time": now.isoformat()},
    )

    return _format_attendance_response(created, employee)


def check_out(
    db: Session,
    user,
    remarks: Optional[str] = None,
) -> dict:
    employee = get_or_ensure_employee(db, user)
    today = date.today()

    attendance = repository.get_attendance_by_employee_and_date(db, employee.id, today)
    if not attendance or not attendance.check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please check in before checking out.",
        )

    if attendance.check_out:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attendance already checked out for today.",
        )

    now = datetime.now(timezone.utc)
    if now < attendance.check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-out time cannot be before check-in time.",
        )

    # Calculate working hours and determine correct shift status
    # 8h+ -> FULL_DAY (PRESENT), 4h to 7h59m -> HALF_DAY, < 4h -> NOT HALF_DAY (PRESENT)
    diff_sec = max(0.0, (now - attendance.check_in).total_seconds())
    if diff_sec >= 8.0 * 3600:
        status_to_set = AttendanceStatus.PRESENT
    elif diff_sec >= 4.0 * 3600:
        status_to_set = AttendanceStatus.HALF_DAY
    else:
        status_to_set = AttendanceStatus.PRESENT

    update_payload = {
        "check_out": now,
        "status": status_to_set,
    }
    if remarks is not None:
        update_payload["remarks"] = remarks

    updated = repository.update_attendance(db, attendance, update_payload)

    wh_str, _ = _calc_working_hours(attendance.check_in, now)

    log_audit_event(
        actor_user_id=user.id,
        action="Attendance logout",
        entity_type="Attendance",
        entity_id=updated.id,
        details={
            "date": str(today),
            "login_time": attendance.check_in.isoformat(),
            "logout_time": now.isoformat(),
            "working_hours": wh_str,
            "status": status_to_set.value,
        },
    )

    return _format_attendance_response(updated, employee)


def get_my_today_attendance(db: Session, user) -> Optional[dict]:
    employee = get_or_ensure_employee(db, user)
    today = date.today()
    attendance = repository.get_attendance_by_employee_and_date(db, employee.id, today)
    if not attendance:
        approved_leave = (
            db.query(LeaveRequest)
            .filter(
                LeaveRequest.employee_id == employee.id,
                LeaveRequest.status == LeaveStatus.APPROVED,
                LeaveRequest.start_date <= today,
                LeaveRequest.end_date >= today,
            )
            .first()
        )
        if approved_leave:
            lt_name = approved_leave.leave_type.name if approved_leave.leave_type else "Leave"
            now_dt = datetime.now(timezone.utc)
            return {
                "id": -approved_leave.id,
                "employee_id": employee.id,
                "employee_name": f"{employee.first_name} {employee.last_name}".strip(),
                "employee_code": employee.employee_code,
                "department": "General Operations",
                "attendance_date": today,
                "check_in": None,
                "check_out": None,
                "working_hours": None,
                "working_hours_decimal": None,
                "status": AttendanceStatus.ON_LEAVE,
                "remarks": f"On Approved Leave: {lt_name}",
                "created_at": approved_leave.created_at or now_dt,
                "updated_at": approved_leave.updated_at or now_dt,
            }
        return None
    return _format_attendance_response(attendance, employee)


def get_my_attendance(
    db: Session,
    user,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status_filter: Optional[AttendanceStatus] = None,
) -> dict:
    employee = get_or_ensure_employee(db, user)
    records = repository.get_employee_attendance(
        db,
        employee.id,
        start_date=start_date,
        end_date=end_date,
        status=status_filter,
    )
    return {
        "total": len(records),
        "attendance": [_format_attendance_response(r, employee) for r in records],
    }


def get_hr_daily_summary(db: Session, target_date: Optional[date] = None) -> dict:
    t_date = target_date or date.today()

    active_employees = (
        db.query(Employee)
        .filter(Employee.employment_status == EmploymentStatus.ACTIVE)
        .all()
    )
    total_active = len(active_employees)
    active_emp_ids = {e.id for e in active_employees}

    # 1. Check approved leaves covering target_date
    approved_leaves = (
        db.query(LeaveRequest.employee_id)
        .filter(
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.start_date <= t_date,
            LeaveRequest.end_date >= t_date,
            LeaveRequest.employee_id.in_(active_emp_ids) if active_emp_ids else False,
        )
        .all()
    )
    leave_emp_ids = {l[0] for l in approved_leaves}

    # 2. Get today's attendance records for active employees
    attendances = (
        db.query(Attendance)
        .filter(
            Attendance.attendance_date == t_date,
            Attendance.employee_id.in_(active_emp_ids) if active_emp_ids else False,
        )
        .all()
    )

    present_count = 0
    half_day_count = 0
    attended_emp_ids = set()

    for a in attendances:
        attended_emp_ids.add(a.employee_id)
        if a.status == AttendanceStatus.PRESENT:
            present_count += 1
        elif a.status == AttendanceStatus.HALF_DAY:
            half_day_count += 1
        elif a.status == AttendanceStatus.ON_LEAVE:
            leave_emp_ids.add(a.employee_id)

    on_leave_count = len(leave_emp_ids)
    # Absent: active employees without present, half-day, or on-leave
    accounted_for = present_count + half_day_count + on_leave_count
    absent_count = max(0, total_active - accounted_for)

    return {
        "date": t_date,
        "total_active_employees": total_active,
        "present_count": present_count,
        "absent_count": absent_count,
        "half_day_count": half_day_count,
        "on_leave_count": on_leave_count,
    }


def get_hr_attendance_list(
    db: Session,
    target_date: Optional[date] = None,
    employee_id: Optional[int] = None,
    status_filter: Optional[AttendanceStatus] = None,
) -> dict:
    t_date = target_date or date.today()

    query = (
        db.query(Attendance)
        .join(Employee, Attendance.employee_id == Employee.id)
        .filter(Attendance.attendance_date == t_date)
    )

    if employee_id is not None:
        query = query.filter(Attendance.employee_id == employee_id)
    if status_filter is not None:
        query = query.filter(Attendance.status == status_filter)

    attendances = query.order_by(Employee.first_name, Employee.last_name).all()

    # Also build virtual/unrecorded list for active employees if viewing today without specific employee filter
    emp_map = {e.id: e for e in db.query(Employee).filter(Employee.employment_status == EmploymentStatus.ACTIVE).all()}

    results = []
    recorded_ids = set()
    for a in attendances:
        recorded_ids.add(a.employee_id)
        emp = emp_map.get(a.employee_id) or a.employee
        results.append(_format_attendance_response(a, emp))

    # If no specific employee was filtered and status is either None or ABSENT/ON_LEAVE, include unrecorded active employees
    if employee_id is None:
        approved_leaves = (
            db.query(LeaveRequest.employee_id)
            .filter(
                LeaveRequest.status == LeaveStatus.APPROVED,
                LeaveRequest.start_date <= t_date,
                LeaveRequest.end_date >= t_date,
            )
            .all()
        )
        leave_emp_ids = {l[0] for l in approved_leaves}

        for eid, emp in emp_map.items():
            if eid not in recorded_ids:
                is_leave = eid in leave_emp_ids
                emp_status = AttendanceStatus.ON_LEAVE if is_leave else AttendanceStatus.ABSENT
                if status_filter is None or status_filter == emp_status:
                    results.append({
                        "id": -eid,  # Virtual id
                        "employee_id": eid,
                        "employee_name": f"{emp.first_name} {emp.last_name}".strip(),
                        "employee_code": emp.employee_code,
                        "department": "General Operations",
                        "attendance_date": t_date,
                        "check_in": None,
                        "check_out": None,
                        "working_hours": None,
                        "working_hours_decimal": None,
                        "status": emp_status,
                        "remarks": "Approved Leave" if is_leave else "Not checked in",
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    })

    return {
        "total": len(results),
        "attendance": results,
    }