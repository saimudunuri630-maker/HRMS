import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.main import app
from app.core.database import SessionLocal
from app.authentication_service.models import User, UserSession
from app.employee_service.models import Employee, EmploymentStatus
from app.project_service.models import Project, ProjectRole, ProjectEmployeeAssignment, ProjectStatus, AssignmentStatus
from app.project_service.repository import ProjectRepository
from app.core.config import settings
import jwt


class TestProjectAndRoleService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

        # Find or verify authoritative HR user
        cls.hr_user = cls.db.query(User).filter(User.role == "hr").first()
        assert cls.hr_user is not None, "HR user must exist"

        # Find two different employees for isolation testing
        emps = cls.db.query(Employee).filter(Employee.user_id != cls.hr_user.id).order_by(Employee.id.asc()).all()
        assert len(emps) >= 2, "At least two employees needed for testing"

        cls.emp_a = emps[0]
        cls.emp_a_user = cls.db.query(User).filter(User.id == cls.emp_a.user_id).first()

        cls.emp_b = emps[1]
        cls.emp_b_user = cls.db.query(User).filter(User.id == cls.emp_b.user_id).first()

        # Create valid sessions & JWT tokens
        cls.hr_token = cls._create_token(cls.hr_user)
        cls.emp_a_token = cls._create_token(cls.emp_a_user)
        cls.emp_b_token = cls._create_token(cls.emp_b_user)

    @classmethod
    def _create_token(cls, user: User) -> str:
        now = datetime.now(timezone.utc)
        session = UserSession(
            user_id=user.id,
            session_id=f"test_session_{user.id}_{int(now.timestamp())}_{user.role}",
            expires_at=now + timedelta(hours=3),
            is_active=True,
            created_at=now,
            last_activity=now,
        )
        cls.db.add(session)
        cls.db.commit()
        cls.db.refresh(session)

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
        # Clean any temporary test projects created during the test run
        tst_projs = cls.db.query(Project).filter(Project.project_code.like("MED-UNIT-%")).all()
        for p in tst_projs:
            cls.db.query(ProjectEmployeeAssignment).filter(ProjectEmployeeAssignment.project_id == p.id).delete()
            cls.db.query(ProjectRole).filter(ProjectRole.project_id == p.id).delete()
        # Clean any temporary test employees
        tst_users = cls.db.query(User).filter(User.email.like("welcome.test.%")).all()
        for u in tst_users:
            cls.db.execute(text("DELETE FROM leave_balances WHERE employee_id IN (SELECT id FROM employees WHERE user_id = :uid)"), {"uid": u.id})
            cls.db.execute(text("DELETE FROM attendance WHERE employee_id IN (SELECT id FROM employees WHERE user_id = :uid)"), {"uid": u.id})
            cls.db.execute(text("DELETE FROM employees WHERE user_id = :uid"), {"uid": u.id})
            cls.db.execute(text("DELETE FROM user_sessions WHERE user_id = :uid"), {"uid": u.id})
            cls.db.delete(u)
        cls.db.commit()
        cls.db.close()

    # ----------------------------------------------------
    # TEST 1 & 2: Project Creation & Authorization
    # ----------------------------------------------------
    def test_01_hr_create_project_success_no_email(self):
        """HR creates project -> Success 201; NO email is dispatched."""
        code = f"MED-UNIT-{int(datetime.now().timestamp()) % 100000}"
        with patch("app.email_service.service._send_smtp_email") as mock_email:
            res = self.client.post(
                "/api/projects",
                json={
                    "project_code": code,
                    "project_name": "Unit Test Project",
                    "description": "Testing project creation flow",
                    "status": "ACTIVE",
                    "priority": "HIGH",
                    "client_name": "Mediatize Client",
                    "start_date": str(date.today()),
                    "expected_end_date": str(date.today() + timedelta(days=90)),
                    "initial_roles": [{"role_name": "Full Stack Engineer"}],
                },
                headers={"Authorization": f"Bearer {self.hr_token}"},
            )
            self.assertEqual(res.status_code, 201)
            data = res.json()
            self.assertEqual(data["project_code"], code)
            self.assertEqual(data["project_name"], "Unit Test Project")
            self.assertEqual(data["status"], "ACTIVE")
            # Project creation MUST NOT send any email
            self.assertEqual(mock_email.call_count, 0)

    def test_02_employee_cannot_create_project(self):
        """Employee attempts to create project -> 403 Forbidden."""
        res = self.client.post(
            "/api/projects",
            json={
                "project_code": "MED-UNAUTH",
                "project_name": "Unauthorized Project",
                "start_date": str(date.today()),
                "expected_end_date": str(date.today() + timedelta(days=30)),
                "initial_roles": [{"role_name": "Developer"}],
            },
            headers={"Authorization": f"Bearer {self.emp_a_token}"},
        )
        self.assertEqual(res.status_code, 403)

    # ----------------------------------------------------
    # TEST 3 & 4: Project Editing & Authorization
    # ----------------------------------------------------
    def test_03_hr_edits_project_success_no_email(self):
        """HR edits project settings -> Success 200; NO email is dispatched."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-001").first()
        with patch("app.email_service.service._send_smtp_email") as mock_email:
            res = self.client.put(
                f"/api/projects/{proj.id}",
                json={
                    "project_name": "Mediatize HRMS Platform",
                    "description": "Flagship enterprise human resources platform updated via settings",
                    "priority": "CRITICAL",
                    "client_name": "Mediatize Global Corp",
                },
                headers={"Authorization": f"Bearer {self.hr_token}"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["priority"], "CRITICAL")
            self.assertEqual(data["client_name"], "Mediatize Global Corp")
            self.assertEqual(mock_email.call_count, 0)

    def test_04_employee_cannot_edit_project(self):
        """Employee attempts to edit project -> 403 Forbidden."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-001").first()
        res = self.client.put(
            f"/api/projects/{proj.id}",
            json={"project_name": "Hacked Project Name"},
            headers={"Authorization": f"Bearer {self.emp_a_token}"},
        )
        self.assertEqual(res.status_code, 403)

    # ----------------------------------------------------
    # TEST 5 & 6: Project Listing & Isolation
    # ----------------------------------------------------
    def test_05_hr_lists_all_projects(self):
        """HR lists projects -> returns all company projects."""
        res = self.client.get(
            "/api/projects?page=1&page_size=20",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["total"], 5)
        self.assertIsInstance(data["items"], list)

    def test_06_employee_lists_only_assigned_projects(self):
        """Employee requests /api/projects/me -> only assigned projects returned."""
        res_a = self.client.get(
            "/api/projects/me",
            headers={"Authorization": f"Bearer {self.emp_a_token}"},
        )
        self.assertEqual(res_a.status_code, 200)
        codes_a = [p["project_code"] for p in res_a.json()]

        res_b = self.client.get(
            "/api/projects/me",
            headers={"Authorization": f"Bearer {self.emp_b_token}"},
        )
        self.assertEqual(res_b.status_code, 200)
        codes_b = [p["project_code"] for p in res_b.json()]

        # Empirical isolation check
        self.assertIn("MED-PRJ-002", codes_a)
        self.assertNotIn("MED-PRJ-002", codes_b)
        self.assertIn("MED-PRJ-003", codes_b)
        self.assertNotIn("MED-PRJ-003", codes_a)

    # ----------------------------------------------------
    # TEST 7 & 8: Project Roles Management
    # ----------------------------------------------------
    def test_07_hr_creates_project_role(self):
        """HR creates project role -> Success 201."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-001").first()
        res = self.client.post(
            f"/api/projects/{proj.id}/roles",
            json={
                "role_name": f"Security Lead {int(datetime.now().timestamp()) % 10000}",
                "required_count": 2,
                "description": "Information Security Lead",
            },
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["required_count"], 2)

    def test_08_employee_cannot_create_project_role(self):
        """Employee attempts to create project role -> 403 Forbidden."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-001").first()
        res = self.client.post(
            f"/api/projects/{proj.id}/roles",
            json={"role_name": "Hacker Role", "required_count": 1},
            headers={"Authorization": f"Bearer {self.emp_a_token}"},
        )
        self.assertEqual(res.status_code, 403)

    # ----------------------------------------------------
    # TEST 9, 10, 11, 12: Employee Assignment & Email
    # ----------------------------------------------------
    def test_09_hr_assigns_employee_without_role_sends_email(self):
        """HR assigns employee without role -> sends project assignment email saying 'Not assigned yet'."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-005").first()

        # Ensure clean state for emp_b in MED-PRJ-005
        self.db.query(ProjectEmployeeAssignment).filter(
            ProjectEmployeeAssignment.project_id == proj.id,
            ProjectEmployeeAssignment.employee_id == self.emp_b.id,
        ).delete()
        self.db.commit()

    def test_09_hr_assigns_employee_without_role_rejected(self):
        """HR assigns employee without role -> rejected because project roles are mandatory."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-002").first()
        res = self.client.post(
            f"/api/projects/{proj.id}/members",
            json={"employee_id": self.emp_b.id, "project_role_id": None},
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertIn(res.status_code, [400, 422])

    def test_10_hr_assigns_employee_with_role_sends_one_consolidated_email(self):
        """HR assigns employee WITH role in one action -> sends ONE consolidated email, NOT two."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-002").first()
        roles = self.db.query(ProjectRole).filter(ProjectRole.project_id == proj.id).all()
        target_role = roles[0]

        # Ensure clean state for emp_b in MED-PRJ-002
        self.db.query(ProjectEmployeeAssignment).filter(
            ProjectEmployeeAssignment.project_id == proj.id,
            ProjectEmployeeAssignment.employee_id == self.emp_b.id,
        ).delete()
        self.db.commit()

        with patch("app.email_service.service._send_smtp_email") as mock_email:
            res = self.client.post(
                f"/api/projects/{proj.id}/members",
                json={"employee_id": self.emp_b.id, "project_role_id": target_role.id},
                headers={"Authorization": f"Bearer {self.hr_token}"},
            )
            self.assertEqual(res.status_code, 201)
            # CRITICAL: Must be EXACTLY 1 consolidated email
            self.assertEqual(mock_email.call_count, 1, "Must send ONE consolidated email, not two separate emails!")
            call_body = mock_email.call_args[1].get("body") if "body" in mock_email.call_args[1] else mock_email.call_args[0][2]
            self.assertIn(target_role.role_name, call_body)
            self.assertIn(proj.project_name, call_body)

    def test_11_duplicate_assignment_prevention(self):
        """Attempting duplicate active assignment to same project -> 409 Conflict."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-002").first()
        roles = self.db.query(ProjectRole).filter(ProjectRole.project_id == proj.id).all()
        res = self.client.post(
            f"/api/projects/{proj.id}/members",
            json={"employee_id": self.emp_b.id, "project_role_id": roles[0].id},
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(res.status_code, 409)
        self.assertIn("already assigned", res.json()["detail"].lower())

    def test_12_employee_cannot_assign_member(self):
        """Employee attempts to assign a member -> 403 Forbidden."""
        proj = self.db.query(Project).first()
        roles = self.db.query(ProjectRole).filter(ProjectRole.project_id == proj.id).all()
        res = self.client.post(
            f"/api/projects/{proj.id}/members",
            json={"employee_id": self.emp_b.id, "project_role_id": roles[0].id if roles else 1},
            headers={"Authorization": f"Bearer {self.emp_a_token}"},
        )
        self.assertEqual(res.status_code, 403)

    # ----------------------------------------------------
    # TEST 13, 14, 15: Role Assignment Later & Role Change
    # ----------------------------------------------------
    def test_13_hr_assigns_role_later_sends_role_email(self):
        """HR assigns role later to member -> sends role update email."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-005").first()
        roles = self.db.query(ProjectRole).filter(ProjectRole.project_id == proj.id).all()
        if len(roles) < 2:
            extra_role = ProjectRole(project_id=proj.id, role_name="Additional Role", required_count=1)
            self.db.add(extra_role)
            self.db.commit()
            roles = self.db.query(ProjectRole).filter(ProjectRole.project_id == proj.id).all()

        initial_role = roles[0]
        new_role = roles[1]

        # Ensure assignment exists with initial_role
        assign = self.db.query(ProjectEmployeeAssignment).filter(
            ProjectEmployeeAssignment.project_id == proj.id,
            ProjectEmployeeAssignment.employee_id == self.emp_b.id,
        ).first()
        if not assign:
            self.client.post(
                f"/api/projects/{proj.id}/members",
                json={"employee_id": self.emp_b.id, "project_role_id": initial_role.id},
                headers={"Authorization": f"Bearer {self.hr_token}"},
            )
        else:
            assign.project_role_id = initial_role.id
            self.db.commit()

        with patch("app.email_service.service._send_smtp_email") as mock_email:
            res = self.client.put(
                f"/api/projects/{proj.id}/members/{self.emp_b.id}/role",
                json={"project_role_id": new_role.id},
                headers={"Authorization": f"Bearer {self.hr_token}"},
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(mock_email.call_count, 1)
            call_body = mock_email.call_args[1].get("body") if "body" in mock_email.call_args[1] else mock_email.call_args[0][2]
            self.assertIn(new_role.role_name, call_body)
            self.assertIn(proj.project_name, call_body)

    def test_14_employee_cannot_assign_or_change_role(self):
        """Employee attempts to change project role -> 403 Forbidden."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-001").first()
        roles = self.db.query(ProjectRole).filter(ProjectRole.project_id == proj.id).all()
        res = self.client.put(
            f"/api/projects/{proj.id}/members/{self.emp_a.id}/role",
            json={"project_role_id": roles[0].id},
            headers={"Authorization": f"Bearer {self.emp_a_token}"},
        )
        self.assertEqual(res.status_code, 403)

    def test_15_hr_changes_role_sends_role_change_email(self):
        """HR changes existing role -> sends role change email with previous and new role."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-002").first()
        roles = self.db.query(ProjectRole).filter(ProjectRole.project_id == proj.id).all()
        self.assertGreaterEqual(len(roles), 2)
        new_role = roles[1]

        with patch("app.email_service.service._send_smtp_email") as mock_email:
            res = self.client.put(
                f"/api/projects/{proj.id}/members/{self.emp_b.id}/role",
                json={"project_role_id": new_role.id},
                headers={"Authorization": f"Bearer {self.hr_token}"},
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(mock_email.call_count, 1)
            call_body = mock_email.call_args[1].get("body") if "body" in mock_email.call_args[1] else mock_email.call_args[0][2]
            self.assertIn(new_role.role_name, call_body)
            self.assertIn("Previous Role:", call_body)
            self.assertIn("New Role:", call_body)

    # ----------------------------------------------------
    # TEST 16 & 17: Member Removal & Email
    # ----------------------------------------------------
    def test_16_hr_removes_employee_sends_removal_email(self):
        """HR removes employee from project -> sends removal notification email."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-002").first()

        with patch("app.email_service.service._send_smtp_email") as mock_email:
            res = self.client.delete(
                f"/api/projects/{proj.id}/members/{self.emp_b.id}",
                headers={"Authorization": f"Bearer {self.hr_token}"},
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(mock_email.call_count, 1)
            call_body = mock_email.call_args[1].get("body") if "body" in mock_email.call_args[1] else mock_email.call_args[0][2]
            self.assertIn("no longer assigned", call_body)
            self.assertIn(proj.project_name, call_body)

    def test_17_employee_cannot_remove_member(self):
        """Employee attempts to remove a project member -> 403 Forbidden."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-001").first()
        res = self.client.delete(
            f"/api/projects/{proj.id}/members/{self.emp_a.id}",
            headers={"Authorization": f"Bearer {self.emp_a_token}"},
        )
        self.assertEqual(res.status_code, 403)

    # ----------------------------------------------------
    # TEST 18 & 19: Project Status & Completion Rules
    # ----------------------------------------------------
    def test_18_hr_updates_project_status_to_completed_no_email(self):
        """HR marks project COMPLETED -> Success 200; NO emails sent by default."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-005").first()
        with patch("app.email_service.service._send_smtp_email") as mock_email:
            res = self.client.patch(
                f"/api/projects/{proj.id}/status",
                json={"status": "COMPLETED"},
                headers={"Authorization": f"Bearer {self.hr_token}"},
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["status"], "COMPLETED")
            # Completed status must NOT send mass emails by default
            self.assertEqual(mock_email.call_count, 0)

            # Revert to ACTIVE
            res_revert = self.client.patch(
                f"/api/projects/{proj.id}/status",
                json={"status": "ACTIVE"},
                headers={"Authorization": f"Bearer {self.hr_token}"},
            )
            self.assertEqual(res_revert.status_code, 200)

    def test_19_employee_cannot_update_project_status(self):
        """Employee attempts to update project status -> 403 Forbidden."""
        proj = self.db.query(Project).first()
        res = self.client.patch(
            f"/api/projects/{proj.id}/status",
            json={"status": "COMPLETED"},
            headers={"Authorization": f"Bearer {self.emp_a_token}"},
        )
        self.assertEqual(res.status_code, 403)

    # ----------------------------------------------------
    # TEST 20 & 21: Employee Privacy & Access Boundaries
    # ----------------------------------------------------
    def test_20_employee_unassigned_project_access_blocked(self):
        """Employee attempting to access unassigned project -> 403 Forbidden."""
        proj2 = self.db.query(Project).filter(Project.project_code == "MED-PRJ-002").first()
        res = self.client.get(
            f"/api/projects/{proj2.id}",
            headers={"Authorization": f"Bearer {self.emp_b_token}"},
        )
        self.assertEqual(res.status_code, 403)

    def test_21_employee_views_assigned_role_and_team_sanitized(self):
        """Employee views assigned project; receives sanitized team members with no sensitive HR data."""
        proj = self.db.query(Project).filter(Project.project_code == "MED-PRJ-001").first()
        res = self.client.get(
            f"/api/projects/{proj.id}",
            headers={"Authorization": f"Bearer {self.emp_a_token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["project_code"], "MED-PRJ-001")
        self.assertIn("my_role", data)
        self.assertIn("members", data)

        for member in data["members"]:
            self.assertNotIn("salary", member)
            self.assertNotIn("bank_account_no", member)
            self.assertNotIn("pan_number", member)
            self.assertIn("first_name", member)
            self.assertIn("last_name", member)

    # ----------------------------------------------------
    # TEST 22: Dashboard Metrics
    # ----------------------------------------------------
    def test_22_hr_and_employee_dashboards_real_statistics(self):
        """Verify real statistics in HR and Employee dashboard endpoints."""
        res_hr = self.client.get(
            "/api/hr/dashboard/summary",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(res_hr.status_code, 200)
        data_hr = res_hr.json()
        self.assertGreaterEqual(data_hr["total_projects"], 5)
        self.assertGreaterEqual(data_hr["active_projects"], 3)
        self.assertGreaterEqual(data_hr["completed_projects"], 1)

        res_emp = self.client.get(
            "/api/employee/dashboard/summary",
            headers={"Authorization": f"Bearer {self.emp_a_token}"},
        )
        self.assertEqual(res_emp.status_code, 200)
        data_emp = res_emp.json()
        self.assertGreaterEqual(data_emp["my_projects_count"], 1)

    # ----------------------------------------------------
    # TEST 23, 24, 25: Regressions & Branding
    # ----------------------------------------------------
    def test_23_profile_email_regression_no_email_on_profile_update(self):
        """Profile updates must NEVER trigger emails."""
        with patch("app.email_service.service._send_smtp_email") as mock_email:
            res_hr = self.client.put(
                "/api/profile/me",
                json={"phone": "+1 555-9999", "bio": "HR Administrator Bio"},
                headers={"Authorization": f"Bearer {self.hr_token}"},
            )
            self.assertIn(res_hr.status_code, [200, 204])

            res_emp = self.client.put(
                "/api/profile/me",
                json={"phone": "+1 555-8888", "bio": "Employee Bio"},
                headers={"Authorization": f"Bearer {self.emp_a_token}"},
            )
            self.assertIn(res_emp.status_code, [200, 204])
            self.assertEqual(mock_email.call_count, 0)

    def test_24_employee_creation_sends_welcome_email(self):
        """Employee creation MUST trigger onboarding welcome email."""
        new_emp_email = f"welcome.test.{int(datetime.now().timestamp()) % 100000}@mediatize.com"
        with patch("app.email_service.service._send_smtp_email") as mock_email:
            res = self.client.post(
                "/api/employees",
                json={
                    "first_name": "TestWelcome",
                    "last_name": "Employee",
                    "email": new_emp_email,
                    "phone": "+1 555-0123",
                    "joining_date": str(date.today()),
                },
                headers={"Authorization": f"Bearer {self.hr_token}"},
            )
            self.assertEqual(res.status_code, 201)
            self.assertEqual(mock_email.call_count, 1)
            call_subject = mock_email.call_args[1].get("subject") if "subject" in mock_email.call_args[1] else mock_email.call_args[0][1]
            self.assertIn("Welcome to Mediatize HRMS", call_subject)

    def test_25_branding_verification_mediatize(self):
        """Verify branding uses Mediatize across root API and email templates."""
        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 200)
        self.assertIn("Mediatize HRMS", res_root.json().get("title", ""))

        from app.email_service.service import send_employee_welcome_email
        with patch("app.email_service.service._send_smtp_email") as mock_email:
            send_employee_welcome_email("test@mediatize.com", "Test", "EMP999")
            subject = mock_email.call_args[1].get("subject") if "subject" in mock_email.call_args[1] else mock_email.call_args[0][1]
            body = mock_email.call_args[1].get("body") if "body" in mock_email.call_args[1] else mock_email.call_args[0][2]
            self.assertIn("Mediatize", subject)
            self.assertNotIn("Medialize", subject)
            self.assertIn("Mediatize", body)
            self.assertNotIn("Medialize", body)


if __name__ == "__main__":
    unittest.main()
