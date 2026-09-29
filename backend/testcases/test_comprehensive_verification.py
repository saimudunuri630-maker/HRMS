import sys
import os
from datetime import date, timedelta
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import SessionLocal
from app.authentication_service.models import User, OTPVerification, UserSession
from app.employee_service.models import Employee
from app.leave_service.models import LeaveType, LeaveBalance, LeaveRequest, LeaveStatus
import jwt
import secrets
from datetime import datetime
from app.core.config import settings
from app.authentication_service import repository as auth_repo

def create_test_token(db, user):
    session_id = secrets.token_urlsafe(32)
    session_expires_at = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    auth_repo.create_session(
        db=db,
        user_id=user.id,
        session_id=session_id,
        expires_at=session_expires_at,
    )
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "session_id": session_id,
        "exp": session_expires_at,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

client = TestClient(app)

def run_tests():
    print("========================================================")
    print("STARTING COMPREHENSIVE ARCHITECTURAL VERIFICATION SUITE")
    print("========================================================")

    db = SessionLocal()

    # --------------------------------------------------------
    # STEP 1: VERIFY HR ACCOUNT IN DB
    # --------------------------------------------------------
    print("\n[TEST 1] Verifying Real HR User and Linked Employee...")
    hr_user = db.query(User).filter(User.role == "hr").first()
    assert hr_user is not None, "HR User not found in database!"
    print(f"  [OK] HR User Found: ID={hr_user.id}, Email={hr_user.email}, Role={hr_user.role}")

    hr_emp = db.query(Employee).filter(Employee.user_id == hr_user.id).first()
    assert hr_emp is not None, "Linked HR Employee profile not found!"
    assert hr_emp.user_id == hr_user.id, "HR Employee profile not linked 1:1 to HR user!"
    print(f"  [OK] HR Employee Found: ID={hr_emp.id}, Code={hr_emp.employee_code}, Name={hr_emp.first_name} {hr_emp.last_name}")

    # Generate authoritative HR JWT Token
    hr_token = create_test_token(db, hr_user)
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    # --------------------------------------------------------
    # STEP 2: TEST /api/auth/me (AUTHORITATIVE SOURCE OF TRUTH)
    # --------------------------------------------------------
    print("\n[TEST 2] Testing GET /api/auth/me...")
    me_resp = client.get("/api/auth/me", headers=hr_headers)
    assert me_resp.status_code == 200, f"Expected 200, got {me_resp.status_code}: {me_resp.text}"
    me_data = me_resp.json()
    assert me_data["id"] == hr_user.id
    assert me_data["email"] == hr_user.email
    assert me_data["role"] == "hr"
    assert me_data["employee_code"] == hr_emp.employee_code
    print(f"  [OK] /api/auth/me authoritative data verified: {me_data['full_name']} ({me_data['role']})")

    # --------------------------------------------------------
    # STEP 3: TEST IMMUTABLE FIELDS IN PROFILE SERVICE
    # --------------------------------------------------------
    print("\n[TEST 3] Testing Profile Immutability & Validation...")
    # Attempt email change -> Must return 400 Bad Request
    bad_email_resp = client.put("/api/profile/me", json={"email": "hacked@company.com"}, headers=hr_headers)
    assert bad_email_resp.status_code == 400, f"Expected 400 for immutable email, got {bad_email_resp.status_code}"
    print(f"  [OK] Modifying email correctly blocked (400 Bad Request): {bad_email_resp.json()['detail']}")

    # Attempt employee_code / employee_number change -> Must return 400 Bad Request
    bad_code_resp = client.put("/api/profile/me", json={"employee_code": "EMP-999"}, headers=hr_headers)
    assert bad_code_resp.status_code == 400, f"Expected 400 for immutable code, got {bad_code_resp.status_code}"
    print(f"  [OK] Modifying employee number correctly blocked (400 Bad Request): {bad_code_resp.json()['detail']}")

    # Valid profile update
    valid_upd_resp = client.put("/api/profile/me", json={"first_name": "Sai", "last_name": "Varma", "phone": "+91 9999988888"}, headers=hr_headers)
    assert valid_upd_resp.status_code == 200, f"Expected 200, got {valid_upd_resp.status_code}"
    print("  [OK] Profile fields updated successfully with email confirmation trigger")

    # --------------------------------------------------------
    # STEP 4: HR CREATES NEW EMPLOYEE (ISOLATION TEST)
    # --------------------------------------------------------
    print("\n[TEST 4] Testing HR Employee Creation & Profile State Isolation...")
    test_emp_email = "emp_verify_auto@mediatize.com"

    # Pre-clean if leftover from prior run
    existing_u = db.query(User).filter(User.email == test_emp_email).first()
    if existing_u:
        db.query(Employee).filter(Employee.user_id == existing_u.id).delete()
        db.query(UserSession).filter(UserSession.user_id == existing_u.id).delete()
        db.delete(existing_u)
        db.commit()

    create_payload = {
        "first_name": "David",
        "last_name": "Miller",
        "email": test_emp_email,
        "phone": "+1 555-0199",
        "joining_date": str(date.today()),
        "address": "456 Tech Park",
    }
    create_resp = client.post("/api/employees", json=create_payload, headers=hr_headers)
    assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.text}"
    created_data = create_resp.json()
    new_emp_id = created_data["id"]
    new_user_id = created_data["user_id"]
    print(f"  [OK] Employee created: {created_data['first_name']} {created_data['last_name']} ({created_data['employee_code']})")

    # CRITICAL: Verify HR is STILL the authenticated user in /api/auth/me
    me_after_create = client.get("/api/auth/me", headers=hr_headers).json()
    assert me_after_create["email"] == hr_user.email, "CRITICAL ERROR: HR currentUser was mutated upon employee creation!"
    assert me_after_create["role"] == "hr"
    print(f"  [OK] CRITICAL CHECK PASSED: HR currentUser remains intact as '{me_after_create['full_name']}' ({me_after_create['role']})")

    # Duplicate email prevention check -> Must return 409 Conflict
    dup_resp = client.post("/api/employees", json=create_payload, headers=hr_headers)
    assert dup_resp.status_code == 409, f"Expected 409, got {dup_resp.status_code}"
    print("  [OK] Duplicate email prevention verified (409 Conflict)")

    # --------------------------------------------------------
    # STEP 5: EMPLOYEE LOGIN & ROLE-BASED DASHBOARD
    # --------------------------------------------------------
    print("\n[TEST 5] Testing Employee Login & Authentication...")
    new_user_obj = db.query(User).filter(User.id == new_user_id).first()
    emp_token = create_test_token(db, new_user_obj)
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    emp_me_resp = client.get("/api/auth/me", headers=emp_headers)
    assert emp_me_resp.status_code == 200
    emp_me = emp_me_resp.json()
    assert emp_me["role"] == "employee"
    assert emp_me["email"] == test_emp_email
    print(f"  [OK] Employee authenticated: {emp_me['full_name']} ({emp_me['role']})")

    # Employee dashboard summary
    emp_dash_resp = client.get("/api/employee/dashboard/summary", headers=emp_headers)
    assert emp_dash_resp.status_code == 200
    emp_dash = emp_dash_resp.json()
    assert emp_dash["role"] == "employee"
    assert "leave_balance" in emp_dash
    print(f"  [OK] Employee Dashboard metrics: Leave Balance={emp_dash['leave_balance']}, Projects={emp_dash['my_projects_count']}")

    # --------------------------------------------------------
    # STEP 6: ROLE-BASED ACCESS CONTROL (RBAC) SECURITY
    # --------------------------------------------------------
    print("\n[TEST 6] Testing Role Security & Forbidden Boundaries (403 Forbidden)...")
    # Employee attempts HR-only endpoints:
    # 1. POST /api/employees
    forbidden_create = client.post("/api/employees", json=create_payload, headers=emp_headers)
    assert forbidden_create.status_code == 403, f"Expected 403, got {forbidden_create.status_code}"
    print("  [OK] Employee cannot create employees (403 Forbidden)")

    # 2. GET /api/employees (Employee Directory HR management)
    forbidden_list = client.get("/api/employees", headers=emp_headers)
    assert forbidden_list.status_code == 403, f"Expected 403, got {forbidden_list.status_code}"
    print("  [OK] Employee cannot access HR employee directory (403 Forbidden)")

    # 3. GET /api/hr/dashboard/summary
    forbidden_hr_dash = client.get("/api/hr/dashboard/summary", headers=emp_headers)
    assert forbidden_hr_dash.status_code == 403, f"Expected 403, got {forbidden_hr_dash.status_code}"
    print("  [OK] Employee cannot view HR-wide company dashboard (403 Forbidden)")

    # 4. Unauthenticated access -> Must return 401 Unauthorized
    unauth_resp = client.get("/api/auth/me")
    assert unauth_resp.status_code == 401, f"Expected 401, got {unauth_resp.status_code}"
    print("  [OK] Unauthenticated requests return 401 Unauthorized")

    # --------------------------------------------------------
    # STEP 7: CONSOLIDATED LEAVE SERVICE WORKFLOW
    # --------------------------------------------------------
    print("\n[TEST 7] Testing Consolidated Leave Service Architecture...")
    # 1. Get Leave Types (both HR and Employee can view)
    types_resp = client.get("/api/leave/types", headers=emp_headers)
    assert types_resp.status_code == 200
    types_list = types_resp.json()
    assert len(types_list) >= 3, "Expected at least 3 default leave types"
    annual_type = next((t for t in types_list if t["code"] == "ANNUAL"), types_list[0])
    print(f"  [OK] Leave Types retrieved ({len(types_list)} types active). Selected: {annual_type['name']}")

    # 2. Employee cannot create leave type
    forbidden_type = client.post("/api/leave/types", json={"name": "Hacked", "code": "HACK", "days_per_year": 5}, headers=emp_headers)
    assert forbidden_type.status_code == 403
    print("  [OK] Employee cannot create leave types (403 Forbidden)")

    # 3. Employee checks balance
    bal_resp = client.get("/api/leave/balances", headers=emp_headers)
    assert bal_resp.status_code == 200
    bals = bal_resp.json()
    assert len(bals) > 0
    print(f"  [OK] Employee balances initialized: {[b['leave_type_code'] + ': ' + str(b['remaining_days']) for b in bals]}")

    # 4. Employee applies for leave
    start_d = str(date.today() + timedelta(days=5))
    end_d = str(date.today() + timedelta(days=6))
    apply_resp = client.post("/api/leave/requests", json={
        "leave_type_id": annual_type["id"],
        "start_date": start_d,
        "end_date": end_d,
        "reason": "Personal family event",
    }, headers=emp_headers)
    assert apply_resp.status_code == 201, f"Expected 201, got {apply_resp.status_code}: {apply_resp.text}"
    leave_req = apply_resp.json()
    assert leave_req["status"] == "PENDING"
    assert leave_req["total_days"] == 2.0
    print(f"  [OK] Leave application created: Request ID={leave_req['id']}, Days={leave_req['total_days']}, Status={leave_req['status']}")

    # 5. Employee CANNOT approve leave
    forbidden_approve = client.post(f"/api/leave/requests/{leave_req['id']}/approve", json={"reason": "Self approved"}, headers=emp_headers)
    assert forbidden_approve.status_code == 403
    print("  [OK] Employee self-approval blocked (403 Forbidden)")

    # 6. HR views requests & approves
    hr_reqs_resp = client.get("/api/leave/requests", headers=hr_headers)
    assert hr_reqs_resp.status_code == 200
    all_reqs = hr_reqs_resp.json()["requests"]
    assert any(r["id"] == leave_req["id"] for r in all_reqs)
    print(f"  [OK] HR viewed leave requests ({len(all_reqs)} requests in queue)")

    approve_resp = client.post(f"/api/leave/requests/{leave_req['id']}/approve", json={"reason": "Approved by HR Admin"}, headers=hr_headers)
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    assert approved_data["status"] == "APPROVED"
    assert approved_data["action_by_name"] == hr_user.full_name
    print(f"  [OK] Leave request approved by HR: Status={approved_data['status']}, ActionBy={approved_data['action_by_name']}")

    # 7. Employee applies again and cancels own pending request
    start_d2 = str(date.today() + timedelta(days=15))
    end_d2 = str(date.today() + timedelta(days=15))
    apply_resp2 = client.post("/api/leave/requests", json={
        "leave_type_id": annual_type["id"],
        "start_date": start_d2,
        "end_date": end_d2,
        "reason": "Doctor appointment",
    }, headers=emp_headers)
    assert apply_resp2.status_code == 201
    leave_req2 = apply_resp2.json()

    cancel_resp = client.post(f"/api/leave/requests/{leave_req2['id']}/cancel", headers=emp_headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"
    print(f"  [OK] Employee cancelled own pending request: Status={cancel_resp.json()['status']}")

    # --------------------------------------------------------
    # STEP 8: SAFE CLEANUP OF TEST ARTIFACTS
    # --------------------------------------------------------
    print("\n[TEST 8] Safely Cleaning Test Data & Preserving Referential Integrity...")
    # Delete test employee's leave requests & balances
    db.query(LeaveRequest).filter(LeaveRequest.employee_id == new_emp_id).delete()
    db.query(LeaveBalance).filter(LeaveBalance.employee_id == new_emp_id).delete()
    # Delete test employee
    db.query(Employee).filter(Employee.id == new_emp_id).delete()
    # Delete test user sessions and user
    db.query(UserSession).filter(UserSession.user_id == new_user_id).delete()
    db.query(User).filter(User.id == new_user_id).delete()
    db.commit()

    # Final DB integrity verification
    remaining_users = db.query(User).all()
    remaining_employees = db.query(Employee).all()
    assert len(remaining_users) == 1, f"Expected exactly 1 user, found {len(remaining_users)}"
    assert len(remaining_employees) == 1, f"Expected exactly 1 employee, found {len(remaining_employees)}"
    assert remaining_users[0].email == hr_user.email
    assert remaining_employees[0].user_id == hr_user.id
    print("  [OK] Test artifacts cleaned successfully.")
    print(f"  [OK] Database State: Exactly 1 HR User ({remaining_users[0].email}) & 1 Linked Employee ({remaining_employees[0].employee_code})")

    db.close()
    print("\n========================================================")
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("========================================================")

if __name__ == "__main__":
    run_tests()
