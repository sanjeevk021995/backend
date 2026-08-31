# from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Time
# from sqlalchemy.orm import Mapped, mapped_column, relationship
# from .base import Base, IDMixin, TimestampMixin

# class Clinic(Base, IDMixin, TimestampMixin):
#     __tablename__ = "clinics"

#     name: Mapped[str] = mapped_column(String(200), nullable=False)
#     short_name: Mapped[str | None] = mapped_column(String(50))
#     phone: Mapped[str | None] = mapped_column(String(30))
#     email: Mapped[str | None] = mapped_column(String(255))
#     address: Mapped[str | None] = mapped_column(Text)
#     currency: Mapped[str] = mapped_column(String(10), default="₹")
#     is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

#     settings = relationship("ClinicSettings", back_populates="clinic", uselist=False, cascade="all, delete-orphan")
#     working_hours = relationship("ClinicWorkingHours", back_populates="clinic", cascade="all, delete-orphan")


# class ClinicSettings(Base, IDMixin, TimestampMixin):
#     __tablename__ = "clinic_settings"

#     clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), unique=True, nullable=False)
#     auto_complete: Mapped[bool] = mapped_column(Boolean, default=True)
#     auto_no_show: Mapped[bool] = mapped_column(Boolean, default=True)
#     country_code: Mapped[str] = mapped_column(String(10), default="91")
#     appointment_reminder_hours: Mapped[int] = mapped_column(Integer, default=24)
#     default_tax_percent: Mapped[float] = mapped_column(default=0)

#     clinic = relationship("Clinic", back_populates="settings")


# class ClinicWorkingHours(Base, IDMixin, TimestampMixin):
#     __tablename__ = "clinic_working_hours"

#     clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
#     day_of_week: Mapped[int] = mapped_column(Integer, nullable=False) # 0 = Sunday, 1 = Monday, etc.
#     open_time: Mapped[str] = mapped_column(String(10), default="08:00")
#     close_time: Mapped[str] = mapped_column(String(10), default="20:00")
#     is_closed: Mapped[bool] = mapped_column(Boolean, default=False)

#     clinic = relationship("Clinic", back_populates="working_hours")

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, IDMixin, TimestampMixin


class Clinic(Base, IDMixin, TimestampMixin):
    __tablename__ = "clinics"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(10), default="₹")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    settings = relationship("ClinicSettings", back_populates="clinic", uselist=False, cascade="all, delete-orphan")
    working_hours = relationship("ClinicWorkingHours", back_populates="clinic", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="clinic", cascade="all, delete-orphan")


class ClinicSettings(Base, IDMixin, TimestampMixin):
    __tablename__ = "clinic_settings"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), unique=True, nullable=False)
    auto_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_no_show: Mapped[bool] = mapped_column(Boolean, default=True)
    country_code: Mapped[str] = mapped_column(String(10), default="91")
    appointment_reminder_hours: Mapped[int] = mapped_column(Integer, default=24)
    default_tax_percent: Mapped[float] = mapped_column(default=0)

    clinic = relationship("Clinic", back_populates="settings")


class ClinicWorkingHours(Base, IDMixin, TimestampMixin):
    __tablename__ = "clinic_working_hours"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    open_time: Mapped[str] = mapped_column(String(10), default="08:00")
    close_time: Mapped[str] = mapped_column(String(10), default="20:00")
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)

    clinic = relationship("Clinic", back_populates="working_hours")