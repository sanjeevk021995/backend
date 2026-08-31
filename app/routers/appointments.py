# from datetime import date, time, datetime
# from fastapi import APIRouter, Depends, HTTPException, Query
# from sqlalchemy.orm import Session
# from app.core.database import get_db
# from app.core.auth import current_user, membership_for, role_for
# from app.models.appointment import Appointment
# from app.models.patient import Patient
# from app.models.clinic import ClinicWorkingHours
# from app.schemas import AppointmentCreate, AppointmentUpdate, AppointmentResponse
# from app.services.scheduling import doctor_available
# from app.services.audit import audit

# router = APIRouter(prefix="/appointments", tags=["Appointments"])

# # Accepts both 'noshow' and 'no_show' formatting
# STATUSES = {"scheduled", "completed", "cancelled", "noshow", "no_show"}

# from datetime import date, time, datetime

# def parse_time_input(time_val: str | time) -> time:
#     """Ensures input is returned as a python datetime.time object."""
#     if isinstance(time_val, time):
#         return time_val
#     if isinstance(time_val, str):
#         time_clean = time_val.strip()[:5]  # Get 'HH:MM'
#         return datetime.strptime(time_clean, "%H:%M").time()
#     raise ValueError(f"Invalid time format: {time_val}")



# def check_access(db: Session, user, clinic_id: str, doctor_id: str | None = None, write: bool = False):
#     m = membership_for(db, user.id, clinic_id)
#     if not m:
#         raise HTTPException(status_code=403, detail="No clinic access")
    
#     role = str(m.role).upper()
#     if role == "DOCTOR" and doctor_id and str(doctor_id) != str(user.id):
#         raise HTTPException(status_code=403, detail="Doctors can only manage their own appointments")
        
#     if write and role not in {"ADMIN", "FRONT_DESK", "DOCTOR"}:
#         raise HTTPException(status_code=403, detail="Insufficient permission")
        
#     return m


# def validate_clinic_operating_hours(db: Session, clinic_id: str, app_date: date, app_time_val):
#     """
#     Validates that the appointment date and time fall within the clinic's operating hours.
#     """
#     # Safely convert time input (time, datetime, or str) into HH:MM string format
#     if isinstance(app_time_val, time):
#         time_clean = app_time_val.strftime("%H:%M")
#     elif isinstance(app_time_val, datetime):
#         time_clean = app_time_val.strftime("%H:%M")
#     elif isinstance(app_time_val, str):
#         time_clean = app_time_val.strip()[:5]
#     else:
#         time_clean = str(app_time_val)[:5]

#     # Python weekday: Mon = 0 ... Sun = 6. Map to Sunday = 0 ... Saturday = 6
#     day_of_week = (app_date.weekday() + 1) % 7

#     working_hour = db.query(ClinicWorkingHours).filter(
#         ClinicWorkingHours.clinic_id == clinic_id,
#         ClinicWorkingHours.day_of_week == day_of_week
#     ).first()

#     if working_hour:
#         day_name = app_date.strftime("%A")
#         if working_hour.is_closed:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"The clinic is closed on {day_name}s."
#             )

#         open_str = working_hour.open_time[:5] if working_hour.open_time else "00:00"
#         close_str = working_hour.close_time[:5] if working_hour.close_time else "23:59"

#         if time_clean < open_str or time_clean >= close_str:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Clinic hours on {day_name} are {open_str} to {close_str}. Selected time ({time_clean}) is outside clinic hours."
#             )


# @router.get("/")
# def list_appointments(
#     clinic_id: str = Query(...),
#     appointment_date: date | None = None,
#     doctor_id: str | None = None,
#     status: str | None = None,
#     user=Depends(current_user),
#     db: Session = Depends(get_db),
# ):
#     m = check_access(db, user, clinic_id, doctor_id)
#     role = str(m.role).upper()
    
#     q = db.query(Appointment).filter(Appointment.clinic_id == clinic_id)
    
#     if role == "DOCTOR":
#         q = q.filter(Appointment.doctor_id == user.id)
#     elif doctor_id:
#         q = q.filter(Appointment.doctor_id == doctor_id)
        
#     if appointment_date:
#         q = q.filter(Appointment.appointment_date == appointment_date)
#     if status:
#         q = q.filter(Appointment.status == status)
        
#     return q.order_by(Appointment.appointment_date, Appointment.appointment_time).all()


