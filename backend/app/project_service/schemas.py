from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.project_service.models import AssignmentStatus, ProjectPriority, ProjectStatus


# =========================================================
# PROJECT ROLE SCHEMAS
# =========================================================
class ProjectRoleBase(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Project role title")
    role_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    project_id: Optional[int] = None
    required_count: Optional[int] = 1

    @model_validator(mode="before")
    @classmethod
    def normalize_role_name(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("name") and data.get("role_name"):
                data["name"] = data["role_name"]
            elif data.get("name") and not data.get("role_name"):
                data["role_name"] = data["name"]
        return data


class ProjectRoleCreate(ProjectRoleBase):
    @model_validator(mode="before")
    @classmethod
    def validate_name_presence(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("name") and data.get("role_name"):
                data["name"] = data["role_name"]
            elif data.get("name") and not data.get("role_name"):
                data["role_name"] = data["name"]
            if not data.get("name"):
                raise ValueError("Project role name is required")
        return data


class ProjectRoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    role_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    required_count: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("name") and data.get("role_name"):
                data["name"] = data["role_name"]
        return data


class ProjectRoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    project_id: Optional[int] = None
    required_count: Optional[int] = 1
    assigned_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def role_name(self) -> str:
        return self.name

    @computed_field
    @property
    def status(self) -> str:
        return "ACTIVE" if self.is_active else "INACTIVE"

    @computed_field
    @property
    def open_count(self) -> int:
        req = self.required_count or 1
        ass = self.assigned_count or 0
        return max(0, req - ass)


# =========================================================
# PROJECT SCHEMAS
# =========================================================
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Project name")
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    priority: ProjectPriority = ProjectPriority.MEDIUM
    client_name: Optional[str] = None

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: Optional[date], info) -> Optional[date]:
        if v and "start_date" in info.data and info.data["start_date"]:
            if v < info.data["start_date"]:
                raise ValueError("end_date cannot be earlier than start_date")
        return v


class ProjectCreate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    project_name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    expected_end_date: Optional[date] = None
    priority: ProjectPriority = ProjectPriority.MEDIUM
    status: Optional[ProjectStatus] = None
    client_name: Optional[str] = None
    project_code: Optional[str] = Field(None, max_length=50)
    initial_roles: Optional[Union[List[str], List[Dict[str, Any]]]] = None
    roles: Optional[Union[List[str], List[Dict[str, Any]]]] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_and_validate(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If initial_roles or roles is explicitly given as empty list, reject
            for k in ("initial_roles", "roles"):
                if k in data and data[k] is not None and len(data[k]) == 0:
                    raise ValueError("At least one initial role is required.")

            if not data.get("name") and data.get("project_name"):
                data["name"] = data["project_name"]
            if not data.get("end_date") and data.get("expected_end_date"):
                data["end_date"] = data["expected_end_date"]
            if not data.get("name"):
                raise ValueError("Project name is required")
        return data

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: Optional[date], info) -> Optional[date]:
        if v and "start_date" in info.data and info.data["start_date"]:
            if v < info.data["start_date"]:
                raise ValueError("end_date cannot be earlier than start_date")
        return v


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    project_name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    expected_end_date: Optional[date] = None
    priority: Optional[ProjectPriority] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    client_name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("name") and data.get("project_name"):
                data["name"] = data["project_name"]
            if not data.get("end_date") and data.get("expected_end_date"):
                data["end_date"] = data["expected_end_date"]
        return data

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: Optional[date], info) -> Optional[date]:
        if v and "start_date" in info.data and info.data["start_date"]:
            if v < info.data["start_date"]:
                raise ValueError("end_date cannot be earlier than start_date")
        return v


class ProjectStatusUpdate(BaseModel):
    status: ProjectStatus


class ProjectProgressUpdate(BaseModel):
    progress_percentage: int = Field(..., ge=0, le=100)


class ProjectResponse(ProjectBase):
    id: int
    project_code: str
    status: ProjectStatus
    progress_percentage: int
    is_overdue: bool = False
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    team_members_count: int = 0
    roles_count: int = 0
    members: Optional[List[dict]] = None
    roles: Optional[List[ProjectRoleResponse]] = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def project_name(self) -> str:
        return self.name

    @computed_field
    @property
    def expected_end_date(self) -> Optional[date]:
        return self.end_date


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
    page: int
    limit: int
    total_pages: int


# =========================================================
# PROJECT ASSIGNMENT SCHEMAS
# =========================================================
class ProjectAssignmentCreate(BaseModel):
    employee_id: int
    project_role_id: int
    assigned_date: Optional[date] = None
    start_date: Optional[date] = None

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("assigned_date") and data.get("start_date"):
                data["assigned_date"] = data["start_date"]
        return data


class ProjectTeamMemberResponse(BaseModel):
    assignment_id: int
    employee_id: int
    employee_code: str
    employee_name: str
    full_name: Optional[str] = None
    official_designation: Optional[str] = None
    email: str
    profile_photo_url: Optional[str] = None
    project_role_id: int
    project_role_name: str
    assigned_date: date
    start_date: Optional[date] = None
    removed_date: Optional[date] = None
    assignment_status: AssignmentStatus
    status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectAssignmentResponse(BaseModel):
    id: int
    project_id: int
    employee_id: int
    project_role_id: int
    assigned_date: date
    removed_date: Optional[date] = None
    status: AssignmentStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    employee_name: Optional[str] = None
    project_role_name: Optional[str] = None
    full_name: Optional[str] = None
    employee_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def assignment_id(self) -> int:
        return self.id

    @computed_field
    @property
    def start_date(self) -> date:
        return self.assigned_date

    @computed_field
    @property
    def role_name(self) -> Optional[str]:
        return self.project_role_name


# =========================================================
# EMPLOYEE SELF-SERVICE SCHEMAS
# =========================================================
class EmployeeProjectResponse(BaseModel):
    project_id: int
    project_code: str
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    priority: ProjectPriority
    status: ProjectStatus
    progress_percentage: int
    is_overdue: bool = False
    project_role_name: str
    my_role: Optional[str] = None
    assigned_date: date
    team_members_count: int = 0

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def project_name(self) -> str:
        return self.name

    @computed_field
    @property
    def id(self) -> int:
        return self.project_id


# =========================================================
# DASHBOARD METRICS SCHEMA
# =========================================================
class HRProjectDashboardMetrics(BaseModel):
    total_projects: int = 0
    active_projects: int = 0
    completed_projects: int = 0
    on_hold_projects: int = 0
    overdue_projects: int = 0


# =========================================================
# PROJECT ROLE EMPLOYEE ASSIGNMENT SCHEMAS
# =========================================================
class RoleAssignEmployeesRequest(BaseModel):
    employee_ids: List[Union[int, str]] = Field(default_factory=list)
    employeeIds: Optional[List[Union[int, str]]] = None
    employee_id: Optional[Union[int, str]] = None
    employeeId: Optional[Union[int, str]] = None
    assigned_date: Optional[date] = None
    required_count: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_employee_ids(cls, data: Any) -> Any:
        if isinstance(data, dict):
            emp_ids = data.get("employee_ids") or data.get("employeeIds")
            if not emp_ids:
                single_id = data.get("employee_id") or data.get("employeeId")
                if single_id is not None:
                    emp_ids = [single_id]
            elif not isinstance(emp_ids, list):
                emp_ids = [emp_ids]
            data["employee_ids"] = emp_ids or []
            data["employeeIds"] = data["employee_ids"]
        return data


class RoleAssignedEmployeeItem(BaseModel):
    assignment_id: int
    employee_id: int
    employee_code: str
    employee_name: str
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    official_designation: Optional[str] = None
    assigned_date: date
    status: str
    role_id: int
    role_name: str
    project_id: int
    project_name: str

    model_config = ConfigDict(from_attributes=True)


class RoleAssignEmployeesResponse(BaseModel):
    success: bool
    assigned_count: int
    already_assigned: List[str] = Field(default_factory=list)
    assignments: List[RoleAssignedEmployeeItem] = Field(default_factory=list)
    message: str