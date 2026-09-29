from datetime import date, datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.authentication_service.models import User
from app.employee_service.models import Employee


class ProjectPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ProjectStatus(str, Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ACTIVE = "ACTIVE"
    PLANNING = "PLANNING"
    UPCOMING = "UPCOMING"


class AssignmentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REMOVED = "REMOVED"
    TERMINATED = "TERMINATED"
    COMPLETED = "COMPLETED"


class ProjectRole(Base):
    __tablename__ = "project_roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Maps directly to PostgreSQL column role_name while exposing .name and .role_name
    name: Mapped[str] = mapped_column("role_name", String(100), unique=False, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    required_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)
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

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="roles")
    assignments: Mapped[List["ProjectAssignment"]] = relationship(
        "ProjectAssignment", back_populates="project_role"
    )

    def __init__(self, **kwargs):
        if "role_name" in kwargs and "name" not in kwargs:
            kwargs["name"] = kwargs.pop("role_name")
        super().__init__(**kwargs)

    @property
    def role_name(self) -> str:
        return self.name

    @role_name.setter
    def role_name(self, value: str):
        self.name = value


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    # Maps directly to PostgreSQL column project_name while exposing .name and .project_name
    name: Mapped[str] = mapped_column("project_name", String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Maps directly to PostgreSQL column expected_end_date while exposing .end_date and .expected_end_date
    end_date: Mapped[Optional[date]] = mapped_column("expected_end_date", Date, nullable=True)
    client_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    actual_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    priority: Mapped[ProjectPriority] = mapped_column(
        SQLEnum(ProjectPriority, name="projectpriority"),
        nullable=False,
        default=ProjectPriority.MEDIUM,
        index=True,
    )

    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus, name="projectstatus"),
        nullable=False,
        default=ProjectStatus.PLANNED,
        index=True,
    )

    progress_percentage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    creator: Mapped[Optional["User"]] = relationship("User")
    roles: Mapped[List["ProjectRole"]] = relationship("ProjectRole", back_populates="project", cascade="all, delete-orphan")
    assignments: Mapped[List["ProjectAssignment"]] = relationship(
        "ProjectAssignment", back_populates="project", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "progress_percentage >= 0 AND progress_percentage <= 100",
            name="chk_project_progress_range",
        ),
    )

    def __init__(self, **kwargs):
        if "project_name" in kwargs and "name" not in kwargs:
            kwargs["name"] = kwargs.pop("project_name")
        if "expected_end_date" in kwargs and "end_date" not in kwargs:
            kwargs["end_date"] = kwargs.pop("expected_end_date")
        super().__init__(**kwargs)

    @property
    def project_name(self) -> str:
        return self.name

    @project_name.setter
    def project_name(self, value: str):
        self.name = value

    @property
    def expected_end_date(self) -> Optional[date]:
        return self.end_date

    @expected_end_date.setter
    def expected_end_date(self, value: Optional[date]):
        self.end_date = value

    @property
    def is_overdue(self) -> bool:
        if not self.end_date:
            return False
        return date.today() > self.end_date and self.status not in (
            ProjectStatus.COMPLETED,
            ProjectStatus.CANCELLED,
        )


class ProjectAssignment(Base):
    __tablename__ = "project_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project_role_id: Mapped[int] = mapped_column(
        ForeignKey("project_roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    assigned_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=lambda: date.today(),
    )

    removed_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )

    status: Mapped[AssignmentStatus] = mapped_column(
        SQLEnum(AssignmentStatus, name="assignmentstatus"),
        nullable=False,
        default=AssignmentStatus.ACTIVE,
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

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="assignments")
    employee: Mapped["Employee"] = relationship("Employee")
    project_role: Mapped["ProjectRole"] = relationship("ProjectRole", back_populates="assignments")

    def __init__(self, **kwargs):
        kwargs.pop("assigned_by", None)
        if "start_date" in kwargs and "assigned_date" not in kwargs:
            kwargs["assigned_date"] = kwargs.pop("start_date")
        if "assigned_at" in kwargs and "assigned_date" not in kwargs:
            kwargs["assigned_date"] = kwargs.pop("assigned_at")
        if "end_date" in kwargs and "removed_date" not in kwargs:
            kwargs["removed_date"] = kwargs.pop("end_date")
        is_act = kwargs.pop("is_active", None)
        if is_act is not None and "status" not in kwargs:
            kwargs["status"] = AssignmentStatus.ACTIVE if is_act else AssignmentStatus.REMOVED
        super().__init__(**kwargs)

    @property
    def start_date(self) -> date:
        return self.assigned_date

    @property
    def end_date(self) -> Optional[date]:
        return self.removed_date


# Unified alias for backward compatibility across modules
ProjectEmployeeAssignment = ProjectAssignment