from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.authentication_service.models import (
    User,
    OTPVerification,
    UserSession,
)


# ============================================================
# USER QUERIES
# ============================================================

def get_user_by_email(
    db: Session,
    email: str
):
    clean_email = email.strip().lower() if email else ""
    return (
        db.query(User)
        .filter(func.lower(User.email) == clean_email)
        .first()
    )


def get_user_by_id(
    db: Session,
    user_id: int
):
    return (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )


# ============================================================
# OTP QUERIES
# ============================================================

def create_otp(
    db: Session,
    email: str,
    otp_hash: str,
    expires_at: datetime
):
    clean_email = email.strip().lower() if email else ""
    otp = OTPVerification(
        email=clean_email,
        otp_hash=otp_hash,
        expires_at=expires_at,
        attempts=0,
        is_used=False,
    )

    db.add(otp)
    db.commit()
    db.refresh(otp)

    return otp


def get_latest_otp(
    db: Session,
    email: str
):
    clean_email = email.strip().lower() if email else ""
    return (
        db.query(OTPVerification)
        .filter(
            func.lower(OTPVerification.email) == clean_email,
            OTPVerification.is_used.is_(False),
        )
        .order_by(
            OTPVerification.created_at.desc()
        )
        .first()
    )


def invalidate_previous_otps(
    db: Session,
    email: str
):
    clean_email = email.strip().lower() if email else ""
    (
        db.query(OTPVerification)
        .filter(
            func.lower(OTPVerification.email) == clean_email,
            OTPVerification.is_used.is_(False),
        )
        .update(
            {
                OTPVerification.is_used: True
            },
            synchronize_session=False,
        )
    )

    db.commit()


def mark_otp_as_used(
    db: Session,
    otp: OTPVerification
):
    otp.is_used = True

    db.commit()
    db.refresh(otp)

    return otp


def increment_otp_attempts(
    db: Session,
    otp: OTPVerification
):
    otp.attempts += 1

    db.commit()
    db.refresh(otp)

    return otp
def get_last_otp(
    db: Session,
    email: str
):
    clean_email = email.strip().lower() if email else ""
    return (
        db.query(OTPVerification)
        .filter(
            func.lower(OTPVerification.email) == clean_email
        )
        .order_by(
            OTPVerification.created_at.desc()
        )
        .first()
    )


# ============================================================
# SESSION QUERIES
# ============================================================

def create_session(
    db: Session,
    user_id: int,
    session_id: str,
    expires_at: datetime,
):
    session = UserSession(
        user_id=user_id,
        session_id=session_id,
        expires_at=expires_at,
        last_activity=datetime.utcnow(),
        is_active=True,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def get_session(
    db: Session,
    session_id: str
):
    return (
        db.query(UserSession)
        .filter(
            UserSession.session_id == session_id,
            UserSession.is_active.is_(True),
        )
        .first()
    )


def update_last_activity(
    db: Session,
    session: UserSession
):
    session.last_activity = datetime.utcnow()

    db.commit()
    db.refresh(session)

    return session


def invalidate_session(
    db: Session,
    session: UserSession
):
    session.is_active = False

    db.commit()
    db.refresh(session)

    return session


def invalidate_all_user_sessions(
    db: Session,
    user_id: int
):
    (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user_id,
            UserSession.is_active.is_(True),
        )
        .update(
            {
                UserSession.is_active: False
            },
            synchronize_session=False,
        )
    )

    db.commit()