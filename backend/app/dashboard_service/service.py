from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.authentication_service.models import User
from app.employee_service.models import Employee, EmploymentStatus
from app.project_service.models import Project, ProjectStatus, ProjectRole, ProjectEmployeeAssignment
from app.attendance_service.models import Attendance, AttendanceStatus
from app.leave_service.models import LeaveRequest, LeaveStatus, LeaveBalance
from app.dashboard_service.schemas import (
    HRDashboardSummaryResponse,
    EmployeeDashboardSummaryResponse,
    ProjectSummaryItem,
    RecentEmployeeItem,
    EmployeeProjectItem,
    AnnouncementItem,
)


def get_hr_dashboard_summary(db: Session) -> dict:
    today = date.today()

    # Employees counts
    total_employees = (
        db.query(func.count(Employee.id))
        .filter(Employee.deleted_at.is_(None))
        .scalar() or 0
    )

    active_employees = (
        db.query(func.count(Employee.id))
        .filter(
            Employee.deleted_at.is_(None),
            Employee.employment_status == EmploymentStatus.ACTIVE
        )
        .scalar() or 0
    )

    inactive_employees = (
        db.query(func.count(Employee.id))
        .filter(
            Employee.deleted_at.is_(None),
            Employee.employment_status.in_([EmploymentStatus.INACTIVE, EmploymentStatus.TERMINATED])
        )
        .scalar() or 0
    )

    # Attendance / Leave counts for today
    on_leave_today = (
        db.query(func.count(Attendance.id))
        .filter(
            Attendance.attendance_date == today,
            Attendance.status == AttendanceStatus.ON_LEAVE
        )
        .scalar() or 0
    )

    active_projects = (
        db.query(func.count(Project.id))
        .filter(Project.status == ProjectStatus.ACTIVE)
        .scalar() or 0
    )

    completed_projects = (
        db.query(func.count(Project.id))
        .filter(Project.status == ProjectStatus.COMPLETED)
        .scalar() or 0
    )

    total_projects = db.query(func.count(Project.id)).scalar() or 0

    project_members = (
        db.query(func.count(ProjectEmployeeAssignment.id))
        .filter(ProjectEmployeeAssignment.status == "ACTIVE")
        .scalar() or 0
    )

    # Pending leave requests
    pending_leaves = (
        db.query(func.count(LeaveRequest.id))
        .filter(LeaveRequest.status == LeaveStatus.PENDING)
        .scalar() or 0
    )

    # Query active/recent projects list
    projects_db = (
        db.query(Project)
        .order_by(Project.id.desc())
        .limit(6)
        .all()
    )

    active_projects_list = []
    for p in projects_db:
        emp_count = (
            db.query(func.count(ProjectEmployeeAssignment.id))
            .filter(
                ProjectEmployeeAssignment.project_id == p.id,
                ProjectEmployeeAssignment.status == "ACTIVE",
            )
            .scalar() or 0
        )
        role_count = (
            db.query(func.count(ProjectRole.id))
            .filter(ProjectRole.project_id == p.id)
            .scalar() or 0
        )
        # Find project creator/manager email or name
        creator = db.query(User).filter(User.id == p.created_by).first() if p.created_by else None
        manager_name = creator.full_name or creator.email if creator else "Admin"

        active_projects_list.append(
            ProjectSummaryItem(
                id=p.id,
                project_code=p.project_code,
                project_name=p.project_name,
                status=p.status.value if hasattr(p.status, "value") else str(p.status),
                priority=p.priority.value if hasattr(p.priority, "value") else str(p.priority),
                start_date=p.start_date,
                expected_end_date=p.expected_end_date,
                employees_count=emp_count,
                roles_count=role_count,
                project_manager=manager_name,
            )
        )

    # Recently joined employees
    recent_emps_db = (
        db.query(Employee, User)
        .join(User, Employee.user_id == User.id)
        .filter(Employee.deleted_at.is_(None))
        .order_by(Employee.id.desc())
        .limit(5)
        .all()
    )

    recent_employees = []
    for emp, usr in recent_emps_db:
        recent_employees.append(
            RecentEmployeeItem(
                id=emp.id,
                employee_code=emp.employee_code,
                first_name=emp.first_name,
                last_name=emp.last_name,
                email=usr.email,
                department_id=emp.department_id,
                designation_id=emp.designation_id,
                department=getattr(emp, "department", None),
                designation=getattr(emp, "designation", None),
                employment_status=emp.employment_status.value if hasattr(emp.employment_status, "value") else str(emp.employment_status),
                joining_date=emp.joining_date,
                profile_photo_url=emp.profile_photo_url,
            )
        )

    # Operational counts across modules
    try:
        from app.complaint_service.models import Complaint, ComplaintStatus
        open_complaints = db.query(func.count(Complaint.id)).filter(
            Complaint.status.in_([ComplaintStatus.OPEN, ComplaintStatus.IN_REVIEW])
        ).scalar() or 0
    except Exception:
        open_complaints = 0

    try:
        from app.work_report_service.models import WorkReport, ReportStatus
        pending_work_reports = db.query(func.count(WorkReport.id)).filter(
            WorkReport.status == ReportStatus.SUBMITTED
        ).scalar() or 0
    except Exception:
        pending_work_reports = 0

    try:
        from app.notification_service.models import Notification
        unread_notifications = db.query(func.count(Notification.id)).filter(
            Notification.is_read.is_(False)
        ).scalar() or 0
    except Exception:
        unread_notifications = 0

    return {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "inactive_employees": inactive_employees,
        "on_leave_today": on_leave_today,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
        "total_projects": total_projects,
        "project_members": project_members,
        "pending_leave_requests": pending_leaves,
        "open_complaints": open_complaints,
        "pending_work_reports": pending_work_reports,
        "unread_notifications": unread_notifications,
        "active_projects_list": active_projects_list,
        "recent_employees": recent_employees,
    }


