from datetime import datetime, timezone
import math
import re

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.authentication_service.models import User
from app.employee_service.models import Employee, EmploymentStatus
from app.employee_service import repository
from app.employee_service.schemas import (
    EmployeeCreate,
    EmployeeProfileUpdate,
    EmployeeStatusUpdate,
    EmployeeUpdate,
)
from app.email_service.service import send_employee_welcome_email
from app.audit_service.service import log_audit_event



# ============================================================
# Employee Code Generator
# ============================================================

def generate_next_employee_code(db: Session) -> str:
    """
    Generate the next employee code.

    Example:
        EMP001
        EMP002
        EMP003
    """

    employee_codes = (
        db.query(Employee.employee_code)
        .filter(Employee.employee_code.like("EMP%"))
        .all()
    )

    max_number = 0

    pattern = re.compile(
        r"^EMP(\d+)$",
        re.IGNORECASE
    )

    for row in employee_codes:
        code = row[0]

        if not code:
            continue

        match = pattern.match(code)

        if match:
            number = int(match.group(1))

            if number > max_number:
                max_number = number

    return f"EMP{max_number + 1:03d}"


# ============================================================
# Create Employee
# ============================================================

def create_employee(
    db: Session,
    data: EmployeeCreate,
) -> Employee:

    # --------------------------------------------------------
    # 1. Normalize and Check email
    # --------------------------------------------------------
    clean_email = data.email.strip().lower()

    existing_user = (
        db.query(User)
        .filter(func.lower(User.email) == clean_email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists.",
        )

    # --------------------------------------------------------
    # 2. Generate or validate employee code
    # --------------------------------------------------------

    if hasattr(data, "employee_code") and data.employee_code and data.employee_code.strip():
        clean_code = data.employee_code.strip().upper()
        existing_emp = (
            db.query(Employee)
            .filter(func.upper(Employee.employee_code) == clean_code)
            .first()
        )
        if existing_emp:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An employee with employee code '{clean_code}' already exists.",
            )
        employee_code = clean_code
    else:
        employee_code = generate_next_employee_code(db)

    # --------------------------------------------------------
    # 3. Create User
    # --------------------------------------------------------

    user = User(
        email=clean_email,
        full_name=(
            f"{data.first_name.strip()} {data.last_name.strip()}"
        ).strip(),
        role="employee",
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    db.flush()

    # --------------------------------------------------------
    # 4. Create Employee profile
    # --------------------------------------------------------

    clean_designation = data.designation.strip() if data.designation else ""
    if not clean_designation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Designation is required.",
        )

    clean_department = data.department.strip() if data.department else "Engineering & Operations"

    employee = Employee(
        user_id=user.id,
        employee_code=employee_code,
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        phone=data.phone.strip() if data.phone else None,
        date_of_birth=data.date_of_birth,
        address=data.address.strip() if data.address else None,
        joining_date=data.joining_date,
        department=clean_department,
        designation=clean_designation,
        department_id=data.department_id,
        designation_id=data.designation_id,
        employment_status=EmploymentStatus.ACTIVE,
    )

    db.add(employee)

    # --------------------------------------------------------
    # 5. Commit transaction
    # --------------------------------------------------------

    try:
        db.commit()
        db.refresh(employee)

        # Send onboarding welcome email (Phase 23)
        try:
            send_employee_welcome_email(
                recipient_email=clean_email,
                first_name=data.first_name.strip(),
                employee_code=employee_code,
                entity_id=employee.id,
                db=db,
            )
        except Exception as e:
            print(f"[WARNING] Could not dispatch employee welcome email: {e}")

        try:
            log_audit_event(
                actor_user_id=None,
                action="Employee created",
                module="EMPLOYEE",
                entity_type="EMPLOYEE",
                entity_id=employee.id,
                employee_id=employee.id,
                description=f"Created employee {employee.first_name} {employee.last_name} ({employee.employee_code})",
                new_value={"code": employee.employee_code, "name": f"{employee.first_name} {employee.last_name}", "email": clean_email},
                db=db,
            )
        except Exception as e:
            print(f"[WARNING] Could not log audit for employee creation: {e}")

    except Exception:
        db.rollback()
        raise

    return employee


