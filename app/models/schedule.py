from datetime import date, time
from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Time, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, IDMixin, TimestampMixin


class DoctorSchedule(Base, IDMixin, TimestampMixin):
    __tablename__ = "doctor_schedules"
    __table_args__ = (UniqueConstraint("clinic_id", "doctor_id", "day_of_week", name="uq_doctor_schedule_day"),)

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 Sunday ... 6 Saturday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_minutes: Mapped[int] = mapped_column(Integer, default=15)
    notes: Mapped[str | None] = mapped_column(Text)


class DoctorScheduleOverride(Base, IDMixin, TimestampMixin):
    __tablename__ = "doctor_schedule_overrides"
    __table_args__ = (UniqueConstraint("clinic_id", "doctor_id", "override_date", name="uq_doctor_schedule_override_date"),)

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    override_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_off: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)


class DoctorLeave(Base, IDMixin, TimestampMixin):
    __tablename__ = "doctor_leaves"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    leave_type: Mapped[str] = mapped_column(String(50), default="leave")
    reason: Mapped[str | None] = mapped_column(Text)