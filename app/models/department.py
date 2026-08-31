from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, IDMixin, TimestampMixin


class Department(Base, IDMixin, TimestampMixin):
    __tablename__ = "departments"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)  # e.g. Cardiology, Orthopedics, Reception
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    clinic = relationship("Clinic", back_populates="departments")
    memberships = relationship("ClinicMembership", back_populates="department")