# from fastapi import APIRouter, Depends, HTTPException, Query
# from sqlalchemy import or_, func
# from sqlalchemy.orm import Session

# from app.core.database import get_db
# from app.core.auth import current_user, membership_for
# from app.models.patient import Patient
# from app.schemas import PatientCreate, PatientUpdate, PatientResponse
# from app.services.audit import audit

# router = APIRouter(prefix="/patients", tags=["Patients"])


# def access(db, user, clinic_id):
#     m = membership_for(db, user.id, clinic_id)

#     if not m:
#         raise HTTPException(status_code=403, detail="No clinic access")

#     return m


# @router.get("/", response_model=list[PatientResponse])
# def list_patients(
#     clinic_id: str,
#     q: str = Query("", max_length=100),
#     user=Depends(current_user),
#     db: Session = Depends(get_db),
# ):
#     access(db, user, clinic_id)

#     query = db.query(Patient).filter(
#         Patient.clinic_id == clinic_id,
#         Patient.is_active.is_(True),
#     )

#     if q:
#         like = f"%{q}%"
#         query = query.filter(
#             or_(
#                 Patient.full_name.ilike(like),
#                 Patient.patient_number.ilike(like),
#                 Patient.phone.ilike(like),
#                 Patient.email.ilike(like),
#             )
#         )

#     return query.order_by(Patient.full_name).all()

# @router.post("/", response_model=PatientResponse, status_code=201)
# def create_patient(
#     clinic_id: str,
#     payload: PatientCreate,
#     user=Depends(current_user),
#     db: Session = Depends(get_db),
# ):
#     access(db, user, clinic_id)

#     # Generate sequential unique Patient Number (e.g., PAT-1001)
#     total_count = db.query(Patient).filter(Patient.clinic_id == clinic_id).count()
#     patient_number = f"PAT-{1001 + total_count}"

#     row = Patient(
#         clinic_id=clinic_id,
#         patient_number=patient_number,
#         **payload.model_dump(),
#     )

#     db.add(row)
#     db.flush()

#     audit(db, user.id, clinic_id, "patient.created", "Patient", row.id)
#     db.commit()
#     db.refresh(row)

#     return row

# @router.get("/{patient_id}", response_model=PatientResponse)
# def get_patient(
#     patient_id: str,
#     clinic_id: str,
#     user=Depends(current_user),
#     db: Session = Depends(get_db),
# ):
#     access(db, user, clinic_id)

#     row = db.get(Patient, patient_id)

#     if not row or row.clinic_id != clinic_id:
#         raise HTTPException(
#             status_code=404,
#             detail="Patient not found",
#         )

#     return row


# @router.patch("/{patient_id}", response_model=PatientResponse)
# def update_patient(
#     patient_id: str,
#     clinic_id: str,
#     payload: PatientUpdate,
#     user=Depends(current_user),
#     db: Session = Depends(get_db),
# ):
#     access(db, user, clinic_id)

#     row = db.get(Patient, patient_id)

#     if not row or row.clinic_id != clinic_id:
#         raise HTTPException(
#             status_code=404,
#             detail="Patient not found",
#         )

#     updates = payload.model_dump(exclude_unset=True)

#     for key, value in updates.items():
#         setattr(row, key, value)

#     audit(
#         db,
#         user.id,
#         clinic_id,
#         "patient.updated",
#         "Patient",
#         row.id,
#     )

#     db.commit()
#     db.refresh(row)

#     return row


# @router.delete("/{patient_id}")
# def deactivate_patient(
#     patient_id: str,
#     clinic_id: str,
#     user=Depends(current_user),
#     db: Session = Depends(get_db),
# ):
#     access(db, user, clinic_id)

#     row = db.get(Patient, patient_id)

#     if not row or row.clinic_id != clinic_id:
#         raise HTTPException(
#             status_code=404,
#             detail="Patient not found",
#         )

#     row.is_active = False

#     audit(
#         db,
#         user.id,
#         clinic_id,
#         "patient.deactivated",
#         "Patient",
#         row.id,
#     )

#     db.commit()

#     return {
#         "message": "Patient deactivated"
#     }

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import current_user, membership_for
from app.models.patient import Patient
from app.models.clinic import Clinic
from app.schemas import PatientCreate, PatientUpdate, PatientResponse
from app.services.audit import audit

router = APIRouter(prefix="/patients", tags=["Patients"])


def access(db, user, clinic_id):
    m = membership_for(db, user.id, clinic_id)

    if not m:
        raise HTTPException(status_code=403, detail="No clinic access")

    return m


@router.get("/", response_model=list[PatientResponse])
def list_patients(
    clinic_id: str,
    q: str = Query("", max_length=100),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    access(db, user, clinic_id)

    query = db.query(Patient).filter(
        Patient.clinic_id == clinic_id,
        Patient.is_active.is_(True),
    )

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Patient.full_name.ilike(like),
                Patient.patient_number.ilike(like),
                Patient.phone.ilike(like),
                Patient.email.ilike(like),
            )
        )

    return query.order_by(Patient.full_name).all()


