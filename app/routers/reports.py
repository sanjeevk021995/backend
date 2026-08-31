from datetime import date, timedelta
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd

from app.core.database import get_db
from app.core.auth import current_user, membership_for
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.billing import Bill
from app.models.membership import ClinicMembership

router = APIRouter(prefix="/reports", tags=["Reports"])

def access(db, user, clinic_id):
    if not membership_for(db, user.id, clinic_id):
        raise HTTPException(403, "No clinic access")

def period_dates(period: str, anchor: date):
    if period == "weekly":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    if period == "monthly":
        start = anchor.replace(day=1)
        nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return start, nxt - timedelta(days=1)
    if period == "half_yearly":
        start_month = 1 if anchor.month <= 6 else 7
        start = date(anchor.year, start_month, 1)
        end = date(anchor.year, start_month + 5, 1)
        nxt = (end.replace(day=28) + timedelta(days=4)).replace(day=1)
        return start, nxt - timedelta(days=1)
    if period == "annual":
        return date(anchor.year, 1, 1), date(anchor.year, 12, 31)
    raise HTTPException(400, "period must be weekly, monthly, half_yearly or annual")

@router.get("/summary")
def summary(
    clinic_id: str, 
    period: str = "monthly", 
    anchor: date | None = None, 
    user = Depends(current_user), 
    db: Session = Depends(get_db)
):
    access(db, user, clinic_id)
    anchor = anchor or date.today()
    start, end = period_dates(period, anchor)

    new_patients = db.query(Patient).filter(
        Patient.clinic_id == clinic_id,
        func.date(Patient.created_at) >= start,
        func.date(Patient.created_at) <= end,
    ).count()

    appts = db.query(Appointment).filter(
        Appointment.clinic_id == clinic_id,
        Appointment.appointment_date.between(start, end),
    ).all()

    bills = db.query(Bill).filter(
        Bill.clinic_id == clinic_id,
        Bill.bill_date.between(start, end),
    ).all()

    billed = sum(float(x.total) for x in bills if getattr(x, "status", None) != "void")
    collected = sum(float(p.amount) for b in bills for p in b.payments if getattr(b, "status", None) != "void")
    visits = sum(1 for x in appts if x.status == "completed")
    cancelled = sum(1 for x in appts if x.status in {"cancelled", "noshow", "no_show"})

    # Doctor Breakdown Aggregation
    doctors = db.query(ClinicMembership).filter(ClinicMembership.clinic_id == clinic_id,ClinicMembership.role == "doctor").all()
    doctor_map = {}
    
    for doc in doctors:
        doc_name = getattr(doc.user, 'full_name', getattr(doc.user, 'name', f"Dr. {doc.user_id[:6]}")) if getattr(doc, 'user', None) else "Doctor"
        doctor_map[str(doc.user_id)] = {
            "doctor": doc_name,
            "appointments": 0,
            "visits": 0,
            "fees_collected": 0.0
        }

    for appt in appts:
        d_id = str(getattr(appt, 'doctor_id', 'unassigned'))
        if d_id not in doctor_map:
            doctor_map[d_id] = {
                "doctor": getattr(appt, 'doctor_name', "Doctor"),
                "appointments": 0,
                "visits": 0,
                "fees_collected": 0.0
            }
        doctor_map[d_id]["appointments"] += 1
        if appt.status == "completed":
            doctor_map[d_id]["visits"] += 1

    return {
        "period": period,
        "start": start,
        "end": end,
        "new_patients": new_patients,
        "appointments_scheduled": len(appts),
        "patients_visited": visits,
        "cancellations_no_shows": cancelled,
        "fees_billed": billed,
        "fees_collected": collected,
        "fees_outstanding": max(0, billed - collected),
        "doctor_breakdown": list(doctor_map.values()),
    }

@router.get("/export")
def export_excel(
    clinic_id: str,
    type: str,
    start: date,
    end: date,
    user = Depends(current_user),
    db: Session = Depends(get_db)
):
    access(db, user, clinic_id)
    
    if type == "patients":
        data = db.query(Patient).filter(Patient.clinic_id == clinic_id, func.date(Patient.created_at).between(start, end)).all()
        df = pd.DataFrame([{"ID": p.id, "Name": p.name, "Phone": p.phone, "Created At": p.created_at} for p in data])
    elif type == "appointments" or type == "visits":
        q = db.query(Appointment).filter(Appointment.clinic_id == clinic_id, Appointment.appointment_date.between(start, end))
        if type == "visits":
            q = q.filter(Appointment.status == "completed")
        data = q.all()
        df = pd.DataFrame([{"ID": a.id, "Date": a.appointment_date, "Time": a.appointment_time, "Status": a.status} for a in data])
    elif type == "fees":
        data = db.query(Bill).filter(Bill.clinic_id == clinic_id, Bill.bill_date.between(start, end)).all()
        df = pd.DataFrame([{"Bill ID": b.id, "Date": b.bill_date, "Total": b.total, "Status": b.status} for b in data])
    else:
        df = pd.DataFrame([{"Report": "Summary", "Start": start, "End": end}])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
    output.seek(0)

    headers = {'Content-Disposition': f'attachment; filename="{type}_report.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')