# @router.get("/availability")
# def availability(
#     clinic_id: str, 
#     doctor_id: str, 
#     appointment_date: date, 
#     appointment_time: str, 
#     user=Depends(current_user), 
#     db: Session = Depends(get_db)
# ):
#     check_access(db, user, clinic_id, doctor_id)
    
#     # Check clinic general hours first
#     try:
#         validate_clinic_operating_hours(db, clinic_id, appointment_date, appointment_time)
#     except HTTPException as e:
#         return {"available": False, "message": e.detail}

#     ok, message = doctor_available(db, clinic_id, doctor_id, appointment_date, appointment_time)
#     return {"available": ok, "message": message}


# @router.post("/", status_code=201)
# def create_appointment(
#     payload: AppointmentCreate, 
#     user=Depends(current_user), 
#     db: Session = Depends(get_db)
# ):
#     check_access(db, user, payload.clinic_id, payload.doctor_id, write=True)
    
#     patient = db.get(Patient, payload.patient_id)
#     if not patient or str(patient.clinic_id) != str(payload.clinic_id):
#         raise HTTPException(status_code=404, detail="Patient not found in clinic")
        
#     if payload.status not in STATUSES:
#         raise HTTPException(status_code=400, detail="Invalid appointment status")
        
#     if payload.status == "scheduled":
#         # Check clinic working hours
#         validate_clinic_operating_hours(
#             db, payload.clinic_id, payload.appointment_date, payload.appointment_time
#         )
        
#         ok, message = doctor_available(
#             db, payload.clinic_id, payload.doctor_id, payload.appointment_date, payload.appointment_time
#         )
#         if not ok:
#             raise HTTPException(status_code=409, detail=message)
            
#     row = Appointment(**payload.model_dump())
#     db.add(row)
#     db.flush()
    
#     audit(db, user.id, row.clinic_id, "appointment.created", "Appointment", row.id)
#     db.commit()
#     db.refresh(row)
#     return row


# @router.get("/{appointment_id}")
# def get_appointment(
#     appointment_id: str, 
#     clinic_id: str, 
#     user=Depends(current_user), 
#     db: Session = Depends(get_db)
# ):
#     check_access(db, user, clinic_id)
#     row = db.get(Appointment, appointment_id)
#     if not row or str(row.clinic_id) != str(clinic_id):
#         raise HTTPException(status_code=404, detail="Appointment not found")
        
#     user_role = role_for(db, user.id, clinic_id)
#     if user_role and str(user_role).upper() == "DOCTOR" and str(row.doctor_id) != str(user.id):
#         raise HTTPException(status_code=403, detail="Access denied")
        
#     return row

# @router.patch("/{appointment_id}")
# def update_appointment(
#     appointment_id: str, 
#     clinic_id: str, 
#     payload: AppointmentUpdate, 
#     user=Depends(current_user), 
#     db: Session = Depends(get_db)
# ):
#     row = db.get(Appointment, appointment_id)
#     if not row or str(row.clinic_id) != str(clinic_id):
#         raise HTTPException(status_code=404, detail="Appointment not found")
        
#     check_access(db, user, clinic_id, row.doctor_id, write=True)
#     data = payload.model_dump(exclude_unset=True)
    
#     new_doctor = data.get("doctor_id", row.doctor_id)
#     new_date = data.get("appointment_date", row.appointment_date)
#     new_time = data.get("appointment_time", row.appointment_time)
#     new_clinic = data.get("clinic_id", row.clinic_id)

#     user_role = role_for(db, user.id, clinic_id)
#     if user_role and str(user_role).upper() == "DOCTOR" and str(new_doctor) != str(user.id):
#         raise HTTPException(status_code=403, detail="Doctor cannot assign another doctor")

#     if data.get("status") and data["status"] not in STATUSES:
#         raise HTTPException(status_code=400, detail="Invalid status")

#     if data.get("status", row.status) == "scheduled":
#         # Check clinic working hours
#         validate_clinic_operating_hours(db, new_clinic, new_date, new_time)

#         ok, message = doctor_available(db, new_clinic, new_doctor, new_date, new_time, exclude_id=row.id)
#         if not ok:
#             raise HTTPException(status_code=409, detail=message)

#     # Convert appointment_time if present in updates
#     if "appointment_time" in data and data["appointment_time"] is not None:
#         data["appointment_time"] = parse_time_input(data["appointment_time"])

#     for k, v in data.items():
#         setattr(row, k, v)
        
#     audit(db, user.id, clinic_id, "appointment.updated", "Appointment", row.id)
#     db.commit()
#     db.refresh(row)
#     return row

