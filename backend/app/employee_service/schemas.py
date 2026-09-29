from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.employee_service.models import EmploymentStatus


# =========================
# CREATE EMPLOYEE
# =========================

class EmployeeCreate(BaseModel):
    email: EmailStr

    first_name: str = Field(
        min_length=1,
        max_length=100
    )

    last_name: str = Field(
        min_length=1,
        max_length=100
    )

    phone: str | None = Field(
        default=None,
        max_length=20
    )

    employee_code: str | None = Field(
        default=None,
        max_length=50
    )

    date_of_birth: date | None = None

    address: str | None = Field(
        default=None,
        max_length=255
    )

    joining_date: date | None = None

    department: str | None = Field(
        default="Engineering & Operations",
        max_length=100
    )

    designation: str = Field(
        min_length=1,
        max_length=100
    )

    department_id: int | None = None

    designation_id: int | None = None


# =========================
# UPDATE EMPLOYEE
# =========================

class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    phone: str | None = Field(
        default=None,
        max_length=20
    )

    date_of_birth: date | None = None

    address: str | None = Field(
        default=None,
        max_length=255
    )

    joining_date: date | None = None

    department: str | None = Field(
        default=None,
        max_length=100
    )

    designation: str | None = Field(
        default=None,
        max_length=100
    )

    department_id: int | None = None

    designation_id: int | None = None

    employment_status: EmploymentStatus | None = None


# =========================
# EMPLOYEE PROFILE UPDATE
# =========================

class EmployeeProfileUpdate(BaseModel):
    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )
    phone: str | None = Field(
        default=None,
        max_length=20
    )
    date_of_birth: date | None = None
    address: str | None = Field(
        default=None,
        max_length=255
    )

# =========================
# EMPLOYEE RESPONSE
# =========================

class EmployeeResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    user_id: int
    employee_code: str
    email: str | None = None

    first_name: str
    last_name: str

    phone: str | None
    date_of_birth: date | None
    address: str | None

    joining_date: date | None

    department_id: int | None
    designation_id: int | None
    department: str | None = None
    designation: str | None = None
    official_designation: str | None = None

    employment_status: EmploymentStatus

    profile_photo_url: str | None
    profile_photo_public_id: str | None
    created_at: datetime
    updated_at: datetime


# =========================
# EMPLOYEE LIST RESPONSE
# =========================

class EmployeeListResponse(BaseModel):
    total: int
    employees: list[EmployeeResponse]


# =========================
# EMPLOYEE STATUS UPDATE
# =========================

class EmployeeStatusUpdate(BaseModel):
    employment_status: EmploymentStatus