from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import current_user, membership_for
from app.models.reminder import Reminder
from app.models.patient import Patient
from app.schemas import ReminderCreate
from app.services.messaging import send_reminder
from app.services.audit import audit

router = APIRouter(prefix="/reminders", tags=["Reminders"])


def access(db: Session, user, clinic_id: str, write: bool = False):
    m = membership_for(db, user.id, clinic_id)
    if not m:
        raise HTTPException(status_code=403, detail="No clinic access")
    if write and m.role not in {"ADMIN", "FRONT_DESK", "DOCTOR"}:
        raise HTTPException(status_code=403, detail="Insufficient permission")


@router.get("/")
def list_reminders(clinic_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    access(db, user, clinic_id)
    return (
        db.query(Reminder)
        .filter(Reminder.clinic_id == clinic_id)
        .order_by(Reminder.created_at.desc())
        .all()
    )


@router.post("/", status_code=201)
def create_reminder(payload: ReminderCreate, user=Depends(current_user), db: Session = Depends(get_db)):
    access(db, user, payload.clinic_id, write=True)
    patient = db.get(Patient, payload.patient_id)
    if not patient or str(patient.clinic_id) != str(payload.clinic_id):
        raise HTTPException(status_code=404, detail="Patient not found in clinic")

    row = Reminder(**payload.model_dump())
    db.add(row)
    db.flush()

    audit(db, user.id, payload.clinic_id, "reminder.created", "Reminder", row.id)
    db.commit()
    db.refresh(row)
    return row


@router.post("/{reminder_id}/send")
def send(reminder_id: str, clinic_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    access(db, user, clinic_id, write=True)
    row = db.get(Reminder, reminder_id)
    if not row or str(row.clinic_id) != str(clinic_id):
        raise HTTPException(status_code=404, detail="Reminder not found")

    patient = db.get(Patient, row.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record missing")

    recipient = patient.phone if row.channel == "whatsapp" else patient.email
    if not recipient:
        raise HTTPException(status_code=400, detail=f"Patient has no {row.channel} contact detail on file")

    row = send_reminder(db, row, recipient)

    if row.status == "failed":
        audit(
            db,
            user.id,
            clinic_id,
            "reminder.failed",
            "Reminder",
            row.id,
            {"channel": row.channel, "error": row.error_message},
        )
        db.commit()
        raise HTTPException(status_code=502, detail=f"Failed to send reminder: {row.error_message}")

    audit(
        db,
        user.id,
        clinic_id,
        "reminder.sent",
        "Reminder",
        row.id,
        {"channel": row.channel, "recipient": recipient, "provider_id": row.provider_message_id},
    )
    db.commit()
    db.refresh(row)
    return row