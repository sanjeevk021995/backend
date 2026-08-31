# from datetime import date
# from sqlalchemy import Date, ForeignKey, JSON, String, Text
# from sqlalchemy.orm import Mapped, mapped_column, relationship
# from .base import Base, IDMixin, TimestampMixin

# class Prescription(Base, IDMixin, TimestampMixin):
#     __tablename__ = "prescriptions"

#     clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
#     patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
#     doctor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    
#     rx_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
#     vitals: Mapped[dict | None] = mapped_column(JSON)  # Stores {bp, pulse, temp, weight}
#     chief_complaints: Mapped[str | None] = mapped_column(Text)
#     diagnosis: Mapped[str | None] = mapped_column(String(255))
#     medicines: Mapped[list | None] = mapped_column(JSON)  # Stores array of medicine dicts
#     advice: Mapped[str | None] = mapped_column(Text)
#     follow_up_date: Mapped[date | None] = mapped_column(Date)

from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import Date, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from patient import Patient


class Prescription(Base, IDMixin, TimestampMixin):
    __tablename__ = "prescriptions"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    rx_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    vitals: Mapped[dict | None] = mapped_column(JSON)  # Stores {bp, pulse, temp, weight}
    chief_complaints: Mapped[str | None] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(String(255))
    medicines: Mapped[list | None] = mapped_column(JSON)  # Stores array of medicine objects
    advice: Mapped[str | None] = mapped_column(Text)
    follow_up_date: Mapped[date | None] = mapped_column(Date)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="prescriptions")
    doctor = relationship("User", lazy="joined")