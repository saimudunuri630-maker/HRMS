import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import SessionLocal
from app.authentication_service.models import User, UserSession
from app.employee_service.models import Employee, EmploymentStatus
from app.core.config import settings
import jwt
from datetime import datetime, timedelta


class TestHRMSFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # Ensure an HR user exists
        cls.hr_user = cls.db.query(User).filter(User.role == "hr").first()
        if not cls.hr_user:
            cls.hr_user = User(
                email="hr_test@mediatize.com",
                full_name="HR Admin",
                role="hr",
                is_active=True,
                is_verified=True,
            )
            cls.db.add(cls.hr_user)
            cls.db.commit()
            cls.db.refresh(cls.hr_user)

        # Create session for HR
        cls.hr_session = UserSession(
            user_id=cls.hr_user.id,
            session_id=f"session_hr_{cls.hr_user.id}_{int(datetime.utcnow().timestamp())}",
            expires_at=datetime.utcnow() + timedelta(hours=2),
            is_active=True,
        )
        cls.db.add(cls.hr_session)
        cls.db.commit()

        # Create JWT for HR
        cls.hr_token = jwt.encode(
            {
                "sub": str(cls.hr_user.id),
                "session_id": cls.hr_session.session_id,
                "role": "hr",
                "email": cls.hr_user.email,
                "exp": datetime.utcnow() + timedelta(hours=2),
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        # Ensure an Employee user exists
        cls.emp_user = cls.db.query(User).filter(User.role == "employee").first()
        if not cls.emp_user:
            cls.emp_user = User(
                email="employee_test@mediatize.com",
                full_name="John Doe",
                role="employee",
                is_active=True,
                is_verified=True,
            )
            cls.db.add(cls.emp_user)
            cls.db.commit()
            cls.db.refresh(cls.emp_user)

            cls.emp_profile = Employee(
                user_id=cls.emp_user.id,
                employee_code="EMP-TEST-001",
                first_name="John",
                last_name="Doe",
                employment_status=EmploymentStatus.ACTIVE,
            )
            cls.db.add(cls.emp_profile)
            cls.db.commit()

        cls.emp_session = UserSession(
            user_id=cls.emp_user.id,
            session_id=f"session_emp_{cls.emp_user.id}_{int(datetime.utcnow().timestamp())}",
            expires_at=datetime.utcnow() + timedelta(hours=2),
            is_active=True,
        )
        cls.db.add(cls.emp_session)
        cls.db.commit()

        cls.emp_token = jwt.encode(
            {
                "sub": str(cls.emp_user.id),
                "session_id": cls.emp_session.session_id,
                "role": "employee",
                "email": cls.emp_user.email,
                "exp": datetime.utcnow() + timedelta(hours=2),
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_auth_me_both_endpoints(self):
        """Test that /auth/me and /api/auth/me both return authenticated user info."""
        headers = {"Authorization": f"Bearer {self.hr_token}"}
        
        res1 = self.client.get("/auth/me", headers=headers)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["email"], self.hr_user.email)
        self.assertEqual(res1.json()["role"], "hr")

        res2 = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["email"], self.hr_user.email)

    def test_hr_dashboard_summary_as_hr(self):
        """HR dashboard summary should return valid counts for HR."""
        headers = {"Authorization": f"Bearer {self.hr_token}"}
        res = self.client.get("/api/hr/dashboard/summary", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_employees", data)
        self.assertIn("active_employees", data)
        self.assertIn("active_projects", data)

    def test_hr_dashboard_summary_forbidden_for_employee(self):
        """Employee cannot access HR dashboard summary."""
        headers = {"Authorization": f"Bearer {self.emp_token}"}
        res = self.client.get("/api/hr/dashboard/summary", headers=headers)
        self.assertEqual(res.status_code, 403)

    def test_employee_dashboard_summary(self):
        """Employee dashboard summary should return personal workspace stats."""
        headers = {"Authorization": f"Bearer {self.emp_token}"}
        res = self.client.get("/api/employee/dashboard/summary", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["email"], self.emp_user.email)
        self.assertIn("my_projects_count", data)
        self.assertIn("today_attendance_status", data)

    def test_immutable_profile_fields_rejection(self):
        """Backend MUST reject attempts to modify email or employee_number."""
        headers = {"Authorization": f"Bearer {self.emp_token}"}

        # Attempt to modify email
        res1 = self.client.put(
            "/api/profile/me",
            json={"email": "hacked@company.com", "first_name": "Johnny"},
            headers=headers,
        )
        self.assertEqual(res1.status_code, 400)
        self.assertIn("immutable", res1.json()["detail"].lower())

        # Attempt to modify employee_number
        res2 = self.client.put(
            "/api/profile/me",
            json={"employee_number": "EMP-9999", "first_name": "Johnny"},
            headers=headers,
        )
        self.assertEqual(res2.status_code, 400)
        self.assertIn("immutable", res2.json()["detail"].lower())

        # Also via /api/employees/me/profile
        res3 = self.client.put(
            "/api/employees/me/profile",
            json={"employee_code": "EMP-9999", "first_name": "Johnny"},
            headers=headers,
        )
        self.assertEqual(res3.status_code, 400)

    def test_allowed_profile_update(self):
        """Updating permitted fields should succeed."""
        headers = {"Authorization": f"Bearer {self.emp_token}"}
        res = self.client.put(
            "/api/profile/me",
            json={"first_name": "JohnUpdated", "phone": "1234567890"},
            headers=headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["first_name"], "JohnUpdated")
        self.assertEqual(res.json()["phone"], "1234567890")

    def test_employee_cannot_create_project(self):
        """Employee role cannot create projects (strict 403 check)."""
        headers = {"Authorization": f"Bearer {self.emp_token}"}
        res = self.client.post(
            "/api/projects",
            json={
                "project_code": "PROJ-SEC",
                "project_name": "Security System",
                "start_date": "2026-09-25",
                "expected_end_date": "2026-12-31",
            },
            headers=headers,
        )
        self.assertEqual(res.status_code, 403)

    def test_hr_create_employee(self):
        """HR creating an employee should create user and employee profile, and dispatch onboarding email."""
        headers = {"Authorization": f"Bearer {self.hr_token}"}
        unique_email = f"new_hire_{int(datetime.utcnow().timestamp())}@mediatize.com"
        res = self.client.post(
            "/api/employees",
            json={
                "email": unique_email,
                "first_name": "Alice",
                "last_name": "Smith",
                "phone": "9876543210",
                "joining_date": "2026-09-25",
            },
            headers=headers,
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["first_name"], "Alice")
        self.assertEqual(data["last_name"], "Smith")
        self.assertTrue(data["employee_code"].startswith("EMP"))


if __name__ == "__main__":
    unittest.main()
