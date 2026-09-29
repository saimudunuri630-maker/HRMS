from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.authentication_service.dependencies import get_current_user
from app.authentication_service.models import User
from app.core.database import get_db
from app.profile_service import service
from app.profile_service.schemas import ProfileResponse, ProfileUpdateRequest

router = APIRouter(prefix="/api/profile", tags=["Profile"])


def _unwrap_user(auth_data) -> User:
    return auth_data[0] if isinstance(auth_data, tuple) else auth_data


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    return service.get_profile(db, user)


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    request: Request,
    data: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    # Extract raw json to detect attempted mutations of immutable fields
    raw_payload = {}
    try:
        raw_payload = await request.json()
    except Exception:
        pass

    return service.update_profile(db, user, data, raw_payload=raw_payload)


@router.post("/me/photo", response_model=ProfileResponse)
def upload_my_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth_data = Depends(get_current_user),
):
    user = _unwrap_user(auth_data)
    return service.upload_profile_photo(db, user, file)
