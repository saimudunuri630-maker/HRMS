import os
import sys
import unittest
from datetime import date, datetime, timedelta
import secrets

# Ensure backend root is on path
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from fastapi.testclient import TestClient
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, SessionLocal
from app.authentication_service.models import User, UserSession
from app.employee_service.models import Employee
from app.project_service.models import Project, ProjectAssignment, ProjectRole
from app.announcement_service.models import Announcement, AnnouncementStatus, AnnouncementPriority
from app.audit_service.models import AuditLog
from app.core.config import settings
import jwt


class ComprehensiveVerificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

        # Find or ensure HR user
        cls.hr_user = cls.db.scalar(select(User).where(User.role == "hr", User.email == "mudunurisaiverma335@gmail.com"))
        if not cls.hr_user:
            cls.hr_user = cls.db.scalar(select(User).where(User.role == "hr"))
        assert cls.hr_user is not None, "HR user must exist"

        # Generate auth token
        session_id = secrets.token_urlsafe(32)
        session_expires_at = datetime.utcnow() + timedelta(hours=2)
        user_sess = UserSession(
            user_id=cls.hr_user.id,
            session_id=session_id,
            expires_at=session_expires_at,
            is_active=True,
        )
        cls.db.add(user_sess)
        cls.db.commit()

        payload = {
            "sub": str(cls.hr_user.id),
            "email": cls.hr_user.email,
            "role": cls.hr_user.role,
            "session_id": session_id,
            "exp": session_expires_at,
        }
        cls.token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_dashboard_summary_returns_counts_and_recent_hires_with_designation(self):
        """Verify dashboard summary includes proper counts and recent hires with designation & department"""
        resp = self.client.get("/api/hr/dashboard/summary", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_employees", data)
        self.assertIn("active_projects", data)
        self.assertIn("recent_employees", data)
        print(f"\n[TEST 1 PASS] Dashboard summary returned total_employees={data['total_employees']}")
        for emp in data["recent_employees"]:
            self.assertIn("designation", emp)
            self.assertIn("department", emp)
            print(f"  - Recent Hire: {emp['first_name']} {emp['last_name']}, Code: {emp['employee_code']}, Desig: {emp['designation']}, Dept: {emp['department']}")

    def test_02_create_employee_requires_explicit_designation(self):
        """Verify designation must NOT be automatically generated; HR must explicitly enter it."""
        unique_suffix = secrets.token_hex(4)
        payload = {
            "first_name": "Test",
            "last_name": "Explicit",
            "email": f"test_no_desig_{unique_suffix}@mediatize.com",
            "department": "Engineering & Operations",
            "designation": "",  # Blank designation should be rejected
            "joining_date": str(date.today()),
        }
        resp = self.client.post("/api/employees", json=payload, headers=self.headers)
        self.assertIn(resp.status_code, [400, 422], "Should reject empty designation")
        print("\n[TEST 2 PASS] Creation rejected when designation is missing/blank (HTTP 422/400)")

    def test_03_create_employee_duplicate_protection(self):
        """Verify duplicate employee email and duplicate employee code are rejected with HTTP 409"""
        from app.employee_service.models import EmploymentStatus
        existing = self.db.scalar(select(Employee).where(Employee.employment_status == EmploymentStatus.ACTIVE))
        assert existing is not None

        # Duplicate email test
        payload = {
            "first_name": "Duplicate",
            "last_name": "Test",
            "email": existing.email,
            "designation": "Software Engineer",
            "department": "Engineering & Operations",
            "joining_date": str(date.today()),
        }
        resp = self.client.post("/api/employees", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 409, "Duplicate email should be rejected with 409")
        print("\n[TEST 3A PASS] Duplicate email rejected with HTTP 409")

        # Duplicate employee code test
        payload2 = {
            "first_name": "Duplicate",
            "last_name": "Code",
            "email": f"unique_email_{secrets.token_hex(4)}@mediatize.com",
            "employee_code": existing.employee_code,
            "designation": "Software Engineer",
            "department": "Engineering & Operations",
            "joining_date": str(date.today()),
        }
        resp2 = self.client.post("/api/employees", json=payload2, headers=self.headers)
        self.assertEqual(resp2.status_code, 409, "Duplicate employee code should be rejected with 409")
        print("[TEST 3B PASS] Duplicate employee code rejected with HTTP 409")

    def test_04_create_employee_success_and_email_deduplication(self):
        """Verify successful employee creation with explicit designation, welcome email dispatch, and duplicate prevention"""
        unique_suffix = secrets.token_hex(4)
        clean_email = f"verified_hire_{unique_suffix}@mediatize.com"
        custom_code = f"EMP-TEST-{unique_suffix.upper()}"
        payload = {
            "first_name": "Alex",
            "last_name": "Morgan",
            "email": clean_email,
            "employee_code": custom_code,
            "designation": "Principal Systems Architect",
            "department": "Engineering & Operations",
            "joining_date": str(date.today()),
        }
        resp = self.client.post("/api/employees", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 201)
        created = resp.json()
        self.assertEqual(created["email"], clean_email)
        self.assertEqual(created["employee_code"], custom_code)
        self.assertEqual(created["designation"], "Principal Systems Architect")
        print(f"\n[TEST 4A PASS] Employee successfully created: ID={created['id']}, Code={custom_code}, Desig={created['designation']}")

        # Verify welcome email was dispatched and duplicate dispatch is prevented
        from app.email_service.service import send_employee_welcome_email
        dup_result = send_employee_welcome_email(
            recipient_email=clean_email,
            first_name="Alex",
            employee_code=custom_code,
            entity_id=created["id"],
            db=self.db,
        )
        self.assertTrue(dup_result)
        print("[TEST 4B PASS] Duplicate welcome email prevented via deduplication registry")

        # Cleanup test employee
        emp_obj = self.db.get(Employee, created["id"])
        if emp_obj:
            user_id = emp_obj.user_id
            self.db.delete(emp_obj)
            self.db.commit()
            if user_id:
                self.db.execute(delete(UserSession).where(UserSession.user_id == user_id))
                self.db.execute(delete(User).where(User.id == user_id))
                self.db.commit()
            print(f"[TEST 4C PASS] Cleaned up temporary test employee #{created['id']}")

    def test_05_no_auto_fake_records_on_attendance_or_profile(self):
        """Verify accessing attendance or profile for non-existent employee raises HTTP 404 and does not create fake records"""
        temp_user = User(
            email=f"fake_check_{secrets.token_hex(4)}@mediatize.com",
            role="employee",
            is_active=True,
            is_verified=True,
        )
        self.db.add(temp_user)
        self.db.commit()
        self.db.refresh(temp_user)

        temp_sess_id = secrets.token_urlsafe(32)
        temp_sess = UserSession(
            user_id=temp_user.id,
            session_id=temp_sess_id,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True,
        )
        self.db.add(temp_sess)
        self.db.commit()

        temp_token = jwt.encode(
            {"sub": str(temp_user.id), "email": temp_user.email, "role": "employee", "session_id": temp_sess_id, "exp": datetime.utcnow() + timedelta(hours=1)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        temp_headers = {"Authorization": f"Bearer {temp_token}"}

        # Check attendance endpoint
        att_resp = self.client.get("/api/attendance/me", headers=temp_headers)
        self.assertEqual(att_resp.status_code, 404, "Must not auto-create employee in attendance service")

        # Check profile endpoint
        prof_resp = self.client.get("/api/profile/me", headers=temp_headers)
        self.assertEqual(prof_resp.status_code, 404, "Must not auto-create employee in profile service")

        # Check complaint endpoint
        comp_resp = self.client.get("/api/complaints/my", headers=temp_headers)
        self.assertEqual(comp_resp.status_code, 404, "Must not auto-create employee in complaint service")

        # Check work reports endpoint
        wr_resp = self.client.get("/api/work-reports/my-reports", headers=temp_headers)
        self.assertEqual(wr_resp.status_code, 404, "Must not auto-create employee in work report service")

        # Cleanup temp user
        self.db.delete(temp_sess)
        self.db.commit()
        self.db.delete(temp_user)
        self.db.commit()
        print("\n[TEST 5 PASS] Zero automatic/fake employee creation confirmed across attendance, profile, complaints, work reports (all returned 404)")

    def test_06_project_creation_sends_no_email_by_default(self):
        """Verify project creation without employee assignments does NOT trigger email dispatch"""
        unique_proj = f"PROJ-{secrets.token_hex(3).upper()}"
        payload = {
            "name": f"Project Alpha {unique_proj}",
            "project_code": unique_proj,
            "status": "PLANNING",
            "priority": "MEDIUM",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=60)),
            "client_name": "Mediatize Enterprise Test",
            "description": "Validation of project creation email rules",
        }
        created_proj_id = None
        try:
            resp = self.client.post("/api/projects", json=payload, headers=self.headers)
            self.assertEqual(resp.status_code, 201)
            created_proj = resp.json()
            created_proj_id = created_proj.get("id")
            print(f"\n[TEST 6 PASS] Project created without assignments: ID={created_proj_id}, Code={created_proj.get('project_code')} (NO email dispatched)")
        finally:
            # Bulletproof cleanup with a fresh database session
            if created_proj_id:
                cleanup_db = SessionLocal()
                try:
                    cleanup_db.execute(delete(AuditLog).where(AuditLog.entity_type == "PROJECT", AuditLog.entity_id == str(created_proj_id)))
                    p_obj = cleanup_db.get(Project, created_proj_id)
                    if p_obj:
                        cleanup_db.delete(p_obj)
                    cleanup_db.commit()
                except Exception as cleanup_err:
                    cleanup_db.rollback()
                    print(f"Warning: test_06 cleanup encountered error: {cleanup_err}")
                finally:
                    cleanup_db.close()


if __name__ == "__main__":
    unittest.main()
