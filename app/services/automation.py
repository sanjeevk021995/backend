from datetime import date
from sqlalchemy.orm import Session
from app.models.appointment import Appointment
from app.models.billing import Bill
from app.models.patient import Patient
from app.models.clinic import ClinicSettings

def apply_auto_rules(db: Session):
    changed = 0
    settings = db.query(ClinicSettings).all()

    for s in settings:
        if s.auto_complete:
            appts = db.query(Appointment).filter(
                Appointment.clinic_id == s.clinic_id,
                Appointment.status == "scheduled",
            ).all()
            for a in appts:
                paid = db.query(Bill).filter(
                    Bill.clinic_id == a.clinic_id,
                    Bill.patient_id == a.patient_id,
                    Bill.bill_date == a.appointment_date,
                    Bill.status == "paid",
                ).first()
                if paid:
                    a.status = "completed"
                    a.auto_note = "Auto-completed — payment received"
                    p = db.get(Patient, a.patient_id)
                    if p and (not p.last_visit or p.last_visit < a.appointment_date):
                        p.last_visit = a.appointment_date
                    changed += 1

        if s.auto_no_show:
            appts = db.query(Appointment).filter(
                Appointment.clinic_id == s.clinic_id,
                Appointment.status == "scheduled",
                Appointment.appointment_date < date.today(),
            ).all()
            for a in appts:
                a.status = "noshow"
                a.auto_note = "Auto-marked no-show — day ended"
                changed += 1

    db.commit()
    return changed