# @router.post("/{appointment_id}/complete")
# def complete(
#     appointment_id: str, 
#     clinic_id: str, 
#     user=Depends(current_user), 
#     db: Session = Depends(get_db)
# ):
#     row = db.get(Appointment, appointment_id)
#     if not row or str(row.clinic_id) != str(clinic_id):
#         raise HTTPException(status_code=404, detail="Appointment not found")
        
#     check_access(db, user, clinic_id, row.doctor_id, write=True)
#     row.status = "completed"
    
#     p = db.get(Patient, row.patient_id)
#     if p and (not p.last_visit or p.last_visit < row.appointment_date):
#         p.last_visit = row.appointment_date
        
#     audit(db, user.id, clinic_id, "appointment.completed", "Appointment", row.id)
#     db.commit()
#     return row


# @router.post("/{appointment_id}/cancel")
# def cancel(
#     appointment_id: str, 
#     clinic_id: str, 
#     user=Depends(current_user), 
#     db: Session = Depends(get_db)
# ):
#     row = db.get(Appointment, appointment_id)
#     if not row or str(row.clinic_id) != str(clinic_id):
#         raise HTTPException(status_code=404, detail="Appointment not found")
        
#     check_access(db, user, clinic_id, row.doctor_id, write=True)
#     row.status = "cancelled"
    
#     audit(db, user.id, clinic_id, "appointment.cancelled", "Appointment", row.id)
#     db.commit()
#     return row


# @router.post("/{appointment_id}/noshow")
# @router.post("/{appointment_id}/no_show")
# def no_show(
#     appointment_id: str, 
#     clinic_id: str, 
#     user=Depends(current_user), 
#     db: Session = Depends(get_db)
# ):
#     row = db.get(Appointment, appointment_id)
#     if not row or str(row.clinic_id) != str(clinic_id):
#         raise HTTPException(status_code=404, detail="Appointment not found")
        
#     check_access(db, user, clinic_id, row.doctor_id, write=True)
#     row.status = "no_show"
    
#     audit(db, user.id, clinic_id, "appointment.noshow", "Appointment", row.id)
#     db.commit()
#     return row


# @router.post("/{appointment_id}/scheduled")
# def set_scheduled(
#     appointment_id: str, 
#     clinic_id: str, 
#     user=Depends(current_user), 
#     db: Session = Depends(get_db)
# ):
#     row = db.get(Appointment, appointment_id)
#     if not row or str(row.clinic_id) != str(clinic_id):
#         raise HTTPException(status_code=404, detail="Appointment not found")
        
#     check_access(db, user, clinic_id, row.doctor_id, write=True)
    
#     # Check clinic working hours
#     validate_clinic_operating_hours(db, clinic_id, row.appointment_date, row.appointment_time)

#     row.status = "scheduled"
    
#     audit(db, user.id, clinic_id, "appointment.scheduled", "Appointment", row.id)
#     db.commit()
#     return row

# @router.post("/{appointment_id}/reschedule")
# def reschedule(
#     appointment_id: str, 
#     clinic_id: str, 
#     appointment_date: date, 
#     appointment_time: str, 
#     user=Depends(current_user), 
#     db: Session = Depends(get_db)
# ):
#     row = db.get(Appointment, appointment_id)
#     if not row or str(row.clinic_id) != str(clinic_id):
#         raise HTTPException(status_code=404, detail="Appointment not found")
        
#     check_access(db, user, clinic_id, row.doctor_id, write=True)
    
#     # Check clinic working hours
#     validate_clinic_operating_hours(db, clinic_id, appointment_date, appointment_time)

#     ok, message = doctor_available(db, clinic_id, row.doctor_id, appointment_date, appointment_time, exclude_id=row.id)
#     if not ok:
#         raise HTTPException(status_code=409, detail=message)
        
#     row.appointment_date = appointment_date
#     row.appointment_time = parse_time_input(appointment_time)  # <--- Convert str to time object here
#     row.status = "scheduled"
    
#     audit(db, user.id, clinic_id, "appointment.rescheduled", "Appointment", row.id)
#     db.commit()
#     return row

# @router.post("/{appointment_id}/reminder")
# def send_appointment_reminder(
#     appointment_id: str,
#     clinic_id: str,
#     user=Depends(current_user),
#     db: Session = Depends(get_db)
# ):
#     row = db.get(Appointment, appointment_id)
#     if not row or str(row.clinic_id) != str(clinic_id):
#         raise HTTPException(status_code=404, detail="Appointment not found")
        
