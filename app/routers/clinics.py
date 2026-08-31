# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from pydantic import BaseModel
# from typing import List, Optional
# from app.core.database import get_db
# from app.core.auth import current_user, membership_for
# from app.models.clinic import Clinic, ClinicSettings, ClinicWorkingHours
# from app.models.membership import ClinicMembership
# from app.schemas import ClinicCreate, ClinicUpdate
# from app.services.audit import audit

# router = APIRouter(prefix="/clinics", tags=["Clinics"])

# class WorkingHourSchema(BaseModel):
#     day_of_week: int
#     open_time: Optional[str] = "08:00"
#     close_time: Optional[str] = "20:00"
#     is_closed: bool = False

# @router.get("/")
# def list_clinics(user=Depends(current_user), db: Session=Depends(get_db)):
#     rows = db.query(ClinicMembership).filter(
#         ClinicMembership.user_id == user.id,
#         ClinicMembership.is_active.is_(True)
#     ).all()
    
#     result = []
#     for x in rows:
#         c = x.clinic
#         if c:
#             result.append({
#                 "id": c.id,
#                 "name": c.name,
#                 "phone": getattr(c, 'phone', None),
#                 "email": getattr(c, 'email', None),
#                 "address": getattr(c, 'address', None),
#                 "role": x.role
#             })
#     return result

# @router.post("/", status_code=201)
# def create_clinic(payload: ClinicCreate, user=Depends(current_user), db: Session=Depends(get_db)):
#     clinic = Clinic(**payload.model_dump())
#     db.add(clinic)
#     db.flush()
#     db.add(ClinicSettings(clinic_id=clinic.id))
#     db.add(ClinicMembership(user_id=user.id, clinic_id=clinic.id, role="ADMIN"))
    
#     # Initialize default operating hours (Mon-Sat Open 8-20, Sun Closed)
#     for day in range(7):
#         db.add(ClinicWorkingHours(
#             clinic_id=clinic.id,
#             day_of_week=day,
#             open_time="08:00",
#             close_time="20:00",
#             is_closed=(day == 0)
#         ))

#     audit(db, user.id, clinic.id, "clinic.created", "Clinic", clinic.id)
#     db.commit()
#     return clinic

# @router.get("/{clinic_id}")
# def get_clinic(clinic_id: str, user=Depends(current_user), db: Session=Depends(get_db)):
#     if not membership_for(db, user.id, clinic_id):
#         raise HTTPException(403, "No access to this clinic")
#     clinic = db.get(Clinic, clinic_id)
#     if not clinic:
#         raise HTTPException(404, "Clinic not found")
#     return clinic

# @router.patch("/{clinic_id}")
# def update_clinic(clinic_id: str, payload: ClinicUpdate, user=Depends(current_user), db: Session=Depends(get_db)):
#     m = membership_for(db, user.id, clinic_id)
#     if not m or m.role != "ADMIN":
#         raise HTTPException(403, "Admin permission required")
#     clinic = db.get(Clinic, clinic_id)
#     if not clinic:
#         raise HTTPException(404, "Clinic not found")
#     for k, v in payload.model_dump(exclude_unset=True).items():
#         setattr(clinic, k, v)
#     audit(db, user.id, clinic_id, "clinic.updated", "Clinic", clinic_id)
#     db.commit()
#     return clinic

# # Clinic Operating Hours endpoints
# @router.get("/{clinic_id}/hours")
# def get_clinic_hours(clinic_id: str, user=Depends(current_user), db: Session=Depends(get_db)):
#     if not membership_for(db, user.id, clinic_id):
#         raise HTTPException(403, "No access to this clinic")
    
#     hours = db.query(ClinicWorkingHours).filter(
#         ClinicWorkingHours.clinic_id == clinic_id
#     ).order_by(ClinicWorkingHours.day_of_week).all()
#     return hours

# @router.put("/{clinic_id}/hours")
# def save_clinic_hours(clinic_id: str, payload: List[WorkingHourSchema], user=Depends(current_user), db: Session=Depends(get_db)):
#     m = membership_for(db, user.id, clinic_id)
#     if not m or m.role != "ADMIN":
#         raise HTTPException(403, "Admin permission required")

#     # Clear and replace hours
#     db.query(ClinicWorkingHours).filter(ClinicWorkingHours.clinic_id == clinic_id).delete()
    
#     for item in payload:
#         db.add(ClinicWorkingHours(
#             clinic_id=clinic_id,
#             day_of_week=item.day_of_week,
#             open_time=item.open_time,
#             close_time=item.close_time,
#             is_closed=item.is_closed
#         ))
        
