from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.complaint_service.models import Complaint, ComplaintType, ComplaintPriority, ComplaintStatus


def create_complaint(db: Session, data: dict) -> Complaint:
    complaint = Complaint(**data)
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


def get_complaint_by_id(db: Session, complaint_id: int) -> Optional[Complaint]:
    return db.query(Complaint).filter(Complaint.id == complaint_id).first()


def list_complaints(
    db: Session,
    employee_id: Optional[int] = None,
    complaint_type: Optional[ComplaintType] = None,
    project_id: Optional[int] = None,
    priority: Optional[ComplaintPriority] = None,
    status: Optional[ComplaintStatus] = None,
) -> List[Complaint]:
    query = db.query(Complaint)
    if employee_id is not None:
        query = query.filter(Complaint.employee_id == employee_id)
    if complaint_type is not None:
        query = query.filter(Complaint.complaint_type == complaint_type)
    if project_id is not None:
        query = query.filter(Complaint.project_id == project_id)
    if priority is not None:
        query = query.filter(Complaint.priority == priority)
    if status is not None:
        query = query.filter(Complaint.status == status)
    return query.order_by(desc(Complaint.created_at)).all()


def update_complaint(db: Session, complaint: Complaint, data: dict) -> Complaint:
    for key, value in data.items():
        if value is not None:
            setattr(complaint, key, value)
    db.commit()
    db.refresh(complaint)
    return complaint
