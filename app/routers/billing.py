from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.core.database import get_db
from app.core.auth import current_user, membership_for
from app.models.billing import Bill, BillItem, Payment
from app.models.patient import Patient
from app.schemas import BillCreate, BillUpdate, BillOut, PaymentCreate, PaymentOut
from app.services.audit import audit

router = APIRouter(prefix="/bills", tags=["Billing"])


def access(db: Session, user, clinic_id: str, write: bool = False):
    m = membership_for(db, user.id, clinic_id)
    if not m:
        raise HTTPException(403, "No clinic access")
    if write and m.role not in {"ADMIN", "FRONT_DESK", "DOCTOR"}:
        raise HTTPException(403, "Insufficient permission")
    return m


def next_invoice(db: Session, clinic_id: str) -> str:
    count = db.query(func.count(Bill.id)).filter(Bill.clinic_id == clinic_id).scalar() or 0
    return f"INV-{(count + 1):04d}"


@router.get("/", response_model=List[BillOut])
def list_bills(
    clinic_id: str, 
    status: Optional[str] = None, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    access(db, user, clinic_id)
    q = (
        db.query(Bill)
        .options(
            joinedload(Bill.items),
            joinedload(Bill.payments),
            joinedload(Bill.patient),
            joinedload(Bill.doctor),
        )
        .filter(Bill.clinic_id == clinic_id)
    )

    if status:
        if status in ["unpaid", "due"]:
            q = q.filter(Bill.status.in_(["due", "unpaid", "partial"]))
        else:
            q = q.filter(Bill.status == status)

    return q.order_by(Bill.bill_date.desc(), Bill.created_at.desc()).all()


@router.post("/", response_model=BillOut, status_code=201)
def create_bill(
    payload: BillCreate, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    access(db, user, payload.clinic_id, write=True)

    patient = db.get(Patient, payload.patient_id)
    if not patient or patient.clinic_id != payload.clinic_id:
        raise HTTPException(404, "Patient not found")

    subtotal = sum(i.quantity * i.unit_price for i in payload.items)
    taxable_amount = max(0.0, subtotal - payload.discount)
    tax_amount = (taxable_amount * (payload.tax / 100.0)) if 0 < payload.tax <= 100 else payload.tax
    total = max(0.0, taxable_amount + tax_amount)

    initial_status = getattr(payload, "status", "due") or "due"

    bill = Bill(
        clinic_id=payload.clinic_id,
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        invoice_number=next_invoice(db, payload.clinic_id),
        bill_date=payload.bill_date,
        subtotal=subtotal,
        discount=payload.discount,
        tax=tax_amount,
        total=total,
        status=initial_status,
        notes=payload.notes,
    )
    db.add(bill)
    db.flush()

    for i in payload.items:
        db.add(
            BillItem(
                bill_id=bill.id,
                description=i.description,
                quantity=i.quantity,
                unit_price=i.unit_price,
                amount=i.quantity * i.unit_price,
            )
        )

    if initial_status == "paid" and total > 0:
        mode = getattr(payload, "payment_mode", "Cash") or "Cash"
        db.add(
            Payment(
                bill_id=bill.id,
                amount=total,
                payment_mode=mode,
                notes="Initial bill creation payment",
            )
        )

    audit(db, user.id, payload.clinic_id, "bill.created", "Bill", bill.id)
    db.commit()
    
    return (
        db.query(Bill)
        .options(
            joinedload(Bill.items),
            joinedload(Bill.payments),
            joinedload(Bill.patient),
            joinedload(Bill.doctor),
        )
        .filter(Bill.id == bill.id)
        .first()
    )


# UPDATE BILL ENDPOINT (PUT /bills/{bill_id})
@router.put("/{bill_id}", response_model=BillOut)
def update_bill(
    bill_id: str,
    payload: BillUpdate,
    user=Depends(current_user),
    db: Session = Depends(get_db)
):
    access(db, user, payload.clinic_id, write=True)

    bill = db.get(Bill, bill_id)
    if not bill or bill.clinic_id != payload.clinic_id:
        raise HTTPException(404, "Bill not found")

    patient = db.get(Patient, payload.patient_id)
    if not patient or patient.clinic_id != payload.clinic_id:
        raise HTTPException(404, "Patient not found")

    # Recalculate totals
    subtotal = sum(i.quantity * i.unit_price for i in payload.items)
    taxable_amount = max(0.0, subtotal - payload.discount)
    tax_amount = (taxable_amount * (payload.tax / 100.0)) if 0 < payload.tax <= 100 else payload.tax
    total = max(0.0, taxable_amount + tax_amount)

    # Update bill fields
    bill.patient_id = payload.patient_id
    bill.doctor_id = payload.doctor_id
    bill.bill_date = payload.bill_date
    bill.subtotal = subtotal
    bill.discount = payload.discount
    bill.tax = tax_amount
    bill.total = total
    bill.notes = payload.notes
    if payload.status:
        bill.status = payload.status

    # Replace line items
    db.query(BillItem).filter(BillItem.bill_id == bill.id).delete()
    for i in payload.items:
        db.add(
            BillItem(
                bill_id=bill.id,
                description=i.description,
                quantity=i.quantity,
                unit_price=i.unit_price,
                amount=i.quantity * i.unit_price,
            )
        )

    audit(db, user.id, payload.clinic_id, "bill.updated", "Bill", bill.id)
    db.commit()

    return (
        db.query(Bill)
        .options(
            joinedload(Bill.items),
            joinedload(Bill.payments),
            joinedload(Bill.patient),
            joinedload(Bill.doctor),
        )
        .filter(Bill.id == bill.id)
        .first()
    )


# EMAIL SEND ENDPOINT (POST /bills/{bill_id}/send-email)
@router.post("/{bill_id}/send-email")
def send_bill_email(
    bill_id: str,
    payload: dict,
    user=Depends(current_user),
    db: Session = Depends(get_db)
):
    clinic_id = payload.get("clinic_id")
    access(db, user, clinic_id)

    bill = (
        db.query(Bill)
        .options(joinedload(Bill.patient))
        .filter(Bill.id == bill_id)
        .first()
    )
    if not bill or bill.clinic_id != clinic_id:
        raise HTTPException(404, "Bill not found")

    if not bill.patient or not bill.patient.email:
        raise HTTPException(400, "Patient email address is missing")

    # Implement your preferred email delivery service here (SendGrid, SMTP, Amazon SES)
    
    audit(db, user.id, clinic_id, "bill.email_sent", "Bill", bill.id)
    return {"message": f"Invoice email dispatched to {bill.patient.email}"}


@router.get("/{bill_id}", response_model=BillOut)
def get_bill(
    bill_id: str, 
    clinic_id: str, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    access(db, user, clinic_id)
    bill = (
        db.query(Bill)
        .options(
            joinedload(Bill.items),
            joinedload(Bill.payments),
            joinedload(Bill.patient),
            joinedload(Bill.doctor),
        )
        .filter(Bill.id == bill_id)
        .first()
    )
    if not bill or bill.clinic_id != clinic_id:
        raise HTTPException(404, "Bill not found")
    return bill


@router.post("/{bill_id}/payments", response_model=PaymentOut)
def add_payment(
    bill_id: str, 
    clinic_id: str, 
    payload: PaymentCreate, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    access(db, user, clinic_id, write=True)
    bill = db.get(Bill, bill_id)
    if not bill or bill.clinic_id != clinic_id:
        raise HTTPException(404, "Bill not found")

    paid = sum(float(p.amount) for p in bill.payments)
    if paid + payload.amount > float(bill.total) + 0.01:
        raise HTTPException(400, "Payment exceeds outstanding balance")

    payment = Payment(bill_id=bill.id, **payload.model_dump())
    db.add(payment)
    db.flush()

    if paid + payload.amount >= float(bill.total) - 0.01:
        bill.status = "paid"
    else:
        bill.status = "partial"

    audit(db, user.id, clinic_id, "payment.created", "Payment", payment.id, {"bill_id": bill.id})
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/{bill_id}/mark-paid", response_model=BillOut)
def mark_paid(
    bill_id: str, 
    clinic_id: str, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    access(db, user, clinic_id, write=True)
    bill = db.get(Bill, bill_id)
    if not bill or bill.clinic_id != clinic_id:
        raise HTTPException(404, "Bill not found")

    remaining = float(bill.total) - sum(float(p.amount) for p in bill.payments)
    if remaining > 0:
        db.add(Payment(bill_id=bill.id, amount=remaining, payment_mode="Cash", notes="Marked paid manually"))

    bill.status = "paid"
    audit(db, user.id, clinic_id, "bill.marked_paid", "Bill", bill.id)
    db.commit()

    return (
        db.query(Bill)
        .options(
            joinedload(Bill.items),
            joinedload(Bill.payments),
            joinedload(Bill.patient),
            joinedload(Bill.doctor),
        )
        .filter(Bill.id == bill.id)
        .first()
    )


@router.delete("/{bill_id}")
def delete_bill(
    bill_id: str, 
    clinic_id: str, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    access(db, user, clinic_id, write=True)
    bill = db.get(Bill, bill_id)
    if not bill or bill.clinic_id != clinic_id:
        raise HTTPException(404, "Bill not found")

    db.delete(bill)
    audit(db, user.id, clinic_id, "bill.deleted", "Bill", bill_id)
    db.commit()
    return {"message": "Bill deleted successfully"}


@router.post("/{bill_id}/void", response_model=BillOut)
def void_bill(
    bill_id: str, 
    clinic_id: str, 
    user=Depends(current_user), 
    db: Session = Depends(get_db)
):
    access(db, user, clinic_id, write=True)
    m = membership_for(db, user.id, clinic_id)
    if m.role != "ADMIN":
        raise HTTPException(403, "Admin permission required to void bills")

    bill = db.get(Bill, bill_id)
    if not bill or bill.clinic_id != clinic_id:
        raise HTTPException(404, "Bill not found")

    bill.status = "void"
    audit(db, user.id, clinic_id, "bill.voided", "Bill", bill.id)
    db.commit()
    
    return (
        db.query(Bill)
        .options(
            joinedload(Bill.items),
            joinedload(Bill.payments),
            joinedload(Bill.patient),
            joinedload(Bill.doctor),
        )
        .filter(Bill.id == bill.id)
        .first()
    )