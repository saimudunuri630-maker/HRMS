from datetime import date
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.work_report_service.models import WorkReport, ReportStatus


def create_report(db: Session, data: dict) -> WorkReport:
    report = WorkReport(**data)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report_by_id(db: Session, report_id: int) -> Optional[WorkReport]:
    return db.query(WorkReport).filter(WorkReport.id == report_id).first()


def get_report_by_emp_project_date(
    db: Session, employee_id: int, project_id: int, report_date: date
) -> Optional[WorkReport]:
    return (
        db.query(WorkReport)
        .filter(
            WorkReport.employee_id == employee_id,
            WorkReport.project_id == project_id,
            WorkReport.report_date == report_date,
        )
        .first()
    )


def list_reports(
    db: Session,
    employee_id: Optional[int] = None,
    project_id: Optional[int] = None,
    report_date: Optional[date] = None,
    status: Optional[ReportStatus] = None,
) -> List[WorkReport]:
    query = db.query(WorkReport)
    if employee_id is not None:
        query = query.filter(WorkReport.employee_id == employee_id)
    if project_id is not None:
        query = query.filter(WorkReport.project_id == project_id)
    if report_date is not None:
        query = query.filter(WorkReport.report_date == report_date)
    if status is not None:
        query = query.filter(WorkReport.status == status)
    return query.order_by(desc(WorkReport.report_date), desc(WorkReport.id)).all()


def update_report(db: Session, report: WorkReport, data: dict) -> WorkReport:
    for key, value in data.items():
        if value is not None:
            setattr(report, key, value)
    db.commit()
    db.refresh(report)
    return report


def delete_report(db: Session, report: WorkReport) -> None:
    db.delete(report)
    db.commit()
