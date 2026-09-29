from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.authentication_service.dependencies import get_current_user
from app.authentication_service.models import User
from app.core.database import get_db
from app.employee_service import service
from app.employee_service.models import EmploymentStatus
from app.cloudinary_service import service as cloudinary_service
from app.employee_service.schemas import (
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeProfileUpdate,
    EmployeeResponse,
    EmployeeStatusUpdate,
    EmployeeUpdate,
)


router = APIRouter(
    prefix="/api/employees",
    tags=["Employees"],
)


# ============================================================
# CREATE EMPLOYEE
# HR ONLY
# ============================================================

@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR can create employees.",
        )

    return service.create_employee(
        db,
        data,
    )


# ============================================================
# LIST EMPLOYEES
# HR ONLY
# ============================================================

@router.get(
    "",
    response_model=EmployeeListResponse,
)
def list_employees(
    page: int = Query(
        default=1,
        ge=1,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        default=None,
    ),
    department_id: int | None = Query(
        default=None,
    ),
    designation_id: int | None = Query(
        default=None,
    ),
    employment_status: EmploymentStatus | None = Query(
        default=None,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR can view the employee list.",
        )

    result = service.list_employees(
        db=db,
        page=page,
        limit=limit,
        search=search,
        department_id=department_id,
        designation_id=designation_id,
        employment_status=employment_status,
    )

    return {
        "total": result["total"],
        "employees": result["items"],
    }


# ============================================================
# GET MY PROFILE
# EMPLOYEE ONLY
# ============================================================

@router.get(
    "/me/profile",
    response_model=EmployeeResponse,
)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("hr", "employee"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this profile.",
        )

    return service.get_employee_by_user_id(
        db,
        current_user.id,
    )


# ============================================================
# UPDATE MY PROFILE
# EMPLOYEE ONLY
# ============================================================

@router.put(
    "/me/profile",
    response_model=EmployeeResponse,
)
async def update_my_profile(
    request: Request,
    data: EmployeeProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("hr", "employee"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this profile.",
        )

    try:
        raw = await request.json()
        if any(k in raw for k in ("email", "employee_number", "employee_code")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee number and email address are immutable and cannot be changed.",
            )
    except HTTPException:
        raise
    except Exception:
        pass

    return service.update_self_profile(
        db,
        current_user.id,
        data,
    )

# ============================================================
# UPLOAD MY PROFILE PHOTO
# HR + EMPLOYEE
# ============================================================

@router.post(
    "/me/profile/photo",
    response_model=EmployeeResponse,
)
def upload_my_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("hr", "employee"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this profile.",
        )

    # Validate file type
    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, and WebP images are allowed.",
        )

    employee = service.get_employee_by_user_id(
        db,
        current_user.id,
    )

    # Delete old Cloudinary image if one exists
    if employee.profile_photo_public_id:
        cloudinary_service.delete_profile_photo(
            employee.profile_photo_public_id
        )

    # Upload new image
    result = cloudinary_service.upload_profile_photo(
        file.file
    )

    # Update employee profile
    employee.profile_photo_url = result["url"]
    employee.profile_photo_public_id = result["public_id"]

    db.commit()
    db.refresh(employee)

    return employee

# ============================================================
# EMPLOYEE COUNTS
# HR ONLY
# ============================================================

@router.get(
    "/dashboard/counts",
)
def employee_counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR can view employee statistics.",
        )

    return service.get_employee_counts(
        db
    )


# ============================================================
# GET EMPLOYEE BY ID
# HR ONLY
# ============================================================

@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR can view employee details.",
        )

    return service.get_employee_by_id(
        db,
        employee_id,
    )


# ============================================================
# UPDATE EMPLOYEE
# HR ONLY
# ============================================================

@router.put(
    "/{employee_id}",
    response_model=EmployeeResponse,
)
async def update_employee(
    employee_id: int,
    request: Request,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR can update employees.",
        )

    try:
        raw = await request.json()
        if any(k in raw for k in ("email", "employee_number", "employee_code")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee number and email address are immutable and cannot be changed.",
            )
    except HTTPException:
        raise
    except Exception:
        pass

    return service.update_employee(
        db,
        employee_id,
        data,
    )


# ============================================================
# UPDATE EMPLOYMENT STATUS
# HR ONLY
# ============================================================

@router.patch(
    "/{employee_id}/status",
    response_model=EmployeeResponse,
)
def update_employee_status(
    employee_id: int,
    data: EmployeeStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR can change employee status.",
        )

    return service.update_employee_status(
        db,
        employee_id,
        data,
    )


# ============================================================
# ACTIVATE EMPLOYEE
# HR ONLY
# ============================================================

@router.patch(
    "/{employee_id}/activate",
    response_model=EmployeeResponse,
)
def activate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR can activate employees.",
        )

    return service.activate_employee(
        db,
        employee_id,
    )


# ============================================================
# DEACTIVATE EMPLOYEE
# HR ONLY
# ============================================================

@router.patch(
    "/{employee_id}/deactivate",
    response_model=EmployeeResponse,
)
def deactivate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR can deactivate employees.",
        )

    return service.deactivate_employee(
        db,
        employee_id,
    )


# ============================================================
# ARCHIVE EMPLOYEE
# HR ONLY
# ============================================================

@router.delete(
    "/{employee_id}",
    response_model=EmployeeResponse,
)
def archive_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR can archive employees.",
        )

    return service.archive_employee(
        db,
        employee_id,
        user_id=current_user.id,
    )