#     check_access(db, user, clinic_id, row.doctor_id, write=True)
    
#     patient = db.get(Patient, row.patient_id)
#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")
        
#     recipient = patient.phone or patient.email
#     if not recipient:
#         raise HTTPException(status_code=400, detail="Patient has no phone or email on record")
        
#     audit(db, user.id, clinic_id, "appointment.reminder_sent", "Appointment", row.id)
#     db.commit()
    
#     return {"message": f"Reminder sent to {recipient}"}

from datetime import date, time, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import current_user, membership_for, role_for
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.clinic import ClinicWorkingHours
from app.models.membership import ClinicMembership
from app.models.department import Department
from app.schemas import AppointmentCreate, AppointmentUpdate, AppointmentResponse
from app.services.scheduling import doctor_available
from app.services.audit import audit

router = APIRouter(prefix="/appointments", tags=["Appointments"])

# Accepts both 'noshow' and 'no_show' formatting
STATUSES = {"scheduled", "completed", "cancelled", "noshow", "no_show"}


def parse_time_input(time_val: str | time) -> time:
    """Ensures input is returned as a python datetime.time object."""
    if isinstance(time_val, time):
        return time_val
    if isinstance(time_val, str):
        time_clean = time_val.strip()[:5]  # Get 'HH:MM'
        return datetime.strptime(time_clean, "%H:%M").time()
    raise ValueError(f"Invalid time format: {time_val}")


