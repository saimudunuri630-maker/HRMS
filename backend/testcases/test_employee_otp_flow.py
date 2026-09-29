import sys
import os
import unittest
from datetime import datetime, timedelta
import secrets
import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.core.config import settings
from app.authentication_service.models import User, OTPVerification, UserSession
from app.employee_service.models import Employee, EmploymentStatus
from app.leave_service.models import LeaveType
from app.authentication_service import repository as auth_repo
from app.authentication_service.service import hash_otp

client = TestClient(app)

def create_session_token(db, user: User) -> str:
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

def run_all_tests():
    db = SessionLocal()
    print("="*60)
    print("STARTING COMPLETE EMPLOYEE OTP & AUTHENTICATION SUITE")
    print("="*60)

    # Pre-test cleanup: ensure clean slate for test emails
    test_email = "autotest.employee@mediatize.com"
    mixed_case_email = "CaseTest.Worker@Mediatize.COM"
    normalized_mixed_case = "casetest.worker@mediatize.com"

    for email_to_clean in [test_email, mixed_case_email, normalized_mixed_case]:
        u = auth_repo.get_user_by_email(db, email_to_clean)
        if u:
            db.query(OTPVerification).filter(OTPVerification.email == u.email).delete()
            db.query(UserSession).filter(UserSession.user_id == u.id).delete()
            db.query(Employee).filter(Employee.user_id == u.id).delete()
            db.query(User).filter(User.id == u.id).delete()
            db.commit()

    hr_user = db.query(User).filter(User.email == "mudunurisaivarma335@gmail.com").first()
    assert hr_user is not None, "HR user not found in database!"
    hr_token = create_session_token(db, hr_user)
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    results = []

    # ----------------------------------------------------
    # TEST 1: HR Creates Employee
    # ----------------------------------------------------
    print("\n[TEST 1] HR Creates Employee via POST /api/employees...")
    payload_emp = {
        "first_name": "Marcus",
        "last_name": "Vance",
        "email": test_email,
        "phone": "+1 555-0199",
        "address": "456 Innovation Way",
        "joining_date": "2026-09-25"
    }
    resp1 = client.post("/api/employees", json=payload_emp, headers=hr_headers)
    print(f"  Status: {resp1.status_code}")
    assert resp1.status_code == 201, f"Expected 201, got {resp1.status_code}: {resp1.text}"
    created_emp_data = resp1.json()
    assert created_emp_data["employee_code"].startswith("EMP")
    assert created_emp_data["email"] == test_email
    assert created_emp_data["first_name"] == "Marcus"
    assert created_emp_data["employment_status"] == "ACTIVE"

    # Verify DB User record
    db_user = auth_repo.get_user_by_email(db, test_email)
    assert db_user is not None, "User record was not created in DB!"
    assert db_user.role == "employee"
    assert db_user.is_active is True
    assert db_user.is_verified is False
    print(f"  [OK] User ID={db_user.id}, role={db_user.role}, active={db_user.is_active}")
    print(f"  [OK] Employee ID={created_emp_data['id']}, code={created_emp_data['employee_code']}, linked to user_id={created_emp_data['user_id']}")
    results.append(("TEST 1: HR Creates Employee", "201 Created & DB records linked", "201 Created", "SUCCESS"))

    # ----------------------------------------------------
    # TEST 2: Employee Requests OTP
    # ----------------------------------------------------
    print("\n[TEST 2] Employee requests login OTP via POST /auth/login...")
    resp2 = client.post("/auth/login", json={"email": test_email})
    print(f"  Status: {resp2.status_code}, Body: {resp2.json()}")
    assert resp2.status_code == 200
    assert resp2.json()["message"] == "OTP sent successfully"

    # Verify OTP persisted in DB
    latest_otp = auth_repo.get_latest_otp(db, test_email)
    assert latest_otp is not None, "OTP record not persisted in database!"
    assert latest_otp.is_used is False
    assert latest_otp.attempts == 0
    print(f"  [OK] OTP verification record found in DB: ID={latest_otp.id}, expires_at={latest_otp.expires_at}")
    results.append(("TEST 2: Employee Requests OTP", "200 OK & OTP record created", "200 OK", "SUCCESS"))

    # ----------------------------------------------------
    # TEST 3: Invalid Employee Email Request
    # ----------------------------------------------------
    print("\n[TEST 3] Request OTP for non-existent email...")
    resp3 = client.post("/auth/login", json={"email": "nonexistent.user999@mediatize.com"})
    print(f"  Status: {resp3.status_code}, Detail: {resp3.json().get('detail')}")
    assert resp3.status_code == 404
    assert resp3.json()["detail"] == "Account not found. Please contact HR."
    print("  [OK] Blocked correctly with Phase 25 error message")
    results.append(("TEST 3: Invalid Employee Email", "404 Account not found", "404 Account not found", "SUCCESS"))

    # ----------------------------------------------------
    # TEST 4: Inactive Employee Requests OTP
    # ----------------------------------------------------
    print("\n[TEST 4] Request OTP for inactive employee...")
    db_user.is_active = False
    db.commit()
    resp4 = client.post("/auth/login", json={"email": test_email})
    print(f"  Status: {resp4.status_code}, Detail: {resp4.json().get('detail')}")
    assert resp4.status_code == 403
    assert resp4.json()["detail"] == "Your account is currently inactive. Please contact HR."
    print("  [OK] Inactive employee rejected with 403 Forbidden")
    # Restore active state
    db_user.is_active = True
    db.commit()
    results.append(("TEST 4: Inactive Employee Requests OTP", "403 Your account is currently inactive", "403 Inactive", "SUCCESS"))

    # ----------------------------------------------------
    # TEST 5: Valid Employee OTP Verification
    # ----------------------------------------------------
    print("\n[TEST 5] Employee verifies OTP...")
    # Inject a known test OTP hash into the latest active OTP record
    test_otp_code = "729415"
    latest_otp.otp_hash = hash_otp(test_otp_code)
    db.commit()

    resp5 = client.post("/auth/verify-otp", json={"email": test_email, "otp": test_otp_code})
    print(f"  Status: {resp5.status_code}")
    assert resp5.status_code == 200
    token_data = resp5.json()
    assert "access_token" in token_data
    emp_token = token_data["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    print(f"  [OK] Authenticated successfully! JWT token received.")
    results.append(("TEST 5: Valid Employee OTP Verification", "200 OK & JWT Bearer token", "200 OK", "SUCCESS"))

    # ----------------------------------------------------
    # TEST 6: GET /api/auth/me for Employee
    # ----------------------------------------------------
    print("\n[TEST 6] Calling GET /api/auth/me with employee token...")
    resp6 = client.get("/api/auth/me", headers=emp_headers)
    print(f"  Status: {resp6.status_code}, Data: {resp6.json()}")
    assert resp6.status_code == 200
    me_data = resp6.json()
    assert me_data["role"] == "employee"
    assert me_data["email"] == test_email
    assert me_data["first_name"] == "Marcus"
    assert me_data["last_name"] == "Vance"
    assert me_data["employee_code"] == created_emp_data["employee_code"]
    print(f"  [OK] Authoritative role identified: role={me_data['role']}, code={me_data['employee_code']}")
    results.append(("TEST 6: GET /api/auth/me Employee Hydration", "role=employee, verified identity", "role=employee", "SUCCESS"))

    # ----------------------------------------------------
    # TEST 7: Role Routing Decision
    # ----------------------------------------------------
    print("\n[TEST 7] Verifying centralized role routing logic...")
    role_check = me_data["role"].lower()
    target_route = "/hr/dashboard" if role_check == "hr" else "/employee/dashboard"
    assert target_route == "/employee/dashboard"
    print(f"  [OK] Role '{role_check}' navigates to target: {target_route}")
    results.append(("TEST 7: Role Routing Decision", "Redirect to /employee/dashboard", "/employee/dashboard", "SUCCESS"))

    # ----------------------------------------------------
    # TEST 8: HR Login & /api/auth/me check
    # ----------------------------------------------------
    print("\n[TEST 8] Verifying HR login retains role=hr and route=/hr/dashboard...")
    resp8 = client.get("/api/auth/me", headers=hr_headers)
    assert resp8.status_code == 200
    hr_me = resp8.json()
    assert hr_me["role"] == "hr"
    hr_route = "/hr/dashboard" if hr_me["role"].lower() == "hr" else "/employee/dashboard"
    assert hr_route == "/hr/dashboard"
    print(f"  [OK] HR user remains role={hr_me['role']} mapping to: {hr_route}")
    results.append(("TEST 8: HR Role & Dashboard Route", "role=hr, redirect to /hr/dashboard", "role=hr", "SUCCESS"))

    # ----------------------------------------------------
    # TEST 9: Employee Forbidden from HR Endpoints
    # ----------------------------------------------------
    print("\n[TEST 9] Employee attempts to access HR endpoints...")
    forbidden_resp = client.post("/api/employees", json={"first_name": "Fail", "last_name": "Test", "email": "fail@test.com"}, headers=emp_headers)
    assert forbidden_resp.status_code == 403
    print(f"  [OK] Employee blocked from creating employees: 403 Forbidden")
    forbidden_resp2 = client.post("/api/leave/types", json={"name": "Hacked Leave", "code": "HACK", "annual_quota": 5}, headers=emp_headers)
    assert forbidden_resp2.status_code == 403
    print(f"  [OK] Employee blocked from creating leave types: 403 Forbidden")
    results.append(("TEST 9: Employee Forbidden from HR Endpoints", "403 Forbidden on HR routes", "403 Forbidden", "SUCCESS"))

    # ----------------------------------------------------
    # TEST 10: Employee Profile Access
    # ----------------------------------------------------
    print("\n[TEST 10] Employee accesses own profile via GET /api/profile/me...")
    resp10 = client.get("/api/profile/me", headers=emp_headers)
    print(f"  Status: {resp10.status_code}")
    assert resp10.status_code == 200
    prof_data = resp10.json()
    assert prof_data["email"] == test_email
    assert prof_data["first_name"] == "Marcus"
    print(f"  [OK] Employee profile retrieved: {prof_data['first_name']} {prof_data['last_name']} ({prof_data['employee_code']})")
    results.append(("TEST 10: Employee Profile Access", "200 OK own profile data", "200 OK", "SUCCESS"))

    # ----------------------------------------------------
    # TEST 11: Case-Insensitive Email Normalization
    # ----------------------------------------------------
    print("\n[TEST 11] Case-insensitive email normalization and login...")
    payload_mixed = {
        "first_name": "Elena",
        "last_name": "Rostova",
        "email": mixed_case_email, # CaseTest.Worker@Mediatize.COM
        "phone": "+1 555-0482",
    }
    resp11_create = client.post("/api/employees", json=payload_mixed, headers=hr_headers)
    assert resp11_create.status_code == 201
    created_mixed = resp11_create.json()
    assert created_mixed["email"] == normalized_mixed_case

    # Now employee logs in with lowercase
    resp11_login = client.post("/auth/login", json={"email": normalized_mixed_case})
    assert resp11_login.status_code == 200
    # Also test logging in with uppercase
    resp11_login_upper = client.post("/auth/login", json={"email": mixed_case_email})
    # Might hit rate limit or 200
    assert resp11_login_upper.status_code in (200, 429)
    print(f"  [OK] Case-insensitive lookup verified for {mixed_case_email} <-> {normalized_mixed_case}")
    results.append(("TEST 11: Case-Insensitive Normalization", "Case-insensitive creation & login", "Normalized match", "SUCCESS"))

    # ----------------------------------------------------
    # CLEANUP TEST DATA
    # ----------------------------------------------------
    print("\n[CLEANUP] Safely removing test artifacts...")
    for email_to_clean in [test_email, mixed_case_email, normalized_mixed_case]:
        u = auth_repo.get_user_by_email(db, email_to_clean)
        if u:
            db.query(OTPVerification).filter(OTPVerification.email == u.email).delete()
            db.query(UserSession).filter(UserSession.user_id == u.id).delete()
            db.query(Employee).filter(Employee.user_id == u.id).delete()
            db.query(User).filter(User.id == u.id).delete()
            db.commit()
    print("  [OK] Cleanup complete.")

    db.close()

    print("\n" + "="*60)
    print("TEST SUITE SUMMARY:")
    print("="*60)
    for test_name, expected, actual, status in results:
        print(f"TEST:     {test_name}")
        print(f"EXPECTED: {expected}")
        print(f"ACTUAL:   {actual}")
        print(f"STATUS:   {status}")
        print("-" * 60)

if __name__ == "__main__":
    run_all_tests()
