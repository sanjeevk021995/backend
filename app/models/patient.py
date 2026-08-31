# from datetime import date
# from sqlalchemy import Date, ForeignKey, String, Text
# from sqlalchemy.orm import Mapped, mapped_column
# from .base import Base, IDMixin, TimestampMixin

# class Patient(Base, IDMixin, TimestampMixin):
#     __tablename__ = "patients"

#     clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
#     patient_number: Mapped[str | None] = mapped_column(String(50), index=True) # Unique ID like PAT-1001
#     full_name: Mapped[str] = mapped_column(String(200), nullable=False)
#     phone: Mapped[str | None] = mapped_column(String(30))
#     email: Mapped[str | None] = mapped_column(String(255))
#     date_of_birth: Mapped[date | None] = mapped_column(Date)
#     gender: Mapped[str | None] = mapped_column(String(30))
#     address: Mapped[str | None] = mapped_column(Text)
#     medical_notes: Mapped[str | None] = mapped_column(Text)
#     last_visit: Mapped[date | None] = mapped_column(Date)
#     is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

from datetime import date
from typing import List, TYPE_CHECKING
from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from prescription import Prescription
    from billing import Bill


class Patient(Base, IDMixin, TimestampMixin):
    __tablename__ = "patients"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    patient_number: Mapped[str | None] = mapped_column(String(50), index=True, unique=True)  # e.g., CLINIC-00001
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(Text)
    medical_notes: Mapped[str | None] = mapped_column(Text)
    last_visit: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    prescriptions: Mapped[List["Prescription"]] = relationship(
        "Prescription",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(Prescription.rx_date)",
    )
    bills: Mapped[List["Bill"]] = relationship(
        "Bill",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(Bill.bill_date)",
    )