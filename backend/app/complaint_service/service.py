import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.complaint_service import repository
from app.complaint_service.models import Complaint, ComplaintType, ComplaintPriority, ComplaintStatus
from app.employee_service.models import Employee, EmploymentStatus
from app.authentication_service.models import User
from app.project_service.models import Project, ProjectEmployeeAssignment, AssignmentStatus
from app.notification_service.service import create_in_app_notification
from app.audit_service.service import log_audit_event

logger = logging.getLogger("hrms.complaints")


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


def _format_complaint_response(c: Complaint) -> dict:
    emp = c.employee
    proj = c.project
    emp_name = f"{emp.first_name} {emp.last_name}".strip() if emp else "Unknown Employee"
    emp_code = emp.employee_code if emp else ""
    proj_name = proj.project_name if proj else None
    proj_code = proj.project_code if proj else None

    return {
        "id": c.id,
        "employee_id": c.employee_id,
        "employee_name": emp_name,
        "employee_code": emp_code,
        "complaint_type": c.complaint_type,
        "project_id": c.project_id,
        "project_name": proj_name,
        "project_code": proj_code,
        "subject": c.subject,
        "description": c.description,
        "priority": c.priority,
        "status": c.status,
        "hr_response": c.hr_response,
        "assigned_hr_id": c.assigned_hr_id,
        "resolved_at": c.resolved_at,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


def create_complaint(db: Session, user, data: dict) -> dict:
    employee = get_or_ensure_employee(db, user)

    complaint_type = data.get("complaint_type", ComplaintType.OTHER)
    project_id = data.get("project_id")

    if complaint_type == ComplaintType.PROJECT:
        if not project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project is required for project-related complaints.",
            )
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected project not found.",
            )
        # Verify employee is assigned to this project
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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can only raise complaints for projects you are actively assigned to.",
            )
    elif complaint_type == ComplaintType.COMPANY:
        project_id = None

    now = datetime.now(timezone.utc)
    payload = {
        "employee_id": employee.id,
        "complaint_type": complaint_type,
        "project_id": project_id,
        "subject": data["subject"].strip(),
        "description": data["description"].strip(),
        "priority": data.get("priority", ComplaintPriority.MEDIUM),
        "status": ComplaintStatus.OPEN,
        "created_at": now,
        "updated_at": now,
    }
    complaint = repository.create_complaint(db, payload)

    emp_name = f"{employee.first_name} {employee.last_name}".strip()
    log_audit_event(
        actor_user_id=user.id,
        action="Complaint created",
        entity_type="Complaint",
        entity_id=complaint.id,
        details={"type": complaint_type.value, "subject": complaint.subject},
    )

    # Notify HR administrators
    try:
        hr_users = db.query(User).filter(User.role == "hr", User.is_active == True).all()
        for hr in hr_users:
            create_in_app_notification(
                user_id=hr.id,
                title="New Complaint",
                message=f"A new complaint has been submitted by {emp_name}.",
                category="COMPLAINT",
                metadata={"complaint_id": complaint.id, "entity_type": "COMPLAINT", "entity_id": complaint.id, "subject": complaint.subject},
                db=db,
            )
    except Exception as err:
        logger.warning(f"Failed to notify HR users of new complaint: {err}")

    return _format_complaint_response(complaint)


def get_my_complaint(db: Session, complaint_id: int, user) -> dict:
    employee = get_or_ensure_employee(db, user)
    complaint = repository.get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found.",
        )

    if complaint.employee_id != employee.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this complaint.",
        )

    return _format_complaint_response(complaint)


def list_my_complaints(
    db: Session,
    user,
    complaint_type: Optional[ComplaintType] = None,
    priority: Optional[ComplaintPriority] = None,
    status_filter: Optional[ComplaintStatus] = None,
) -> dict:
    employee = get_or_ensure_employee(db, user)
    items = repository.list_complaints(
        db,
        employee_id=employee.id,
        complaint_type=complaint_type,
        priority=priority,
        status=status_filter,
    )
    return {
        "total": len(items),
        "items": [_format_complaint_response(c) for c in items],
    }


def list_hr_complaints(
    db: Session,
    employee_id: Optional[int] = None,
    complaint_type: Optional[ComplaintType] = None,
    project_id: Optional[int] = None,
    priority: Optional[ComplaintPriority] = None,
    status_filter: Optional[ComplaintStatus] = None,
) -> dict:
    items = repository.list_complaints(
        db,
        employee_id=employee_id,
        complaint_type=complaint_type,
        project_id=project_id,
        priority=priority,
        status=status_filter,
    )
    return {
        "total": len(items),
        "items": [_format_complaint_response(c) for c in items],
    }


def get_hr_complaint(db: Session, complaint_id: int) -> dict:
    complaint = repository.get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found.",
        )
    return _format_complaint_response(complaint)


def add_hr_feedback(
    db: Session,
    complaint_id: int,
    feedback: str,
    status_val: Optional[ComplaintStatus],
    hr_user_id: int,
) -> dict:
    complaint = repository.get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found.",
        )

    clean_feedback = feedback.strip()
    if not clean_feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback content cannot be empty.",
        )

    target_status = status_val or ComplaintStatus.RESPONDED
    now = datetime.now(timezone.utc)
    resolved_at = now if target_status in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED] else complaint.resolved_at

    update_data = {
        "hr_response": clean_feedback,
        "status": target_status,
        "assigned_hr_id": hr_user_id,
        "resolved_at": resolved_at,
        "updated_at": now,
    }
    updated = repository.update_complaint(db, complaint, update_data)

    action = "Complaint resolved" if target_status == ComplaintStatus.RESOLVED else "HR feedback added"
    log_audit_event(
        actor_user_id=hr_user_id,
        action=action,
        entity_type="Complaint",
        entity_id=updated.id,
        details={"status": target_status.value},
    )

    # Notify complaint owner
    if updated.employee and updated.employee.user_id:
        try:
            create_in_app_notification(
                user_id=updated.employee.user_id,
                title="Complaint Updated",
                message="HR has provided feedback on your complaint.",
                category="COMPLAINT",
                metadata={"complaint_id": updated.id, "entity_type": "COMPLAINT", "entity_id": updated.id, "status": target_status.value},
                db=db,
            )
        except Exception as err:
            logger.warning(f"Failed to notify employee of complaint update: {err}")

    return _format_complaint_response(updated)


def update_complaint_by_hr(
    db: Session,
    complaint_id: int,
    data: dict,
    hr_user_id: int,
) -> dict:
    complaint = repository.get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found.",
        )

    target_status = data.get("status")
    now = datetime.now(timezone.utc)
    data["updated_at"] = now
    data["assigned_hr_id"] = hr_user_id

    if target_status in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED] and not complaint.resolved_at:
        data["resolved_at"] = now

    updated = repository.update_complaint(db, complaint, data)

    log_audit_event(
        actor_user_id=hr_user_id,
        action="Complaint status updated",
        entity_type="Complaint",
        entity_id=updated.id,
        details={"status": updated.status.value},
    )

    if updated.employee and updated.employee.user_id:
        try:
            create_in_app_notification(
                user_id=updated.employee.user_id,
                title="Complaint Status Changed",
                message=f"Your complaint status was updated to {updated.status.value}.",
                category="COMPLAINT",
                metadata={"complaint_id": updated.id, "status": updated.status.value},
            )
        except Exception as err:
            logger.warning(f"Failed to notify employee of complaint status update: {err}")

    return _format_complaint_response(updated)
