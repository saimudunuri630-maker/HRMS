from datetime import date, datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict


class ProjectSummaryItem(BaseModel):
    id: int
    project_code: str
    project_name: str
    status: str
    priority: str
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None
    employees_count: int = 0
    roles_count: int = 0
    project_manager: Optional[str] = None


class RecentEmployeeItem(BaseModel):
    id: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    employment_status: str
    joining_date: Optional[date] = None
    profile_photo_url: Optional[str] = None


class HRDashboardSummaryResponse(BaseModel):
    total_employees: int
    active_employees: int
    inactive_employees: int
    on_leave_today: int
    active_projects: int
    completed_projects: int = 0
    total_projects: int
    project_members: int = 0
    pending_leave_requests: int
    open_complaints: int
    pending_work_reports: int
    unread_notifications: int
    active_projects_list: List[ProjectSummaryItem]
    recent_employees: List[RecentEmployeeItem]


class EmployeeProjectItem(BaseModel):
    id: int
    project_code: str
    project_name: str
    status: str
    role_name: Optional[str] = None
    team_members_count: int = 0
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None


class AnnouncementItem(BaseModel):
    id: int
    title: str
    content: str
    created_at: str
    priority: str = "NORMAL"


class EmployeeDashboardSummaryResponse(BaseModel):
    employee_id: Optional[int] = None
    employee_code: Optional[str] = None
    employee_name: str
    email: str
    role: str
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    profile_photo_url: Optional[str] = None
    my_projects_count: int
    my_active_projects: int = 0
    my_completed_projects: int = 0
    today_attendance_status: str
    today_clock_in_time: Optional[str] = None
    leave_balance: float
    pending_leave_requests: int
    pending_work_reports: int
    unread_notifications: int
    assigned_projects: List[EmployeeProjectItem]
    recent_announcements: List[AnnouncementItem]
