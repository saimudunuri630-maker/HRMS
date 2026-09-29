import unittest
from datetime import date, datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import jwt

from app.main import app
from app.core.database import SessionLocal
from app.authentication_service.models import User, UserSession
from app.employee_service.models import Employee, EmploymentStatus
from app.project_service.models import (
    Project,
    ProjectRole,
    ProjectEmployeeAssignment,
    ProjectStatus,
    AssignmentStatus,
)
from app.work_report_service.models import WorkReport, ReportStatus
from app.core.config import settings


class TestWorkReportProjectValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

        # 1. Authoritative HR user
        cls.hr_user = cls.db.query(User).filter(User.role == "hr").first()
        assert cls.hr_user is not None, "HR user must exist in database"

        # 2. Find two active employees
        active_emps = (
            cls.db.query(Employee)
            .filter(
                Employee.user_id != cls.hr_user.id,
                Employee.employment_status == EmploymentStatus.ACTIVE,
            )
            .order_by(Employee.id.asc())
            .all()
        )
        assert len(active_emps) >= 2, "At least two active employees needed for testing"

        cls.emp_a = active_emps[0]
        cls.emp_a_user = cls.db.query(User).filter(User.id == cls.emp_a.user_id).first()

        cls.emp_b = active_emps[1]
        cls.emp_b_user = cls.db.query(User).filter(User.id == cls.emp_b.user_id).first()

        # 3. Create tokens
        cls.hr_token = cls._create_token(cls.hr_user)
        cls.emp_a_token = cls._create_token(cls.emp_a_user)
        cls.emp_b_token = cls._create_token(cls.emp_b_user)

        cls.hr_headers = {"Authorization": f"Bearer {cls.hr_token}"}
        cls.emp_a_headers = {"Authorization": f"Bearer {cls.emp_a_token}"}
        cls.emp_b_headers = {"Authorization": f"Bearer {cls.emp_b_token}"}

        # 4. Set up an active project assigned only to emp_a
        today = date.today()
        ts = int(datetime.now().timestamp())
        cls.assigned_project = Project(
            project_code=f"PRJ-VAL-A-{ts}",
            project_name="Assigned Test Project Alpha",
            description="Testing assigned project flow",
            status=ProjectStatus.ACTIVE,
            priority="HIGH",
            start_date=today - timedelta(days=10),
            expected_end_date=today + timedelta(days=60),
            created_by=cls.hr_user.id,
        )
        cls.db.add(cls.assigned_project)
        cls.db.commit()
        cls.db.refresh(cls.assigned_project)

        cls.role_a = ProjectRole(
            project_id=cls.assigned_project.id,
            role_name="Backend Developer",
            required_count=2,
            description="Backend dev",
        )
        cls.db.add(cls.role_a)
        cls.db.commit()
        cls.db.refresh(cls.role_a)

        cls.assignment_a = ProjectEmployeeAssignment(
            project_id=cls.assigned_project.id,
            employee_id=cls.emp_a.id,
            project_role_id=cls.role_a.id,
            start_date=today - timedelta(days=10),
            status=AssignmentStatus.ACTIVE,
            assigned_by=cls.hr_user.id,
        )
        cls.db.add(cls.assignment_a)
        cls.db.commit()

        # 5. Set up an unassigned project (neither emp_a nor emp_b assigned)
        cls.unassigned_project = Project(
            project_code=f"PRJ-VAL-U-{ts}",
            project_name="Unassigned Test Project",
            description="Testing unassigned project flow",
            status=ProjectStatus.ACTIVE,
            priority="LOW",
            start_date=today - timedelta(days=5),
            expected_end_date=today + timedelta(days=30),
            created_by=cls.hr_user.id,
        )
        cls.db.add(cls.unassigned_project)
        cls.db.commit()
        cls.db.refresh(cls.unassigned_project)

        # 6. Set up a completed project assigned to emp_a
        cls.completed_project = Project(
            project_code=f"PRJ-VAL-C-{ts}",
            project_name="Completed Test Project",
            description="Testing completed project validation",
            status=ProjectStatus.COMPLETED,
            priority="MEDIUM",
            start_date=today - timedelta(days=90),
            expected_end_date=today - timedelta(days=10),
            actual_end_date=today - timedelta(days=10),
            created_by=cls.hr_user.id,
        )
        cls.db.add(cls.completed_project)
        cls.db.commit()
        cls.db.refresh(cls.completed_project)

        cls.role_c = ProjectRole(
            project_id=cls.completed_project.id,
            role_name="Consultant",
            required_count=1,
            description="Consultant",
        )
        cls.db.add(cls.role_c)
        cls.db.commit()
        cls.db.refresh(cls.role_c)

        cls.assignment_c = ProjectEmployeeAssignment(
            project_id=cls.completed_project.id,
            employee_id=cls.emp_a.id,
            project_role_id=cls.role_c.id,
            start_date=today - timedelta(days=90),
            status=AssignmentStatus.ACTIVE,
            assigned_by=cls.hr_user.id,
        )
        cls.db.add(cls.assignment_c)
        cls.db.commit()

        # 7. Create a historical work report on completed_project for emp_a
        past_date = today - timedelta(days=15)
        cls.historical_report = WorkReport(
            employee_id=cls.emp_a.id,
            project_id=cls.completed_project.id,
            report_date=past_date,
            work_summary="Historical milestone completion before project closed.",
            hours_worked=8.0,
            status=ReportStatus.SUBMITTED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        cls.db.add(cls.historical_report)
        cls.db.commit()
        cls.db.refresh(cls.historical_report)

    @classmethod
    def _create_token(cls, user: User) -> str:
        now = datetime.now(timezone.utc)
        session = UserSession(
            user_id=user.id,
            session_id=f"val_session_{user.id}_{int(now.timestamp())}_{user.role}",
            expires_at=now + timedelta(hours=3),
            is_active=True,
        )
        cls.db.add(session)
        cls.db.commit()

        token = jwt.encode(
            {
                "sub": str(user.id),
                "role": user.role,
                "session_id": session.session_id,
                "exp": int((now + timedelta(hours=3)).timestamp()),
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        return token

    @classmethod
    def tearDownClass(cls):
        # Clean up created records if desired
        cls.db.close()

    # =========================================================================
    # TESTS
    # =========================================================================

    def test_01_employee_has_assigned_active_project(self):
        """TEST 1: Employee has assigned active project -> Project appears in allowed project list."""
        res = self.client.get("/api/projects/me", headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIsInstance(data, list)
        project_ids = [p["id"] for p in data]
        self.assertIn(self.assigned_project.id, project_ids)

        assigned_item = next(p for p in data if p["id"] == self.assigned_project.id)
        self.assertEqual(assigned_item["project_name"], "Assigned Test Project Alpha")
        self.assertEqual(assigned_item["status"], "ACTIVE")
        self.assertEqual(assigned_item["my_role"], "Backend Developer")

    def test_02_employee_has_no_project_assignment(self):
        """TEST 2: Employee has no project assignment -> Project does not appear in allowed list."""
        res = self.client.get("/api/projects/me", headers=self.emp_b_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        project_ids = [p["id"] for p in data]
        # emp_b is not assigned to assigned_project or unassigned_project
        self.assertNotIn(self.assigned_project.id, project_ids)
        self.assertNotIn(self.unassigned_project.id, project_ids)

    def test_03_employee_attempts_report_for_assigned_project(self):
        """TEST 3: Employee attempts report for assigned project -> Success."""
        today = date.today().isoformat()
        payload = {
            "project_id": self.assigned_project.id,
            "report_date": today,
            "work_summary": "Implemented API endpoint validation and tested response formats.",
            "tasks_completed": "Verified project status rules and role enforcement.",
            "hours_worked": 8.0,
            "status": "DRAFT",
        }
        res = self.client.post("/api/work-reports", json=payload, headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 201, res.text)
        data = res.json()
        self.assertEqual(data["employee_id"], self.emp_a.id)
        self.assertEqual(data["project_id"], self.assigned_project.id)
        self.assertEqual(data["project_name"], self.assigned_project.project_name)

    def test_04_employee_attempts_report_for_unassigned_project(self):
        """TEST 4: Employee attempts report for unassigned project -> Rejected (403)."""
        today = date.today().isoformat()
        payload = {
            "project_id": self.unassigned_project.id,
            "report_date": today,
            "work_summary": "Attempting to submit for a project I am not assigned to.",
            "hours_worked": 4.0,
            "status": "DRAFT",
        }
        res = self.client.post("/api/work-reports", json=payload, headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 403, res.text)
        data = res.json()
        self.assertIn("not assigned", data.get("detail", "").lower())

    def test_05_employee_attempts_report_for_another_project_id(self):
        """TEST 5: Employee attempts report for another project's ID (assigned only to emp_a, submitted by emp_b) -> Rejected (403)."""
        today = date.today().isoformat()
        payload = {
            "project_id": self.assigned_project.id,
            "report_date": today,
            "work_summary": "Emp B attempting to report on Emp A's project.",
            "hours_worked": 6.0,
            "status": "DRAFT",
        }
        res = self.client.post("/api/work-reports", json=payload, headers=self.emp_b_headers)
        self.assertEqual(res.status_code, 403, res.text)
        data = res.json()
        self.assertIn("not assigned", data.get("detail", "").lower())

    def test_06_completed_project_rejected_for_new_report(self):
        """TEST 6: Completed project -> New report rejected (400)."""
        today = date.today().isoformat()
        payload = {
            "project_id": self.completed_project.id,
            "report_date": today,
            "work_summary": "Attempting to create report for a project that is already completed.",
            "hours_worked": 8.0,
            "status": "DRAFT",
        }
        res = self.client.post("/api/work-reports", json=payload, headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 400, res.text)
        data = res.json()
        self.assertIn("active", data.get("detail", "").lower())

    def test_07_historical_report_for_completed_project_accessible(self):
        """TEST 7: Historical report for completed project -> Still accessible."""
        res = self.client.get(f"/api/work-reports/me/{self.historical_report.id}", headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["id"], self.historical_report.id)
        self.assertEqual(data["project_id"], self.completed_project.id)
        self.assertEqual(data["project_name"], self.completed_project.project_name)

        # Also verify it appears in list
        list_res = self.client.get("/api/work-reports/me", headers=self.emp_a_headers)
        self.assertEqual(list_res.status_code, 200, list_res.text)
        items = list_res.json().get("items", [])
        self.assertTrue(any(r["id"] == self.historical_report.id for r in items))

    def test_08_unauthenticated_request_rejected(self):
        """TEST 8: Unauthenticated request -> 401."""
        today = date.today().isoformat()
        payload = {
            "project_id": self.assigned_project.id,
            "report_date": today,
            "work_summary": "No auth header provided.",
            "hours_worked": 8.0,
        }
        res = self.client.post("/api/work-reports", json=payload)
        self.assertEqual(res.status_code, 401, res.text)

        # GET /api/projects/me without auth
        res_projs = self.client.get("/api/projects/me")
        self.assertEqual(res_projs.status_code, 401, res_projs.text)

    def test_09_duplicate_or_invalid_project_id(self):
        """TEST 9: Non-existent project ID -> 404, and duplicate report on same date -> 409."""
        today = date.today().isoformat()
        # Invalid / non-existent project ID
        invalid_payload = {
            "project_id": 99999999,
            "report_date": today,
            "work_summary": "Report for non-existent project.",
            "hours_worked": 8.0,
        }
        res_404 = self.client.post("/api/work-reports", json=invalid_payload, headers=self.emp_a_headers)
        self.assertEqual(res_404.status_code, 404, res_404.text)

        # Duplicate check on same date and assigned project
        dup_payload = {
            "project_id": self.assigned_project.id,
            "report_date": today,
            "work_summary": "Second report on the same project and date should fail with conflict.",
            "hours_worked": 4.0,
        }
        # Note: test_03 already created a report for assigned_project on `today`
        res_409 = self.client.post("/api/work-reports", json=dup_payload, headers=self.emp_a_headers)
        self.assertEqual(res_409.status_code, 409, res_409.text)
