import unittest
import uuid
from datetime import date, datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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


class TestProjectReferenceFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

        cls.hr_user = cls.db.query(User).filter(User.role == "hr").first()
        assert cls.hr_user is not None

        emps = (
            cls.db.query(Employee)
            .filter(
                Employee.user_id != cls.hr_user.id,
                Employee.employment_status == EmploymentStatus.ACTIVE,
            )
            .order_by(Employee.id.asc())
            .all()
        )
        assert len(emps) >= 2

        cls.emp_a = emps[0]
        cls.emp_a_user = cls.db.query(User).filter(User.id == cls.emp_a.user_id).first()

        cls.emp_b = emps[1]
        cls.emp_b_user = cls.db.query(User).filter(User.id == cls.emp_b.user_id).first()

        cls.hr_token = cls._create_token(cls.hr_user)
        cls.emp_a_token = cls._create_token(cls.emp_a_user)
        cls.emp_b_token = cls._create_token(cls.emp_b_user)

        cls.hr_headers = {"Authorization": f"Bearer {cls.hr_token}"}
        cls.emp_a_headers = {"Authorization": f"Bearer {cls.emp_a_token}"}
        cls.emp_b_headers = {"Authorization": f"Bearer {cls.emp_b_token}"}

        cls.created_proj_ids = []

    @classmethod
    def _create_token(cls, user: User) -> str:
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

        return jwt.encode(
            {
                "sub": str(user.id),
                "role": user.role,
                "session_id": session.session_id,
                "exp": int((now + timedelta(hours=3)).timestamp()),
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    @classmethod
    def tearDownClass(cls):
        for pid in cls.created_proj_ids:
            cls.db.query(ProjectEmployeeAssignment).filter(ProjectEmployeeAssignment.project_id == pid).delete()
            cls.db.query(ProjectRole).filter(ProjectRole.project_id == pid).delete()
            cls.db.query(Project).filter(Project.id == pid).delete()
        cls.db.commit()
        cls.db.close()

    def test_01_hr_project_metrics_endpoint(self):
        res = self.client.get("/api/projects/metrics", headers=self.hr_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        for k in ["total_projects", "active_projects", "completed_projects", "on_hold_projects", "overdue_projects"]:
            self.assertIn(k, data)
            self.assertIsInstance(data[k], int)

    def test_02_create_project_and_test_progress_patch(self):
        code = f"MED-REF-{int(datetime.now().timestamp()) % 100000}"
        payload = {
            "project_code": code,
            "project_name": "Progress Tracking Project",
            "start_date": str(date.today()),
            "expected_end_date": str(date.today() + timedelta(days=60)),
            "initial_roles": [
                {"role_name": "Full Stack Engineer", "required_count": 2},
            ],
        }
        res = self.client.post("/api/projects", json=payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 201, res.text)
        pdata = res.json()
        pid = pdata["id"]
        self.created_proj_ids.append(pid)
        role_id = pdata["roles"][0]["id"]

        # 1. Update progress to 50%
        res_prog = self.client.patch(f"/api/projects/{pid}/progress", json={"progress_percentage": 50}, headers=self.hr_headers)
        self.assertEqual(res_prog.status_code, 200, res_prog.text)
        self.assertEqual(res_prog.json()["progress_percentage"], 50)

        # 2. Reject invalid progress
        res_invalid = self.client.patch(f"/api/projects/{pid}/progress", json={"progress_percentage": 150}, headers=self.hr_headers)
        self.assertIn(res_invalid.status_code, [400, 422])

        # 3. Assign Employee A via reference endpoint /api/projects/{id}/assignments
        res_assign = self.client.post(
            f"/api/projects/{pid}/assignments",
            json={"employee_id": self.emp_a.id, "project_role_id": role_id},
            headers=self.hr_headers,
        )
        self.assertEqual(res_assign.status_code, 201, res_assign.text)
        assignment_id = res_assign.json()["assignment_id"]

        # 4. List assignments via reference endpoint
        res_team = self.client.get(f"/api/projects/{pid}/assignments", headers=self.hr_headers)
        self.assertEqual(res_team.status_code, 200)
        self.assertTrue(any(m["employee_id"] == self.emp_a.id for m in res_team.json()))

        # 5. Employee A self-service /api/projects/my-projects includes this project
        res_my = self.client.get("/api/projects/my-projects", headers=self.emp_a_headers)
        self.assertEqual(res_my.status_code, 200)
        my_pids = [p["project_id"] for p in res_my.json()]
        self.assertIn(pid, my_pids)

        # 6. Employee A accesses their assigned project details via /api/projects/my-projects/{id} -> 200
        res_detail_a = self.client.get(f"/api/projects/my-projects/{pid}", headers=self.emp_a_headers)
        self.assertEqual(res_detail_a.status_code, 200)
        self.assertEqual(res_detail_a.json()["id"], pid)

        # 7. IDOR PROTECTION: Employee B (not assigned) tries to access /api/projects/my-projects/{id} -> 403 Forbidden
        res_detail_b = self.client.get(f"/api/projects/my-projects/{pid}", headers=self.emp_b_headers)
        self.assertEqual(res_detail_b.status_code, 403, "Unassigned employee must receive 403 Forbidden")

        # 8. Remove employee assignment via PATCH /api/projects/{id}/assignments/{assignment_id}/remove
        res_remove = self.client.patch(f"/api/projects/{pid}/assignments/{assignment_id}/remove", headers=self.hr_headers)
        self.assertEqual(res_remove.status_code, 200)

        # 9. Verify employee account remains active
        emp_check = self.db.query(Employee).filter(Employee.id == self.emp_a.id).first()
        self.assertEqual(emp_check.employment_status, EmploymentStatus.ACTIVE)

        # 10. Update progress to 100% -> status becomes COMPLETED
        res_comp = self.client.patch(f"/api/projects/{pid}/progress", json={"progress_percentage": 100}, headers=self.hr_headers)
        self.assertEqual(res_comp.status_code, 200)
        self.assertEqual(res_comp.json()["status"], "COMPLETED")
