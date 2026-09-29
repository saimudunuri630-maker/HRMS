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
from app.project_service.models import (
    Project,
    ProjectRole,
    ProjectEmployeeAssignment,
    ProjectStatus,
    AssignmentStatus,
)
from app.core.config import settings
import jwt


class TestProjectEditAndTeamRoles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

        # Find authoritative HR user
        cls.hr_user = cls.db.query(User).filter(User.role == "hr").first()
        assert cls.hr_user is not None, "HR user must exist"

        # Find 3 employees to act as John, Priya, and Rahul
        employees = (
            cls.db.query(Employee)
            .filter(Employee.employment_status == EmploymentStatus.ACTIVE, Employee.user_id != cls.hr_user.id)
            .order_by(Employee.id.asc())
            .all()
        )
        assert len(employees) >= 3, "At least 3 active employees required for testing"

        cls.emp_john = employees[0]
        cls.emp_priya = employees[1]
        cls.emp_rahul = employees[2]

        cls.john_user = cls.db.query(User).filter_by(id=cls.emp_john.user_id).first()
        cls.priya_user = cls.db.query(User).filter_by(id=cls.emp_priya.user_id).first()
        cls.rahul_user = cls.db.query(User).filter_by(id=cls.emp_rahul.user_id).first()

        cls.hr_token = cls._create_token(cls.hr_user)
        cls.john_token = cls._create_token(cls.john_user)
        cls.rahul_token = cls._create_token(cls.rahul_user)

        # Create isolated test projects: Project A and Project B
        today = date.today()
        # Clean any old test records
        cls.db.execute(text("DELETE FROM projects WHERE project_code IN ('TEST-PRJ-A', 'TEST-PRJ-B')"))
        cls.db.commit()

        # Project A
        cls.proj_a = Project(
            project_code="TEST-PRJ-A",
            project_name="Project Alpha Platform",
            description="Alpha Enterprise Platform",
            status=ProjectStatus.ACTIVE,
            priority="HIGH",
            client_name="Mediatize Alpha",
            start_date=today,
            expected_end_date=today + timedelta(days=90),
            created_by=cls.hr_user.id,
        )
        cls.db.add(cls.proj_a)

        # Project B
        cls.proj_b = Project(
            project_code="TEST-PRJ-B",
            project_name="Project Beta Mobile",
            description="Beta Mobile Initiatives",
            status=ProjectStatus.ACTIVE,
            priority="MEDIUM",
            client_name="Mediatize Beta",
            start_date=today,
            expected_end_date=today + timedelta(days=60),
            created_by=cls.hr_user.id,
        )
        cls.db.add(cls.proj_b)
        cls.db.commit()
        cls.db.refresh(cls.proj_a)
        cls.db.refresh(cls.proj_b)

        # Roles for Project A
        cls.role_a_backend = ProjectRole(
            project_id=cls.proj_a.id,
            role_name="Backend Developer",
            required_count=2,
            description="Backend Node/Python Services",
        )
        cls.role_a_frontend = ProjectRole(
            project_id=cls.proj_a.id,
            role_name="Frontend Developer",
            required_count=2,
            description="Frontend React UI",
        )
        cls.role_a_qa = ProjectRole(
            project_id=cls.proj_a.id,
            role_name="QA Engineer",
            required_count=1,
            description="Quality Assurance",
        )
        cls.db.add_all([cls.role_a_backend, cls.role_a_frontend, cls.role_a_qa])

        # Roles for Project B
        cls.role_b_mobile = ProjectRole(
            project_id=cls.proj_b.id,
            role_name="Mobile Developer",
            required_count=2,
            description="iOS/Android",
        )
        cls.db.add(cls.role_b_mobile)
        cls.db.commit()
        cls.db.refresh(cls.role_a_backend)
        cls.db.refresh(cls.role_a_frontend)
        cls.db.refresh(cls.role_a_qa)
        cls.db.refresh(cls.role_b_mobile)

        # Assign John and Priya to Project A
        cls.assign_john_a = ProjectEmployeeAssignment(
            project_id=cls.proj_a.id,
            employee_id=cls.emp_john.id,
            project_role_id=cls.role_a_backend.id,
            assigned_by=cls.hr_user.id,
            start_date=today,
            status=AssignmentStatus.ACTIVE,
        )
        cls.assign_priya_a = ProjectEmployeeAssignment(
            project_id=cls.proj_a.id,
            employee_id=cls.emp_priya.id,
            project_role_id=cls.role_a_frontend.id,
            assigned_by=cls.hr_user.id,
            start_date=today,
            status=AssignmentStatus.ACTIVE,
        )
        cls.db.add_all([cls.assign_john_a, cls.assign_priya_a])

        # Assign Rahul to Project B
        cls.assign_rahul_b = ProjectEmployeeAssignment(
            project_id=cls.proj_b.id,
            employee_id=cls.emp_rahul.id,
            project_role_id=cls.role_b_mobile.id,
            assigned_by=cls.hr_user.id,
            start_date=today,
            status=AssignmentStatus.ACTIVE,
        )
        cls.db.add(cls.assign_rahul_b)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        # Clean up test projects and assignments
        try:
            cls.db.execute(
                text("DELETE FROM projects WHERE project_code IN ('TEST-PRJ-A', 'TEST-PRJ-B')")
            )
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

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
                "exp": now + timedelta(hours=3),
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        return token

    # ========================================================
    # TEST 1: Open Project A -> Details (READ ONLY project information)
    # ========================================================
    def test_01_project_details_read_only(self):
        resp = self.client.get(
            f"/api/projects/{self.proj_a.id}",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["project_name"], "Project Alpha Platform")
        self.assertEqual(data["project_code"], "TEST-PRJ-A")
        self.assertEqual(data["status"], "ACTIVE")
        self.assertEqual(data["priority"], "HIGH")
        self.assertEqual(data["client_name"], "Mediatize Alpha")
        self.assertEqual(data["team_members_count"], 2)
        self.assertEqual(len(data["roles"]), 3)

    # ========================================================
    # TEST 2: Open Project A -> Edit loads details, team, and roles
    # ========================================================
    def test_02_project_edit_loads_all_sections(self):
        # 1. Project details
        p_resp = self.client.get(
            f"/api/projects/{self.proj_a.id}",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(p_resp.status_code, 200)
        p_data = p_resp.json()
        self.assertIn("project_name", p_data)

        # 2. Team members
        m_resp = self.client.get(
            f"/api/projects/{self.proj_a.id}/members",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(m_resp.status_code, 200)
        members = m_resp.json()
        self.assertEqual(len(members), 2)

        # 3. Project roles
        r_resp = self.client.get(
            f"/api/projects/{self.proj_a.id}/roles",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(r_resp.status_code, 200)
        roles = r_resp.json()
        self.assertEqual(len(roles), 3)

    # ========================================================
    # TEST 3: Project A has John and Priya, NOT Rahul
    # ========================================================
    def test_03_project_a_members_contain_john_priya_not_rahul(self):
        resp = self.client.get(
            f"/api/projects/{self.proj_a.id}/members",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(resp.status_code, 200)
        members = resp.json()
        emp_ids = [m["employee_id"] for m in members]
        self.assertIn(self.emp_john.id, emp_ids)
        self.assertIn(self.emp_priya.id, emp_ids)
        self.assertNotIn(self.emp_rahul.id, emp_ids)

    # ========================================================
    # TEST 4: Project A roles: Backend Developer, Frontend Developer, QA Engineer
    # ========================================================
    def test_04_project_a_roles_belong_to_project_a(self):
        resp = self.client.get(
            f"/api/projects/{self.proj_a.id}/roles",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(resp.status_code, 200)
        role_names = [r["role_name"] for r in resp.json()]
        self.assertIn("Backend Developer", role_names)
        self.assertIn("Frontend Developer", role_names)
        self.assertIn("QA Engineer", role_names)
        self.assertNotIn("Mobile Developer", role_names)  # from Project B!

    # ========================================================
    # TEST 5: Add Employee shows only employees not currently in Project A
    # ========================================================
    def test_05_available_employees_excludes_active_members(self):
        resp = self.client.get(
            f"/api/projects/{self.proj_a.id}/available-employees",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(resp.status_code, 200)
        avail = resp.json()
        avail_emp_ids = [e["id"] for e in avail]
        self.assertNotIn(self.emp_john.id, avail_emp_ids)
        self.assertNotIn(self.emp_priya.id, avail_emp_ids)

    # ========================================================
    # TEST 6: Employee belongs to Project B can still appear in Project A available list
    # ========================================================
    def test_06_employee_in_project_b_is_available_for_project_a(self):
        resp = self.client.get(
            f"/api/projects/{self.proj_a.id}/available-employees",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(resp.status_code, 200)
        avail = resp.json()
        avail_emp_ids = [e["id"] for e in avail]
        self.assertIn(self.emp_rahul.id, avail_emp_ids)

    # ========================================================
    # TEST 7 & TEST 8: Assign Rahul to Project A with Backend Developer role
    # ========================================================
    @patch("app.project_service.service.send_project_assignment_email")
    def test_07_and_08_assign_rahul_with_role(self, mock_email):
        resp = self.client.post(
            f"/api/projects/{self.proj_a.id}/members",
            json={
                "employee_id": self.emp_rahul.id,
                "project_role_id": self.role_a_backend.id,
                "start_date": str(date.today()),
            },
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["employee_id"], self.emp_rahul.id)
        self.assertEqual(data["project_role_name"], "Backend Developer")

        # Verify team count increased to 3
        p_resp = self.client.get(
            f"/api/projects/{self.proj_a.id}",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(p_resp.json()["team_members_count"], 3)

        # Verify email dispatched with role
        mock_email.assert_called_once()
        self.assertEqual(mock_email.call_args[1]["role_name"], "Backend Developer")

    # ========================================================
    # TEST 9: Create DevOps Engineer for Project A
    # ========================================================
    def test_09_create_devops_role_for_project_a(self):
        resp = self.client.post(
            f"/api/projects/{self.proj_a.id}/roles",
            json={
                "role_name": "DevOps Engineer",
                "required_count": 1,
                "description": "Cloud CI/CD infrastructure",
            },
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["role_name"], "DevOps Engineer")
        self.assertEqual(data["project_id"], self.proj_a.id)

        # Immediately visible in Project A roles
        roles_resp = self.client.get(
            f"/api/projects/{self.proj_a.id}/roles",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        names = [r["role_name"] for r in roles_resp.json()]
        self.assertIn("DevOps Engineer", names)

    # ========================================================
    # TEST 10: Attempt to assign Project B role to Project A -> Rejected 400
    # ========================================================
    def test_10_reject_cross_project_role_assignment(self):
        resp = self.client.put(
            f"/api/projects/{self.proj_a.id}/members/{self.emp_john.id}/role",
            json={"project_role_id": self.role_b_mobile.id},
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("does not exist in this project", resp.json()["detail"])

    # ========================================================
    # TEST 11: Remove Rahul -> Disappears from team, becomes available again
    # ========================================================
    @patch("app.project_service.service.send_project_removal_email")
    def test_11_remove_rahul_and_verify_available(self, mock_email):
        resp = self.client.delete(
            f"/api/projects/{self.proj_a.id}/members/{self.emp_rahul.id}",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(resp.status_code, 200)

        # Removed from Project A team
        members_resp = self.client.get(
            f"/api/projects/{self.proj_a.id}/members",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        emp_ids = [m["employee_id"] for m in members_resp.json()]
        self.assertNotIn(self.emp_rahul.id, emp_ids)

        # Rahul becomes available again for Project A
        avail_resp = self.client.get(
            f"/api/projects/{self.proj_a.id}/available-employees",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        avail_ids = [e["id"] for e in avail_resp.json()]
        self.assertIn(self.emp_rahul.id, avail_ids)

        # Removal email dispatched
        mock_email.assert_called_once()

    # ========================================================
    # TEST 12: Change John: Backend Developer -> Frontend Developer
    # ========================================================
    @patch("app.project_service.service.send_project_role_assignment_email")
    def test_12_change_john_role(self, mock_email):
        resp = self.client.put(
            f"/api/projects/{self.proj_a.id}/members/{self.emp_john.id}/role",
            json={"project_role_id": self.role_a_frontend.id},
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["project_role_name"], "Frontend Developer")

        # Verified in email call
        mock_email.assert_called_once()
        self.assertEqual(mock_email.call_args[1]["role_name"], "Frontend Developer")
        self.assertEqual(mock_email.call_args[1]["previous_role"], "Backend Developer")

    # ========================================================
    # TEST 13: Employee logs in -> sees assigned project, own role, team, CANNOT edit
    # ========================================================
    def test_13_employee_permissions(self):
        # 1. John sees assigned project
        my_resp = self.client.get(
            "/api/projects/me",
            headers={"Authorization": f"Bearer {self.john_token}"},
        )
        self.assertEqual(my_resp.status_code, 200)
        my_projects = my_resp.json()
        proj_ids = [p["id"] for p in my_projects]
        self.assertIn(self.proj_a.id, proj_ids)

        # 2. John sees team members of Project A
        team_resp = self.client.get(
            f"/api/projects/{self.proj_a.id}/members",
            headers={"Authorization": f"Bearer {self.john_token}"},
        )
        self.assertEqual(team_resp.status_code, 200)

        # 3. John CANNOT edit project
        edit_resp = self.client.put(
            f"/api/projects/{self.proj_a.id}",
            json={"project_name": "Hacked Name"},
            headers={"Authorization": f"Bearer {self.john_token}"},
        )
        self.assertEqual(edit_resp.status_code, 403)

        # 4. John CANNOT assign role
        role_resp = self.client.put(
            f"/api/projects/{self.proj_a.id}/members/{self.emp_priya.id}/role",
            json={"project_role_id": self.role_a_backend.id},
            headers={"Authorization": f"Bearer {self.john_token}"},
        )
        self.assertEqual(role_resp.status_code, 403)

    # ========================================================
    # TEST 14: HR changes project details -> team and roles remain unchanged
    # ========================================================
    def test_14_update_project_preserves_team_and_roles(self):
        # Update details
        resp = self.client.put(
            f"/api/projects/{self.proj_a.id}",
            json={
                "project_name": "Project Alpha Renamed",
                "client_name": "Mediatize Enterprise Client",
                "priority": "CRITICAL",
            },
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["project_name"], "Project Alpha Renamed")

        # Team remains unchanged
        members_resp = self.client.get(
            f"/api/projects/{self.proj_a.id}/members",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(len(members_resp.json()), 2)

        # Roles remain unchanged
        roles_resp = self.client.get(
            f"/api/projects/{self.proj_a.id}/roles",
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertGreaterEqual(len(roles_resp.json()), 3)

    # ========================================================
    # TEST 15: Profile update -> NO profile-update email
    # ========================================================
    @patch("app.email_service.service.send_project_assignment_email")
    @patch("app.email_service.service.send_project_role_assignment_email")
    @patch("app.email_service.service.send_project_removal_email")
    def test_15_profile_update_sends_no_email(self, mock_rem, mock_role, mock_assign):
        resp = self.client.put(
            f"/api/employees/{self.emp_john.id}",
            json={"phone": "9876543210"},
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(resp.status_code, 200)
        mock_rem.assert_not_called()
        mock_role.assert_not_called()
        mock_assign.assert_not_called()

    # ========================================================
    # TEST 16: Employee added to project -> Project assignment email
    # ========================================================
    @patch("app.project_service.service.send_project_assignment_email")
    def test_16_employee_assigned_without_role(self, mock_email):
        # Assigning without a role is now rejected by the backend validation
        resp = self.client.post(
            f"/api/projects/{self.proj_a.id}/members",
            json={
                "employee_id": self.emp_rahul.id,
                "project_role_id": None,
                "start_date": str(date.today()),
            },
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertIn(resp.status_code, [400, 422])

    # ========================================================
    # TEST 17: Employee + role assigned together -> ONE consolidated email
    # ========================================================
    @patch("app.project_service.service.send_project_role_assignment_email")
    @patch("app.project_service.service.send_project_assignment_email")
    def test_17_employee_assigned_with_role_sends_single_email(
        self, mock_assign_email, mock_role_email
    ):
        resp = self.client.post(
            f"/api/projects/{self.proj_a.id}/members",
            json={
                "employee_id": self.emp_rahul.id,
                "project_role_id": self.role_a_backend.id,
                "start_date": str(date.today()),
            },
            headers={"Authorization": f"Bearer {self.hr_token}"},
        )
        self.assertEqual(resp.status_code, 201)

        # EXACTLY ONE email sent
        self.assertEqual(mock_assign_email.call_count, 1)
        self.assertEqual(mock_role_email.call_count, 0)
        self.assertEqual(
            mock_assign_email.call_args[1]["role_name"], "Backend Developer"
        )


if __name__ == "__main__":
    unittest.main()