def get_employee_dashboard_summary(db: Session, current_user: User) -> dict:
    today = date.today()

    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    emp_name = (
        f"{emp.first_name} {emp.last_name}".strip()
        if emp and (emp.first_name or emp.last_name)
        else (current_user.full_name or current_user.email.split("@")[0])
    )

    # Assigned projects
    assigned_projects_list = []
    my_projects_count = 0
    my_active_projects = 0
    my_completed_projects = 0

    if emp:
        assignments = (
            db.query(ProjectEmployeeAssignment, Project)
            .join(Project, ProjectEmployeeAssignment.project_id == Project.id)
            .filter(
                ProjectEmployeeAssignment.employee_id == emp.id,
                ProjectEmployeeAssignment.status == "ACTIVE",
            )
            .all()
        )
        my_projects_count = len(assignments)

        for assign, proj in assignments:
            if proj.status == ProjectStatus.ACTIVE:
                my_active_projects += 1
            elif proj.status == ProjectStatus.COMPLETED:
                my_completed_projects += 1

            role_obj = (
                db.query(ProjectRole)
                .filter(ProjectRole.id == assign.project_role_id)
                .first()
                if getattr(assign, "project_role_id", None)
                else None
            )
            role_title = role_obj.role_name if role_obj else "Role not assigned"

            team_count = (
                db.query(func.count(ProjectEmployeeAssignment.id))
                .filter(
                    ProjectEmployeeAssignment.project_id == proj.id,
                    ProjectEmployeeAssignment.status == "ACTIVE",
                )
                .scalar() or 0
            )

            assigned_projects_list.append(
                EmployeeProjectItem(
                    id=proj.id,
                    project_code=proj.project_code,
                    project_name=proj.project_name,
                    status=proj.status.value if hasattr(proj.status, "value") else str(proj.status),
                    role_name=role_title,
                    team_members_count=team_count,
                    start_date=proj.start_date,
                    expected_end_date=proj.expected_end_date,
                )
            )

    # Today's attendance
    today_status = "NOT_CLOCKED_IN"
    clock_in_time = None

    if emp:
        today_att = (
            db.query(Attendance)
            .filter(Attendance.employee_id == emp.id, Attendance.attendance_date == today)
            .first()
        )

        if today_att:
            if today_att.check_out:
                today_status = "CLOCKED_OUT"
            elif today_att.check_in:
                today_status = "CLOCKED_IN"
                clock_in_time = today_att.check_in.strftime("%I:%M %p")

    # Live announcements
    try:
        from app.announcement_service.models import Announcement, AnnouncementStatus
        db_announcements = (
            db.query(Announcement)
            .filter(Announcement.status == AnnouncementStatus.PUBLISHED)
            .order_by(Announcement.id.desc())
            .limit(5)
            .all()
        )
        if db_announcements:
            recent_announcements = [
                AnnouncementItem(
                    id=a.id,
                    title=a.title,
                    content=a.content,
                    created_at=a.created_at.strftime("%b %d, %Y") if hasattr(a.created_at, "strftime") else str(a.created_at)[:10],
                    priority=a.priority.value if hasattr(a.priority, "value") else str(a.priority),
                )
                for a in db_announcements
            ]
        else:
            recent_announcements = [
                AnnouncementItem(
                    id=1,
                    title="Enterprise HRMS System Upgrade",
                    content="Welcome to the updated Mediatize HRMS workspace. Biometric and project tracking are now live.",
                    created_at=today.strftime("%b %d, %Y"),
                    priority="HIGH",
                ),
                AnnouncementItem(
                    id=2,
                    title="Quarterly Review & Leave Policy",
                    content="Please ensure your work reports and pending leave applications are filed before month end.",
                    created_at=today.strftime("%b %d, %Y"),
                    priority="NORMAL",
                )
            ]
    except Exception:
        recent_announcements = []

    # Unread notifications count
    try:
        from app.notification_service.models import Notification
        unread_notifications = db.query(func.count(Notification.id)).filter(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False)
        ).scalar() or 0
    except Exception:
        unread_notifications = 0

    # Pending / draft work reports count
    try:
        from app.work_report_service.models import WorkReport, ReportStatus
        pending_work_reports = (
            db.query(func.count(WorkReport.id)).filter(
                WorkReport.employee_id == emp.id,
                WorkReport.status == ReportStatus.DRAFT
            ).scalar() or 0
        ) if emp else 0
    except Exception:
        pending_work_reports = 0

    return {
        "employee_id": emp.id if emp else None,
        "employee_code": emp.employee_code if emp else None,
        "employee_name": emp_name,
        "email": current_user.email,
        "role": current_user.role,
        "department_id": emp.department_id if emp else None,
        "designation_id": emp.designation_id if emp else None,
        "profile_photo_url": emp.profile_photo_url if emp else None,
        "my_projects_count": my_projects_count,
        "my_active_projects": my_active_projects,
        "my_completed_projects": my_completed_projects,
        "today_attendance_status": today_status,
        "today_clock_in_time": clock_in_time,
        "leave_balance": (
            sum(b.remaining_days for b in db.query(LeaveBalance).filter(LeaveBalance.employee_id == emp.id).all())
            if emp and db.query(LeaveBalance).filter(LeaveBalance.employee_id == emp.id).count() > 0
            else 12.0
        ),
        "pending_leave_requests": (
            db.query(func.count(LeaveRequest.id))
            .filter(LeaveRequest.employee_id == emp.id, LeaveRequest.status == LeaveStatus.PENDING)
            .scalar() or 0
        ) if emp else 0,
        "pending_work_reports": pending_work_reports,
        "unread_notifications": unread_notifications,
        "assigned_projects": assigned_projects_list,
        "recent_announcements": recent_announcements,
    }
