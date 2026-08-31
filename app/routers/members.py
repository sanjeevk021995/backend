# from fastapi import APIRouter, Depends, HTTPException, Query
# from sqlalchemy.orm import Session, joinedload
# from pydantic import BaseModel

# from app.core.database import get_db
# from app.core.auth import current_user, membership_for
# from app.core.security import hash_password
# from app.models.user import User
# from app.models.membership import ClinicMembership
# from app.models.doctor import DoctorProfile
# from app.schemas import MemberCreate, MemberUpdate, Assignment
# from app.services.audit import audit

# router = APIRouter(prefix="/members", tags=["Team"])

# VALID_ROLES = {"ADMIN", "DOCTOR", "FRONT_DESK"}


# class StatusUpdate(BaseModel):
#     is_active: bool


# def member_access_check(db: Session, user, clinic_id: str):
#     """Allows any active clinic member (ADMIN, FRONT_DESK, DOCTOR) access."""
#     m = membership_for(db, user.id, clinic_id)
#     if not m:
#         raise HTTPException(
#             status_code=403, 
#             detail=f"Access denied for clinic {clinic_id}"
#         )
#     return m


# def admin_check(db: Session, user, clinic_id: str):
#     """Restricts operations strictly to ADMIN users."""
#     m = member_access_check(db, user, clinic_id)
#     if str(m.role).upper() != "ADMIN":
#         raise HTTPException(
#             status_code=403, 
#             detail=f"Admin permission required for clinic {clinic_id}"
#         )
#     return m


# @router.get("/clinics/{clinic_id}")
# def list_members(clinic_id: str, user=Depends(current_user), db: Session=Depends(get_db)):
#     # Any active team member in the clinic can view team members
#     member_access_check(db, user, clinic_id)
    
#     # Joined loading ensures user and doctor_profile are fully hydrated
#     rows = (
#         db.query(ClinicMembership)
#         .options(
#             joinedload(ClinicMembership.user).joinedload(User.doctor_profile)
#         )
#         .filter(ClinicMembership.clinic_id == clinic_id)
#         .all()
#     )
    
#     result = []
#     for x in rows:
#         u = x.user
#         doc_prof = u.doctor_profile if u else None
        
#         result.append({
#             "id": x.user_id,
#             "user_id": x.user_id,
#             "full_name": u.full_name if u else "",
#             "name": u.full_name if u else "",
#             "email": u.email if u else "",
#             "phone": u.phone if u else "",
#             "role": str(x.role).upper(),
#             "is_active": x.is_active,
#             "specialty": doc_prof.specialty if doc_prof else None,
#             "degrees": doc_prof.degrees if doc_prof else None,
#             "license_number": doc_prof.license_number if doc_prof else None,
#         })
        
#     return result


# @router.post("/clinics/{clinic_id}", status_code=201)
# def create_member(clinic_id: str, payload: MemberCreate, user=Depends(current_user), db: Session=Depends(get_db)):
#     admin_check(db, user, clinic_id)
#     role = payload.role.upper()
    
#     if role not in VALID_ROLES:
#         raise HTTPException(400, "Role must be ADMIN, DOCTOR or FRONT_DESK")
        
#     if db.query(User).filter(User.email == payload.email).first():
#         raise HTTPException(409, "Email already exists")

#     u = User(
#         full_name=payload.full_name,
#         email=payload.email,
#         phone=payload.phone,
#         password_hash=hash_password(payload.password),
#     )
#     db.add(u)
#     db.flush()
    
#     db.add(ClinicMembership(user_id=u.id, clinic_id=clinic_id, role=role, is_active=True))
    
#     if role == "DOCTOR":
#         db.add(DoctorProfile(
#             user_id=u.id,
#             specialty=getattr(payload, 'specialty', None),
#             degrees=getattr(payload, 'degrees', None),
#             license_number=getattr(payload, 'license_number', None),
#         ))
        
#     audit(db, user.id, clinic_id, "member.created", "User", u.id, {"role": role})
#     db.commit()
#     return {"user_id": u.id, "role": role}


# @router.post("/{user_id}/assign")
# def assign_member(user_id: str, payload: Assignment, user=Depends(current_user), db: Session=Depends(get_db)):
#     admin_check(db, user, payload.clinic_id)
#     role = payload.role.upper()
#     if role not in VALID_ROLES:
#         raise HTTPException(400, "Invalid role")
#     target = db.get(User, user_id)
#     if not target:
#         raise HTTPException(404, "User not found")

