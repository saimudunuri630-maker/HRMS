from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    email: str
    role: str
    employee_code: str
    first_name: str
    last_name: str
    full_name: str
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    joining_date: Optional[date] = None
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    employment_status: str
    profile_photo_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    date_of_birth: Optional[date] = None
    address: Optional[str] = Field(default=None, max_length=255)
    
    # Optional placeholders to intercept and explicitly reject unauthorized mutations
    email: Optional[str] = None
    employee_number: Optional[str] = None
    employee_code: Optional[str] = None
