import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.audit_service.models import AuditAction, AuditLog
from app.core.config import settings
from app.email_service.service import (
    send_project_assignment_email,
    send_project_removal_email,
    send_project_role_assignment_email,
)
from app.employee_service.models import Employee, EmploymentStatus
from app.notification_service.models import Notification, NotificationType
from app.notification_service.service import create_in_app_notification
from app.project_service.models import (
    AssignmentStatus,
    Project,
    ProjectAssignment,
    ProjectPriority,
    ProjectRole,
    ProjectStatus,
)
from app.project_service.schemas import (
    HRProjectDashboardMetrics,
    ProjectAssignmentCreate,
    ProjectCreate,
    ProjectProgressUpdate,
    ProjectRoleCreate,
    ProjectRoleUpdate,
    ProjectStatusUpdate,
    ProjectUpdate,
    RoleAssignEmployeesRequest,
    RoleAssignedEmployeeItem,
    RoleAssignEmployeesResponse,
)
from app.authentication_service.models import User

logger = logging.getLogger(__name__)


# =========================================================
# CALCULATE OVERDUE HELPER
# =========================================================
def calculate_is_overdue(end_date: Optional[date], project_status: ProjectStatus) -> bool:
    if not end_date:
        return False
    if project_status in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED):
        return False
    return end_date < date.today()


# =========================================================
# PROJECT ROLES SERVICE
# =========================================================
def create_project_role(
    db: Session,
    schema: ProjectRoleCreate,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> ProjectRole:
    clean_name = schema.name.strip() if schema.name else ""
    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name is required.",
        )

    if not schema.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID is required.",
        )

    # Validate that project exists
    project = db.scalar(select(Project).where(Project.id == schema.project_id))
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {schema.project_id} not found.",
        )

    # Scoped duplicate check for this specific project
    query = select(ProjectRole).where(
        func.lower(ProjectRole.name) == clean_name.lower(),
        ProjectRole.is_active.is_(True),
        ProjectRole.project_id == schema.project_id,
    )
    existing = db.scalar(query)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project role '{clean_name}' already exists in this project.",
        )

    role = ProjectRole(
        name=clean_name,
        description=schema.description.strip() if schema.description else None,
        project_id=schema.project_id,
        required_count=schema.required_count or 1,
        is_active=True,
    )
    db.add(role)
    db.flush()

    audit = AuditLog(
        user_id=user_id,
        action=AuditAction.PROJECT_ROLE_CREATED,
        module="PROJECTS",
        entity_type="PROJECT_ROLE",
        entity_id=role.id,
        description=f"Created project role '{role.name}' for project '{project.name}' ({project.project_code})",
        ip_address=ip_address,
    )
    db.add(audit)
    db.commit()
    db.refresh(role)
    return role


def get_project_roles(
    db: Session, active_only: bool = False, project_id: Optional[int] = None
) -> List[ProjectRole]:
    stmt = select(ProjectRole)
    if active_only:
        stmt = stmt.where(ProjectRole.is_active.is_(True))
    if project_id is not None:
        stmt = stmt.where(ProjectRole.project_id == project_id)
    stmt = stmt.order_by(ProjectRole.name.asc())
    roles = list(db.scalars(stmt).all())

    for r in roles:
        assigned_cnt = db.scalar(
            select(func.count(ProjectAssignment.id)).where(
                ProjectAssignment.project_role_id == r.id,
                ProjectAssignment.status == AssignmentStatus.ACTIVE,
            )
        ) or 0
        r.assigned_count = assigned_cnt
    return roles