@router.post("/", response_model=PatientResponse, status_code=201)
def create_patient(
    clinic_id: str,
    payload: PatientCreate,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    access(db, user, clinic_id)

    # 1. Retrieve clinic and extract short_name (fallback to first 4 letters of name or 'PAT')
    clinic = db.get(Clinic, clinic_id)
    raw_prefix = clinic.short_name if (clinic and clinic.short_name) else (clinic.name[:4] if clinic else "PAT")
    prefix = raw_prefix.upper().strip()

    # 2. Sequential unique Patient Number (e.g., CLINIC-00001)
    total_count = db.query(Patient).filter(Patient.clinic_id == clinic_id).count()
    patient_number = f"{prefix}-{total_count + 1:05d}"

    row = Patient(
        clinic_id=clinic_id,
        patient_number=patient_number,
        **payload.model_dump(),
    )

    db.add(row)
    db.flush()

    audit(db, user.id, clinic_id, "patient.created", "Patient", row.id)
    db.commit()
    db.refresh(row)

    return row


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: str,
    clinic_id: str,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    access(db, user, clinic_id)

    row = db.get(Patient, patient_id)

    if not row or row.clinic_id != clinic_id:
        raise HTTPException(
            status_code=404,
            detail="Patient not found",
        )

    return row


@router.get("/{patient_id}/profile")
def get_patient_profile(
    patient_id: str,
    clinic_id: str,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    """
    Returns full patient basic details alongside chronological visit history,
    including prescriptions, vitals, diagnoses, doctor profile info, and billing data.
    """
    access(db, user, clinic_id)

    patient = db.get(Patient, patient_id)
    if not patient or patient.clinic_id != clinic_id:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Chronologically sort prescriptions (oldest to newest for indexing)
    sorted_rx = sorted(patient.prescriptions, key=lambda rx: rx.rx_date)
    total_visits = len(sorted_rx)

    visits_timeline = []
    for index, rx in enumerate(sorted_rx, start=1):
        # Match bill for this encounter date (if available)
        linked_bill = next((b for b in patient.bills if b.bill_date == rx.rx_date), None)

        # Extract doctor details from User and DoctorProfile
        doctor_info = None
        if rx.doctor:
            doc_profile = getattr(rx.doctor, "doctor_profile", None)
            doctor_info = {
                "id": rx.doctor.id,
                "full_name": rx.doctor.full_name,
                "specialty": doc_profile.specialty if doc_profile else None,
                "degrees": doc_profile.degrees if doc_profile else None,
                "license_number": doc_profile.license_number if doc_profile else None,
            }

        visits_timeline.append({
            "visit_label": f"Visit {index}",
            "visit_number": index,
            "rx_date": rx.rx_date,
            "doctor": doctor_info,
            "vitals": rx.vitals,
            "chief_complaints": rx.chief_complaints,
            "diagnosis": rx.diagnosis,
            "medicines": rx.medicines,
            "advice": rx.advice,
            "follow_up_date": rx.follow_up_date,
            "billing": {
                "invoice_number": linked_bill.invoice_number,
                "total": float(linked_bill.total),
                "status": linked_bill.status,
            } if linked_bill else None,
        })

    # Reverse to show newest visit first on UI
    visits_timeline.reverse()

    return {
        "id": patient.id,
        "patient_number": patient.patient_number,
        "full_name": patient.full_name,
        "phone": patient.phone,
        "email": patient.email,
        "date_of_birth": patient.date_of_birth,
        "gender": patient.gender,
        "address": patient.address,
        "medical_notes": patient.medical_notes,
        "last_visit": patient.last_visit,
        "total_visits": total_visits,
        "visits": visits_timeline,
    }


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: str,
    clinic_id: str,
    payload: PatientUpdate,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    access(db, user, clinic_id)

    row = db.get(Patient, patient_id)

    if not row or row.clinic_id != clinic_id:
        raise HTTPException(
            status_code=404,
            detail="Patient not found",
        )

    updates = payload.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(row, key, value)

    audit(
        db,
        user.id,
        clinic_id,
        "patient.updated",
        "Patient",
        row.id,
    )

    db.commit()
    db.refresh(row)

    return row


@router.delete("/{patient_id}")
def deactivate_patient(
    patient_id: str,
    clinic_id: str,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    access(db, user, clinic_id)

    row = db.get(Patient, patient_id)

    if not row or row.clinic_id != clinic_id:
        raise HTTPException(
            status_code=404,
            detail="Patient not found",
        )

    row.is_active = False

    audit(
        db,
        user.id,
        clinic_id,
        "patient.deactivated",
        "Patient",
        row.id,
    )

    db.commit()

    return {"message": "Patient deactivated"}