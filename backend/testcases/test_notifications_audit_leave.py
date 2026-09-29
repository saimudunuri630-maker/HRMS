import unittest
from datetime import date, datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import jwt

from app.main import app
from app.core.database import SessionLocal
from app.core.config import settings
from app.authentication_service.models import User, UserSession, OTPVerification
from app.authentication_service.service import hash_otp
from app.employee_service.models import Employee, EmploymentStatus
from app.notification_service.models import Notification
from app.audit_service.models import AuditLog
from app.leave_service.models import LeaveType, LeaveBalance, LeaveRequest, LeaveStatus
from app.attendance_service.models import Attendance, AttendanceStatus


class TestNotificationsAuditLeave(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

        # 1. Authoritative HR User
        cls.hr_user = cls.db.query(User).filter(User.role == "hr", User.is_active == True).first()
        assert cls.hr_user is not None, "HR user must exist in database"

        # 2. Authoritative Active Employees
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

        # 3. Create or find inactive employee
        cls.inactive_emp = (
            cls.db.query(Employee)
            .filter(Employee.employment_status != EmploymentStatus.ACTIVE)
            .first()
        )
        if not cls.inactive_emp:
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
                employment_status=EmploymentStatus.INACTIVE,
            )
            cls.db.add(cls.inactive_emp)
            cls.db.commit()
            cls.db.refresh(cls.inactive_emp)

        # 4. Generate Auth Headers
        cls.hr_token = cls._create_token(cls.hr_user)
        cls.emp_a_token = cls._create_token(cls.emp_a_user)
        cls.emp_b_token = cls._create_token(cls.emp_b_user)

        cls.hr_headers = {"Authorization": f"Bearer {cls.hr_token}"}
        cls.emp_a_headers = {"Authorization": f"Bearer {cls.emp_a_token}"}
        cls.emp_b_headers = {"Authorization": f"Bearer {cls.emp_b_token}"}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    @classmethod
    def _create_token(cls, user: User) -> str:
        now = datetime.now(timezone.utc)
        session = UserSession(
            user_id=user.id,
            session_id=f"test_session_{user.id}_{int(now.timestamp())}_{user.role}",
            expires_at=now + timedelta(hours=2),
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
                "exp": int((now + timedelta(hours=2)).timestamp()),
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    # ============================================================
    # NOTIFICATION TESTS
    # ============================================================

    def test_01_create_new_project_creates_notifications(self):
        """TEST 1: Create new project -> Project notification created in database for employees."""
        ts = int(datetime.now().timestamp())
        proj_code = f"MED-PRJ-{ts}"
        payload = {
            "project_code": proj_code,
            "project_name": f"Automation Platform {ts}",
            "description": "Integration test project",
            "start_date": str(date.today()),
            "expected_end_date": str(date.today() + timedelta(days=60)),
            "priority": "HIGH",
            "initial_roles": [
                {"role_name": "Tech Lead", "required_count": 1, "description": "Lead"},
                {"role_name": "Dev", "required_count": 2, "description": "Developer"},
            ],
        }

        notifs_before = self.db.query(Notification).filter(Notification.user_id == self.emp_a_user.id).count()

        res = self.client.post("/api/projects", json=payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 201, f"Failed to create project: {res.text}")

        notifs_after = self.db.query(Notification).filter(
            Notification.user_id == self.emp_a_user.id,
            Notification.title == "New Project Created",
        ).count()
        self.assertGreater(notifs_after, 0, "Active employee must receive project creation notification")

    def test_02_project_creation_failure_no_notification(self):
        """TEST 2: Project creation fails -> No project notification."""
        # Intentionally invalid payload (empty initial_roles)
        ts = int(datetime.now().timestamp())
        payload = {
            "project_code": f"MED-FAIL-{ts}",
            "project_name": "Failed Project",
            "start_date": str(date.today()),
            "expected_end_date": str(date.today() + timedelta(days=60)),
            "initial_roles": [],
        }

        notif_count_before = self.db.query(Notification).count()
        res = self.client.post("/api/projects", json=payload, headers=self.hr_headers)
        self.assertIn(res.status_code, [400, 422])

        notif_count_after = self.db.query(Notification).count()
        self.assertEqual(notif_count_before, notif_count_after, "No notification should be created when project creation fails")

    def test_03_publish_announcement_notifies_all_active_employees(self):
        """TEST 3: Publish announcement -> All active employees receive notification."""
        ts = int(datetime.now().timestamp())
        payload = {
            "title": f"Holiday Notice {ts}",
            "content": "All offices will remain closed.",
            "priority": "IMPORTANT",
            "status": "PUBLISHED",
        }

        res = self.client.post("/api/announcements", json=payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 201)
        ann_id = res.json()["id"]

        # Verify active employee A received in-app notification
        notif_a = self.db.query(Notification).filter(
            Notification.user_id == self.emp_a_user.id,
            Notification.entity_id == ann_id,
        ).first()
        self.assertIsNotNone(notif_a, "Active employee A must receive announcement notification")
        self.assertEqual(notif_a.notification_type, "ANNOUNCEMENT")

        # Verify active employee B received in-app notification
        notif_b = self.db.query(Notification).filter(
            Notification.user_id == self.emp_b_user.id,
            Notification.entity_id == ann_id,
        ).first()
        self.assertIsNotNone(notif_b, "Active employee B must receive announcement notification")

    def test_04_inactive_employee_does_not_receive_announcement_notification(self):
        """TEST 4: Inactive employee -> Does not receive new announcement notification."""
        if self.inactive_emp and self.inactive_emp.user_id:
            ts = int(datetime.now().timestamp())
            payload = {
                "title": f"Strictly Active Notice {ts}",
                "content": "Notice for active staff only.",
                "priority": "NORMAL",
                "status": "PUBLISHED",
            }
            res = self.client.post("/api/announcements", json=payload, headers=self.hr_headers)
            self.assertEqual(res.status_code, 201)
            ann_id = res.json()["id"]

            inactive_notif = self.db.query(Notification).filter(
                Notification.user_id == self.inactive_emp.user_id,
                Notification.entity_id == ann_id,
            ).first()
            self.assertIsNone(inactive_notif, "Inactive employee must NOT receive published announcement notifications")

    def test_05_employee_opens_notification_marks_as_read(self):
        """TEST 5: Employee opens notification -> Notification marked read."""
        # Find an unread notification for employee A or create one
        notif = self.db.query(Notification).filter(
            Notification.user_id == self.emp_a_user.id,
            Notification.is_read == False,
        ).first()
        if not notif:
            notif = Notification(
                user_id=self.emp_a_user.id,
                notification_type="SYSTEM",
                title="Test Unread Notification",
                message="Please review.",
                is_read=False,
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(notif)
            self.db.commit()
            self.db.refresh(notif)

        res = self.client.put(f"/api/notifications/{notif.id}/read", headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["is_read"])
        self.assertIsNotNone(data["read_at"])

    def test_06_mark_all_read_clears_unread_count(self):
        """TEST 6: Mark all read -> Unread count becomes zero."""
        # Create 2 unread notifications for employee B
        for i in range(2):
            n = Notification(
                user_id=self.emp_b_user.id,
                notification_type="SYSTEM",
                title=f"Bulk Notification {i}",
                message="Action required.",
                is_read=False,
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(n)
        self.db.commit()

        # Mark all read
        res = self.client.put("/api/notifications/read-all", headers=self.emp_b_headers)
        self.assertEqual(res.status_code, 200)

        # Check unread count
        count_res = self.client.get("/api/notifications/unread-count", headers=self.emp_b_headers)
        self.assertEqual(count_res.status_code, 200)
        self.assertEqual(count_res.json()["unread_count"], 0)

    # ============================================================
    # AUDIT LOG TESTS
    # ============================================================

    def test_07_hr_and_employee_login_audit_record(self):
        """TEST 1 & 2: HR login and Employee login -> LOGIN audit record created."""
        # Test HR Login Audit
        clean_email = self.hr_user.email
        otp_code = "123456"
        otp_hash = hash_otp(otp_code)

        otp_record = OTPVerification(
            email=clean_email,
            otp_hash=otp_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            is_used=False,
            attempts=0,
        )
        self.db.add(otp_record)
        self.db.commit()

        login_res = self.client.post("/auth/verify-otp", json={"email": clean_email, "otp": otp_code})
        self.assertEqual(login_res.status_code, 200)

        audit_entry = self.db.query(AuditLog).filter(
            AuditLog.user_id == self.hr_user.id,
            AuditLog.action == "LOGIN",
            AuditLog.module == "AUTHENTICATION",
        ).order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(audit_entry, "Successful HR login must create LOGIN audit record")

        # Test Employee Login Audit
        emp_email = self.emp_a_user.email
        otp_emp = "654321"
        otp_emp_hash = hash_otp(otp_emp)

        otp_rec_emp = OTPVerification(
            email=emp_email,
            otp_hash=otp_emp_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            is_used=False,
            attempts=0,
        )
        self.db.add(otp_rec_emp)
        self.db.commit()

        login_emp_res = self.client.post("/auth/verify-otp", json={"email": emp_email, "otp": otp_emp})
        self.assertEqual(login_emp_res.status_code, 200)

        audit_emp_entry = self.db.query(AuditLog).filter(
            AuditLog.user_id == self.emp_a_user.id,
            AuditLog.action == "LOGIN",
            AuditLog.module == "AUTHENTICATION",
        ).order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(audit_emp_entry, "Successful Employee login must create LOGIN audit record")

    def test_08_hr_and_employee_logout_audit_record(self):
        """TEST 3 & 4: HR logout and Employee logout -> LOGOUT audit record created."""
        # HR Logout
        hr_logout_res = self.client.post("/auth/logout", headers=self.hr_headers)
        self.assertEqual(hr_logout_res.status_code, 200)

        audit_hr_logout = self.db.query(AuditLog).filter(
            AuditLog.user_id == self.hr_user.id,
            AuditLog.action == "LOGOUT",
            AuditLog.module == "AUTHENTICATION",
        ).order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(audit_hr_logout, "HR logout must create LOGOUT audit record")

        # Employee Logout
        emp_logout_res = self.client.post("/auth/logout", headers=self.emp_a_headers)
        self.assertEqual(emp_logout_res.status_code, 200)

        audit_emp_logout = self.db.query(AuditLog).filter(
            AuditLog.user_id == self.emp_a_user.id,
            AuditLog.action == "LOGOUT",
            AuditLog.module == "AUTHENTICATION",
        ).order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(audit_emp_logout, "Employee logout must create LOGOUT audit record")

    def test_09_failed_login_creates_audit_record_without_sensitive_otp(self):
        """TEST 5: Login with invalid OTP -> Appropriate audit record without sensitive credentials."""
        # Seed an OTP record first so the lookup succeeds and OTP mismatch triggers LOGIN_FAILED
        clean_email = self.hr_user.email
        otp_hash = hash_otp("123456")
        otp_record = OTPVerification(
            email=clean_email,
            otp_hash=otp_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            is_used=False,
            attempts=0,
        )
        self.db.add(otp_record)
        self.db.commit()

        # Send bad OTP
        res = self.client.post("/auth/verify-otp", json={"email": clean_email, "otp": "999999"})
        self.assertEqual(res.status_code, 400)

        # Verify audit record does not store "999999"
        audit = self.db.query(AuditLog).filter(
            AuditLog.action == "LOGIN_FAILED",
            AuditLog.user_id == self.hr_user.id,
        ).order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(audit, "Failed login must generate LOGIN_FAILED audit record")
        self.assertNotIn("999999", audit.description, "Sensitive OTP must never be logged")

    def test_10_employee_access_to_audit_logs_is_forbidden(self):
        """TEST 6: Employee attempts to access audit logs -> 403 Forbidden."""
        res = self.client.get("/api/audit-logs", headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 403, "Non-HR user must receive 403 Forbidden on audit logs")

    def test_11_hr_views_audit_logs(self):
        """TEST 7: HR views audit logs -> All authorized audit records visible."""
        res = self.client.get("/api/audit-logs", headers=self.hr_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertGreater(data["total"], 0)

    def test_12_audit_record_modification_not_allowed(self):
        """TEST 8: Audit record modification attempt -> Not allowed (immutable)."""
        latest = self.db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(latest)

        # PUT/PATCH/DELETE should be 405 Method Not Allowed
        put_res = self.client.put(f"/api/audit-logs/{latest.id}", json={"description": "Tampered"}, headers=self.hr_headers)
        self.assertEqual(put_res.status_code, 405)

        del_res = self.client.delete(f"/api/audit-logs/{latest.id}", headers=self.hr_headers)
        self.assertEqual(del_res.status_code, 405)

    # ============================================================
    # LEAVE MANAGEMENT TESTS
    # ============================================================

    def test_13_hr_creates_leave_type(self):
        """TEST 1: HR creates leave type -> Leave type created."""
        ts = int(datetime.now().timestamp())
        payload = {
            "name": f"Paternity Leave {ts}",
            "code": f"PAT_{ts}",
            "description": "Leave for new fathers",
            "days_per_year": 15.0,
            "is_paid": True,
            "is_active": True,
        }
        res = self.client.post("/api/leave/types", json=payload, headers=self.hr_headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["name"], payload["name"])
        self.assertEqual(data["code"], payload["code"])

    def test_14_employee_views_balance(self):
        """TEST 2: Employee views balance -> Correct balance."""
        res = self.client.get("/api/leave/balances/me", headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 200)
        balances = res.json()
        self.assertIsInstance(balances, list)
        self.assertGreater(len(balances), 0)
        self.assertIn("remaining_days", balances[0])

    def test_15_employee_submits_leave_and_hr_receives_notification(self):
        """TEST 3 & 4: Employee submits leave -> PENDING & HR receives notification."""
        # Get an active leave type
        lt = self.db.query(LeaveType).filter(LeaveType.is_active == True).first()
        self.assertIsNotNone(lt)

        # Submit leave in near future within the current year
        future_start = date.today() + timedelta(days=10)
        future_end = future_start + timedelta(days=2)

        # Ensure employee has enough balance for future_start.year
        bal = self.db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == self.emp_a.id,
            LeaveBalance.leave_type_id == lt.id,
            LeaveBalance.year == future_start.year,
        ).first()
        if not bal:
            bal = LeaveBalance(
                employee_id=self.emp_a.id,
                leave_type_id=lt.id,
                year=future_start.year,
                total_allocated=15.0,
                used_days=0.0,
                pending_days=0.0,
            )
            self.db.add(bal)
            self.db.commit()
        else:
            bal.used_days = 0.0
            bal.pending_days = 0.0
            self.db.commit()

        # Clear any overlapping requests for this window
        self.db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == self.emp_a.id,
            LeaveRequest.start_date <= future_end,
            LeaveRequest.end_date >= future_start,
        ).delete()
        self.db.commit()

        payload = {
            "leave_type_id": lt.id,
            "start_date": str(future_start),
            "end_date": str(future_end),
            "reason": "Personal family commitment",
        }

        res = self.client.post("/api/leave/requests", json=payload, headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 201)
        req_data = res.json()
        self.assertEqual(req_data["status"], "PENDING")
        self.assertEqual(req_data["total_days"], 3.0)

        # Verify HR received in-app notification
        hr_notif = self.db.query(Notification).filter(
            Notification.user_id == self.hr_user.id,
            Notification.entity_id == req_data["id"],
            Notification.notification_type == "LEAVE",
        ).first()
        self.assertIsNotNone(hr_notif, "HR must receive in-app notification when leave request is submitted")

    def test_16_hr_approves_leave_and_balance_deducted(self):
        """TEST 5: HR approves -> APPROVED, Balance updated, Employee notified, Audit created."""
        lt = self.db.query(LeaveType).filter(LeaveType.is_active == True).first()
        start = date.today() + timedelta(days=20)
        end = start + timedelta(days=1)

        # Clean any overlapping requests
        self.db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == self.emp_b.id,
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start,
        ).delete()
        self.db.commit()

        # Submit request
        req = LeaveRequest(
            employee_id=self.emp_b.id,
            leave_type_id=lt.id,
            start_date=start,
            end_date=end,
            total_days=2.0,
            reason="Medical test",
            status=LeaveStatus.PENDING,
        )
        self.db.add(req)
        # Ensure balance
        bal = self.db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == self.emp_b.id,
            LeaveBalance.leave_type_id == lt.id,
            LeaveBalance.year == start.year,
        ).first()
        if not bal:
            bal = LeaveBalance(
                employee_id=self.emp_b.id,
                leave_type_id=lt.id,
                year=start.year,
                total_allocated=50.0,
                used_days=0.0,
                pending_days=2.0,
            )
            self.db.add(bal)
        else:
            bal.total_allocated = 50.0
            bal.pending_days += 2.0
        self.db.commit()
        self.db.refresh(req)

        used_before = bal.used_days

        # HR approves
        res = self.client.put(
            f"/api/leave/requests/{req.id}/approve",
            json={"reason": "Approved by HR management"},
            headers=self.hr_headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "APPROVED")

        # Verify balance updated (used_days incremented by 2)
        self.db.refresh(bal)
        self.assertEqual(bal.used_days, used_before + 2.0)

        # Verify employee notification created
        emp_notif = self.db.query(Notification).filter(
            Notification.user_id == self.emp_b_user.id,
            Notification.entity_id == req.id,
            Notification.title == "Leave Request Approved",
        ).first()
        self.assertIsNotNone(emp_notif, "Employee must receive approval notification")

        # Verify audit log created
        audit_entry = self.db.query(AuditLog).filter(
            AuditLog.entity_id == req.id,
            AuditLog.action == "LEAVE APPROVED",
        ).first()
        self.assertIsNotNone(audit_entry, "Audit record must be created when leave is approved")

    def test_17_hr_rejects_leave_balance_not_deducted(self):
        """TEST 6: HR rejects -> REJECTED, Balance NOT deducted, Employee notified."""
        lt = self.db.query(LeaveType).filter(LeaveType.is_active == True).first()
        start = date.today() + timedelta(days=30)
        end = start + timedelta(days=1)

        # Clean any overlapping requests
        self.db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == self.emp_b.id,
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start,
        ).delete()
        self.db.commit()

        req = LeaveRequest(
            employee_id=self.emp_b.id,
            leave_type_id=lt.id,
            start_date=start,
            end_date=end,
            total_days=2.0,
            reason="Short break",
            status=LeaveStatus.PENDING,
        )
        self.db.add(req)
        bal = self.db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == self.emp_b.id,
            LeaveBalance.leave_type_id == lt.id,
            LeaveBalance.year == start.year,
        ).first()
        if bal:
            bal.pending_days += 2.0
        self.db.commit()
        self.db.refresh(req)

        used_before = bal.used_days if bal else 0.0

        # HR rejects
        res = self.client.put(
            f"/api/leave/requests/{req.id}/reject",
            json={"reason": "Project workload too high"},
            headers=self.hr_headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "REJECTED")

        # Verify used balance is NOT deducted
        if bal:
            self.db.refresh(bal)
            self.assertEqual(bal.used_days, used_before)

        # Verify employee notification created
        emp_notif = self.db.query(Notification).filter(
            Notification.user_id == self.emp_b_user.id,
            Notification.entity_id == req.id,
            Notification.title == "Leave Request Rejected",
        ).first()
        self.assertIsNotNone(emp_notif, "Employee must receive rejection notification")

    def test_18_employee_insufficient_balance_rejected(self):
        """TEST 7: Employee applies with insufficient balance -> Rejected (HTTP 400)."""
        lt = self.db.query(LeaveType).filter(LeaveType.is_active == True).first()

        start = date.today() + timedelta(days=40)
        end = start + timedelta(days=5)

        # Set employee balance remaining to 0 for start.year
        bal = self.db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == self.emp_a.id,
            LeaveBalance.leave_type_id == lt.id,
            LeaveBalance.year == start.year,
        ).first()
        if not bal:
            bal = LeaveBalance(
                employee_id=self.emp_a.id,
                leave_type_id=lt.id,
                year=start.year,
                total_allocated=15.0,
                used_days=15.0,
                pending_days=0.0,
            )
            self.db.add(bal)
            self.db.commit()
        else:
            bal.used_days = bal.total_allocated
            bal.pending_days = 0.0
            self.db.commit()

        # Clean any overlapping requests
        self.db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == self.emp_a.id,
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start,
        ).delete()
        self.db.commit()

        res = self.client.post(
            "/api/leave/requests",
            json={
                "leave_type_id": lt.id,
                "start_date": str(start),
                "end_date": str(end),
                "reason": "Exceeding vacation",
            },
            headers=self.emp_a_headers,
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Insufficient", res.json()["detail"])

    def test_19_employee_overlapping_leave_rejected(self):
        """TEST 8: Employee creates overlapping leave -> Rejected (HTTP 400)."""
        lt = self.db.query(LeaveType).filter(LeaveType.is_active == True).first()
        start = date.today() + timedelta(days=50)
        end = start + timedelta(days=5)

        # Reset balance so balance check passes
        bal = self.db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == self.emp_a.id,
            LeaveBalance.leave_type_id == lt.id,
            LeaveBalance.year == start.year,
        ).first()
        if not bal:
            bal = LeaveBalance(
                employee_id=self.emp_a.id,
                leave_type_id=lt.id,
                year=start.year,
                total_allocated=20.0,
                used_days=0.0,
                pending_days=0.0,
            )
            self.db.add(bal)
            self.db.commit()
        else:
            bal.used_days = 0.0
            bal.pending_days = 0.0
            self.db.commit()

        # Delete any existing requests for emp_a overlapping with this window
        self.db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == self.emp_a.id,
            LeaveRequest.start_date <= end + timedelta(days=5),
            LeaveRequest.end_date >= start - timedelta(days=5),
        ).delete()
        self.db.commit()

        # 1. First valid request
        res1 = self.client.post(
            "/api/leave/requests",
            json={
                "leave_type_id": lt.id,
                "start_date": str(start),
                "end_date": str(end),
                "reason": "Family vacation",
            },
            headers=self.emp_a_headers,
        )
        self.assertEqual(res1.status_code, 201)

        # 2. Overlapping request (middle of start and end)
        overlap_start = start + timedelta(days=2)
        overlap_end = end + timedelta(days=2)
        res2 = self.client.post(
            "/api/leave/requests",
            json={
                "leave_type_id": lt.id,
                "start_date": str(overlap_start),
                "end_date": str(overlap_end),
                "reason": "Duplicate overlapping request",
            },
            headers=self.emp_a_headers,
        )
        self.assertEqual(res2.status_code, 400)
        self.assertIn("overlapping", res2.json()["detail"].lower())

    def test_20_approved_leave_integrates_with_attendance_as_on_leave(self):
        """TEST 9: Approved leave -> Attendance shows ON_LEAVE."""
        lt = self.db.query(LeaveType).filter(LeaveType.is_active == True).first()
        today = date.today()

        # Delete any existing attendance for emp_a today for a clean test
        self.db.query(Attendance).filter(
            Attendance.employee_id == self.emp_a.id,
            Attendance.attendance_date == today,
        ).delete()
        self.db.commit()

        # Create an APPROVED leave covering today
        leave = LeaveRequest(
            employee_id=self.emp_a.id,
            leave_type_id=lt.id,
            start_date=today,
            end_date=today,
            total_days=1.0,
            reason="Approved sick leave for today",
            status=LeaveStatus.APPROVED,
        )
        self.db.add(leave)
        self.db.commit()

        # Check today's attendance endpoint
        res = self.client.get("/api/attendance/me/today", headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ON_LEAVE")

        # Employee check-in attempt should notify they are on leave
        checkin_res = self.client.post("/api/attendance/check-in", json={"remarks": "test"}, headers=self.emp_a_headers)
        self.assertEqual(checkin_res.status_code, 400)
        self.assertIn("approved leave", checkin_res.json()["detail"].lower())

    def test_21_employee_cannot_approve_own_leave(self):
        """TEST 10: Employee attempts to approve own leave through API -> 403 Forbidden."""
        lt = self.db.query(LeaveType).filter(LeaveType.is_active == True).first()
        req = LeaveRequest(
            employee_id=self.emp_a.id,
            leave_type_id=lt.id,
            start_date=date.today() + timedelta(days=320),
            end_date=date.today() + timedelta(days=321),
            total_days=2.0,
            reason="Test approve attempt",
            status=LeaveStatus.PENDING,
        )
        self.db.add(req)
        self.db.commit()
        self.db.refresh(req)

        # Attempt approve using Employee A headers
        res = self.client.put(f"/api/leave/requests/{req.id}/approve", json={"reason": "Self-approval"}, headers=self.emp_a_headers)
        self.assertEqual(res.status_code, 403, "Non-HR user must receive 403 Forbidden when attempting to approve leave")


if __name__ == "__main__":
    unittest.main()
