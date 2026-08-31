# from fastapi import Depends, HTTPException, status
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from sqlalchemy.orm import Session
# from app.core.database import get_db
# from app.core.security import decode_token
# from app.models.user import User
# from app.models.membership import ClinicMembership

# bearer = HTTPBearer(auto_error=False)

# def current_user(
#     credentials: HTTPAuthorizationCredentials = Depends(bearer),
#     db: Session = Depends(get_db),
# ):
#     if not credentials:
#         raise HTTPException(status_code=401, detail="Authentication required")
#     payload = decode_token(credentials.credentials)
#     if not payload or payload.get("type") != "access":
#         raise HTTPException(status_code=401, detail="Invalid or expired access token")
#     user = db.get(User, payload["sub"])
#     if not user or not user.is_active:
#         raise HTTPException(status_code=401, detail="User is inactive or missing")
#     return user

# def membership_for(db: Session, user_id: str, clinic_id: str):
#     return (
#         db.query(ClinicMembership)
#         .filter(
#             ClinicMembership.user_id == user_id,
#             ClinicMembership.clinic_id == clinic_id,
#             ClinicMembership.is_active.is_(True),
#         )
#         .first()
#     )

# def require_clinic(clinic_id: str, roles=None):
#     def dependency(user=Depends(current_user), db: Session=Depends(get_db)):
#         m = membership_for(db, user.id, clinic_id)
#         if not m:
#             raise HTTPException(status_code=403, detail="No access to this clinic")
#         if roles and m.role not in roles:
#             raise HTTPException(status_code=403, detail="Insufficient permission")
#         return m
#     return dependency

# def role_for(db: Session, user_id: str, clinic_id: str):
#     m = membership_for(db, user_id, clinic_id)
#     return m.role if m else None


import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.membership import ClinicMembership

bearer = HTTPBearer(auto_error=False)

def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    user = db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive or missing")
    
    # Securely bind authenticated user_id to structlog context
    structlog.contextvars.bind_contextvars(user_id=str(user.id))
    
    return user

def membership_for(db: Session, user_id: str, clinic_id: str):
    return (
        db.query(ClinicMembership)
        .filter(
            ClinicMembership.user_id == user_id,
            ClinicMembership.clinic_id == clinic_id,
            ClinicMembership.is_active.is_(True),
        )
        .first()
    )

def require_clinic(clinic_id: str, roles=None):
    def dependency(user=Depends(current_user), db: Session=Depends(get_db)):
        m = membership_for(db, user.id, clinic_id)
        if not m:
            raise HTTPException(status_code=403, detail="No access to this clinic")
        if roles and m.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permission")
        
        # Securely bind verified clinic_id and user's role in this clinic to structlog
        structlog.contextvars.bind_contextvars(
            clinic_id=str(clinic_id),
            user_role=str(m.role)
        )
        
        return m
    return dependency

def role_for(db: Session, user_id: str, clinic_id: str):
    m = membership_for(db, user_id, clinic_id)
    return m.role if m else None