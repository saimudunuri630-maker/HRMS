import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Any

import jwt
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.authentication_service import repository
from app.core.config import settings
from app.email_service.service import send_otp_email


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def send_login_otp(db: Session, email: str, background_tasks: BackgroundTasks = None):
    clean_email = email.strip().lower() if email else ""
    print(f"[AUTH] Login OTP requested for email: {clean_email}")

    user = repository.get_user_by_email(db, clean_email)

    if not user:
        print(f"[AUTH] User not found for email: {clean_email}")
        raise HTTPException(
            status_code=404,
            detail="Account not found. Please contact HR."
        )

    if not user.is_active:
        print(f"[AUTH] User inactive for email: {clean_email}")
        raise HTTPException(
            status_code=403,
            detail="Your account is currently inactive. Please contact HR."
        )

    print(f"[AUTH] User verified: ID={user.id}, role={user.role}, active={user.is_active}")

    last_otp = repository.get_last_otp(db, clean_email)

    if last_otp:
        seconds_since_last_otp = (
            datetime.utcnow() - last_otp.created_at
        ).total_seconds()

        if seconds_since_last_otp < 60:
            remaining_seconds = int(60 - seconds_since_last_otp)
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {remaining_seconds} seconds before requesting another OTP"
            )

    repository.invalidate_previous_otps(db, clean_email)

    otp = generate_otp()
    otp_hash = hash_otp(otp)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    repository.create_otp(
        db=db,
        email=clean_email,
        otp_hash=otp_hash,
        expires_at=expires_at
    )
    print(f"[AUTH] OTP record persisted to database for {clean_email}")

    # Dispatch email and verify delivery result
    email_delivered = send_otp_email(
        recipient_email=clean_email,
        otp=otp,
        full_name=user.full_name
    )

    if not email_delivered:
        print(f"[AUTH] Email delivery failed via SMTP for {clean_email}")
        raise HTTPException(
            status_code=500,
            detail="Unable to send OTP right now. Please try again."
        )

    print(f"[AUTH] OTP email sent successfully to {clean_email}")

    return {
        "message": "OTP sent successfully"
    }


def verify_login_otp(
    db: Session,
    email: str,
    otp: str
):
    clean_email = email.strip().lower() if email else ""
    user = repository.get_user_by_email(db, clean_email)

    if not user:
        raise HTTPException(status_code=404, detail="Account not found. Please contact HR.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Your account is currently inactive. Please contact HR.")

    otp_record = repository.get_latest_otp(db, clean_email)

    if not otp_record:
        raise HTTPException(status_code=400, detail="OTP not found or already used")

    if datetime.utcnow() > otp_record.expires_at:
        repository.mark_otp_as_used(db, otp_record)
        raise HTTPException(status_code=400, detail="OTP has expired")

    if otp_record.attempts >= 5:
        repository.mark_otp_as_used(db, otp_record)
        raise HTTPException(status_code=400, detail="Too many incorrect attempts")

    if hash_otp(otp) != otp_record.otp_hash:
        repository.increment_otp_attempts(db, otp_record)
        try:
            from app.audit_service.service import log_audit_event
            log_audit_event(
                actor_user_id=user.id,
                action="LOGIN_FAILED",
                module="AUTHENTICATION",
                entity_type="USER",
                entity_id=user.id,
                description=f"Failed login attempt for {user.email}: Invalid OTP",
                db=db,
            )
        except Exception:
            pass

        if otp_record.attempts >= 5:
            repository.mark_otp_as_used(db, otp_record)
            raise HTTPException(status_code=400, detail="Too many incorrect attempts. Please request a new OTP.")
        raise HTTPException(status_code=400, detail="Invalid OTP")

    repository.mark_otp_as_used(db, otp_record)
    user.is_verified = True
    db.commit()
    db.refresh(user)

    session_id = secrets.token_urlsafe(32)
    session_expires_at = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    repository.create_session(
        db=db,
        user_id=user.id,
        session_id=session_id,
        expires_at=session_expires_at
    )

    # Mandatory LOGIN audit logging for all users (both HR and Employee)
    try:
        from app.audit_service.service import log_audit_event
        from app.employee_service.models import Employee
        emp = db.query(Employee).filter(Employee.user_id == user.id, Employee.deleted_at.is_(None)).first()
        rec_time = datetime.now()
        log_audit_event(
            actor_user_id=user.id,
            action="LOGIN",
            module="AUTHENTICATION",
            entity_type="USER",
            entity_id=user.id,
            employee_id=emp.id if emp else None,
            description=f"User {user.email} logged in successfully",
            new_value={
                "user_email": user.email,
                "login_time": rec_time.strftime("%I:%M %p"),
                "date": rec_time.strftime("%Y-%m-%d"),
                "event": "LOGIN",
            },
            db=db,
        )
    except Exception as err:
        print(f"[AUTH] Failed to log login audit: {err}")

    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "session_id": session_id,
        "exp": session_expires_at
    }

    access_token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


def logout(db: Session, session_id: Optional[str] = None, user: Optional[Any] = None):
    target_user = user
    if session_id:
        session = repository.get_session(db, session_id)
        if session:
            if not target_user:
                target_user = session.user
            repository.invalidate_session(db, session)

    if target_user:
        try:
            from app.audit_service.service import log_audit_event
            from app.employee_service.models import Employee
            emp = db.query(Employee).filter(Employee.user_id == target_user.id, Employee.deleted_at.is_(None)).first()
            rec_time = datetime.now()
            log_audit_event(
                actor_user_id=target_user.id,
                action="LOGOUT",
                module="AUTHENTICATION",
                entity_type="USER",
                entity_id=target_user.id,
                employee_id=emp.id if emp else None,
                description=f"User {target_user.email} logged out",
                new_value={
                    "user_email": target_user.email,
                    "logout_time": rec_time.strftime("%I:%M %p"),
                    "date": rec_time.strftime("%Y-%m-%d"),
                    "event": "LOGOUT",
                },
                db=db,
            )
        except Exception as err:
            print(f"[AUTH] Failed to log logout audit: {err}")

    return {"message": "Logged out successfully"}


def logout_all_devices(db: Session, user_id: int):
    repository.invalidate_all_user_sessions(db, user_id)
    try:
        from app.audit_service.service import log_audit_event
        from app.employee_service.models import Employee
        emp = db.query(Employee).filter(Employee.user_id == user_id, Employee.deleted_at.is_(None)).first()
        rec_time = datetime.now()
        log_audit_event(
            actor_user_id=user_id,
            action="LOGOUT",
            module="AUTHENTICATION",
            entity_type="USER",
            entity_id=user_id,
            employee_id=emp.id if emp else None,
            description=f"User #{user_id} logged out from all devices",
            new_value={
                "logout_time": rec_time.strftime("%I:%M %p"),
                "date": rec_time.strftime("%Y-%m-%d"),
                "event": "LOGOUT_ALL_DEVICES",
            },
            db=db,
        )
    except Exception as err:
        print(f"[AUTH] Failed to log logout_all audit: {err}")

    return {"message": "Logged out from all devices successfully"}