#     existing = membership_for(db, user_id, payload.clinic_id)
#     if existing:
#         existing.role = role
#         existing.is_active = True
#     else:
#         db.add(ClinicMembership(user_id=user_id, clinic_id=payload.clinic_id, role=role, is_active=True))
#     audit(db, user.id, payload.clinic_id, "member.assigned", "User", user_id, {"role": role})
#     db.commit()
#     return {"message": "Member assigned"}


# @router.patch("/{user_id}")
# def update_member(user_id: str, payload: MemberUpdate, clinic_id: str, user=Depends(current_user), db: Session=Depends(get_db)):
#     admin_check(db, user, clinic_id)
#     target = db.get(User, user_id)
#     if not target:
#         raise HTTPException(404, "User not found")
        
#     for k, v in payload.model_dump(exclude_unset=True).items():
#         if k in {"specialty", "degrees", "license_number"}:
#             if not target.doctor_profile:
#                 target.doctor_profile = DoctorProfile(user_id=target.id)
#             setattr(target.doctor_profile, k, v)
#         else:
#             setattr(target, k, v)
            
#     audit(db, user.id, clinic_id, "member.updated", "User", user_id)
#     db.commit()
#     return target


# @router.patch("/{user_id}/status")
# def toggle_member_status(
#     user_id: str, 
#     payload: StatusUpdate, 
#     clinic_id: str = Query(...), 
#     user=Depends(current_user), 
#     db: Session = Depends(get_db)
# ):
#     admin_check(db, user, clinic_id)
    
#     if user_id == user.id and not payload.is_active:
#         raise HTTPException(400, "You cannot deactivate your own admin account.")
        
#     membership = (
#         db.query(ClinicMembership)
#         .filter(ClinicMembership.user_id == user_id, ClinicMembership.clinic_id == clinic_id)
#         .first()
#     )
#     if not membership:
#         raise HTTPException(404, "Team member not found in this clinic.")
        
#     membership.is_active = payload.is_active
#     action_str = "member.activated" if payload.is_active else "member.deactivated"
#     audit(db, user.id, clinic_id, action_str, "User", user_id)
    
#     db.commit()
#     return {"message": f"Member status updated to {'Active' if payload.is_active else 'Inactive'}"}

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.auth import current_user, membership_for
from app.core.security import hash_password
from app.models.user import User
from app.models.membership import ClinicMembership
from app.models.doctor import DoctorProfile
from app.models.department import Department
from app.schemas import MemberCreate, MemberUpdate, Assignment
from app.services.audit import audit

router = APIRouter(prefix="/members", tags=["Team"])

VALID_ROLES = {"ADMIN", "DOCTOR", "FRONT_DESK"}


class StatusUpdate(BaseModel):
    is_active: bool


def member_access_check(db: Session, user, clinic_id: str):
    """Allows any active clinic member (ADMIN, FRONT_DESK, DOCTOR) access."""
    m = membership_for(db, user.id, clinic_id)
    if not m:
        raise HTTPException(
            status_code=403, 
            detail=f"Access denied for clinic {clinic_id}"
        )
    return m


def admin_check(db: Session, user, clinic_id: str):
    """Restricts operations strictly to ADMIN users."""
    m = member_access_check(db, user, clinic_id)
    if str(m.role).upper() != "ADMIN":
        raise HTTPException(
            status_code=403, 
            detail=f"Admin permission required for clinic {clinic_id}"
        )
    return m


@router.get("/clinics/{clinic_id}")
def list_members(clinic_id: str, user=Depends(current_user), db: Session=Depends(get_db)):
    # Any active team member in the clinic can view team members
    member_access_check(db, user, clinic_id)
    
    # Joined loading ensures user, doctor_profile, and department are hydrated
    rows = (
        db.query(ClinicMembership)
        .options(
            joinedload(ClinicMembership.user).joinedload(User.doctor_profile),
            joinedload(ClinicMembership.department),
        )
        .filter(ClinicMembership.clinic_id == clinic_id)
        .all()
    )
    
    result = []
    for x in rows:
        u = x.user
        doc_prof = u.doctor_profile if u else None
        
        result.append({
            "id": x.user_id,
            "user_id": x.user_id,
            "full_name": u.full_name if u else "",
            "name": u.full_name if u else "",
            "email": u.email if u else "",
            "phone": u.phone if u else "",
            "role": str(x.role).upper(),
            "is_active": x.is_active,
            "department_id": x.department_id,
            "department_name": x.department.name if x.department else None,
            "specialty": doc_prof.specialty if doc_prof else None,
            "degrees": doc_prof.degrees if doc_prof else None,
            "license_number": doc_prof.license_number if doc_prof else None,
        })
        
    return result


