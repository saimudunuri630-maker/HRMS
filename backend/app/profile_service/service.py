from datetime import datetime, timezone
import os
import uuid
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.authentication_service.models import User
from app.employee_service.models import Employee, EmploymentStatus
from app.cloudinary_service import service as cloudinary_service
from app.profile_service.schemas import ProfileResponse, ProfileUpdateRequest


def get_or_create_profile(db: Session, user: User) -> Employee:
    employee = (
        db.query(Employee)
        .filter(Employee.user_id == user.id, Employee.deleted_at.is_(None))
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found for this account. Please contact HR.",
        )
    return employee


def build_profile_response(employee: Employee, user: User) -> ProfileResponse:
    full_name = f"{employee.first_name} {employee.last_name}".strip()
    return ProfileResponse(
        id=employee.id,
        user_id=user.id,
        email=user.email,
        role=user.role,
        employee_code=employee.employee_code,
        first_name=employee.first_name,
        last_name=employee.last_name,
        full_name=full_name or user.email.split("@")[0],
        phone=employee.phone,
        date_of_birth=employee.date_of_birth,
        address=employee.address,
        joining_date=employee.joining_date,
        department_id=employee.department_id,
        designation_id=employee.designation_id,
        employment_status=employee.employment_status.value if hasattr(employee.employment_status, "value") else str(employee.employment_status),
        profile_photo_url=employee.profile_photo_url,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
    )


def get_profile(db: Session, user: User) -> ProfileResponse:
    employee = get_or_create_profile(db, user)
    return build_profile_response(employee, user)


def update_profile(db: Session, user: User, data: ProfileUpdateRequest, raw_payload: dict | None = None) -> ProfileResponse:
    employee = get_or_create_profile(db, user)

    # STRICT IMMUTABLE CHECK:
    # Reject modification of email or employee code/number
    payload_keys = set()
    if raw_payload:
        payload_keys = set(raw_payload.keys())
    else:
        payload_keys = set(data.model_dump(exclude_unset=True).keys())

    if "email" in payload_keys or data.email is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee email is immutable and cannot be changed.",
        )

    if "employee_number" in payload_keys or data.employee_number is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee number is immutable and cannot be changed.",
        )

    if "employee_code" in payload_keys or data.employee_code is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee code is immutable and cannot be changed.",
        )

    updated_fields = []

    if data.first_name is not None:
        employee.first_name = data.first_name.strip()
        updated_fields.append("First Name")

    if data.last_name is not None:
        employee.last_name = data.last_name.strip()
        updated_fields.append("Last Name")

    if data.phone is not None:
        employee.phone = data.phone.strip()
        updated_fields.append("Phone Number")

    if data.date_of_birth is not None:
        employee.date_of_birth = data.date_of_birth
        updated_fields.append("Date of Birth")

    if data.address is not None:
        employee.address = data.address.strip()
        updated_fields.append("Address")

    # Sync User full name
    new_full_name = f"{employee.first_name} {employee.last_name}".strip()
    user.full_name = new_full_name

    employee.updated_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(employee)
    db.refresh(user)

    return build_profile_response(employee, user)


def upload_profile_photo(db: Session, user: User, file: UploadFile) -> ProfileResponse:
    employee = get_or_create_profile(db, user)

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, and WebP images are allowed.",
        )

    # Max 5MB check
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile photo must not exceed 5MB.",
        )

    # Delete old Cloudinary photo if exists
    if employee.profile_photo_public_id:
        try:
            cloudinary_service.delete_profile_photo(employee.profile_photo_public_id)
        except Exception:
            pass

    # Upload to Cloudinary with graceful fallback
    photo_url = None
    public_id = None
    try:
        res = cloudinary_service.upload_profile_photo(file.file)
        photo_url = res.get("url")
        public_id = res.get("public_id")
    except Exception as err:
        print(f"[WARNING] Cloudinary upload failed: {err}. Using generated avatar data.")
        # If offline/unreachable, create simulated URL
        photo_url = f"https://api.dicebear.com/7.x/initials/svg?seed={employee.first_name}+{employee.last_name}&backgroundColor=047857"
        public_id = f"local_{uuid.uuid4().hex[:8]}"

    employee.profile_photo_url = photo_url
    employee.profile_photo_public_id = public_id
    employee.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(employee)

    return build_profile_response(employee, user)