# ============================================================
# Get Employee By ID
# ============================================================

def get_employee_by_id(
    db: Session,
    employee_id: int,
) -> Employee:

    employee = repository.get_employee_by_id(
        db,
        employee_id,
    )

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    return employee


# ============================================================
# Get Employee By User ID
# ============================================================

def get_employee_by_user_id(
    db: Session,
    user_id: int,
) -> Employee:

    employee = repository.get_employee_by_user_id(
        db,
        user_id,
    )

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found",
        )

    return employee


# ============================================================
# List Employees
# ============================================================

def list_employees(
    db: Session,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
    department_id: int | None = None,
    designation_id: int | None = None,
    employment_status: EmploymentStatus | None = None,
):

    if page < 1:
        page = 1

    if limit < 1:
        limit = 20

    if limit > 100:
        limit = 100

    query = (
        db.query(Employee)
        .join(User, Employee.user_id == User.id)
        .filter(Employee.deleted_at.is_(None))
    )

    # --------------------------------------------------------
    # Department filter
    # --------------------------------------------------------

    if department_id is not None:
        query = query.filter(
            Employee.department_id == department_id
        )

    # --------------------------------------------------------
    # Designation filter
    # --------------------------------------------------------

    if designation_id is not None:
        query = query.filter(
            Employee.designation_id == designation_id
        )

    # --------------------------------------------------------
    # Employment status filter
    # --------------------------------------------------------

    if employment_status is not None:
        query = query.filter(
            Employee.employment_status
            == employment_status
        )

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    if search:
        search_pattern = f"%{search.strip()}%"

        query = query.filter(
            or_(
                Employee.employee_code.ilike(
                    search_pattern
                ),
                Employee.first_name.ilike(
                    search_pattern
                ),
                Employee.last_name.ilike(
                    search_pattern
                ),
                User.email.ilike(
                    search_pattern
                ),
            )
        )

    # --------------------------------------------------------
    # Total count
    # --------------------------------------------------------

    total = query.count()

    # --------------------------------------------------------
    # Pagination
    # --------------------------------------------------------

    offset = (page - 1) * limit

    employees = (
        query
        .order_by(Employee.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    total_pages = (
        math.ceil(total / limit)
        if total > 0
        else 1
    )

    return {
        "items": employees,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
    }


# ============================================================
# Update Employee
# ============================================================

def update_employee(
    db: Session,
    employee_id: int,
    data: EmployeeUpdate,
) -> Employee:

    employee = get_employee_by_id(
        db,
        employee_id,
    )

    update_data = data.model_dump(
        exclude_unset=True
    )

    updated = repository.update_employee(
        db,
        employee,
        update_data,
    )

    try:
        log_audit_event(
            actor_user_id=None,
            action="Employee updated",
            module="EMPLOYEE",
            entity_type="EMPLOYEE",
            entity_id=updated.id,
            employee_id=updated.id,
            description=f"Updated employee {updated.first_name} {updated.last_name} ({updated.employee_code})",
            new_value=list(update_data.keys()),
            db=db,
        )
    except Exception as e:
        print(f"[WARNING] Could not log audit for employee update: {e}")

    return updated


# ============================================================
# Update Employment Status
# ============================================================

def update_employee_status(
    db: Session,
    employee_id: int,
    data: EmployeeStatusUpdate,
) -> Employee:

    employee = get_employee_by_id(
        db,
        employee_id,
    )

    old_status = employee.employment_status.value if hasattr(employee.employment_status, "value") else str(employee.employment_status)

    employee = repository.update_employee_status(
        db,
        employee,
        data.employment_status,
    )

    # Keep User account status synchronized
    if data.employment_status in (
        EmploymentStatus.INACTIVE,
        EmploymentStatus.TERMINATED,
    ):
        employee.user.is_active = False

    elif data.employment_status == EmploymentStatus.ACTIVE:
        employee.user.is_active = True

    db.commit()
    db.refresh(employee)

    new_status = employee.employment_status.value if hasattr(employee.employment_status, "value") else str(employee.employment_status)
    try:
        log_audit_event(
            actor_user_id=None,
            action="Employee status updated",
            module="EMPLOYEE",
            entity_type="EMPLOYEE",
            entity_id=employee.id,
            employee_id=employee.id,
            description=f"Status changed from {old_status} to {new_status} for {employee.employee_code}",
            old_value=old_status,
            new_value=new_status,
            db=db,
        )
    except Exception as e:
        print(f"[WARNING] Could not log audit for employee status update: {e}")

    return employee


# ============================================================
# Activate Employee
# ============================================================

def activate_employee(
    db: Session,
    employee_id: int,
) -> Employee:

    employee = get_employee_by_id(
        db,
        employee_id,
    )

    employee.employment_status = (
        EmploymentStatus.ACTIVE
    )

    employee.user.is_active = True
    employee.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(employee)

    try:
        log_audit_event(
            actor_user_id=None,
            action="Employee activated",
            module="EMPLOYEE",
            entity_type="EMPLOYEE",
            entity_id=employee.id,
            employee_id=employee.id,
            description=f"Activated employee {employee.first_name} {employee.last_name} ({employee.employee_code})",
            new_value="ACTIVE",
            db=db,
        )
    except Exception as e:
        print(f"[WARNING] Could not log audit for employee activation: {e}")

    return employee


# ============================================================
# Deactivate Employee
# ============================================================

def deactivate_employee(
    db: Session,
    employee_id: int,
) -> Employee:

    employee = get_employee_by_id(
        db,
        employee_id,
    )

    employee.employment_status = (
        EmploymentStatus.INACTIVE
    )

    employee.user.is_active = False
    employee.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(employee)

    try:
        log_audit_event(
            actor_user_id=None,
            action="Employee deactivated",
            module="EMPLOYEE",
            entity_type="EMPLOYEE",
            entity_id=employee.id,
            employee_id=employee.id,
            description=f"Deactivated employee {employee.first_name} {employee.last_name} ({employee.employee_code})",
            new_value="INACTIVE",
            db=db,
        )
    except Exception as e:
        print(f"[WARNING] Could not log audit for employee deactivation: {e}")

    return employee


# ============================================================
# Archive Employee
# ============================================================

def archive_employee(
    db: Session,
    employee_id: int,
    user_id: int | None = None,
) -> Employee:

    employee = get_employee_by_id(
        db,
        employee_id,
    )

    now = datetime.now(timezone.utc)

    employee.deleted_at = now

    employee.employment_status = (
        EmploymentStatus.INACTIVE
    )

    if employee.user:
        employee.user.is_active = False

    employee.updated_at = now

    db.commit()
    db.refresh(employee)

    try:
        log_audit_event(
            actor_user_id=user_id,
            action="Employee removed",
            module="EMPLOYEE",
            entity_type="EMPLOYEE",
            entity_id=employee.id,
            employee_id=employee.id,
            description=f"Removed employee {employee.first_name} {employee.last_name} ({employee.employee_code})",
            db=db,
        )
    except Exception as e:
        print(f"[WARNING] Could not log audit for employee removal: {e}")

    return employee


# ============================================================
# Update Own Profile
# ============================================================

def update_self_profile(
    db: Session,
    user_id: int,
    data: EmployeeProfileUpdate,
) -> Employee:

    employee = get_employee_by_user_id(
        db,
        user_id,
    )

    update_data = data.model_dump(
        exclude_unset=True
    )

    updated = repository.update_employee(
        db,
        employee,
        update_data,
    )

    # Sync User full_name if first_name or last_name changed
    if "first_name" in update_data or "last_name" in update_data:
        employee.user.full_name = f"{employee.first_name} {employee.last_name}".strip()
        db.commit()
        db.refresh(employee)

    return updated


# ============================================================
# Employee Counts
# ============================================================

def get_employee_counts(
    db: Session,
):

    total_employees = repository.count_employees(
        db
    )

    active_employees = repository.count_active_employees(
        db
    )

    return {
        "total_employees": total_employees,
        "active_employees": active_employees,
    }