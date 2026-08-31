from datetime import date, time, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import current_user, membership_for
from app.models.schedule import DoctorSchedule, DoctorLeave, DoctorScheduleOverride
from app.models.membership import ClinicMembership
from app.models.clinic import ClinicWorkingHours
from app.schemas import ScheduleIn, LeaveIn, ScheduleOverrideIn
from app.services.audit import audit

router = APIRouter(prefix="/schedules", tags=["Doctor Scheduling"])

# Standardized app indexing: 0=Sunday, 1=Monday, ..., 6=Saturday
DAY_NAMES = {
    0: "Sunday",
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
}

def verify_member(db: Session, user, clinic_id: str):
    m = membership_for(db, user.id, clinic_id)
    if not m:
        raise HTTPException(status_code=403, detail="No clinic access")
    return m


def to_time_str(val) -> str:
    """Helper to safely convert time, datetime, or string to HH:MM format."""
    if not val:
        return ""
    if isinstance(val, time):
        return val.strftime("%H:%M")
    return str(val).strip()[:5]


def validate_schedule_against_clinic_hours(db: Session, clinic_id: str, schedules: list[ScheduleIn]):
    """Validates that weekly shifts fall within clinic operating hours."""
    working_hours = db.query(ClinicWorkingHours).filter(
        ClinicWorkingHours.clinic_id == clinic_id
    ).all()
    
    hours_map = {int(wh.day_of_week): wh for wh in working_hours if wh.day_of_week is not None}

    for sch in schedules:
        day_idx = int(sch.day_of_week)
        day_name = DAY_NAMES.get(day_idx, f"Day {day_idx}")

        doc_start = to_time_str(sch.start_time)
        doc_end = to_time_str(sch.end_time)

        if doc_end <= doc_start:
            raise HTTPException(
                status_code=400,
                detail=f"End time must be after start time on {day_name}."
            )

        wh = hours_map.get(day_idx)
        if wh:
            if wh.is_closed:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot schedule doctor on {day_name} because the clinic is closed."
                )

            clinic_open = to_time_str(wh.open_time) or "00:00"
            clinic_close = to_time_str(wh.close_time) or "23:59"

            if doc_start < clinic_open or doc_end > clinic_close:
                raise HTTPException(
                    status_code=400,
                    detail=f"Doctor hours on {day_name} ({doc_start}-{doc_end}) must fall within clinic operating hours ({clinic_open}-{clinic_close})."
                )


