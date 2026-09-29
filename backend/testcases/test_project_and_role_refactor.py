import unittest
from datetime import date, datetime, timedelta, timezone
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


class TestProjectAndRoleRefactor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

        # Authoritative HR user
        cls.hr_user = cls.db.query(User).filter(User.role == "hr").first()
        assert cls.hr_user is not None, "HR user must exist in database"

        # Find two active employees
        emps = (
            cls.db.query(Employee)
            .filter(
                Employee.user_id != cls.hr_user.id,
                Employee.employment_status == EmploymentStatus.ACTIVE,
            )
            .order_by(Employee.id.asc())
            .all()
        )
        assert len(emps) >= 2, "At least two active employees needed for testing"

        cls.emp_a = emps[0]
        cls.emp_a_user = cls.db.query(User).filter(User.id == cls.emp_a.user_id).first()

        cls.emp_b = emps[1]
        cls.emp_b_user = cls.db.query(User).filter(User.id == cls.emp_b.user_id).first()

        # Create valid sessions & JWT tokens
        cls.hr_token = cls._create_token(cls.hr_user)
        cls.emp_a_token = cls._create_token(cls.emp_a_user)
        cls.emp_b_token = cls._create_token(cls.emp_b_user)

        cls.hr_headers = {"Authorization": f"Bearer {cls.hr_token}"}
        cls.emp_a_headers = {"Authorization": f"Bearer {cls.emp_a_token}"}
        cls.emp_b_headers = {"Authorization": f"Bearer {cls.emp_b_token}"}

        cls.created_project_ids = []

    @classmethod
    def _create_token(cls, user: User) -> str:
        import uuid
        now = datetime.now(timezone.utc)
        session = UserSession(
            user_id=user.id,
            session_id=f"test_session_{user.id}_{int(now.timestamp())}_{uuid.uuid4().hex[:6]}_{user.role}",
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
        tst_projs = cls.db.query(Project).filter(Project.project_code.like("MED-TEST-%")).all()
        for p in tst_projs:
            cls.db.query(ProjectEmployeeAssignment).filter(
                ProjectEmployeeAssignment.project_id == p.id
            ).delete()
            cls.db.query(ProjectRole).filter(ProjectRole.project_id == p.id).delete()
            cls.db.delete(p)
        cls.db.commit()
        cls.db.close()

    # =========================================================================
    # TEST 1: Create project without roles.
    # Expected: REJECTED (400 or 422 Bad Request).
    # =========================================================================
    def test_01_create_project_without_roles_rejected(self):
        code = f"MED-TEST-NOROLE-{int(datetime.now().timestamp()) % 100000}"
        payload = {
            "project_code": code,
            "project_name": "Project Without Roles",
            "start_date": str(date.today()),
            "expected_end_date": str(date.today() + timedelta(days=30)),
            "initial_roles": [],  # Empty initial_roles
        }
        res = self.client.post("/api/projects", json=payload, headers=self.hr_headers)
        self.assertIn(res.status_code, [400, 422], f"Expected 400 or 422 for empty roles: {res.text}")

        # Also test with 'roles' key as empty list
        payload2 = {
            "code": f"MED-TEST-NOROLE2-{int(datetime.now().timestamp()) % 100000}",
            "name": "Project Without Roles 2",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=30)),
            "roles": [],  # Empty roles
        }
        res2 = self.client.post("/api/projects", json=payload2, headers=self.hr_headers)
        self.assertIn(res2.status_code, [400, 422], f"Expected 400 or 422 for empty roles: {res2.text}")

        # Ensure neither project was saved
        p1 = self.db.query(Project).filter(Project.project_code == code).first()
        self.assertIsNone(p1, "Project without roles must not be created")

    # =========================================================================
    # TEST 2: Create project with one role.
    # Expected: SUCCESS (201 Created).
    # =========================================================================
    def test_02_create_project_with_one_role_success(self):
        code = f"MED-TEST-ONE-{int(datetime.now().timestamp()) % 100000}"
        payload = {
            "project_code": code,
            "project_name": "Single Role Project",
            "description": "Project with exactly one role",
            "start_date": str(date.today()),
            "expected_end_date": str(date.today() + timedelta(days=30)),
            "initial_roles": [
                {"role_name": "Lead Architect", "required_count": 1, "description": "System architecture"},
            ],
        }
        res = self.client.post("/api/projects", json=payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 201, f"Failed: {res.text}")
        data = res.json()
        self.assertEqual(len(data["roles"]), 1)
        self.assertEqual(data["roles"][0]["role_name"], "Lead Architect")
        self.assertEqual(data["roles"][0]["project_id"], data["id"])
        self.created_project_ids.append(data["id"])

    # =========================================================================
    # TEST 3: Create project with multiple roles.
    # Expected: SUCCESS (201 Created).
    # =========================================================================
    def test_03_create_project_with_multiple_roles_success(self):
        code = f"MED-TEST-MULTI-{int(datetime.now().timestamp()) % 100000}"
        payload = {
            "project_code": code,
            "project_name": "Mediatize HRMS Core",
            "description": "Enterprise Core System",
            "start_date": str(date.today()),
            "expected_end_date": str(date.today() + timedelta(days=90)),
            "status": "ACTIVE",
            "initial_roles": [
                {"role_name": "Backend Developer", "required_count": 2, "description": "FastAPI & Postgres"},
                {"role_name": "Frontend Developer", "required_count": 2, "description": "React & Vite"},
                {"role_name": "QA Engineer", "required_count": 1, "description": "Automation testing"},
            ],
        }
        res = self.client.post("/api/projects", json=payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 201, f"Failed: {res.text}")
        data = res.json()
        self.assertEqual(len(data["roles"]), 3)

        role_names = {r["role_name"] for r in data["roles"]}
        self.assertEqual(role_names, {"Backend Developer", "Frontend Developer", "QA Engineer"})

        TestProjectAndRoleRefactor.primary_proj_id = data["id"]
        TestProjectAndRoleRefactor.primary_roles = {r["role_name"]: r["id"] for r in data["roles"]}
        self.created_project_ids.append(data["id"])

    # =========================================================================
    # TEST 4: Verify project-role relationship.
    # Expected: Every role has correct project_id.
    # =========================================================================
    def test_04_verify_project_role_relationship(self):
        pid = TestProjectAndRoleRefactor.primary_proj_id
        res = self.client.get(f"/api/projects/{pid}", headers=self.hr_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        for r in data["roles"]:
            self.assertEqual(r["project_id"], pid)
            # Verify direct database record
            db_role = self.db.query(ProjectRole).filter(ProjectRole.id == r["id"]).first()
            self.assertIsNotNone(db_role)
            self.assertEqual(db_role.project_id, pid)

    # =========================================================================
    # TEST 5: Create duplicate role in same project.
    # Expected: REJECTED (409 Conflict).
    # =========================================================================
    def test_05_create_duplicate_role_in_same_project_rejected(self):
        pid = TestProjectAndRoleRefactor.primary_proj_id
        dup_payload = {
            "project_id": pid,
            "role_name": "backend developer",  # Case-insensitive duplicate
            "required_count": 1,
        }
        res = self.client.post("/api/project-roles", json=dup_payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 409)
        self.assertIn("already exists in this project", res.text)

    # =========================================================================
    # TEST 6: Create same role in different project.
    # Expected: ALLOWED (201 Created).
    # =========================================================================
    def test_06_create_same_role_in_different_project_allowed(self):
        # Create Project 2
        code2 = f"MED-TEST-P2-{int(datetime.now().timestamp()) % 100000}"
        p2_payload = {
            "project_code": code2,
            "project_name": "Project Beta",
            "start_date": str(date.today()),
            "expected_end_date": str(date.today() + timedelta(days=60)),
            "initial_roles": [
                {"role_name": "UI Designer", "required_count": 1},
            ],
        }
        res2 = self.client.post("/api/projects", json=p2_payload, headers=self.hr_headers)
        self.assertEqual(res2.status_code, 201)
        p2_data = res2.json()
        TestProjectAndRoleRefactor.p2_id = p2_data["id"]
        TestProjectAndRoleRefactor.p2_role_id = p2_data["roles"][0]["id"]
        self.created_project_ids.append(p2_data["id"])

        # Add "Backend Developer" to Project 2 (same name as in Primary Project)
        role_payload = {
            "project_id": TestProjectAndRoleRefactor.p2_id,
            "role_name": "Backend Developer",
            "required_count": 2,
        }
        res_role = self.client.post("/api/project-roles", json=role_payload, headers=self.hr_headers)
        self.assertEqual(res_role.status_code, 201)
        data = res_role.json()
        self.assertEqual(data["role_name"], "Backend Developer")
        self.assertEqual(data["project_id"], TestProjectAndRoleRefactor.p2_id)

    # =========================================================================
    # TEST 7: Assign employee.
    # Expected: Employee assigned to selected role.
    # =========================================================================
    def test_07_assign_employee_to_selected_role(self):
        pid = TestProjectAndRoleRefactor.primary_proj_id
        backend_role_id = TestProjectAndRoleRefactor.primary_roles["Backend Developer"]

        payload = {
            "employee_id": self.emp_a.id,
            "project_role_id": backend_role_id,
            "start_date": str(date.today()),
        }
        res = self.client.post(f"/api/projects/{pid}/employees", json=payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 201, f"Assignment failed: {res.text}")
        data = res.json()
        self.assertEqual(data["employee_id"], self.emp_a.id)
        self.assertEqual(data["project_role_id"], backend_role_id)
        self.assertEqual(data["project_role_name"], "Backend Developer")

        # Verify in database
        assign = (
            self.db.query(ProjectEmployeeAssignment)
            .filter(
                ProjectEmployeeAssignment.project_id == pid,
                ProjectEmployeeAssignment.employee_id == self.emp_a.id,
                ProjectEmployeeAssignment.status == AssignmentStatus.ACTIVE,
            )
            .first()
        )
        self.assertIsNotNone(assign)
        self.assertEqual(assign.project_role_id, backend_role_id)

    # =========================================================================
    # TEST 8: Role dropdown.
    # Expected: Only current project's roles.
    # =========================================================================
    def test_08_role_dropdown_scoped_to_current_project(self):
        pid = TestProjectAndRoleRefactor.primary_proj_id
        res = self.client.get(f"/api/projects/{pid}/roles", headers=self.hr_headers)
        self.assertEqual(res.status_code, 200)
        roles = res.json()
        for r in roles:
            self.assertEqual(r["project_id"], pid)
            # Ensure no role from Project 2 is present
            self.assertNotEqual(r["id"], TestProjectAndRoleRefactor.p2_role_id)

    # =========================================================================
    # TEST 9: Try cross-project role assignment through API.
    # Expected: REJECTED (400 Bad Request).
    # =========================================================================
    def test_09_reject_cross_project_role_assignment(self):
        pid = TestProjectAndRoleRefactor.primary_proj_id
        p2_role_id = TestProjectAndRoleRefactor.p2_role_id  # Role belonging to Project 2

        attack_payload = {
            "employee_id": self.emp_b.id,
            "project_role_id": p2_role_id,
            "start_date": str(date.today()),
        }
        res = self.client.post(f"/api/projects/{pid}/employees", json=attack_payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Project role does not exist in this project", res.text)

    # =========================================================================
    # TEST 10: Create additional role through Project Roles service.
    # Expected: SUCCESS (201 Created).
    # =========================================================================
    def test_10_create_additional_role_through_project_roles_service(self):
        pid = TestProjectAndRoleRefactor.primary_proj_id
        payload = {
            "project_id": pid,
            "role_name": "DevOps Engineer",
            "required_count": 1,
            "description": "Infrastructure and CI/CD pipelines.",
        }
        res = self.client.post("/api/project-roles", json=payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["role_name"], "DevOps Engineer")
        self.assertEqual(data["project_id"], pid)
        TestProjectAndRoleRefactor.primary_roles["DevOps Engineer"] = data["id"]

    # =========================================================================
    # TEST 11: Assign employee using newly created role.
    # Expected: SUCCESS (201 Created).
    # =========================================================================
    def test_11_assign_employee_using_newly_created_role(self):
        pid = TestProjectAndRoleRefactor.primary_proj_id
        devops_role_id = TestProjectAndRoleRefactor.primary_roles["DevOps Engineer"]

        payload = {
            "employee_id": self.emp_b.id,
            "project_role_id": devops_role_id,
            "start_date": str(date.today()),
        }
        res = self.client.post(f"/api/projects/{pid}/employees", json=payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["employee_id"], self.emp_b.id)
        self.assertEqual(data["project_role_id"], devops_role_id)
        self.assertEqual(data["project_role_name"], "DevOps Engineer")

    # =========================================================================
    # TEST 12: Remove employee.
    # Expected: Assignment inactive/removed. Employee account still active.
    # =========================================================================
    def test_12_remove_employee_preserves_employee_account(self):
        pid = TestProjectAndRoleRefactor.primary_proj_id
        emp_id = self.emp_a.id

        res = self.client.delete(f"/api/projects/{pid}/employees/{emp_id}", headers=self.hr_headers)
        self.assertEqual(res.status_code, 200)

        # 1. Employee record must be ACTIVE and intact
        emp_db = self.db.query(Employee).filter(Employee.id == emp_id).first()
        self.assertIsNotNone(emp_db)
        self.assertEqual(emp_db.employment_status, EmploymentStatus.ACTIVE)

        user_db = self.db.query(User).filter(User.id == self.emp_a_user.id).first()
        self.assertIsNotNone(user_db)
        self.assertTrue(user_db.is_active)

        # 2. Assignment is TERMINATED
        assign_db = (
            self.db.query(ProjectEmployeeAssignment)
            .filter(
                ProjectEmployeeAssignment.project_id == pid,
                ProjectEmployeeAssignment.employee_id == emp_id,
            )
            .first()
        )
        self.assertIsNotNone(assign_db)
        self.assertEqual(assign_db.status, AssignmentStatus.TERMINATED)

    # =========================================================================
    # TEST 13: Removed employee appears in available employees.
    # Expected: YES.
    # =========================================================================
    def test_13_removed_employee_appears_in_available_employees(self):
        pid = TestProjectAndRoleRefactor.primary_proj_id
        emp_id = self.emp_a.id

        res = self.client.get(f"/api/projects/{pid}/available-employees", headers=self.hr_headers)
        self.assertEqual(res.status_code, 200)
        avail = res.json()
        avail_ids = [e["id"] for e in avail]
        self.assertIn(emp_id, avail_ids, "Removed employee must reappear in available employees list")

        # Re-assign emp_a for subsequent tests
        backend_role_id = TestProjectAndRoleRefactor.primary_roles["Backend Developer"]
        res_reassign = self.client.post(
            f"/api/projects/{pid}/employees",
            json={
                "employee_id": emp_id,
                "project_role_id": backend_role_id,
                "start_date": str(date.today()),
            },
            headers=self.hr_headers,
        )
        self.assertEqual(res_reassign.status_code, 201)

    # =========================================================================
    # TEST 14: Change employee role.
    # Expected: New role belongs to same project.
    # =========================================================================
    def test_14_change_employee_role_same_project(self):
        pid = TestProjectAndRoleRefactor.primary_proj_id
        emp_id = self.emp_a.id
        frontend_role_id = TestProjectAndRoleRefactor.primary_roles["Frontend Developer"]

        payload = {"project_role_id": frontend_role_id}
        res = self.client.put(f"/api/projects/{pid}/employees/{emp_id}/role", json=payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["project_role_id"], frontend_role_id)
        self.assertEqual(data["project_role_name"], "Frontend Developer")

        # Cross-project role change must be rejected (400)
        bad_payload = {"project_role_id": TestProjectAndRoleRefactor.p2_role_id}
        res_bad = self.client.put(f"/api/projects/{pid}/employees/{emp_id}/role", json=bad_payload, headers=self.hr_headers)
        self.assertEqual(res_bad.status_code, 400)
        self.assertIn("Project role does not exist in this project", res_bad.text)

    # =========================================================================
    # TEST 15: Employee tries to create project.
    # Expected: 403 Forbidden.
    # =========================================================================
    def test_15_employee_cannot_create_project(self):
        payload = {
            "project_code": f"MED-TEST-ROGUE-{int(datetime.now().timestamp()) % 100000}",
            "project_name": "Rogue Project",
            "start_date": str(date.today()),
            "expected_end_date": str(date.today() + timedelta(days=30)),
            "initial_roles": [{"role_name": "Dev", "required_count": 1}],
        }
        res = self.client.post("/api/projects", json=payload, headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 403)

    # =========================================================================
    # TEST 16: Employee tries to create project role.
    # Expected: 403 Forbidden.
    # =========================================================================
    def test_16_employee_cannot_create_project_role(self):
        pid = TestProjectAndRoleRefactor.primary_proj_id
        payload = {
            "project_id": pid,
            "role_name": "Unauthorized Role",
            "required_count": 1,
        }
        res = self.client.post("/api/project-roles", json=payload, headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 403)

    # =========================================================================
    # TEST 17: Employee tries to assign employee.
    # Expected: 403 Forbidden.
    # =========================================================================
    def test_17_employee_cannot_assign_employee(self):
        pid = TestProjectAndRoleRefactor.primary_proj_id
        frontend_role_id = TestProjectAndRoleRefactor.primary_roles["Frontend Developer"]
        payload = {
            "employee_id": self.emp_b.id,
            "project_role_id": frontend_role_id,
            "start_date": str(date.today()),
        }
        res = self.client.post(f"/api/projects/{pid}/employees", json=payload, headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 403)

    # =========================================================================
    # TEST 18: Complete project.
    # Expected: Existing team/roles remain intact.
    # =========================================================================
    def test_18_completed_project_intact_and_blocks_new_assignments(self):
        p2_id = TestProjectAndRoleRefactor.p2_id

        # Mark Project 2 as COMPLETED
        res_status = self.client.patch(
            f"/api/projects/{p2_id}/status", json={"status": "COMPLETED"}, headers=self.hr_headers
        )
        self.assertEqual(res_status.status_code, 200)

        # Existing roles and details remain completely visible
        res_get = self.client.get(f"/api/projects/{p2_id}", headers=self.hr_headers)
        self.assertEqual(res_get.status_code, 200)
        data = res_get.json()
        self.assertEqual(data["status"], "COMPLETED")
        self.assertGreater(len(data["roles"]), 0)

        # New employee assignment is blocked
        assign_payload = {
            "employee_id": self.emp_a.id,
            "project_role_id": TestProjectAndRoleRefactor.p2_role_id,
            "start_date": str(date.today()),
        }
        res_assign = self.client.post(f"/api/projects/{p2_id}/employees", json=assign_payload, headers=self.hr_headers)
        self.assertEqual(res_assign.status_code, 400)
        self.assertIn("completed", res_assign.text.lower())

    # =========================================================================
    # TEST 19: Role deletion safety.
    # Expected: Role with active assignments cannot be deleted (400 Bad Request).
    # =========================================================================
    def test_19_role_deletion_safety_with_active_assignments(self):
        pid = TestProjectAndRoleRefactor.primary_proj_id
        # emp_a is assigned to Frontend Developer
        frontend_role_id = TestProjectAndRoleRefactor.primary_roles["Frontend Developer"]

        res = self.client.delete(f"/api/project-roles/{frontend_role_id}", headers=self.hr_headers)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json()["detail"],
            "This role is currently assigned to employees. Reassign those employees before removing the role.",
        )

        # Role with 0 assigned employees CAN be deleted
        qa_role_id = TestProjectAndRoleRefactor.primary_roles["QA Engineer"]
        res_qa = self.client.delete(f"/api/project-roles/{qa_role_id}", headers=self.hr_headers)
        self.assertEqual(res_qa.status_code, 200)

    # =========================================================================
    # TEST 20: Transactional rollback on project creation failure.
    # Expected: If any role fails, full rollback occurs.
    # =========================================================================
    def test_20_transactional_rollback_on_role_failure(self):
        code = f"MED-TEST-ROLLBACK-{int(datetime.now().timestamp()) % 100000}"
        bad_payload = {
            "project_code": code,
            "project_name": "Rollback Test Project",
            "start_date": str(date.today()),
            "expected_end_date": str(date.today() + timedelta(days=30)),
            # Duplicate role name in initial roles causes rejection
            "initial_roles": [
                {"role_name": "Developer"},
                {"role_name": "developer"},
            ],
        }
        res = self.client.post("/api/projects", json=bad_payload, headers=self.hr_headers)
        self.assertIn(res.status_code, [400, 422])

        # Verify no project was committed
        proj = self.db.query(Project).filter(Project.project_code == code).first()
        self.assertIsNone(proj, "Project must not be created if role creation fails")


if __name__ == "__main__":
    unittest.main()
