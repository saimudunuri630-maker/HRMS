from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.authentication_service.dependencies import (
    get_current_hr,
    get_current_user,
)
from app.authentication_service.models import User
from app.core.database import get_db
from app.employee_service.models import Employee
from app.employee_service.service import get_employee_by_user_id
from app.project_service.models import ProjectPriority, ProjectStatus
from app.project_service.schemas import (
    EmployeeProjectResponse,
    HRProjectDashboardMetrics,
    ProjectAssignmentCreate,
    ProjectAssignmentResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectProgressUpdate,
    ProjectResponse,
    ProjectRoleCreate,
    ProjectRoleResponse,
    ProjectRoleUpdate,
    ProjectStatusUpdate,
    ProjectTeamMemberResponse,
    ProjectUpdate,
    RoleAssignEmployeesRequest,
    RoleAssignedEmployeeItem,
    RoleAssignEmployeesResponse,
)
from app.project_service.service import (
    assign_employee_to_project,
    assign_employees_to_role,
    calculate_is_overdue,
    create_project,
    create_project_role,
    delete_project_role,
    get_available_employees,
    get_employee_my_projects,
    get_employee_project_details,
    get_hr_dashboard_metrics,
    get_project_by_id,
    get_project_roles,
    get_project_team,
    get_projects,
    get_role_assigned_employees,
    remove_employee_from_project,
    remove_employee_from_role,
    update_project,
    update_project_progress,
    update_project_role,
    update_project_status,
)

router = APIRouter(prefix="/projects", tags=["Project Management"])
roles_router = APIRouter(prefix="/project-roles", tags=["Project Roles"])
project_roles_router = roles_router


