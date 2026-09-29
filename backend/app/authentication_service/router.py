from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.authentication_service import service
from app.authentication_service.dependencies import get_current_user
from app.authentication_service.schemas import (
    MessageResponse,
    SendOTPRequest,
    TokenResponse,
    VerifyOTPRequest,
)
from app.core.database import get_db

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=MessageResponse)
@router.post("/send-otp", response_model=MessageResponse)
def send_otp(
    request: SendOTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    return service.send_login_otp(
        db=db,
        email=request.email,
        background_tasks=background_tasks
    )


@router.post("/verify-otp", response_model=TokenResponse)
@router.post("/verify", response_model=TokenResponse)
def verify_otp(
    request: VerifyOTPRequest,
    db: Session = Depends(get_db)
):
    return service.verify_login_otp(
        db=db,
        email=request.email,
        otp=request.otp
    )


@router.post("/resend-otp", response_model=MessageResponse)
def resend_otp(
    request: SendOTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    return service.send_login_otp(
        db=db,
        email=request.email,
        background_tasks=background_tasks
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    db: Session = Depends(get_db),
    auth_data=Depends(get_current_user)
):
    user, session = auth_data if isinstance(auth_data, tuple) else (auth_data, None)
    return service.logout(
        db=db,
        session_id=session.session_id if session else None,
        user=user,
    )


@router.post("/logout-all", response_model=MessageResponse)
def logout_all_devices(
    db: Session = Depends(get_db),
    auth_data=Depends(get_current_user)
):
    user = auth_data[0] if isinstance(auth_data, tuple) else auth_data
    return service.logout_all_devices(
        db=db,
        user_id=user.id
    )


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    auth_data=Depends(get_current_user),
):
    user = auth_data[0] if isinstance(auth_data, tuple) else auth_data
    from app.employee_service.models import Employee
    emp = db.query(Employee).filter(Employee.user_id == user.id, Employee.deleted_at.is_(None)).first()

    first_name = emp.first_name if emp else (user.full_name.split(" ")[0] if user.full_name else "User")
    last_name = emp.last_name if emp else (user.full_name.split(" ")[1] if user.full_name and len(user.full_name.split(" ")) > 1 else "")
    full_name = f"{first_name} {last_name}".strip() if (first_name or last_name) else (user.full_name or user.email.split("@")[0])

    return {
        "id": user.id,
        "email": user.email,
        "full_name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "employee_code": emp.employee_code if emp else None,
        "profile_photo_url": emp.profile_photo_url if emp else None,
    }