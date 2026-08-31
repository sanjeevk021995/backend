from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import current_user, membership_for
from app.models.prescription import Prescription
from app.models.patient import Patient
from app.schemas import PrescriptionCreate, PrescriptionUpdate, PrescriptionResponse
from app.services.audit import audit

router = APIRouter(tags=["Prescriptions"])


def access(db, user, clinic_id):
    m = membership_for(db, user.id, clinic_id)
    if not m:
        raise HTTPException(status_code=403, detail="No clinic access")
    return m


@router.post("/prescriptions/", response_model=PrescriptionResponse, status_code=201)
def create_prescription(
    payload: PrescriptionCreate,
    clinic_id: str = Query(...),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    access(db, user, clinic_id)

    patient = db.get(Patient, payload.patient_id)
    if not patient or patient.clinic_id != clinic_id:
        raise HTTPException(status_code=404, detail="Patient not found")

    row = Prescription(
        clinic_id=clinic_id,
        doctor_id=user.id,
        **payload.model_dump()
    )
    
    patient.last_visit = payload.rx_date or date.today()

    db.add(row)
    db.commit()
    db.refresh(row)

    audit(db, user.id, clinic_id, "prescription.created", "Prescription", row.id)
    return row


@router.get("/prescriptions/patient/{patient_id}", response_model=list[PrescriptionResponse])
def get_patient_history(
    patient_id: str,
    clinic_id: str = Query(...),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    access(db, user, clinic_id)

    records = (
        db.query(Prescription)
        .filter(
            Prescription.patient_id == patient_id,
            Prescription.clinic_id == clinic_id
        )
        .order_by(Prescription.rx_date.desc(), Prescription.created_at.desc())
        .all()
    )

    return records


@router.patch("/prescriptions/{prescription_id}", response_model=PrescriptionResponse)
def update_prescription(
    prescription_id: str,
    payload: PrescriptionUpdate,
    clinic_id: str = Query(...),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    """
    Updates an existing prescription record.
    """
    access(db, user, clinic_id)

    row = db.get(Prescription, prescription_id)

    if not row or row.clinic_id != clinic_id:
        raise HTTPException(
            status_code=404,
            detail="Prescription not found",
        )

    updates = payload.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(row, key, value)

    # Sync patient's last visit if rx_date was modified
    if "rx_date" in updates and updates["rx_date"] and row.patient_id:
        patient = db.get(Patient, row.patient_id)
        if patient:
            patient.last_visit = updates["rx_date"]

    audit(
        db,
        user.id,
        clinic_id,
        "prescription.updated",
        "Prescription",
        row.id,
    )

    db.commit()
    db.refresh(row)

    return row