@router.get("/clinics/{clinic_id}/members")
def get_schedulable_members(clinic_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    verify_member(db, user, clinic_id)
    
    memberships = db.query(ClinicMembership).filter(
        ClinicMembership.clinic_id == clinic_id,
        ClinicMembership.is_active.is_(True),
        ClinicMembership.role.in_(["DOCTOR", "STAFF", "RECEPTIONIST"])
    ).all()
    
    result = []
    for m in memberships:
        if m.user:
            result.append({
                "id": m.user.id,
                "full_name": getattr(m.user, 'full_name', getattr(m.user, 'email', 'Staff Member')),
                "email": m.user.email,
                "role": m.role,
                "specialty": getattr(m.user, 'specialty', m.role)
            })
    return result


@router.get("/clinics/{clinic_id}/doctors/{doctor_id}/month-calendar")
def get_monthly_schedule(
    clinic_id: str,
    doctor_id: str,
    start_date: date = Query(...),
    end_date: date = Query(...),
    user=Depends(current_user),
    db: Session = Depends(get_db)
):
    """
    Returns a day-by-day calendar for a date range (1 month).
    Applies order of priority: Leave > Custom Date Override > Weekly Schedule > Default Clinic Hours.
    """
    verify_member(db, user, clinic_id)

    clinic_hours = {
        int(wh.day_of_week): wh 
        for wh in db.query(ClinicWorkingHours).filter(ClinicWorkingHours.clinic_id == clinic_id).all()
    }

    weekly_schedules = {
        int(sch.day_of_week): sch
        for sch in db.query(DoctorSchedule).filter(
            DoctorSchedule.clinic_id == clinic_id,
            DoctorSchedule.doctor_id == doctor_id
        ).all()
    }

    overrides = {
        ov.override_date: ov 
        for ov in db.query(DoctorScheduleOverride).filter(
            DoctorScheduleOverride.clinic_id == clinic_id,
            DoctorScheduleOverride.doctor_id == doctor_id,
            DoctorScheduleOverride.override_date >= start_date,
            DoctorScheduleOverride.override_date <= end_date
        ).all()
    }

    leaves = db.query(DoctorLeave).filter(
        DoctorLeave.clinic_id == clinic_id,
        DoctorLeave.doctor_id == doctor_id,
        DoctorLeave.from_date <= end_date,
        DoctorLeave.to_date >= start_date
    ).all()

    calendar_list = []
    curr = start_date
    while curr <= end_date:
        # Converts Python weekday (Mon=0..Sun=6) to App Standard (Sun=0..Sat=6)
        dow = (curr.weekday() + 1) % 7

        c_hour = clinic_hours.get(dow)
        w_sch = weekly_schedules.get(dow)
        override = overrides.get(curr)

        is_on_leave = any(l.from_date <= curr <= l.to_date for l in leaves)

        if is_on_leave:
            status = "ON_LEAVE"
            start_t, end_t, is_off = None, None, True
        elif override:
            status = "CUSTOM_OVERRIDE"
            start_t = to_time_str(override.start_time)
            end_t = to_time_str(override.end_time)
            is_off = override.is_off
        elif w_sch:
            status = "WEEKLY_SCHEDULE"
            start_t = to_time_str(w_sch.start_time)
            end_t = to_time_str(w_sch.end_time)
            is_off = False
        elif c_hour:
            status = "DEFAULT_CLINIC_HOURS"
            start_t = to_time_str(c_hour.open_time)
            end_t = to_time_str(c_hour.close_time)
            is_off = c_hour.is_closed
        else:
            status = "DEFAULT_CLINIC_HOURS"
            start_t, end_t, is_off = "08:00", "20:00", (dow == 0)

        calendar_list.append({
            "date": str(curr),
            "day_of_week": dow,
            "day_name": DAY_NAMES[dow],
            "start_time": start_t,
            "end_time": end_t,
            "is_off": is_off,
            "schedule_type": status
        })
        curr += timedelta(days=1)

    return calendar_list

def parse_to_time_obj(val) -> Optional[time]:
    """Ensures input is converted to a Python time object for SQLite compatibility."""
    if not val:
        return None
    if isinstance(val, time):
        return val
    if isinstance(val, str):
        parts = [int(p) for p in val.strip().split(":")]
        return time(*parts)
    return None



@router.get("/clinics/{clinic_id}/doctors/{doctor_id}/schedule")
def schedules(clinic_id: str, doctor_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    verify_member(db, user, clinic_id)
    return db.query(DoctorSchedule).filter(
        DoctorSchedule.clinic_id == clinic_id,
        DoctorSchedule.doctor_id == doctor_id
    ).order_by(DoctorSchedule.day_of_week).all()


@router.put("/clinics/{clinic_id}/doctors/{doctor_id}/schedule")
def replace_schedule(
    clinic_id: str, 
    doctor_id: str, 
    payload: list[ScheduleIn], 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    verify_member(db, user, clinic_id)
    validate_schedule_against_clinic_hours(db, clinic_id, payload)

    db.query(DoctorSchedule).filter(
        DoctorSchedule.clinic_id == clinic_id,
        DoctorSchedule.doctor_id == doctor_id
    ).delete()

    for x in payload:
        data = x.model_dump() if hasattr(x, 'model_dump') else x.dict()
        db.add(DoctorSchedule(clinic_id=clinic_id, doctor_id=doctor_id, **data))

    audit(db, user.id, clinic_id, "schedule.replaced", "Doctor", doctor_id)
    db.commit()
    return {"message": "Schedule updated successfully"}


@router.get("/clinics/{clinic_id}/doctors/{doctor_id}/leave")
def leaves(clinic_id: str, doctor_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    verify_member(db, user, clinic_id)
    return db.query(DoctorLeave).filter(
        DoctorLeave.clinic_id == clinic_id,
        DoctorLeave.doctor_id == doctor_id
    ).order_by(DoctorLeave.from_date).all()


@router.post("/clinics/{clinic_id}/doctors/{doctor_id}/leave", status_code=201)
def create_leave(
    clinic_id: str, 
    doctor_id: str, 
    payload: LeaveIn, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    verify_member(db, user, clinic_id)
    if payload.clinic_id != clinic_id:
        raise HTTPException(status_code=400, detail="Clinic mismatch")

    data = payload.model_dump(exclude={"clinic_id"}) if hasattr(payload, 'model_dump') else payload.dict(exclude={"clinic_id"})
    row = DoctorLeave(clinic_id=clinic_id, doctor_id=doctor_id, **data)
    db.add(row)
    db.flush()  # Populates row.id before calling audit
    
    audit(db, user.id, clinic_id, "doctor.leave.created", "DoctorLeave", str(row.id))
    db.commit()
    return row


@router.delete("/clinics/{clinic_id}/leave/{leave_id}")
def delete_leave(clinic_id: str, leave_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    verify_member(db, user, clinic_id)
    row = db.get(DoctorLeave, leave_id)
    if not row or row.clinic_id != clinic_id:
        raise HTTPException(status_code=404, detail="Leave not found")

    db.delete(row)
    audit(db, user.id, clinic_id, "doctor.leave.deleted", "DoctorLeave", leave_id)
    db.commit()
    return {"message": "Deleted"}


@router.delete("/clinics/{clinic_id}/doctors/{doctor_id}/override")
def delete_override(
    clinic_id: str,
    doctor_id: str,
    override_date: date = Query(...),
    user=Depends(current_user),
    db: Session = Depends(get_db)
):
    """Removes a custom override so the date reverts to standard weekly schedules."""
    verify_member(db, user, clinic_id)
    
    override = db.query(DoctorScheduleOverride).filter(
        DoctorScheduleOverride.clinic_id == clinic_id,
        DoctorScheduleOverride.doctor_id == doctor_id,
        DoctorScheduleOverride.override_date == override_date
    ).first()

    if not override:
        raise HTTPException(status_code=404, detail="Override not found for this date")

    db.delete(override)
    audit(db, user.id, clinic_id, "schedule.override.deleted", "DoctorScheduleOverride", str(override_date))
    db.commit()
    return {"message": "Override removed successfully"}

@router.post("/clinics/{clinic_id}/doctors/{doctor_id}/override")
def create_or_update_override(
    clinic_id: str,
    doctor_id: str,
    payload: ScheduleOverrideIn,
    user=Depends(current_user),
    db: Session = Depends(get_db)
):
    verify_member(db, user, clinic_id)

    dow = (payload.override_date.weekday() + 1) % 7
    c_hour = db.query(ClinicWorkingHours).filter(
        ClinicWorkingHours.clinic_id == clinic_id,
        ClinicWorkingHours.day_of_week == dow
    ).first()

    if c_hour and c_hour.is_closed and not payload.is_off:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot schedule doctor on {payload.override_date.strftime('%A')} because the clinic is closed."
        )

    start_t = parse_to_time_obj(payload.start_time)
    end_t = parse_to_time_obj(payload.end_time)

    try:
        existing = db.query(DoctorScheduleOverride).filter(
            DoctorScheduleOverride.clinic_id == clinic_id,
            DoctorScheduleOverride.doctor_id == doctor_id,
            DoctorScheduleOverride.override_date == payload.override_date
        ).first()

        if existing:
            existing.start_time = start_t
            existing.end_time = end_t
            existing.is_off = payload.is_off
        else:
            existing = DoctorScheduleOverride(
                clinic_id=clinic_id,
                doctor_id=doctor_id,
                override_date=payload.override_date,
                start_time=start_t,
                end_time=end_t,
                is_off=payload.is_off
            )
            db.add(existing)

        db.flush()
        audit(db, user.id, clinic_id, "schedule.override.updated", "DoctorScheduleOverride", str(existing.id or payload.override_date))
        db.commit()
    except Exception as e:
        db.rollback()
        raise e

    return {"message": "Date schedule updated successfully"}