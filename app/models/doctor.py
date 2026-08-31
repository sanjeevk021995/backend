from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, IDMixin, TimestampMixin

class DoctorProfile(Base, IDMixin, TimestampMixin):
    __tablename__ = "doctor_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(150))
    degrees: Mapped[str | None] = mapped_column(String(300))
    license_number: Mapped[str | None] = mapped_column(String(100))
    registration_body: Mapped[str | None] = mapped_column(String(200))
    bio: Mapped[str | None] = mapped_column(Text)

    user = relationship("User", back_populates="doctor_profile")