@router.post("/clinics/{clinic_id}", status_code=201)
def create_member(clinic_id: str, payload: MemberCreate, user=Depends(current_user), db: Session=Depends(get_db)):
    admin_check(db, user, clinic_id)
    role = payload.role.upper()
    
    if role not in VALID_ROLES:
        raise HTTPException(400, "Role must be ADMIN, DOCTOR or FRONT_DESK")
        
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(409, "Email already exists")

    # Validate Department ID if provided
    department_id = getattr(payload, "department_id", None)
    if department_id:
        dept = db.get(Department, department_id)
        if not dept or dept.clinic_id != clinic_id:
            raise HTTPException(404, "Department not found in this clinic")

    u = User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
    )
    db.add(u)
    db.flush()
    
    db.add(
        ClinicMembership(
            user_id=u.id, 
            clinic_id=clinic_id, 
            department_id=department_id,
            role=role, 
            is_active=True
        )
    )
    
    if role == "DOCTOR":
        db.add(DoctorProfile(
            user_id=u.id,
            specialty=getattr(payload, 'specialty', None),
            degrees=getattr(payload, 'degrees', None),
            license_number=getattr(payload, 'license_number', None),
        ))
        
    audit(db, user.id, clinic_id, "member.created", "User", u.id, {"role": role, "department_id": department_id})
    db.commit()
    return {"user_id": u.id, "role": role, "department_id": department_id}


@router.post("/{user_id}/assign")
def assign_member(user_id: str, payload: Assignment, user=Depends(current_user), db: Session=Depends(get_db)):
    admin_check(db, user, payload.clinic_id)
    role = payload.role.upper()
    if role not in VALID_ROLES:
        raise HTTPException(400, "Invalid role")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")

    department_id = getattr(payload, "department_id", None)
    if department_id:
        dept = db.get(Department, department_id)
        if not dept or dept.clinic_id != payload.clinic_id:
            raise HTTPException(404, "Department not found in this clinic")

    existing = membership_for(db, user_id, payload.clinic_id)
    if existing:
        existing.role = role
        existing.department_id = department_id
        existing.is_active = True
    else:
        db.add(
            ClinicMembership(
                user_id=user_id, 
                clinic_id=payload.clinic_id, 
                department_id=department_id,
                role=role, 
                is_active=True
            )
        )
    audit(db, user.id, payload.clinic_id, "member.assigned", "User", user_id, {"role": role, "department_id": department_id})
    db.commit()
    return {"message": "Member assigned"}


@router.patch("/{user_id}")
def update_member(user_id: str, payload: MemberUpdate, clinic_id: str, user=Depends(current_user), db: Session=Depends(get_db)):
    admin_check(db, user, clinic_id)
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")

    membership = (
        db.query(ClinicMembership)
        .filter(ClinicMembership.user_id == user_id, ClinicMembership.clinic_id == clinic_id)
        .first()
    )
    if not membership:
        raise HTTPException(404, "Team member not found in this clinic.")

    for k, v in payload.model_dump(exclude_unset=True).items():
        if k == "department_id":
            if v:
                dept = db.get(Department, v)
                if not dept or dept.clinic_id != clinic_id:
                    raise HTTPException(404, "Department not found in this clinic")
            membership.department_id = v
        elif k in {"specialty", "degrees", "license_number"}:
            if not target.doctor_profile:
                target.doctor_profile = DoctorProfile(user_id=target.id)
            setattr(target.doctor_profile, k, v)
        else:
            setattr(target, k, v)
            
    audit(db, user.id, clinic_id, "member.updated", "User", user_id)
    db.commit()
    return target


@router.patch("/{user_id}/status")
def toggle_member_status(
    user_id: str, 
    payload: StatusUpdate, 
    clinic_id: str = Query(...), 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    admin_check(db, user, clinic_id)
    
    if user_id == user.id and not payload.is_active:
        raise HTTPException(400, "You cannot deactivate your own admin account.")
        
    membership = (
        db.query(ClinicMembership)
        .filter(ClinicMembership.user_id == user_id, ClinicMembership.clinic_id == clinic_id)
        .first()
    )
    if not membership:
        raise HTTPException(404, "Team member not found in this clinic.")
        
    membership.is_active = payload.is_active
    action_str = "member.activated" if payload.is_active else "member.deactivated"
    audit(db, user.id, clinic_id, action_str, "User", user_id)
    
    db.commit()
    return {"message": f"Member status updated to {'Active' if payload.is_active else 'Inactive'}"}