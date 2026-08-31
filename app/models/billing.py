

# from datetime import date, datetime
# from typing import Optional, List
# from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
# from sqlalchemy.orm import Mapped, mapped_column, relationship
# from .base import Base, IDMixin, TimestampMixin

# class Bill(Base, IDMixin, TimestampMixin):
#     __tablename__ = "bills"

#     clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
#     patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False)
#     doctor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
#     invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
#     bill_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
#     subtotal: Mapped[float] = mapped_column(Numeric(12,2), default=0, nullable=False)
#     discount: Mapped[float] = mapped_column(Numeric(12,2), default=0, nullable=False)
#     tax: Mapped[float] = mapped_column(Numeric(12,2), default=0, nullable=False)
#     total: Mapped[float] = mapped_column(Numeric(12,2), default=0, nullable=False)
#     status: Mapped[str] = mapped_column(String(30), default="due")  # "due", "paid", "void", "partial"
#     notes: Mapped[str | None] = mapped_column(Text)

#     # Relationships
#     patient = relationship("Patient", lazy="joined")
#     doctor = relationship("User", lazy="joined")
#     items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan", lazy="joined")
#     payments = relationship("Payment", back_populates="bill", cascade="all, delete-orphan", lazy="joined")


# class BillItem(Base, IDMixin):
#     __tablename__ = "bill_items"

#     bill_id: Mapped[str] = mapped_column(ForeignKey("bills.id", ondelete="CASCADE"), nullable=False)
#     description: Mapped[str] = mapped_column(String(300), nullable=False)
#     quantity: Mapped[int] = mapped_column(Integer, default=1)
#     unit_price: Mapped[float] = mapped_column(Numeric(12,2), nullable=False)
#     amount: Mapped[float] = mapped_column(Numeric(12,2), nullable=False)

#     bill = relationship("Bill", back_populates="items")


# class Payment(Base, IDMixin):
#     __tablename__ = "payments"

#     bill_id: Mapped[str] = mapped_column(ForeignKey("bills.id", ondelete="CASCADE"), nullable=False)
#     amount: Mapped[float] = mapped_column(Numeric(12,2), nullable=False)
#     payment_mode: Mapped[str] = mapped_column(String(30), nullable=False)  # "Cash", "Card", "UPI"
#     paid_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
#     reference: Mapped[str | None] = mapped_column(String(200))
#     notes: Mapped[str | None] = mapped_column(Text)

#     bill = relationship("Bill", back_populates="payments")


from datetime import date, datetime
from typing import TYPE_CHECKING
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from .patient import Patient


class Bill(Base, IDMixin, TimestampMixin):
    __tablename__ = "bills"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False)
    doctor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    bill_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    discount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    tax: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="due")  # "due", "paid", "void", "partial"
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="bills")
    doctor = relationship("User", lazy="joined")
    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan", lazy="joined")
    payments = relationship("Payment", back_populates="bill", cascade="all, delete-orphan", lazy="joined")


class BillItem(Base, IDMixin):
    __tablename__ = "bill_items"

    bill_id: Mapped[str] = mapped_column(ForeignKey("bills.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    bill = relationship("Bill", back_populates="items")


class Payment(Base, IDMixin):
    __tablename__ = "payments"

    bill_id: Mapped[str] = mapped_column(ForeignKey("bills.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(30), nullable=False)  # "Cash", "Card", "UPI"
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)

    bill = relationship("Bill", back_populates="payments")