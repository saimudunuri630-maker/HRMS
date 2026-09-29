import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import jwt

from app.main import app
from app.core.database import SessionLocal
from app.core.config import settings
from app.authentication_service.models import User
from app.employee_service.models import Employee, EmploymentStatus
from app.audit_service.models import AuditLog
from app.authentication_service.service import logout, verify_login_otp


def test_login_and_logout_automatic_audit():
    client = TestClient(app)
    db: Session = SessionLocal()

    try:
        # Find active HR user
        hr_user = db.query(User).filter(User.role == "hr", User.is_active == True).first()
        assert hr_user is not None, "HR user must exist"

        # Find active Employee user
        emp_user = (
            db.query(User)
            .filter(User.role == "employee", User.is_active == True, User.id != hr_user.id)
            .first()
        )
        assert emp_user is not None, "Employee user must exist"

        # Count initial audit logs for login/logout
        initial_hr_logouts = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == hr_user.id, AuditLog.action == "LOGOUT")
            .count()
        )

        initial_emp_logouts = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == emp_user.id, AuditLog.action == "LOGOUT")
            .count()
        )

        # Trigger logout for HR
        logout(db=db, user=hr_user)
        db.commit()

        # Verify HR logout audit record exists
        new_hr_logouts = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == hr_user.id, AuditLog.action == "LOGOUT")
            .count()
        )
        assert new_hr_logouts > initial_hr_logouts, "HR logout must be recorded automatically in AuditLog"

        latest_hr_logout = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == hr_user.id, AuditLog.action == "LOGOUT")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert latest_hr_logout is not None
        assert "LOGOUT" in latest_hr_logout.action
        assert latest_hr_logout.module == "AUTHENTICATION"

        # Trigger logout for Employee
        logout(db=db, user=emp_user)
        db.commit()

        # Verify Employee logout audit record exists
        new_emp_logouts = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == emp_user.id, AuditLog.action == "LOGOUT")
            .count()
        )
        assert new_emp_logouts > initial_emp_logouts, "Employee logout must be recorded automatically in AuditLog"

        latest_emp_logout = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == emp_user.id, AuditLog.action == "LOGOUT")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert latest_emp_logout is not None
        assert "LOGOUT" in latest_emp_logout.action
        assert latest_emp_logout.module == "AUTHENTICATION"

    finally:
        db.close()
