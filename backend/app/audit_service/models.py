from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.authentication_service.models import User
from app.employee_service.models import Employee


class AuditAction:
    PROJECT_CREATED = "PROJECT_CREATED"
    PROJECT_UPDATED = "PROJECT_UPDATED"
    PROJECT_STATUS_CHANGED = "PROJECT_STATUS_CHANGED"
    PROJECT_PROGRESS_UPDATED = "PROJECT_PROGRESS_UPDATED"
    PROJECT_ROLE_CREATED = "PROJECT_ROLE_CREATED"
    PROJECT_ROLE_UPDATED = "PROJECT_ROLE_UPDATED"
    EMPLOYEE_ASSIGNED_TO_PROJECT = "EMPLOYEE_ASSIGNED_TO_PROJECT"
    EMPLOYEE_ASSIGNED_TO_PROJECT_ROLE = "EMPLOYEE_ASSIGNED_TO_PROJECT_ROLE"
    EMPLOYEE_REMOVED_FROM_PROJECT = "EMPLOYEE_REMOVED_FROM_PROJECT"
    EMPLOYEE_REMOVED_FROM_PROJECT_ROLE = "EMPLOYEE_REMOVED_FROM_PROJECT_ROLE"
    EMPLOYEE_ROLE_CHANGED = "EMPLOYEE_ROLE_CHANGED"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    employee_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id], lazy="joined")
    employee: Mapped[Optional["Employee"]] = relationship("Employee", foreign_keys=[employee_id], lazy="joined")