#     audit(db, user.id, clinic_id, "clinic.working_hours.updated", "Clinic", clinic_id)
#     db.commit()
#     return {"message": "Working hours updated successfully"}

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.core.database import get_db
from app.core.auth import current_user, membership_for
from app.models.clinic import Clinic, ClinicSettings, ClinicWorkingHours
from app.models.membership import ClinicMembership
from app.models.department import Department
from app.schemas import ClinicCreate, ClinicUpdate
from app.services.audit import audit


router = APIRouter(prefix="/clinics", tags=["Clinics"])


class WorkingHourSchema(BaseModel):
    day_of_week: int
    open_time: Optional[str] = "08:00"
    close_time: Optional[str] = "20:00"
    is_closed: bool = False


@router.get("/")
def list_clinics(user=Depends(current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(ClinicMembership)
        .filter(
            ClinicMembership.user_id == user.id,
            ClinicMembership.is_active.is_(True),
        )
        .all()
    )

    result = []
    for x in rows:
        c = x.clinic
        if c:
            result.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "short_name": getattr(c, "short_name", None),
                    "phone": getattr(c, "phone", None),
                    "email": getattr(c, "email", None),
                    "address": getattr(c, "address", None),
                    "role": x.role,
                    "department_id": x.department_id,
                    "department_name": x.department.name if x.department else None,
                }
            )
    return result


@router.post("/", status_code=201)
def create_clinic(
    payload: ClinicCreate,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    clinic = Clinic(**payload.model_dump())
    db.add(clinic)
    db.flush()

    # 1. Initialize Default Settings
    db.add(ClinicSettings(clinic_id=clinic.id))

    # 2. Create Default Department for the Clinic
    default_dept = Department(
        clinic_id=clinic.id,
        name="General / OPD",
        description="Default general outpatient department",
    )
    db.add(default_dept)
    db.flush()

    # 3. Create Membership for Creator (Admin) assigned to Default Department
    db.add(
        ClinicMembership(
            user_id=user.id,
            clinic_id=clinic.id,
            department_id=default_dept.id,
            role="ADMIN",
        )
    )

    # 4. Initialize default operating hours (Mon-Sat Open 8-20, Sun Closed)
    for day in range(7):
        db.add(
            ClinicWorkingHours(
                clinic_id=clinic.id,
                day_of_week=day,
                open_time="08:00",
                close_time="20:00",
                is_closed=(day == 0),
            )
        )

    audit(db, user.id, clinic.id, "clinic.created", "Clinic", clinic.id)
    db.commit()
    db.refresh(clinic)
    return clinic


@router.get("/{clinic_id}")
def get_clinic(
    clinic_id: str,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    if not membership_for(db, user.id, clinic_id):
        raise HTTPException(403, "No access to this clinic")
    clinic = db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(404, "Clinic not found")
    return clinic


@router.patch("/{clinic_id}")
def update_clinic(
    clinic_id: str,
    payload: ClinicUpdate,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    m = membership_for(db, user.id, clinic_id)
    if not m or m.role != "ADMIN":
        raise HTTPException(403, "Admin permission required")

    clinic = db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(404, "Clinic not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(clinic, k, v)

    audit(db, user.id, clinic_id, "clinic.updated", "Clinic", clinic_id)
    db.commit()
    db.refresh(clinic)
    return clinic


# Clinic Operating Hours endpoints
@router.get("/{clinic_id}/hours")
def get_clinic_hours(
    clinic_id: str,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    if not membership_for(db, user.id, clinic_id):
        raise HTTPException(403, "No access to this clinic")

    hours = (
        db.query(ClinicWorkingHours)
        .filter(ClinicWorkingHours.clinic_id == clinic_id)
        .order_by(ClinicWorkingHours.day_of_week)
        .all()
    )
    return hours


@router.put("/{clinic_id}/hours")
def save_clinic_hours(
    clinic_id: str,
    payload: List[WorkingHourSchema],
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    m = membership_for(db, user.id, clinic_id)
    if not m or m.role != "ADMIN":
        raise HTTPException(403, "Admin permission required")

    # Clear and replace hours
    db.query(ClinicWorkingHours).filter(
        ClinicWorkingHours.clinic_id == clinic_id
    ).delete()

    for item in payload:
        db.add(
            ClinicWorkingHours(
                clinic_id=clinic_id,
                day_of_week=item.day_of_week,
                open_time=item.open_time,
                close_time=item.close_time,
                is_closed=item.is_closed,
            )
        )

    audit(
        db,
        user.id,
        clinic_id,
        "clinic.working_hours.updated",
        "Clinic",
        clinic_id,
    )
    db.commit()
    return {"message": "Working hours updated successfully"}