def update_project_role(
    db: Session,
    role_id: int,
    schema: ProjectRoleUpdate,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> ProjectRole:
    role = db.get(ProjectRole, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project role not found.")

    if schema.name and schema.name.strip().lower() != role.name.lower():
        query = select(ProjectRole).where(
            func.lower(ProjectRole.name) == schema.name.strip().lower(),
            ProjectRole.id != role.id,
        )
        if role.project_id is not None:
            query = query.where(ProjectRole.project_id == role.project_id)
        else:
            query = query.where(ProjectRole.project_id.is_(None))
        existing = db.scalar(query)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another project role with this name exists.",
            )
        role.name = schema.name.strip()

    if schema.description is not None:
        role.description = schema.description.strip() if schema.description else None

    if schema.is_active is not None:
        role.is_active = schema.is_active

    if schema.required_count is not None:
        role.required_count = schema.required_count

    audit = AuditLog(
        user_id=user_id,
        action=AuditAction.PROJECT_ROLE_UPDATED,
        module="PROJECTS",
        entity_type="PROJECT_ROLE",
        entity_id=role.id,
        description=f"Updated project role '{role.name}'",
        ip_address=ip_address,
    )
    db.add(audit)
    db.commit()
    db.refresh(role)
    return role


def delete_project_role(
    db: Session,
    role_id: int,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> dict:
    role = db.get(ProjectRole, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project role not found.")

    active_assignments = db.scalar(
        select(func.count(ProjectAssignment.id)).where(
            ProjectAssignment.project_role_id == role_id,
            ProjectAssignment.status == AssignmentStatus.ACTIVE,
        )
    ) or 0
    if active_assignments > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This role is currently assigned to employees. Reassign those employees before removing the role.",
        )

    db.delete(role)
    db.commit()
    return {"message": f"Project role '{role.name}' deleted successfully."}


def assign_employees_to_role(
    db: Session,
    role_id: int,
    schema: RoleAssignEmployeesRequest,
    project_id: Optional[int] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Assigns one or multiple employees to a specific Project Role.
    Validates project, role, headcount, employee status, and prevents duplicates.
    Emits audit logs and in-app notifications.
    """
    # 1. Validate role exists & is active
    role = db.get(ProjectRole, role_id)
    if not role or not role.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project role not found or is inactive.",
        )

    # 2. Validate project context
    target_project_id = project_id if project_id is not None else role.project_id
    if not target_project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project context is required for role assignment.",
        )

    project = db.get(Project, target_project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {target_project_id} not found.",
        )

    if role.project_id is not None and role.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project role '{role.name}' does not belong to project '{project.name}'.",
        )

    # 3. Check project lifecycle
    if project.status in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED):
        status_str = project.status.value if hasattr(project.status, "value") else str(project.status)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign employees to a {status_str} project.",
        )

    # 4. Parse employee IDs
    raw_employee_ids = schema.employee_ids or []
    if not raw_employee_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one employee must be selected for assignment.",
        )

    # Resolve each employee from DB
    resolved_employees = []
    seen_ids = set()
    for raw_id in raw_employee_ids:
        emp = None
        # Try integer ID
        if isinstance(raw_id, int) or (isinstance(raw_id, str) and raw_id.isdigit()):
            emp = db.scalar(
                select(Employee)
                .options(joinedload(Employee.user))
                .where(
                    Employee.id == int(raw_id),
                    Employee.deleted_at.is_(None),
                )
            )
        # Try employee_code
        if not emp and isinstance(raw_id, str):
            emp = db.scalar(
                select(Employee)
                .options(joinedload(Employee.user))
                .where(
                    func.lower(Employee.employee_code) == raw_id.strip().lower(),
                    Employee.deleted_at.is_(None),
                )
            )

        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee '{raw_id}' not found.",
            )

        if emp.id in seen_ids:
            continue
        seen_ids.add(emp.id)

        # Validate employee is active
        if emp.employment_status != EmploymentStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee {emp.first_name} {emp.last_name} ({emp.employee_code}) is not currently ACTIVE.",
            )

        resolved_employees.append(emp)

    # 5. Check duplicate assignments for this role
    active_assignments_stmt = (
        select(ProjectAssignment)
        .where(
            ProjectAssignment.project_id == project.id,
            ProjectAssignment.project_role_id == role.id,
            ProjectAssignment.status == AssignmentStatus.ACTIVE,
        )
    )
    current_role_assignments = list(db.scalars(active_assignments_stmt).all())
    current_assigned_emp_ids = {a.employee_id for a in current_role_assignments}

    to_assign = []
    already_assigned_names = []

    for emp in resolved_employees:
        if emp.id in current_assigned_emp_ids:
            already_assigned_names.append(f"{emp.first_name} {emp.last_name}".strip())
        else:
            to_assign.append(emp)

    if already_assigned_names:
        msg = (
            f"Employee '{already_assigned_names[0]}' is already assigned to this project role."
            if len(already_assigned_names) == 1
            else f"Employees ({', '.join(already_assigned_names)}) are already assigned to this project role."
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=msg,
        )

    # 6. Headcount enforcement
    if schema.required_count is not None and schema.required_count >= 1:
        if schema.required_count != role.required_count:
            role.required_count = schema.required_count
            db.flush()

    required_count = role.required_count or 1
    current_assigned_count = len(current_assigned_emp_ids)
    if current_assigned_count >= required_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Required headcount of {required_count} has already been reached for role '{role.name}'.",
        )

    if current_assigned_count + len(to_assign) > required_count:
        remaining_slots = required_count - current_assigned_count
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign {len(to_assign)} employee(s). Role '{role.name}' only has {remaining_slots} open position(s) remaining (Required headcount: {required_count}, currently assigned: {current_assigned_count}).",
        )

    assigned_date_val = schema.assigned_date or date.today()
    created_assignments = []

    # 7. Persist assignments, create audit logs and in-app notifications
    for emp in to_assign:
        existing_assign = (
            db.query(ProjectAssignment)
            .filter(
                ProjectAssignment.project_id == project.id,
                ProjectAssignment.employee_id == emp.id,
            )
            .order_by(ProjectAssignment.id.desc())
            .first()
        )
        if existing_assign:
            existing_assign.status = AssignmentStatus.ACTIVE
            existing_assign.project_role_id = role.id
            existing_assign.assigned_date = assigned_date_val
            existing_assign.removed_date = None
            asgn = existing_assign
        else:
            asgn = ProjectAssignment(
                project_id=project.id,
                employee_id=emp.id,
                project_role_id=role.id,
                assigned_date=assigned_date_val,
                status=AssignmentStatus.ACTIVE,
            )
            db.add(asgn)
        db.flush()

        # Audit Log
        audit = AuditLog(
            user_id=user_id,
            employee_id=emp.id,
            action=AuditAction.EMPLOYEE_ASSIGNED_TO_PROJECT_ROLE,
            module="PROJECTS",
            entity_type="PROJECT_ASSIGNMENT",
            entity_id=asgn.id,
            description=f"Assigned employee {emp.first_name} {emp.last_name} ({emp.employee_code}) to role '{role.name}' in project '{project.name}' ({project.project_code})",
            ip_address=ip_address,
        )
        db.add(audit)

        # In-App Notification using existing Notification Service
        if emp.user_id:
            try:
                create_in_app_notification(
                    user_id=emp.user_id,
                    title="Project Assignment",
                    message=f"You have been assigned to the {role.name} role for the {project.name}.",
                    category="PROJECT_ASSIGNMENT",
                    metadata={
                        "project_id": project.id,
                        "project_name": project.name,
                        "project_code": project.project_code,
                        "role_id": role.id,
                        "role_name": role.name,
                        "assignment_date": str(asgn.assigned_date),
                    },
                    db=db,
                )
            except Exception as e:
                logger.error(f"Failed to create notification for employee user {emp.user_id}: {e}")

        # Send project assignment email if user email is present
        if emp.user and emp.user.email:
            try:
                assigned_by_user = db.get(User, user_id) if user_id else None
                assigned_by_name = assigned_by_user.email if assigned_by_user else "HR Department"
                send_project_assignment_email(
                    recipient_email=emp.user.email,
                    employee_name=f"{emp.first_name} {emp.last_name}".strip(),
                    project_name=project.name,
                    project_code=project.project_code,
                    role_name=role.name,
                    description=project.description,
                    start_date=project.start_date,
                    end_date=project.end_date,
                    status=project.status.value if hasattr(project.status, "value") else str(project.status),
                    assigned_date=asgn.assigned_date,
                    assigned_by_name=assigned_by_name,
                    entity_id=asgn.id,
                    db=db,
                )
            except Exception as e:
                logger.warning(f"Could not send assignment email to {emp.user.email}: {e}")

        created_assignments.append({
            "assignment_id": asgn.id,
            "employee_id": emp.id,
            "employee_code": emp.employee_code,
            "employee_name": f"{emp.first_name} {emp.last_name}".strip(),
            "full_name": f"{emp.first_name} {emp.last_name}".strip(),
            "first_name": emp.first_name,
            "last_name": emp.last_name,
            "email": emp.user.email if emp.user else None,
            "department": getattr(emp, "department_name", None),
            "designation": getattr(emp, "official_designation", None) or getattr(emp, "designation", None),
            "official_designation": getattr(emp, "official_designation", None) or getattr(emp, "designation", None),
            "assigned_date": asgn.assigned_date,
            "status": asgn.status.value if hasattr(asgn.status, "value") else str(asgn.status),
            "role_id": role.id,
            "role_name": role.name,
            "project_id": project.id,
            "project_name": project.name,
        })

    db.commit()

    msg = f"Successfully assigned {len(created_assignments)} employee(s) to '{role.name}'."
    if already_assigned_names:
        msg += f" Note: {', '.join(already_assigned_names)} already assigned."

    return {
        "success": True,
        "assigned_count": len(created_assignments),
        "already_assigned": already_assigned_names,
        "assignments": created_assignments,
        "message": msg,
    }


def get_role_assigned_employees(
    db: Session,
    role_id: int,
    project_id: Optional[int] = None,
) -> List[dict]:
    """Retrieve all actively assigned employees for a specific project role."""
    role = db.get(ProjectRole, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project role not found.")

    stmt = (
        select(ProjectAssignment)
        .options(
            joinedload(ProjectAssignment.employee).joinedload(Employee.user),
            joinedload(ProjectAssignment.project_role),
            joinedload(ProjectAssignment.project),
        )
        .where(
            ProjectAssignment.project_role_id == role_id,
            ProjectAssignment.status == AssignmentStatus.ACTIVE,
        )
    )
    if project_id is not None:
        stmt = stmt.where(ProjectAssignment.project_id == project_id)
    stmt = stmt.order_by(ProjectAssignment.assigned_date.desc())

    assignments = list(db.scalars(stmt).all())
    result = []
    for a in assignments:
        emp = a.employee
        prj = a.project
        r = a.project_role
        emp_name = f"{emp.first_name} {emp.last_name}".strip() if emp else "Unknown"
        result.append({
            "assignment_id": a.id,
            "id": a.id,
            "employee_id": emp.id if emp else a.employee_id,
            "employee_code": emp.employee_code if emp else "N/A",
            "employee_name": emp_name,
            "full_name": emp_name,
            "first_name": emp.first_name if emp else "",
            "last_name": emp.last_name if emp else "",
            "email": emp.user.email if (emp and emp.user) else None,
            "department": getattr(emp, "department_name", None),
            "designation": getattr(emp, "official_designation", None) or getattr(emp, "designation", None),
            "official_designation": getattr(emp, "official_designation", None) or getattr(emp, "designation", None),
            "assigned_date": a.assigned_date,
            "start_date": a.assigned_date,
            "status": a.status.value if hasattr(a.status, "value") else str(a.status),
            "role_id": r.id if r else role_id,
            "role_name": r.name if r else role.name,
            "project_id": prj.id if prj else a.project_id,
            "project_name": prj.name if prj else "N/A",
        })
    return result


def remove_employee_from_role(
    db: Session,
    role_id: int,
    assignment_id: int,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> dict:
    """Removes an employee from a project role without deleting their employee account."""
    asgn = db.get(ProjectAssignment, assignment_id)
    if not asgn or asgn.project_role_id != role_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment record not found for this project role.",
        )

    if asgn.status in (AssignmentStatus.REMOVED, AssignmentStatus.TERMINATED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee assignment is already removed.",
        )

    asgn.status = AssignmentStatus.TERMINATED
    asgn.removed_date = date.today()

    emp = db.get(Employee, asgn.employee_id)
    role = db.get(ProjectRole, role_id)
    project = db.get(Project, asgn.project_id)

    emp_name = f"{emp.first_name} {emp.last_name}".strip() if emp else f"#{asgn.employee_id}"
    role_name = role.name if role else f"#{role_id}"
    proj_name = project.name if project else f"#{asgn.project_id}"

    # Audit log
    audit = AuditLog(
        user_id=user_id,
        employee_id=emp.id if emp else None,
        action=AuditAction.EMPLOYEE_REMOVED_FROM_PROJECT_ROLE,
        module="PROJECTS",
        entity_type="PROJECT_ASSIGNMENT",
        entity_id=asgn.id,
        description=f"Removed employee {emp_name} from role '{role_name}' in project '{proj_name}'",
        ip_address=ip_address,
    )
    db.add(audit)

    # In-app notification for removal if emp exists
    if emp and emp.user_id and project and role:
        try:
            create_in_app_notification(
                user_id=emp.user_id,
                title="Project Role Update",
                message=f"You have been removed from the {role_name} role in {proj_name}.",
                category="PROJECT_ASSIGNMENT",
                metadata={
                    "project_id": project.id,
                    "project_name": project.name,
                    "role_id": role.id,
                    "role_name": role.name,
                },
                db=db,
            )
        except Exception as e:
            logger.error(f"Failed to create removal notification: {e}")

    db.commit()
    db.refresh(asgn)

    return {
        "success": True,
        "message": f"Successfully removed {emp_name} from role '{role_name}'.",
        "assignment_id": asgn.id,
        "status": asgn.status.value if hasattr(asgn.status, "value") else str(asgn.status),
    }



# =========================================================
# PROJECTS SERVICE
# =========================================================
def generate_next_project_code(db: Session) -> str:
    stmt = select(Project.project_code).order_by(Project.id.desc()).limit(1)
    last_code = db.scalar(stmt)
    if not last_code:
        return "PRJ001"
    if last_code.startswith("PRJ") and last_code[3:].isdigit():
        num = int(last_code[3:]) + 1
        return f"PRJ{num:03d}"
    return f"PRJ{db.query(Project).count() + 1:03d}"


def create_project(
    db: Session,
    schema: ProjectCreate,
    creator_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> Project:
    if schema.project_code and schema.project_code.strip():
        code = schema.project_code.strip().upper()
        existing = db.scalar(select(Project).where(Project.project_code == code))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project code '{code}' already exists.",
            )
    else:
        code = generate_next_project_code(db)

    # Initial roles validation
    initial_roles_list = schema.initial_roles or schema.roles
    if initial_roles_list is not None and len(initial_roles_list) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one initial role is required when specifying roles.",
        )

    if initial_roles_list:
        seen = set()
        for r_entry in initial_roles_list:
            r_name = r_entry if isinstance(r_entry, str) else r_entry.get("role_name", r_entry.get("name", ""))
            clean_r = r_name.strip().lower()
            if clean_r in seen:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate role '{r_name}' in initial_roles.",
                )
            seen.add(clean_r)

    status_val = schema.status or ProjectStatus.PLANNED

    project = Project(
        project_code=code,
        name=schema.name.strip(),
        description=schema.description.strip() if schema.description else None,
        start_date=schema.start_date,
        end_date=schema.end_date,
        priority=schema.priority,
        status=status_val,
        progress_percentage=0,
        client_name=schema.client_name.strip() if schema.client_name else None,
        created_by=creator_id,
    )
    db.add(project)
    db.flush()

    if initial_roles_list:
        for r_entry in initial_roles_list:
            if isinstance(r_entry, str):
                r_name = r_entry.strip()
                r_desc = None
                req_cnt = 1
            else:
                r_name = r_entry.get("role_name", r_entry.get("name", "")).strip()
                r_desc = r_entry.get("description")
                req_cnt = r_entry.get("required_count", 1)
            if r_name:
                p_role = ProjectRole(
                    name=r_name,
                    project_id=project.id,
                    description=r_desc,
                    required_count=req_cnt,
                    is_active=True,
                )
                db.add(p_role)

    audit = AuditLog(
        user_id=creator_id,
        action=AuditAction.PROJECT_CREATED,
        module="PROJECTS",
        entity_type="PROJECT",
        entity_id=project.id,
        description=f"Created project '{project.name}' ({project.project_code})",
        ip_address=ip_address,
    )
    db.add(audit)

    if creator_id:
        try:
            from app.notification_service.service import create_in_app_notification
            create_in_app_notification(
                user_id=creator_id,
                title="Project Created",
                message=f"Project '{project.name}' ({project.project_code}) was created successfully.",
                category="PROJECT",
                metadata={"project_id": project.id, "project_code": project.project_code},
                db=db,
            )
        except Exception as notif_err:
            logger.warning(f"Could not create in-app notification for project {project.id}: {notif_err}")

    db.commit()
    db.refresh(project)
    return get_project_by_id(db, project.id)


def get_projects(
    db: Session,
    search: Optional[str] = None,
    status_filter: Optional[ProjectStatus] = None,
    priority_filter: Optional[ProjectPriority] = None,
    page: int = 1,
    limit: int = 10,
) -> Tuple[List[Project], int, int]:
    stmt = select(Project).where(Project.deleted_at.is_(None))

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Project.name).ilike(term),
                func.lower(Project.project_code).ilike(term),
                func.lower(Project.description).ilike(term),
                func.lower(Project.client_name).ilike(term),
            )
        )

    if status_filter:
        stmt = stmt.where(Project.status == status_filter)

    if priority_filter:
        stmt = stmt.where(Project.priority == priority_filter)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0
    total_pages = max(1, (total + limit - 1) // limit)

    offset_val = (page - 1) * limit
    stmt = stmt.order_by(desc(Project.created_at)).offset(offset_val).limit(limit)
    projects = list(db.scalars(stmt).all())

    for p in projects:
        p.team_members_count = db.scalar(
            select(func.count(ProjectAssignment.id)).where(
                ProjectAssignment.project_id == p.id,
                ProjectAssignment.status == AssignmentStatus.ACTIVE,
            )
        ) or 0
        p.roles_count = db.scalar(
            select(func.count(ProjectRole.id)).where(
                ProjectRole.project_id == p.id,
                ProjectRole.is_active.is_(True),
            )
        ) or 0

    return projects, total, total_pages


def get_project_by_id(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found",
        )

    project.team_members_count = db.scalar(
        select(func.count(ProjectAssignment.id)).where(
            ProjectAssignment.project_id == project.id,
            ProjectAssignment.status == AssignmentStatus.ACTIVE,
        )
    ) or 0
    project.roles_count = db.scalar(
        select(func.count(ProjectRole.id)).where(
            ProjectRole.project_id == project.id,
            ProjectRole.is_active.is_(True),
        )
    ) or 0

    project.members = get_project_team(db, project_id)
    for r in project.roles:
        r.assigned_count = db.scalar(
            select(func.count(ProjectAssignment.id)).where(
                ProjectAssignment.project_role_id == r.id,
                ProjectAssignment.status == AssignmentStatus.ACTIVE,
            )
        ) or 0
    return project


def update_project(
    db: Session,
    project_id: int,
    schema: ProjectUpdate,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> Project:
    project = db.get(Project, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found",
        )

    name_val = schema.name or schema.project_name
    if name_val is not None:
        project.name = name_val.strip()

    if schema.description is not None:
        project.description = schema.description.strip() if schema.description else None

    if schema.start_date is not None:
        project.start_date = schema.start_date

    end_date_val = schema.end_date or schema.expected_end_date
    if end_date_val is not None:
        project.end_date = end_date_val

    if schema.priority is not None:
        project.priority = schema.priority

    if schema.progress_percentage is not None:
        project.progress_percentage = schema.progress_percentage
        if project.progress_percentage == 100:
            project.status = ProjectStatus.COMPLETED

    if schema.client_name is not None:
        project.client_name = schema.client_name.strip() if schema.client_name else None

    if project.end_date and project.end_date < project.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date cannot be earlier than start_date.",
        )

    audit = AuditLog(
        user_id=user_id,
        action=AuditAction.PROJECT_UPDATED,
        module="PROJECTS",
        entity_type="PROJECT",
        entity_id=project.id,
        description=f"Updated project '{project.name}' ({project.project_code})",
        ip_address=ip_address,
    )
    db.add(audit)
    db.commit()
    db.refresh(project)
    return get_project_by_id(db, project.id)


def update_project_status(
    db: Session,
    project_id: int,
    schema: ProjectStatusUpdate,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> Project:
    project = db.get(Project, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found",
        )

    old_status = project.status
    new_status = schema.status

    if new_status == ProjectStatus.COMPLETED:
        project.progress_percentage = 100

    project.status = new_status

    audit = AuditLog(
        user_id=user_id,
        action=AuditAction.PROJECT_STATUS_CHANGED,
        module="PROJECTS",
        entity_type="PROJECT",
        entity_id=project.id,
        description=f"Changed status of project '{project.name}' from {old_status} to {new_status}",
        ip_address=ip_address,
    )
    db.add(audit)
    db.commit()
    db.refresh(project)
    return get_project_by_id(db, project.id)


def update_project_progress(
    db: Session,
    project_id: int,
    schema: ProjectProgressUpdate,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> Project:
    project = db.get(Project, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found",
        )

    project.progress_percentage = schema.progress_percentage
    if schema.progress_percentage == 100:
        project.status = ProjectStatus.COMPLETED

    audit = AuditLog(
        user_id=user_id,
        action=AuditAction.PROJECT_UPDATED,
        module="PROJECTS",
        entity_type="PROJECT",
        entity_id=project.id,
        description=f"Updated progress of project '{project.name}' to {schema.progress_percentage}%",
        ip_address=ip_address,
    )
    db.add(audit)
    db.commit()
    db.refresh(project)
    return get_project_by_id(db, project.id)


# =========================================================
# TEAM ASSIGNMENTS SERVICE
# =========================================================
def assign_employee_to_project(
    db: Session,
    project_id: int,
    schema: ProjectAssignmentCreate,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> ProjectAssignment:
    project = db.get(Project, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    if project.status in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign employee to a {project.status.value if hasattr(project.status, 'value') else project.status} project.",
        )

    if not schema.project_role_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_role_id is required.",
        )

    employee = db.get(Employee, schema.employee_id)
    if (
        not employee
        or employee.employment_status != EmploymentStatus.ACTIVE
        or employee.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee not found or is not currently ACTIVE.",
        )

    role = db.get(ProjectRole, schema.project_role_id)
    if not role or not role.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Project role not found or is inactive."
        )

    if role.project_id is not None and role.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project role does not exist in this project.",
        )

    assigned_date_val = schema.assigned_date or schema.start_date or date.today()

    # Check duplicate assignment
    existing = db.scalar(
        select(ProjectAssignment).where(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.employee_id == schema.employee_id,
        )
    )
    if existing:
        if existing.status == AssignmentStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Employee {employee.first_name} {employee.last_name} is already assigned to this project.",
            )
        else:
            existing.status = AssignmentStatus.ACTIVE
            existing.project_role_id = schema.project_role_id
            existing.assigned_date = assigned_date_val
            existing.removed_date = None
            assignment = existing
    else:
        assignment = ProjectAssignment(
            project_id=project_id,
            employee_id=schema.employee_id,
            project_role_id=schema.project_role_id,
            assigned_date=assigned_date_val,
            status=AssignmentStatus.ACTIVE,
        )
        db.add(assignment)
    db.flush()

    audit = AuditLog(
        user_id=user_id,
        action=AuditAction.EMPLOYEE_ASSIGNED_TO_PROJECT,
        module="PROJECTS",
        entity_type="PROJECT_ASSIGNMENT",
        entity_id=assignment.id,
        description=f"Assigned employee {employee.first_name} {employee.last_name} to project '{project.name}' as {role.name}",
        ip_address=ip_address,
    )
    db.add(audit)

    # In-app notification for employee
    if employee.user_id:
        notif = Notification(
            user_id=employee.user_id,
            title=f"New Project Assignment: {project.name}",
            message=f"You have been assigned to project '{project.name}' ({project.project_code}) as {role.name}.",
            notification_type=NotificationType.PROJECT_UPDATE.value,
            entity_type="PROJECT",
            entity_id=project.id,
        )
        db.add(notif)

    db.commit()
    db.refresh(assignment)

    # Send consolidated email notification to assigned employee
    if employee.user and employee.user.email:
        try:
            assigned_by_user = db.get(User, user_id) if user_id else None
            assigned_by_name = (
                f"{assigned_by_user.email}" if assigned_by_user else "HR Department"
            )

            send_project_assignment_email(
                recipient_email=employee.user.email,
                employee_name=f"{employee.first_name} {employee.last_name}".strip(),
                project_name=project.name,
                project_code=project.project_code,
                role_name=role.name,
                description=project.description,
                start_date=project.start_date,
                end_date=project.end_date,
                status=project.status.value if hasattr(project.status, "value") else str(project.status),
                assigned_date=assignment.assigned_date,
                assigned_by_name=assigned_by_name,
                entity_id=assignment.id,
                db=db,
            )
            logger.info(f"Project assignment email sent successfully to {employee.user.email}")
        except Exception as e:
            logger.error(f"Failed to send project assignment email: {e}", exc_info=True)

    assignment.employee_name = f"{employee.first_name} {employee.last_name}".strip()
    assignment.full_name = assignment.employee_name
    assignment.employee_code = employee.employee_code
    assignment.project_role_name = role.name
    return assignment


def remove_employee_from_project(
    db: Session,
    project_id: int,
    assignment_id: int,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> ProjectAssignment:
    assignment = db.get(ProjectAssignment, assignment_id)
    if not assignment or assignment.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project assignment record not found."
        )

    if assignment.status in (AssignmentStatus.REMOVED, AssignmentStatus.TERMINATED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee assignment is already removed.",
        )

    assignment.status = AssignmentStatus.TERMINATED
    assignment.removed_date = date.today()

    audit = AuditLog(
        user_id=user_id,
        action=AuditAction.EMPLOYEE_REMOVED_FROM_PROJECT,
        module="PROJECTS",
        entity_type="PROJECT_ASSIGNMENT",
        entity_id=assignment.id,
        description=f"Removed assignment #{assignment_id} from project #{project_id}",
        ip_address=ip_address,
    )
    db.add(audit)

    employee = db.get(Employee, assignment.employee_id)
    project = db.get(Project, project_id)
    if employee and employee.user_id and project:
        notif = Notification(
            user_id=employee.user_id,
            title=f"Project Removal: {project.name}",
            message=f"You have been removed from project '{project.name}' ({project.project_code}).",
            notification_type=NotificationType.PROJECT_UPDATE.value,
            entity_type="PROJECT",
            entity_id=project.id,
        )
        db.add(notif)

    db.commit()
    db.refresh(assignment)

    if employee and employee.user and employee.user.email and project:
        try:
            role = db.get(ProjectRole, assignment.project_role_id) if assignment.project_role_id else None
            send_project_removal_email(
                recipient_email=employee.user.email,
                first_name=employee.first_name,
                project_name=project.name,
                project_code=project.project_code,
                previous_role=role.name if role else None,
                entity_id=assignment.id,
                db=db,
            )
        except Exception as e:
            logger.error(f"Failed to send removal email: {e}")

    return assignment


def update_project_assignment_role(
    db: Session,
    project_id: int,
    employee_id: int,
    new_role_id: int,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> dict:
    assign = db.scalar(
        select(ProjectAssignment).where(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.employee_id == employee_id,
            ProjectAssignment.status == AssignmentStatus.ACTIVE,
        )
    )
    if not assign:
        raise HTTPException(status_code=404, detail="Active assignment not found.")

    new_role = db.get(ProjectRole, new_role_id)
    if not new_role or not new_role.is_active:
        raise HTTPException(status_code=400, detail="Project role not found or inactive.")

    if new_role.project_id is not None and new_role.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Project role does not exist in this project.",
        )

    old_role = db.get(ProjectRole, assign.project_role_id) if assign.project_role_id else None
    previous_role_name = old_role.name if old_role else "Not Assigned"

    assign.project_role_id = new_role.id
    db.commit()
    db.refresh(assign)

    audit = AuditLog(
        user_id=user_id,
        action=AuditAction.EMPLOYEE_ROLE_CHANGED,
        module="PROJECTS",
        entity_type="PROJECT_ASSIGNMENT",
        entity_id=assign.id,
        description=f"Changed role of employee #{employee_id} to '{new_role.name}' in project #{project_id}",
        ip_address=ip_address,
    )
    db.add(audit)
    db.commit()

    emp = db.get(Employee, employee_id)
    project = db.get(Project, project_id)
    if emp and emp.user and emp.user.email and project:
        try:
            send_project_role_assignment_email(
                recipient_email=emp.user.email,
                first_name=emp.first_name,
                project_name=project.name,
                role_name=new_role.name,
                previous_role=previous_role_name,
                entity_id=assign.id,
                db=db,
            )
        except Exception as e:
            logger.error(f"Failed to send role update email: {e}")

    return {
        "assignment_id": assign.id,
        "employee_id": employee_id,
        "project_role_id": new_role.id,
        "project_role_name": new_role.name,
        "role_name": new_role.name,
        "message": "Role updated successfully.",
    }


def get_project_team(db: Session, project_id: int) -> List[dict]:
    p = db.get(Project, project_id)
    if not p or p.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found",
        )

    stmt = (
        select(ProjectAssignment)
        .options(
            joinedload(ProjectAssignment.employee),
            joinedload(ProjectAssignment.project_role),
        )
        .where(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.status == AssignmentStatus.ACTIVE,
        )
        .order_by(ProjectAssignment.assigned_date.desc())
    )
    assignments = db.scalars(stmt).all()

    result = []
    for a in assignments:
        emp = a.employee
        role = a.project_role
        emp_name = f"{emp.first_name} {emp.last_name}".strip() if emp else "Unknown"
        result.append({
            "assignment_id": a.id,
            "id": a.id,
            "employee_id": emp.id if emp else a.employee_id,
            "employee_code": emp.employee_code if emp else "N/A",
            "employee_name": emp_name,
            "full_name": emp_name,
            "first_name": emp.first_name if emp else "",
            "last_name": emp.last_name if emp else "",
            "official_designation": getattr(emp, "official_designation", None)
            or getattr(emp, "designation", None)
            or "N/A",
            "email": emp.user.email if (emp and emp.user) else "N/A",
            "profile_photo_url": emp.profile_photo_url if emp else None,
            "project_role_id": role.id if role else a.project_role_id,
            "project_role_name": role.name if role else "N/A",
            "role_name": role.name if role else "N/A",
            "assigned_date": a.assigned_date,
            "start_date": a.assigned_date,
            "removed_date": a.removed_date,
            "assignment_status": a.status,
            "status": a.status.value if hasattr(a.status, "value") else str(a.status),
        })
    return result


def get_available_employees(db: Session, project_id: int) -> List[dict]:
    assigned_emp_ids = db.scalars(
        select(ProjectAssignment.employee_id).where(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.status == AssignmentStatus.ACTIVE,
        )
    ).all()

    stmt = select(Employee).where(
        Employee.employment_status == EmploymentStatus.ACTIVE,
        Employee.deleted_at.is_(None),
    )
    if assigned_emp_ids:
        stmt = stmt.where(Employee.id.notin_(assigned_emp_ids))
    stmt = stmt.order_by(Employee.first_name.asc(), Employee.last_name.asc())

    employees = db.scalars(stmt).all()
    return [
        {
            "id": e.id,
            "employee_code": e.employee_code,
            "first_name": e.first_name,
            "last_name": e.last_name,
            "full_name": f"{e.first_name} {e.last_name}".strip(),
            "email": e.user.email if e.user else None,
            "official_designation": getattr(e, "official_designation", None)
            or getattr(e, "designation", None),
        }
        for e in employees
    ]


# =========================================================
# EMPLOYEE SELF-SERVICE & IDOR PROTECTION
# =========================================================
def get_employee_my_projects(db: Session, employee_id: int) -> List[dict]:
    stmt = (
        select(ProjectAssignment)
        .options(
            joinedload(ProjectAssignment.project),
            joinedload(ProjectAssignment.project_role),
        )
        .where(
            ProjectAssignment.employee_id == employee_id,
            ProjectAssignment.status == AssignmentStatus.ACTIVE,
        )
        .order_by(ProjectAssignment.assigned_date.desc())
    )
    assignments = db.scalars(stmt).all()

    result = []
    for a in assignments:
        prj = a.project
        if not prj or prj.deleted_at is not None:
            continue

        team_count = db.scalar(
            select(func.count(ProjectAssignment.id)).where(
                ProjectAssignment.project_id == prj.id,
                ProjectAssignment.status == AssignmentStatus.ACTIVE,
            )
        ) or 0

        result.append({
            "id": prj.id,
            "project_id": prj.id,
            "project_code": prj.project_code,
            "name": prj.name,
            "project_name": prj.name,
            "description": prj.description,
            "start_date": prj.start_date,
            "end_date": prj.end_date,
            "expected_end_date": prj.end_date,
            "priority": prj.priority,
            "status": prj.status,
            "progress_percentage": prj.progress_percentage,
            "is_overdue": calculate_is_overdue(prj.end_date, prj.status),
            "project_role_name": a.project_role.name if a.project_role else "Team Member",
            "my_role": a.project_role.name if a.project_role else "Team Member",
            "assigned_date": a.assigned_date,
            "team_members_count": team_count,
        })
    return result


def get_employee_project_details(db: Session, employee_id: int, project_id: int) -> dict:
    active_assignment = db.scalar(
        select(ProjectAssignment).where(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.employee_id == employee_id,
            ProjectAssignment.status == AssignmentStatus.ACTIVE,
        )
    )
    if not active_assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not an active member of this project.",
        )

    prj = db.get(Project, project_id)
    if not prj or prj.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found",
        )
    team = get_project_team(db, project_id)

    return {
        "id": prj.id,
        "project": {
            "id": prj.id,
            "project_code": prj.project_code,
            "name": prj.name,
            "project_name": prj.name,
            "description": prj.description,
            "start_date": prj.start_date,
            "end_date": prj.end_date,
            "expected_end_date": prj.end_date,
            "priority": prj.priority,
            "status": prj.status,
            "progress_percentage": prj.progress_percentage,
            "is_overdue": calculate_is_overdue(prj.end_date, prj.status),
            "created_at": prj.created_at,
            "updated_at": prj.updated_at,
        },
        "project_code": prj.project_code,
        "project_name": prj.name,
        "name": prj.name,
        "description": prj.description,
        "start_date": prj.start_date,
        "end_date": prj.end_date,
        "expected_end_date": prj.end_date,
        "status": prj.status,
        "priority": prj.priority,
        "progress_percentage": prj.progress_percentage,
        "my_role": active_assignment.project_role.name if active_assignment.project_role else "Team Member",
        "assigned_date": active_assignment.assigned_date,
        "members": team,
        "team": team,
    }


# =========================================================
# HR DASHBOARD METRICS
# =========================================================
def get_hr_dashboard_metrics(db: Session) -> HRProjectDashboardMetrics:
    total = db.scalar(select(func.count(Project.id)).where(Project.deleted_at.is_(None))) or 0
    active = db.scalar(
        select(func.count(Project.id)).where(
            Project.deleted_at.is_(None),
            Project.status.in_([ProjectStatus.IN_PROGRESS, ProjectStatus.ACTIVE]),
        )
    ) or 0
    completed = db.scalar(
        select(func.count(Project.id)).where(
            Project.deleted_at.is_(None),
            Project.status == ProjectStatus.COMPLETED,
        )
    ) or 0
    on_hold = db.scalar(
        select(func.count(Project.id)).where(
            Project.deleted_at.is_(None),
            Project.status == ProjectStatus.ON_HOLD,
        )
    ) or 0

    today = date.today()
    overdue = db.scalar(
        select(func.count(Project.id)).where(
            Project.deleted_at.is_(None),
            Project.end_date < today,
            Project.status.notin_([ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]),
        )
    ) or 0

    return HRProjectDashboardMetrics(
        total_projects=total,
        active_projects=active,
        completed_projects=completed,
        on_hold_projects=on_hold,
        overdue_projects=overdue,
    )


# =========================================================
# BACKWARDS COMPATIBILITY CLASS WRAPPER
# =========================================================
class ProjectService:
    @staticmethod
    def get_hr_project_metrics(db: Session) -> HRProjectDashboardMetrics:
        return get_hr_dashboard_metrics(db)

    @staticmethod
    def get_employee_my_projects(db: Session, employee_id: int) -> List[dict]:
        return get_employee_my_projects(db, employee_id)

    @staticmethod
    def get_employee_project_details(db: Session, employee_id: int, project_id: int) -> dict:
        return get_employee_project_details(db, employee_id, project_id)

    @staticmethod
    def get_project_details(db: Session, project_id: int, user_id: Optional[int] = None, is_hr: bool = True) -> Project:
        return get_project_by_id(db, project_id)

    @staticmethod
    def update_project_progress(db: Session, project_id: int, progress: int, user_id: Optional[int] = None) -> Project:
        return update_project_progress(db, project_id, ProjectProgressUpdate(progress_percentage=progress), user_id)

    @staticmethod
    def create_project(db: Session, project_in: ProjectCreate, current_user_id: Optional[int] = None) -> Project:
        return create_project(db, project_in, current_user_id)

    @staticmethod
    def list_project_roles(db: Session, project_id: Optional[int] = None) -> List[ProjectRole]:
        return get_project_roles(db, active_only=True, project_id=project_id)

    @staticmethod
    def add_project_role(db: Session, project_id: Optional[int], payload: dict) -> ProjectRole:
        schema = ProjectRoleCreate(**payload, project_id=project_id)
        return create_project_role(db, schema)

    @staticmethod
    def update_project_role(db: Session, project_id: Optional[int], role_id: int, payload: dict) -> ProjectRole:
        schema = ProjectRoleUpdate(**payload)
        return update_project_role(db, role_id, schema)

    @staticmethod
    def delete_project_role(db: Session, project_id: Optional[int], role_id: int) -> dict:
        return delete_project_role(db, role_id)

    @staticmethod
    def assign_employee_to_project(db: Session, project_id: int, employee_id: int, project_role_id: int, user_id: Optional[int] = None) -> ProjectAssignment:
        schema = ProjectAssignmentCreate(employee_id=employee_id, project_role_id=project_role_id)
        return assign_employee_to_project(db, project_id, schema, user_id)

    @staticmethod
    def remove_assignment_by_id(db: Session, project_id: int, assignment_id: int, user_id: Optional[int] = None) -> dict:
        remove_employee_from_project(db, project_id, assignment_id, user_id)
        return {"message": "Assignment removed successfully."}

    @staticmethod
    def update_member_role(db: Session, project_id: int, employee_id: int, project_role_id: int, user_id: Optional[int] = None) -> dict:
        return update_project_assignment_role(db, project_id, employee_id, project_role_id, user_id)