def check_access(db: Session, user, clinic_id: str, doctor_id: str | None = None, write: bool = False):
    m = membership_for(db, user.id, clinic_id)
    if not m:
        raise HTTPException(status_code=403, detail="No clinic access")
    
    role = str(m.role).upper()
    if role == "DOCTOR" and doctor_id and str(doctor_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Doctors can only manage their own appointments")
        
    if write and role not in {"ADMIN", "FRONT_DESK", "DOCTOR"}:
        raise HTTPException(status_code=403, detail="Insufficient permission")
        
    return m


def validate_clinic_operating_hours(db: Session, clinic_id: str, app_date: date, app_time_val):
    """
    Validates that the appointment date and time fall within the clinic's operating hours.
    """
    if isinstance(app_time_val, time):
        time_clean = app_time_val.strftime("%H:%M")
    elif isinstance(app_time_val, datetime):
        time_clean = app_time_val.strftime("%H:%M")
    elif isinstance(app_time_val, str):
        time_clean = app_time_val.strip()[:5]
    else:
        time_clean = str(app_time_val)[:5]

    # Python weekday: Mon = 0 ... Sun = 6. Map to Sunday = 0 ... Saturday = 6
    day_of_week = (app_date.weekday() + 1) % 7

    working_hour = db.query(ClinicWorkingHours).filter(
        ClinicWorkingHours.clinic_id == clinic_id,
        ClinicWorkingHours.day_of_week == day_of_week
    ).first()

    if working_hour:
        day_name = app_date.strftime("%A")
        if working_hour.is_closed:
            raise HTTPException(
                status_code=400,
                detail=f"The clinic is closed on {day_name}s."
            )

        open_str = working_hour.open_time[:5] if working_hour.open_time else "00:00"
        close_str = working_hour.close_time[:5] if working_hour.close_time else "23:59"

        if time_clean < open_str or time_clean >= close_str:
            raise HTTPException(
                status_code=400,
                detail=f"Clinic hours on {day_name} are {open_str} to {close_str}. Selected time ({time_clean}) is outside clinic hours."
            )


@router.get("/")
def list_appointments(
    clinic_id: str = Query(...),
    appointment_date: date | None = None,
    doctor_id: str | None = None,
    department_id: str | None = None,
    status: str | None = None,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    m = check_access(db, user, clinic_id, doctor_id)
    role = str(m.role).upper()
    
    q = db.query(Appointment).filter(Appointment.clinic_id == clinic_id)
    
    if role == "DOCTOR":
        q = q.filter(Appointment.doctor_id == user.id)
    elif doctor_id:
        q = q.filter(Appointment.doctor_id == doctor_id)
        
    if department_id:
        q = q.filter(Appointment.department_id == department_id)
    if appointment_date:
        q = q.filter(Appointment.appointment_date == appointment_date)
    if status:
        q = q.filter(Appointment.status == status)
        
    appointments = q.order_by(Appointment.appointment_date, Appointment.appointment_time).all()

    # Format response with department information included
    out = []
    for app in appointments:
        dept = db.get(Department, app.department_id) if app.department_id else None
        data = {
            "id": app.id,
            "clinic_id": app.clinic_id,
            "patient_id": app.patient_id,
            "doctor_id": app.doctor_id,
            "department_id": app.department_id,
            "department_name": dept.name if dept else None,
            "appointment_date": app.appointment_date,
            "appointment_time": app.appointment_time,
            "status": app.status,
            "reason": getattr(app, "reason", None),
            "created_at": getattr(app, "created_at", None),
        }
        out.append(data)

    return out


@router.get("/availability")
def availability(
    clinic_id: str, 
    doctor_id: str, 
    appointment_date: date, 
    appointment_time: str, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    check_access(db, user, clinic_id, doctor_id)
    
    try:
        validate_clinic_operating_hours(db, clinic_id, appointment_date, appointment_time)
    except HTTPException as e:
        return {"available": False, "message": e.detail}

    ok, message = doctor_available(db, clinic_id, doctor_id, appointment_date, appointment_time)
    return {"available": ok, "message": message}


@router.post("/", status_code=201)
def create_appointment(
    payload: AppointmentCreate, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    check_access(db, user, payload.clinic_id, payload.doctor_id, write=True)
    
    patient = db.get(Patient, payload.patient_id)
    if not patient or str(patient.clinic_id) != str(payload.clinic_id):
        raise HTTPException(status_code=404, detail="Patient not found in clinic")
        
    if payload.status not in STATUSES:
        raise HTTPException(status_code=400, detail="Invalid appointment status")

    # Determine department_id (use provided department_id or fall back to doctor's primary department)
    dept_id = getattr(payload, "department_id", None)
    if dept_id:
        dept = db.get(Department, dept_id)
        if not dept or str(dept.clinic_id) != str(payload.clinic_id):
            raise HTTPException(status_code=404, detail="Department not found in clinic")
    else:
        # Resolve doctor's assigned department in this clinic
        doc_membership = (
            db.query(ClinicMembership)
            .filter(
                ClinicMembership.user_id == payload.doctor_id,
                ClinicMembership.clinic_id == payload.clinic_id,
                ClinicMembership.is_active.is_(True),
            )
            .first()
        )
        if doc_membership:
            dept_id = doc_membership.department_id

    if payload.status == "scheduled":
        validate_clinic_operating_hours(
            db, payload.clinic_id, payload.appointment_date, payload.appointment_time
        )
        
        ok, message = doctor_available(
            db, payload.clinic_id, payload.doctor_id, payload.appointment_date, payload.appointment_time
        )
        if not ok:
            raise HTTPException(status_code=409, detail=message)
            
    payload_dict = payload.model_dump()
    payload_dict["department_id"] = dept_id

    row = Appointment(**payload_dict)
    db.add(row)
    db.flush()
    
    audit(db, user.id, row.clinic_id, "appointment.created", "Appointment", row.id)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{appointment_id}")
def get_appointment(
    appointment_id: str, 
    clinic_id: str, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    check_access(db, user, clinic_id)
    row = db.get(Appointment, appointment_id)
    if not row or str(row.clinic_id) != str(clinic_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    user_role = role_for(db, user.id, clinic_id)
    if user_role and str(user_role).upper() == "DOCTOR" and str(row.doctor_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    return row


@router.patch("/{appointment_id}")
def update_appointment(
    appointment_id: str, 
    clinic_id: str, 
    payload: AppointmentUpdate, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    row = db.get(Appointment, appointment_id)
    if not row or str(row.clinic_id) != str(clinic_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    check_access(db, user, clinic_id, row.doctor_id, write=True)
    data = payload.model_dump(exclude_unset=True)
    
    new_doctor = data.get("doctor_id", row.doctor_id)
    new_date = data.get("appointment_date", row.appointment_date)
    new_time = data.get("appointment_time", row.appointment_time)
    new_clinic = data.get("clinic_id", row.clinic_id)

    if "department_id" in data and data["department_id"] is not None:
        dept = db.get(Department, data["department_id"])
        if not dept or str(dept.clinic_id) != str(clinic_id):
            raise HTTPException(status_code=404, detail="Department not found in clinic")

    user_role = role_for(db, user.id, clinic_id)
    if user_role and str(user_role).upper() == "DOCTOR" and str(new_doctor) != str(user.id):
        raise HTTPException(status_code=403, detail="Doctor cannot assign another doctor")

    if data.get("status") and data["status"] not in STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    if data.get("status", row.status) == "scheduled":
        validate_clinic_operating_hours(db, new_clinic, new_date, new_time)

        ok, message = doctor_available(db, new_clinic, new_doctor, new_date, new_time, exclude_id=row.id)
        if not ok:
            raise HTTPException(status_code=409, detail=message)

    if "appointment_time" in data and data["appointment_time"] is not None:
        data["appointment_time"] = parse_time_input(data["appointment_time"])

    for k, v in data.items():
        setattr(row, k, v)
        
    audit(db, user.id, clinic_id, "appointment.updated", "Appointment", row.id)
    db.commit()
    db.refresh(row)
    return row


@router.post("/{appointment_id}/complete")
def complete(
    appointment_id: str, 
    clinic_id: str, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    row = db.get(Appointment, appointment_id)
    if not row or str(row.clinic_id) != str(clinic_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    check_access(db, user, clinic_id, row.doctor_id, write=True)
    row.status = "completed"
    
    p = db.get(Patient, row.patient_id)
    if p and (not p.last_visit or p.last_visit < row.appointment_date):
        p.last_visit = row.appointment_date
        
    audit(db, user.id, clinic_id, "appointment.completed", "Appointment", row.id)
    db.commit()
    return row


@router.post("/{appointment_id}/cancel")
def cancel(
    appointment_id: str, 
    clinic_id: str, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    row = db.get(Appointment, appointment_id)
    if not row or str(row.clinic_id) != str(clinic_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    check_access(db, user, clinic_id, row.doctor_id, write=True)
    row.status = "cancelled"
    
    audit(db, user.id, clinic_id, "appointment.cancelled", "Appointment", row.id)
    db.commit()
    return row


@router.post("/{appointment_id}/noshow")
@router.post("/{appointment_id}/no_show")
def no_show(
    appointment_id: str, 
    clinic_id: str, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    row = db.get(Appointment, appointment_id)
    if not row or str(row.clinic_id) != str(clinic_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    check_access(db, user, clinic_id, row.doctor_id, write=True)
    row.status = "no_show"
    
    audit(db, user.id, clinic_id, "appointment.noshow", "Appointment", row.id)
    db.commit()
    return row


@router.post("/{appointment_id}/scheduled")
def set_scheduled(
    appointment_id: str, 
    clinic_id: str, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    row = db.get(Appointment, appointment_id)
    if not row or str(row.clinic_id) != str(clinic_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    check_access(db, user, clinic_id, row.doctor_id, write=True)
    
    validate_clinic_operating_hours(db, clinic_id, row.appointment_date, row.appointment_time)

    row.status = "scheduled"
    
    audit(db, user.id, clinic_id, "appointment.scheduled", "Appointment", row.id)
    db.commit()
    return row


@router.post("/{appointment_id}/reschedule")
def reschedule(
    appointment_id: str, 
    clinic_id: str, 
    appointment_date: date, 
    appointment_time: str, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    row = db.get(Appointment, appointment_id)
    if not row or str(row.clinic_id) != str(clinic_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    check_access(db, user, clinic_id, row.doctor_id, write=True)
    
    validate_clinic_operating_hours(db, clinic_id, appointment_date, appointment_time)

    ok, message = doctor_available(db, clinic_id, row.doctor_id, appointment_date, appointment_time, exclude_id=row.id)
    if not ok:
        raise HTTPException(status_code=409, detail=message)
        
    row.appointment_date = appointment_date
    row.appointment_time = parse_time_input(appointment_time)
    row.status = "scheduled"
    
    audit(db, user.id, clinic_id, "appointment.rescheduled", "Appointment", row.id)
    db.commit()
    return row


@router.post("/{appointment_id}/reminder")
def send_appointment_reminder(
    appointment_id: str,
    clinic_id: str,
    user=Depends(current_user),
    db: Session = Depends(get_db)
):
    row = db.get(Appointment, appointment_id)
    if not row or str(row.clinic_id) != str(clinic_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    check_access(db, user, clinic_id, row.doctor_id, write=True)
    
    patient = db.get(Patient, row.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    recipient = patient.phone or patient.email
    if not recipient:
        raise HTTPException(status_code=400, detail="Patient has no phone or email on record")
        
    audit(db, user.id, clinic_id, "appointment.reminder_sent", "Appointment", row.id)
    db.commit()
    
    return {"message": f"Reminder sent to {recipient}"}