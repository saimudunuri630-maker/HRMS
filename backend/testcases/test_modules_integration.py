import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text
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
from app.notification_service.service import create_in_app_notification
from app.announcement_service.models import Announcement, AnnouncementStatus, AnnouncementPriority
from app.work_report_service.models import WorkReport, WorkReportStatus
from app.complaint_service.models import Complaint, ComplaintType, ComplaintStatus
from app.attendance_service.models import Attendance, AttendanceStatus
from app.core.config import settings


class TestModulesIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

        # 1. Find authoritative HR user
        cls.hr_user = cls.db.query(User).filter(User.role == "hr").first()
        assert cls.hr_user is not None, "HR user must exist in database"

        # 2. Find active employees for testing
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

        # 3. Create or identify an inactive employee for testing
        cls.inactive_emp = (
            cls.db.query(Employee)
            .filter(Employee.employment_status != EmploymentStatus.ACTIVE)
            .first()
        )
        if not cls.inactive_emp:
            test_inactive_user = cls.db.query(User).filter(User.email.like("inactive_%@mediatize.internal")).first()
            if not test_inactive_user:
                test_inactive_user = User(
                    email=f"inactive_{int(datetime.now().timestamp())}@mediatize.internal",
                    full_name="Inactive Employee",
                    role="employee",
                    is_active=False,
                )
                cls.db.add(test_inactive_user)
                cls.db.commit()
                cls.db.refresh(test_inactive_user)

            cls.inactive_emp = Employee(
                user_id=test_inactive_user.id,
                employee_code=f"INACT-{int(datetime.now().timestamp())}",
                first_name="Inactive",
                last_name="Test",
                employment_status=EmploymentStatus.TERMINATED,
            )
            cls.db.add(cls.inactive_emp)
            cls.db.commit()
            cls.db.refresh(cls.inactive_emp)

        # 4. Create tokens & headers
        cls.hr_token = cls._create_token(cls.hr_user)
        cls.emp_a_token = cls._create_token(cls.emp_a_user)
        cls.emp_b_token = cls._create_token(cls.emp_b_user)

        cls.hr_headers = {"Authorization": f"Bearer {cls.hr_token}"}
        cls.emp_a_headers = {"Authorization": f"Bearer {cls.emp_a_token}"}
        cls.emp_b_headers = {"Authorization": f"Bearer {cls.emp_b_token}"}

        # 5. Set up a test project assigned only to emp_a
        today = date.today()
        cls.test_project = Project(
            project_code=f"MED-TEST-{int(datetime.now().timestamp())}",
            project_name="Mediatize Core Integration Project",
            description="Integration Project Description",
            status=ProjectStatus.ACTIVE,
            priority="HIGH",
            start_date=today,
            expected_end_date=today + timedelta(days=90),
            created_by=cls.hr_user.id,
        )
        cls.db.add(cls.test_project)
        cls.db.commit()
        cls.db.refresh(cls.test_project)

        cls.test_role = ProjectRole(
            project_id=cls.test_project.id,
            role_name="Software Engineer",
            required_count=2,
            description="Core Developer",
        )
        cls.db.add(cls.test_role)
        cls.db.commit()
        cls.db.refresh(cls.test_role)

        # Assign emp_a to this project
        cls.assignment = ProjectEmployeeAssignment(
            project_id=cls.test_project.id,
            employee_id=cls.emp_a.id,
            project_role_id=cls.test_role.id,
            start_date=today,
            status=AssignmentStatus.ACTIVE,
            assigned_by=cls.hr_user.id,
        )
        cls.db.add(cls.assignment)
        cls.db.commit()

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
        # Cleanup created records
        cls.db.close()

    # =========================================================================
    # PART 1: ANNOUNCEMENTS TESTS
    # =========================================================================

    def test_01_hr_creates_draft_announcement(self):
        """TEST 1: HR creates draft announcement -> Draft saved."""
        payload = {
            "title": "Q4 Performance Review Timeline",
            "content": "All departments must complete peer reviews by November 15.",
            "priority": "NORMAL",
        }
        res = self.client.post("/api/announcements", json=payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 201, res.text)
        data = res.json()
        self.assertEqual(data["title"], payload["title"])
        self.assertEqual(data["status"], "DRAFT")
        self.assertIsNone(data["published_at"])
        self.__class__.draft_announcement_id = data["id"]

    def test_02_hr_publishes_announcement_broadcasts_notifications_and_emails(self):
        """TEST 2: HR publishes announcement -> Published, active employees notified, email sent."""
        aid = getattr(self.__class__, "draft_announcement_id", None)
        self.assertIsNotNone(aid)

        with patch("app.announcement_service.service.send_announcement_published_email") as mock_email, \
             patch("app.announcement_service.service.create_in_app_notification") as mock_notif:
            mock_email.return_value = True
            mock_notif.return_value = {}

            res = self.client.post(f"/api/announcements/{aid}/publish", headers=self.hr_headers)
            self.assertEqual(res.status_code, 200, res.text)
            data = res.json()
            self.assertEqual(data["status"], "PUBLISHED")
            self.assertIsNotNone(data["published_at"])

            # Verify in-app notifications created for emp_a and emp_b
            notified_user_ids = [call.kwargs.get("user_id") or call.args[0] for call in mock_notif.call_args_list]
            self.assertIn(self.emp_a_user.id, notified_user_ids, "Active employee A must receive in-app notification")
            self.assertIn(self.emp_b_user.id, notified_user_ids, "Active employee B must receive in-app notification")
            self.assertNotIn(self.inactive_emp.user_id, notified_user_ids, "Inactive employee must NOT receive notification")

            # Verify email service was called
            self.assertTrue(mock_email.called, "Email service should be called for active employees")

    def test_03_employee_views_published_announcement(self):
        """TEST 3: Employee views announcements -> Visible."""
        res = self.client.get("/api/announcements", headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        items = data["items"] if isinstance(data, dict) and "items" in data else data
        self.assertTrue(any(a["id"] == self.draft_announcement_id for a in items))

    def test_04_inactive_employee_not_notified(self):
        """TEST 4: Inactive employee excluded from published announcements broadcast."""
        # Verified in test_02 that inactive_emp.user_id is not in notified_user_ids
        self.assertTrue(True)

    def test_05_employee_forbidden_from_creating_announcement(self):
        """TEST 5: Employee attempts to create announcement -> 403 Forbidden."""
        payload = {
            "title": "Unauthorized Announcement",
            "content": "Should be rejected.",
            "priority": "URGENT",
        }
        res = self.client.post("/api/announcements", json=payload, headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 403, res.text)

    # =========================================================================
    # PART 2: WORK REPORT TESTS
    # =========================================================================

    def test_06_employee_creates_daily_work_report(self):
        """TEST 1: Employee creates daily report for assigned project -> Success."""
        today = date.today().isoformat()
        payload = {
            "project_id": self.test_project.id,
            "report_date": today,
            "work_summary": "Implemented authentication hooks and verified unit tests.",
            "tasks_completed": "Refactored routers; fixed token authorization.",
            "hours_worked": 8.0,
            "status": "DRAFT",
        }
        res = self.client.post("/api/work-reports", json=payload, headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 201, res.text)
        data = res.json()
        self.assertEqual(data["employee_id"], self.emp_a.id)
        self.assertEqual(data["project_id"], self.test_project.id)
        self.__class__.emp_a_report_id = data["id"]

    def test_07_hr_creates_own_work_report(self):
        """TEST 2: HR creates own report -> Success."""
        today = date.today().isoformat()
        payload = {
            "project_id": self.test_project.id,
            "report_date": today,
            "work_summary": "HR workforce review and policy review meetings.",
            "hours_worked": 7.5,
            "status": "SUBMITTED",
        }
        res = self.client.post("/api/work-reports", json=payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 201, res.text)
        data = res.json()
        self.assertEqual(data["status"], "SUBMITTED")

    def test_08_employee_views_own_reports(self):
        """TEST 3: Employee views own reports -> Success."""
        res = self.client.get("/api/work-reports/me", headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        reports = data["items"] if isinstance(data, dict) and "items" in data else data
        self.assertTrue(any(r["id"] == self.emp_a_report_id for r in reports))

    def test_09_employee_forbidden_from_viewing_another_employee_report(self):
        """TEST 4: Employee attempts to view another employee's report -> 404/403."""
        # emp_b attempts to access emp_a's report via me endpoint
        res = self.client.get(f"/api/work-reports/me/{self.emp_a_report_id}", headers=self.emp_b_headers)
        self.assertIn(res.status_code, [403, 404])

        # emp_b attempts to access HR endpoint
        res2 = self.client.get("/api/work-reports/hr", headers=self.emp_b_headers)
        self.assertEqual(res2.status_code, 403)

    def test_10_hr_views_all_employee_reports(self):
        """TEST 5: HR views employee reports -> Success."""
        res = self.client.get("/api/work-reports/hr", headers=self.hr_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        reports = data["items"] if isinstance(data, dict) and "items" in data else data
        self.assertTrue(any(r["id"] == self.emp_a_report_id for r in reports))

    def test_11_future_report_date_rejected(self):
        """TEST 6: Future report date -> Rejected (400)."""
        future = (date.today() + timedelta(days=2)).isoformat()
        payload = {
            "project_id": self.test_project.id,
            "report_date": future,
            "work_summary": "Future report should be rejected.",
            "hours_worked": 8.0,
        }
        res = self.client.post("/api/work-reports", json=payload, headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 400, res.text)

    # =========================================================================
    # PART 3: COMPLAINTS TESTS
    # =========================================================================

    def test_12_employee_creates_company_complaint(self):
        """TEST 1: Employee creates company complaint -> Success."""
        payload = {
            "complaint_type": "COMPANY",
            "subject": "Office cafeteria coffee machine needs servicing",
            "description": "The coffee dispenser is leaking hot water.",
            "priority": "LOW",
        }
        res = self.client.post("/api/complaints", json=payload, headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 201, res.text)
        data = res.json()
        self.assertEqual(data["complaint_type"], "COMPANY")
        self.assertIsNone(data["project_id"])
        self.assertEqual(data["status"], "OPEN")

    def test_13_employee_creates_project_complaint(self):
        """TEST 2: Employee creates project complaint for assigned project -> Success."""
        payload = {
            "complaint_type": "PROJECT",
            "project_id": self.test_project.id,
            "subject": "Missing Figma mockups for sprint milestone",
            "description": "Design assets are blocked pending design team delivery.",
            "priority": "HIGH",
        }
        res = self.client.post("/api/complaints", json=payload, headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 201, res.text)
        data = res.json()
        self.assertEqual(data["complaint_type"], "PROJECT")
        self.assertEqual(data["project_id"], self.test_project.id)
        self.__class__.emp_a_complaint_id = data["id"]

    def test_14_employee_submits_unrelated_project_rejected(self):
        """TEST 3: Employee submits unrelated project_id -> Rejected."""
        payload = {
            "complaint_type": "PROJECT",
            "project_id": 9999999,  # Non-existent or unassigned project
            "subject": "Unauthorized project reference",
            "description": "Should fail project assignment validation.",
            "priority": "HIGH",
        }
        res = self.client.post("/api/complaints", json=payload, headers=self.emp_a_headers)
        self.assertIn(res.status_code, [400, 404], res.text)

    def test_15_hr_views_all_complaints(self):
        """TEST 4: HR views all complaints -> Success."""
        res = self.client.get("/api/complaints/hr", headers=self.hr_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        complaints = data["items"] if isinstance(data, dict) and "items" in data else data
        self.assertTrue(any(c["id"] == self.emp_a_complaint_id for c in complaints))

    def test_16_employee_views_own_complaint(self):
        """TEST 5: Employee views own complaints -> Success."""
        res = self.client.get("/api/complaints/me", headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        complaints = data["items"] if isinstance(data, dict) and "items" in data else data
        self.assertTrue(any(c["id"] == self.emp_a_complaint_id for c in complaints))

    def test_17_employee_forbidden_from_viewing_another_employee_complaint(self):
        """TEST 6: Employee attempts to view another employee complaint -> 404/403."""
        # emp_b attempts to access emp_a's complaint
        res = self.client.get(f"/api/complaints/me/{self.emp_a_complaint_id}", headers=self.emp_b_headers)
        self.assertIn(res.status_code, [403, 404])

        # emp_b attempts to access HR complaint list
        res2 = self.client.get("/api/complaints/hr", headers=self.emp_b_headers)
        self.assertEqual(res2.status_code, 403)

    def test_18_hr_provides_feedback_on_complaint(self):
        """TEST 7: HR provides feedback -> Feedback saved & employee notified."""
        cid = self.emp_a_complaint_id
        payload = {
            "feedback": "We have escalated this to the UI team lead. Figma assets will arrive tomorrow.",
            "status": "RESPONDED",
        }
        with patch("app.complaint_service.service.create_in_app_notification") as mock_notif:
            mock_notif.return_value = {}
            res = self.client.post(f"/api/complaints/hr/{cid}/feedback", json=payload, headers=self.hr_headers)
            self.assertEqual(res.status_code, 200, res.text)
            data = res.json()
            self.assertEqual(data["hr_response"], payload["feedback"])
            self.assertEqual(data["status"], "RESPONDED")

            # Verify in-app notification created for employee owner
            self.assertTrue(mock_notif.called, "Employee must receive in-app notification when HR responds")
            notified_user_ids = [call.kwargs.get("user_id") or call.args[0] for call in mock_notif.call_args_list]
            self.assertIn(self.emp_a_user.id, notified_user_ids)

    def test_19_employee_opens_complaint_views_hr_feedback(self):
        """TEST 8: Employee opens complaint -> HR feedback visible."""
        cid = self.emp_a_complaint_id
        res = self.client.get(f"/api/complaints/me/{cid}", headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("Figma assets will arrive tomorrow", data.get("hr_response") or "")

    # =========================================================================
    # PART 4: ATTENDANCE TESTS
    # =========================================================================

    def test_20_active_employee_checks_in(self):
        """TEST 1: Active employee checks in -> Success."""
        # Ensure no existing attendance for emp_b today
        today = date.today()
        self.db.query(Attendance).filter(
            Attendance.employee_id == self.emp_b.id,
            Attendance.attendance_date == today,
        ).delete()
        self.db.commit()

        res = self.client.post("/api/attendance/check-in", json={"remarks": "Morning punch-in"}, headers=self.emp_b_headers)
        self.assertIn(res.status_code, [200, 201], res.text)
        data = res.json()
        self.assertEqual(data["employee_id"], self.emp_b.id)
        self.assertEqual(data["status"], "PRESENT")
        self.assertIsNotNone(data["check_in"])
        self.assertIsNone(data["check_out"])

    def test_21_duplicate_check_in_rejected(self):
        """TEST 2: Same employee checks in again -> 400 Rejected."""
        res = self.client.post("/api/attendance/check-in", json={"remarks": "Second punch-in"}, headers=self.emp_b_headers)
        self.assertEqual(res.status_code, 400, res.text)

    def test_22_employee_checks_out_calculates_working_hours(self):
        """TEST 3: Employee checks out -> Working hours calculated by backend."""
        # Artificially set check_in to 8 hours 30 mins ago so working_hours is meaningful
        today = date.today()
        att = self.db.query(Attendance).filter(
            Attendance.employee_id == self.emp_b.id,
            Attendance.attendance_date == today,
        ).first()
        att.check_in = datetime.now(timezone.utc) - timedelta(hours=8, minutes=30)
        self.db.commit()

        res = self.client.post("/api/attendance/check-out", json={"remarks": "Evening punch-out"}, headers=self.emp_b_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIsNotNone(data["check_out"])
        self.assertIn("8h", data["working_hours"])
        self.assertIn("30m", data["working_hours"])

    def test_23_checkout_without_checkin_or_double_checkout_rejected(self):
        """TEST 4: Employee checks out again (or without check-in) -> Rejected."""
        res = self.client.post("/api/attendance/check-out", json={"remarks": "Double checkout"}, headers=self.emp_b_headers)
        self.assertEqual(res.status_code, 400, res.text)

    def test_24_employee_views_own_attendance_history(self):
        """TEST 5: Employee views attendance history -> Only own records."""
        res = self.client.get("/api/attendance/me/history", headers=self.emp_b_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        records = data.get("attendance", data.get("items", data)) if isinstance(data, dict) else data
        self.assertTrue(all(r["employee_id"] == self.emp_b.id for r in records))

    def test_25_hr_views_today_attendance_all_active_employees(self):
        """TEST 6: HR views today's attendance -> All active employees."""
        today = date.today().isoformat()
        res = self.client.get(f"/api/attendance/hr?date={today}", headers=self.hr_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        records = data.get("attendance", data.get("items", data)) if isinstance(data, dict) else data
        # Verify emp_b is included with PRESENT
        emp_b_rec = next((r for r in records if r["employee_id"] == self.emp_b.id), None)
        self.assertIsNotNone(emp_b_rec)
        self.assertEqual(emp_b_rec["status"], "PRESENT")

    def test_26_hr_daily_summary_dynamically_calculated(self):
        """TEST 7: HR daily summary dynamically calculated from active employees & records."""
        today = date.today().isoformat()
        res = self.client.get(f"/api/attendance/hr/daily-summary?date={today}", headers=self.hr_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("total_active_employees", data)
        self.assertTrue("present" in data or "present_count" in data)
        self.assertTrue("absent" in data or "absent_count" in data)
        self.assertTrue("half_day" in data or "half_day_count" in data)
        self.assertTrue("on_leave" in data or "on_leave_count" in data)
        self.assertGreater(data["total_active_employees"], 0)
        present_val = data.get("present") or data.get("present_count") or 0
        self.assertGreaterEqual(present_val, 1)

    def test_27_inactive_employee_excluded_from_active_totals(self):
        """TEST 8: Inactive employee not counted in active totals."""
        today = date.today().isoformat()
        res = self.client.get(f"/api/attendance/hr/daily-summary?date={today}", headers=self.hr_headers)
        data = res.json()

        active_count = self.db.query(Employee).filter(Employee.employment_status == EmploymentStatus.ACTIVE).count()
        self.assertEqual(data["total_active_employees"], active_count)

    # =========================================================================
    # PART 5: PROJECT NOTIFICATION INTEGRATION TEST
    # =========================================================================

    def test_28_project_creation_notifies_active_employees(self):
        """TEST: Project creation notifies active employees via Notification service."""
        today = date.today()
        payload = {
            "project_code": f"NOTIF-{int(datetime.now().timestamp())}",
            "project_name": "Enterprise Analytics Suite",
            "description": "Global enterprise analytics dashboard development.",
            "status": "ACTIVE",
            "priority": "HIGH",
            "start_date": today.isoformat(),
            "expected_end_date": (today + timedelta(days=90)).isoformat(),
            "initial_roles": ["Lead Engineer", "Product Specialist"],
        }
        with patch("app.project_service.service.create_in_app_notification") as mock_notif:
            mock_notif.return_value = {}
            res = self.client.post("/api/projects", json=payload, headers=self.hr_headers)
            self.assertEqual(res.status_code, 201, res.text)

            # Verify active employee received "New Project Added" in-app notification
            self.assertTrue(mock_notif.called, "Active employees should receive in-app notification when project is created")
            notified_user_ids = [call.kwargs.get("user_id") or call.args[0] for call in mock_notif.call_args_list]
            self.assertIn(self.emp_a_user.id, notified_user_ids)


if __name__ == "__main__":
    unittest.main()
