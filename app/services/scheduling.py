from datetime import date
from sqlalchemy.orm import Session
from app.models.schedule import DoctorScheduleOverride, DoctorLeave
from app.models.appointment import Appointment
from app.models.clinic import ClinicWorkingHours


def doctor_available(db: Session, clinic_id: str, doctor_id: str, appt_date: date, appt_time: str, exclude_id=None):
    """
    Checks if a doctor is available for an appointment by evaluating:
    1. Doctor leave records.
    2. Specific date schedule overrides (if set for the exact calendar date).
    3. Default clinic operating hours for that day of the week.
    4. Conflicting scheduled appointments.
    """
    time_clean = str(appt_time).strip()[:5]
    day_of_week = (appt_date.weekday() + 1) % 7  # 0=Sunday ... 6=Saturday

    # 1. Check Doctor Leave First
    leave = (
        db.query(DoctorLeave)
        .filter(
            DoctorLeave.clinic_id == clinic_id,
            DoctorLeave.doctor_id == doctor_id,
            DoctorLeave.from_date <= appt_date,
            DoctorLeave.to_date >= appt_date,
        )
        .first()
    )

    if leave:
        return False, "Doctor is on leave for this date"

    # 2. Check Date-Specific Override
    override = (
        db.query(DoctorScheduleOverride)
        .filter(
            DoctorScheduleOverride.clinic_id == clinic_id,
            DoctorScheduleOverride.doctor_id == doctor_id,
            DoctorScheduleOverride.override_date == appt_date,
        )
        .first()
    )

    if override:
        if override.is_off:
            return False, f"Doctor is marked off on {appt_date}"

        start_t = override.start_time[:5] if override.start_time else "00:00"
        end_t = override.end_time[:5] if override.end_time else "23:59"

        if time_clean < start_t or time_clean >= end_t:
            return False, f"Appointment time ({time_clean}) is outside doctor's override hours ({start_t} - {end_t})"

    # 3. Fallback to Default Clinic Operating Hours
    else:
        clinic_hours = (
            db.query(ClinicWorkingHours)
            .filter(
                ClinicWorkingHours.clinic_id == clinic_id,
                ClinicWorkingHours.day_of_week == day_of_week,
            )
            .first()
        )

        if clinic_hours:
            if clinic_hours.is_closed:
                return False, f"Clinic is closed on {appt_date.strftime('%A')}s"

            open_str = clinic_hours.open_time[:5] if clinic_hours.open_time else "00:00"
            close_str = clinic_hours.close_time[:5] if clinic_hours.close_time else "23:59"

            if time_clean < open_str or time_clean >= close_str:
                return False, f"Appointment time ({time_clean}) is outside clinic operating hours ({open_str} - {close_str})"

    # 4. Check Existing Appointment Conflicts
    q = db.query(Appointment).filter(
        Appointment.clinic_id == clinic_id,
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == appt_date,
        Appointment.appointment_time == appt_time,
        Appointment.status == "scheduled",
    )

    if exclude_id:
        q = q.filter(Appointment.id != exclude_id)

    if q.first():
        return False, "Time slot is already booked"

    return True, "Available"