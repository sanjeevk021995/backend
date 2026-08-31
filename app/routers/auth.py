from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.core.auth import current_user
from app.models.user import User
from app.models.membership import ClinicMembership
from app.schemas import LoginRequest, TokenPair, RefreshRequest, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )

@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")
    user = db.get(User, data["sub"])
    if not user or not user.is_active:
        raise HTTPException(401, "User is inactive or missing")
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )

@router.get("/me", response_model=UserOut)
def me(user=Depends(current_user)):
    return user

@router.get("/my-clinics")
def my_clinics(user=Depends(current_user), db: Session=Depends(get_db)):
    rows = (
        db.query(ClinicMembership)
        .filter(ClinicMembership.user_id == user.id, ClinicMembership.is_active.is_(True))
        .all()
    )
    return [{"clinic_id": x.clinic_id, "role": x.role, "clinic": x.clinic.name if x.clinic else None} for x in rows]
