from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    hash_password,
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    decode_token,
)
from app.models.clinic import Clinic, ClinicSettings
from app.models.user import User
from app.models.membership import ClinicMembership
from app.schemas import (
    SetupRegister,
    TokenPair,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)

router = APIRouter(prefix="/setup", tags=["Setup"])


@router.get("/status")
def status(db: Session = Depends(get_db)):
    exists = db.query(Clinic).first() is not None
    return {"setup_required": not exists}


@router.post("/register-clinic", response_model=TokenPair, status_code=201)
def register_clinic(payload: SetupRegister, db: Session = Depends(get_db)):
    # 1. Multi-tenant check: Block if a clinic with this exact email already exists
    if payload.email and db.query(Clinic).filter(Clinic.email == payload.email).first():
        raise HTTPException(
            status_code=409,
            detail="A clinic with this email ID is already registered",
        )

    # 2. Block if the admin user's email already exists
    if db.query(User).filter(User.email == payload.admin_email).first():
        raise HTTPException(
            status_code=409,
            detail="Admin email already exists",
        )

    try:
        clinic = Clinic(
            name=payload.clinic_name,
            short_name=payload.short_name,
            phone=payload.phone,
            email=payload.email,
            address=payload.address,
            currency=payload.currency,
        )
        db.add(clinic)
        db.flush()

        admin = User(
            full_name=payload.admin_name,
            email=payload.admin_email,
            phone=payload.admin_phone,
            password_hash=hash_password(payload.password),
        )
        db.add(admin)
        db.flush()

        db.add(ClinicMembership(user_id=admin.id, clinic_id=clinic.id, role="ADMIN"))
        db.add(ClinicSettings(clinic_id=clinic.id))
        db.commit()

        return TokenPair(
            access_token=create_access_token(admin.id),
            refresh_token=create_refresh_token(admin.id),
        )
    except Exception:
        db.rollback()
        raise


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    # Generic success response to avoid exposing registered email addresses
    if not user or not user.is_active:
        return {
            "message": "If that email is registered, password reset instructions have been generated."
        }

    # Generate token valid for 15 minutes
    token = create_password_reset_token(user.id)
    user.reset_token = token
    user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    db.commit()

    # Print token in dev console for quick local testing
    print(f"\n[DEV MODE] Reset Token for {user.email}:\n{token}\n")

    return {
        "message": "If that email is registered, password reset instructions have been generated.",
        "dev_token": token,
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    payload_data = decode_token(payload.token)

    if not payload_data or payload_data.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user_id = payload_data.get("sub")
    user = db.get(User, user_id)

    if not user or user.reset_token != payload.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token is invalid or has already been used",
        )

    if (
        user.reset_token_expires_at
        and datetime.now(timezone.utc)
        > user.reset_token_expires_at.replace(tzinfo=timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )

    # Update password and invalidate reset token
    user.password_hash = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()

    return {"message": "Password updated successfully. You can now log in."}