# =========================================================
# PROJECT ROLES ENDPOINTS
# =========================================================
@roles_router.get("", response_model=List[ProjectRoleResponse])
def list_project_roles(
    active_only: bool = Query(True, description="Filter active roles only"),
    project_id: Optional[int] = Query(None, description="Filter by project"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all project roles (Accessible to all authenticated users for selection)."""
    return get_project_roles(db, active_only=active_only, project_id=project_id)


@roles_router.post("", response_model=ProjectRoleResponse, status_code=status.HTTP_201_CREATED)
def create_new_project_role(
    schema: ProjectRoleCreate,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Create a new project role (HR Only)."""
    return create_project_role(db, schema, current_user.id, request.client.host if request.client else None)


@roles_router.put("/{role_id}", response_model=ProjectRoleResponse)
def edit_project_role(
    role_id: int,
    schema: ProjectRoleUpdate,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Update a project role name, description, or active status (HR Only)."""
    return update_project_role(db, role_id, schema, current_user.id, request.client.host if request.client else None)


@roles_router.delete("/{role_id}")
def delete_role(
    role_id: int,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Delete an unassigned project role (HR Only)."""
    return delete_project_role(db, role_id, current_user.id, request.client.host if request.client else None)


@roles_router.post("/{role_id}/assignments", response_model=RoleAssignEmployeesResponse, status_code=status.HTTP_201_CREATED)
@roles_router.post("/{role_id}/employees", response_model=RoleAssignEmployeesResponse, status_code=status.HTTP_201_CREATED)
def assign_employees_to_role_endpoint(
    role_id: int,
    schema: RoleAssignEmployeesRequest,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Assign one or multiple employees to a specific project role (HR Only)."""
    return assign_employees_to_role(
        db=db,
        role_id=role_id,
        schema=schema,
        project_id=None,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


@roles_router.get("/{role_id}/assignments", response_model=List[RoleAssignedEmployeeItem])
@roles_router.get("/{role_id}/employees", response_model=List[RoleAssignedEmployeeItem])
def list_role_assignments(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve actively assigned employees for a project role."""
    return get_role_assigned_employees(db, role_id=role_id)


@roles_router.delete("/{role_id}/assignments/{assignment_id}")
@roles_router.patch("/{role_id}/assignments/{assignment_id}/remove")
@roles_router.delete("/{role_id}/employees/{assignment_id}")
def remove_employee_from_role_endpoint(
    role_id: int,
    assignment_id: int,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Remove an employee assignment from a project role (HR Only)."""
    return remove_employee_from_role(
        db=db,
        role_id=role_id,
        assignment_id=assignment_id,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )



# =========================================================
# HR DASHBOARD METRICS
# =========================================================
@router.get("/metrics", response_model=HRProjectDashboardMetrics)
def get_project_dashboard_metrics(
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Retrieve HR project overview metrics (HR Only)."""
    return get_hr_dashboard_metrics(db)


# =========================================================
# EMPLOYEE SELF-SERVICE (MY PROJECTS & IDOR PROTECTED DETAILS)
# =========================================================
@router.get("/my-projects", response_model=List[EmployeeProjectResponse])
def get_my_assigned_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve projects assigned to the current employee (Employee Self-Service)."""
    emp = get_employee_by_user_id(db, current_user.id)
    if not emp:
        return []
    return get_employee_my_projects(db, emp.id)


@router.get("/me", response_model=List[EmployeeProjectResponse])
def get_my_projects_alias(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve projects assigned to current employee (Alias)."""
    emp = get_employee_by_user_id(db, current_user.id)
    if not emp:
        return []
    return get_employee_my_projects(db, emp.id)


@router.get("/my-projects/{id}")
def get_my_assigned_project_details(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve details for a specific project assigned to current employee (IDOR Protected)."""
    emp = get_employee_by_user_id(db, current_user.id)
    if not emp:
        raise HTTPException(status_code=403, detail="Employee record not found.")
    return get_employee_project_details(db, emp.id, id)


# =========================================================
# HR PROJECT MANAGEMENT ENDPOINTS
# =========================================================
@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_new_project(
    schema: ProjectCreate,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Create a new project (HR Only)."""
    proj = create_project(db, schema, current_user.id, request.client.host if request.client else None)
    res = ProjectResponse.model_validate(proj)
    res.is_overdue = calculate_is_overdue(proj.end_date, proj.status)
    return res


@router.get("", response_model=ProjectListResponse)
def list_projects(
    search: Optional[str] = Query(None, description="Search by project name, code, or description"),
    status: Optional[ProjectStatus] = Query(None, description="Filter by status"),
    priority: Optional[ProjectPriority] = Query(None, description="Filter by priority"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """List projects with pagination, search, and status/priority filters (HR Only)."""
    effective_limit = page_size if page_size is not None else limit
    projects, total, total_pages = get_projects(
        db, search=search, status_filter=status, priority_filter=priority, page=page, limit=effective_limit
    )
    items = []
    for p in projects:
        item = ProjectResponse.model_validate(p)
        item.is_overdue = calculate_is_overdue(p.end_date, p.status)
        items.append(item)

    return ProjectListResponse(
        items=items,
        total=total,
        page=page,
        limit=effective_limit,
        total_pages=total_pages,
    )


@router.get("/{id}")
def get_project_details(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve details for a single project."""
    is_hr = current_user.role == "hr"
    if not is_hr:
        emp = get_employee_by_user_id(db, current_user.id)
        if not emp:
            raise HTTPException(status_code=403, detail="Employee record not found.")
        # Non-HR must have active assignment to view
        return get_employee_project_details(db, emp.id, id)

    proj = get_project_by_id(db, id)
    res = ProjectResponse.model_validate(proj)
    res.is_overdue = calculate_is_overdue(proj.end_date, proj.status)
    return res


@router.put("/{id}", response_model=ProjectResponse)
def edit_project_metadata(
    id: int,
    schema: ProjectUpdate,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Update project metadata, dates, or progress (HR Only)."""
    proj = update_project(db, id, schema, current_user.id, request.client.host if request.client else None)
    res = ProjectResponse.model_validate(proj)
    res.is_overdue = calculate_is_overdue(proj.end_date, proj.status)
    return res


@router.patch("/{id}/status", response_model=ProjectResponse)
def change_project_status(
    id: int,
    schema: ProjectStatusUpdate,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Change project status enforcing state transition rules (HR Only)."""
    proj = update_project_status(db, id, schema, current_user.id, request.client.host if request.client else None)
    res = ProjectResponse.model_validate(proj)
    res.is_overdue = calculate_is_overdue(proj.end_date, proj.status)
    return res


@router.patch("/{id}/progress", response_model=ProjectResponse)
def change_project_progress(
    id: int,
    schema: ProjectProgressUpdate,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Update project progress percentage (0-100%) (HR Only)."""
    proj = update_project_progress(db, id, schema, current_user.id, request.client.host if request.client else None)
    res = ProjectResponse.model_validate(proj)
    res.is_overdue = calculate_is_overdue(proj.end_date, proj.status)
    return res


# =========================================================
# TEAM ASSIGNMENTS ENDPOINTS
# =========================================================
@router.post("/{id}/assignments", response_model=ProjectAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_employee(
    id: int,
    schema: ProjectAssignmentCreate,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Assign an active employee to a project with a project role (HR Only)."""
    return assign_employee_to_project(db, id, schema, current_user.id, request.client.host if request.client else None)


@router.get("/{id}/assignments", response_model=List[ProjectTeamMemberResponse])
def get_team_members(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full project team roster with designations & roles."""
    return get_project_team(db, id)


@router.patch("/{id}/assignments/{assignment_id}/remove", response_model=ProjectAssignmentResponse)
def remove_employee(
    id: int,
    assignment_id: int,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Soft-remove an employee from a project, setting removed_date and status=REMOVED (HR Only)."""
    return remove_employee_from_project(db, id, assignment_id, current_user.id, request.client.host if request.client else None)


@router.get("/{id}/available-employees")
def list_available_employees(
    id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Retrieve active employees not currently assigned to this project (HR Only)."""
    return get_available_employees(db, id)


@router.get("/{id}/roles", response_model=List[ProjectRoleResponse])
def list_roles_for_project(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List roles scoped to a specific project."""
    return get_project_roles(db, active_only=True, project_id=id)


@router.post("/{id}/roles", response_model=ProjectRoleResponse, status_code=status.HTTP_201_CREATED)
def create_role_for_project(
    id: int,
    schema: ProjectRoleCreate,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Create a project role scoped to a project (HR Only)."""
    schema.project_id = id
    return create_project_role(db, schema, current_user.id, request.client.host if request.client else None)


@router.delete("/{id}/roles/{role_id}")
def delete_role_for_project(
    id: int,
    role_id: int,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Delete an unassigned project role (HR Only)."""
    return delete_project_role(db, role_id, current_user.id, request.client.host if request.client else None)


@router.post("/{id}/roles/{role_id}/assignments", response_model=RoleAssignEmployeesResponse, status_code=status.HTTP_201_CREATED)
@router.post("/{id}/roles/{role_id}/employees", response_model=RoleAssignEmployeesResponse, status_code=status.HTTP_201_CREATED)
def assign_employees_to_project_role_endpoint(
    id: int,
    role_id: int,
    schema: RoleAssignEmployeesRequest,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Assign one or multiple employees to a specific project role scoped to project (HR Only)."""
    return assign_employees_to_role(
        db=db,
        role_id=role_id,
        schema=schema,
        project_id=id,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


@router.get("/{id}/roles/{role_id}/assignments", response_model=List[RoleAssignedEmployeeItem])
@router.get("/{id}/roles/{role_id}/employees", response_model=List[RoleAssignedEmployeeItem])
def list_project_role_assignments(
    id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve actively assigned employees for a role within a project."""
    return get_role_assigned_employees(db, role_id=role_id, project_id=id)


@router.delete("/{id}/roles/{role_id}/assignments/{assignment_id}")
@router.patch("/{id}/roles/{role_id}/assignments/{assignment_id}/remove")
@router.delete("/{id}/roles/{role_id}/employees/{assignment_id}")
def remove_employee_from_project_role_endpoint(
    id: int,
    role_id: int,
    assignment_id: int,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Remove an employee assignment from a project role within a project (HR Only)."""
    return remove_employee_from_role(
        db=db,
        role_id=role_id,
        assignment_id=assignment_id,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )



# =========================================================
# COMPATIBILITY ALIASES (/members)
# =========================================================
# =========================================================
# COMPATIBILITY ALIASES (/members and /employees)
# =========================================================
@router.post("/{id}/members", response_model=ProjectAssignmentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/{id}/employees", response_model=ProjectAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_member_alias(
    id: int,
    schema: ProjectAssignmentCreate,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    return assign_employee_to_project(db, id, schema, current_user.id, request.client.host if request.client else None)


@router.get("/{id}/members", response_model=List[ProjectTeamMemberResponse])
@router.get("/{id}/employees", response_model=List[ProjectTeamMemberResponse])
def get_members_alias(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_project_team(db, id)


@router.delete("/{id}/members/{employee_id}")
@router.delete("/{id}/employees/{employee_id}")
def remove_member_by_employee_id(
    id: int,
    employee_id: int,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    from sqlalchemy import select
    from app.project_service.models import ProjectAssignment, AssignmentStatus
    assign = db.scalar(
        select(ProjectAssignment).where(
            ProjectAssignment.project_id == id,
            ProjectAssignment.employee_id == employee_id,
            ProjectAssignment.status == AssignmentStatus.ACTIVE,
        )
    )
    if not assign:
        raise HTTPException(status_code=404, detail="Active assignment not found.")
    remove_employee_from_project(db, id, assign.id, current_user.id, request.client.host if request.client else None)
    return {"message": "Member removed from project successfully."}


@router.put("/{id}/members/{employee_id}/role")
@router.put("/{id}/employees/{employee_id}/role")
def update_member_role_endpoint(
    id: int,
    employee_id: int,
    payload: dict,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    new_role_id = payload.get("project_role_id")
    if not new_role_id:
        raise HTTPException(status_code=400, detail="project_role_id is required.")
    from app.project_service.service import update_project_assignment_role
    return update_project_assignment_role(
        db=db,
        project_id=id,
        employee_id=employee_id,
        new_role_id=new_role_id,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )