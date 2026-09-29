import logging
from datetime import date, datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.work_report_service import repository
from app.work_report_service.models import WorkReport, ReportStatus
from app.employee_service.models import Employee, EmploymentStatus
from app.project_service.models import Project, ProjectEmployeeAssignment, AssignmentStatus, ProjectStatus
from app.audit_service.service import log_audit_event

logger = logging.getLogger("hrms.work_reports")


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


def _format_report_response(r: WorkReport) -> dict:
    emp = r.employee
    proj = r.project
    emp_name = f"{emp.first_name} {emp.last_name}".strip() if emp else "Unknown"
    emp_code = emp.employee_code if emp else ""
    proj_name = proj.project_name if proj else "Unknown Project"
    proj_code = proj.project_code if proj else ""

    return {
        "id": r.id,
        "employee_id": r.employee_id,
        "employee_name": emp_name,
        "employee_code": emp_code,
        "project_id": r.project_id,
        "project_name": proj_name,
        "project_code": proj_code,
        "report_date": r.report_date,
        "work_summary": r.work_summary,
        "tasks_completed": r.tasks_completed,
        "hours_worked": r.hours_worked,
        "achievements": r.achievements,
        "blockers": r.blockers,
        "next_day_plan": r.next_day_plan,
        "status": r.status,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def create_work_report(
    db: Session,
    user,
    data: dict,
) -> dict:
    employee = get_or_ensure_employee(db, user)

    report_date = data["report_date"]
    if report_date > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report date cannot be a future date.",
        )

    hours = float(data.get("hours_worked", 8.0))
    if hours < 0.0 or hours > 24.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hours worked must be between 0 and 24.",
        )

    project_id = data["project_id"]
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    # Project status validation: New work reports cannot be submitted against non-active/completed projects
    if project.status != ProjectStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Work reports can only be submitted for active projects (project is currently {project.status.value.lower()}).",
        )

    # Project assignment check: employees must be assigned to the project
    is_hr = user.role == "hr"
    if not is_hr:
        assign = (
            db.query(ProjectEmployeeAssignment)
            .filter(
                ProjectEmployeeAssignment.project_id == project_id,
                ProjectEmployeeAssignment.employee_id == employee.id,
                ProjectEmployeeAssignment.status == AssignmentStatus.ACTIVE,
            )
            .first()
        )
        if not assign:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this project.",
            )

    # Duplicate check: UNIQUE(employee_id, project_id, report_date)
    existing = repository.get_report_by_emp_project_date(db, employee.id, project_id, report_date)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A work report for '{project.project_name}' on {report_date} already exists.",
        )

    now = datetime.now(timezone.utc)
    report_status = data.get("status") or ReportStatus.DRAFT

    payload = {
        "employee_id": employee.id,
        "project_id": project_id,
        "report_date": report_date,
        "work_summary": data["work_summary"].strip(),
        "tasks_completed": data.get("tasks_completed"),
        "hours_worked": hours,
        "achievements": data.get("achievements"),
        "blockers": data.get("blockers"),
        "next_day_plan": data.get("next_day_plan"),
        "status": report_status,
        "created_at": now,
        "updated_at": now,
    }
    report = repository.create_report(db, payload)

    action = "Work report submitted" if report_status == ReportStatus.SUBMITTED else "Work report created"
    log_audit_event(
        actor_user_id=user.id,
        action=action,
        entity_type="WorkReport",
        entity_id=report.id,
        details={"project_id": project_id, "report_date": str(report_date), "status": report_status.value},
    )

    return _format_report_response(report)


def update_work_report(
    db: Session,
    report_id: int,
    user,
    data: dict,
) -> dict:
    employee = get_or_ensure_employee(db, user)
    report = repository.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work report not found.",
        )

    if report.employee_id != employee.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own work reports.",
        )

    if report.status == ReportStatus.SUBMITTED and data.get("status") != ReportStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submitted work reports cannot be edited.",
        )

    if "project_id" in data and data["project_id"] is not None and data["project_id"] != report.project_id:
        proj_id = data["project_id"]
        proj = db.query(Project).filter(Project.id == proj_id).first()
        if not proj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )
        if proj.status != ProjectStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Work reports cannot be assigned to a {proj.status.value.lower()} project.",
            )
        is_hr = user.role == "hr"
        if not is_hr:
            assign = (
                db.query(ProjectEmployeeAssignment)
                .filter(
                    ProjectEmployeeAssignment.project_id == proj_id,
                    ProjectEmployeeAssignment.employee_id == employee.id,
                    ProjectEmployeeAssignment.status == AssignmentStatus.ACTIVE,
                )
                .first()
            )
            if not assign:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not assigned to this project.",
                )

    if "report_date" in data and data["report_date"] is not None:
        if data["report_date"] > date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Report date cannot be a future date.",
            )

    if "hours_worked" in data and data["hours_worked"] is not None:
        if data["hours_worked"] < 0.0 or data["hours_worked"] > 24.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours worked must be between 0 and 24.",
            )

    data["updated_at"] = datetime.now(timezone.utc)
    updated = repository.update_report(db, report, data)

    action = "Work report submitted" if updated.status == ReportStatus.SUBMITTED and report.status != ReportStatus.SUBMITTED else "Work report updated"
    log_audit_event(
        actor_user_id=user.id,
        action=action,
        entity_type="WorkReport",
        entity_id=updated.id,
        details={"updated_fields": list(data.keys())},
    )

    return _format_report_response(updated)


def delete_work_report(db: Session, report_id: int, user) -> dict:
    employee = get_or_ensure_employee(db, user)
    report = repository.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work report not found.",
        )

    if report.employee_id != employee.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own draft reports.",
        )

    if report.status == ReportStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submitted work reports cannot be deleted.",
        )

    repository.delete_report(db, report)

    log_audit_event(
        actor_user_id=user.id,
        action="Work report draft deleted",
        entity_type="WorkReport",
        entity_id=report_id,
        details={"project_id": report.project_id, "report_date": str(report.report_date)},
    )
    return {"message": "Draft work report deleted successfully."}


def get_my_report(db: Session, report_id: int, user) -> dict:
    employee = get_or_ensure_employee(db, user)
    report = repository.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work report not found.",
        )

    if report.employee_id != employee.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view another employee's report.",
        )

    return _format_report_response(report)


def list_my_reports(
    db: Session,
    user,
    project_id: Optional[int] = None,
    report_date: Optional[date] = None,
    status_filter: Optional[ReportStatus] = None,
) -> dict:
    employee = get_or_ensure_employee(db, user)
    reports = repository.list_reports(
        db,
        employee_id=employee.id,
        project_id=project_id,
        report_date=report_date,
        status=status_filter,
    )
    return {
        "total": len(reports),
        "items": [_format_report_response(r) for r in reports],
    }


def list_hr_reports(
    db: Session,
    employee_id: Optional[int] = None,
    project_id: Optional[int] = None,
    report_date: Optional[date] = None,
    status_filter: Optional[ReportStatus] = None,
) -> dict:
    reports = repository.list_reports(
        db,
        employee_id=employee_id,
        project_id=project_id,
        report_date=report_date,
        status=status_filter,
    )
    return {
        "total": len(reports),
        "items": [_format_report_response(r) for r in reports],
    }


def get_hr_report_by_id(db: Session, report_id: int) -> dict:
    report = repository.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work report not found.",
        )
    return _format_report_response(report)
