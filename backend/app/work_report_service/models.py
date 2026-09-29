from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReportStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"

WorkReportStatus = ReportStatus


class WorkReport(Base):
    __tablename__ = "work_reports"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True
    )
    work_summary: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    tasks_completed: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    hours_worked: Mapped[float] = mapped_column(
        Float, nullable=False, default=8.0
    )
    achievements: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    blockers: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    next_day_plan: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(ReportStatus, name="work_report_status"),
        nullable=False,
        default=ReportStatus.DRAFT,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "project_id",
            "report_date",
            name="uq_emp_project_report_date",
        ),
    )

    employee = relationship("Employee")
    project = relationship("Project")
