# from sqlalchemy import ForeignKey, String, UniqueConstraint
# from sqlalchemy.orm import Mapped, mapped_column, relationship
# from .base import Base, IDMixin, TimestampMixin

# class ClinicMembership(Base, IDMixin, TimestampMixin):
#     __tablename__ = "clinic_memberships"
#     __table_args__ = (UniqueConstraint("user_id", "clinic_id", name="uq_user_clinic"),)

#     user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#     clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
#     role: Mapped[str] = mapped_column(String(30), nullable=False)  # ADMIN, DOCTOR, FRONT_DESK
#     is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

#     user = relationship("User", back_populates="memberships")
#     clinic = relationship("Clinic")

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, IDMixin, TimestampMixin


class ClinicMembership(Base, IDMixin, TimestampMixin):
    __tablename__ = "clinic_memberships"
    __table_args__ = (UniqueConstraint("user_id", "clinic_id", name="uq_user_clinic"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False)  # ADMIN, DOCTOR, FRONT_DESK
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="memberships")
    clinic = relationship("Clinic")
    department = relationship("Department", back_populates="memberships")