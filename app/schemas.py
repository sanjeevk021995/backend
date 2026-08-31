from datetime import date, time, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator, field_validator
from typing import Optional, List, Dict , Any

class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


# class MemberStaffResponse(BaseModel):
#     membership_id: str
#     user_id: str
#     full_name: str
#     email: Optional[str] = None
#     phone: Optional[str] = None
#     role: str
#     specialty: Optional[str] = None

#     class Config:
#         from_attributes = True


class MemberStaffResponse(BaseModel):
    membership_id: str
    user_id: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    is_active: bool
    specialty: Optional[str] = None

    class Config:
        from_attributes = True


class DepartmentResponse(DepartmentBase):
    id: str
    clinic_id: str
    is_active: bool
    created_at: datetime
    member_count: Optional[int] = 0

    class Config:
        from_attributes = True


class AssignStaffDepartmentRequest(BaseModel):
    user_id: str
    department_id: Optional[str] = None  # Pass None / null to unassign from department

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, description="Password must be at least 8 characters long")


class ScheduleOverrideIn(BaseModel):
    override_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_off: bool = False
    notes: Optional[str] = None

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_time(cls, v):
        if isinstance(v, str) and v.strip():
            # Parses HH:MM or HH:MM:SS strings into python time objects
            parts = [int(p) for p in v.split(":")]
            return time(*parts)
        return v


class PrescriptionCreate(BaseModel):
    patient_id: str
    rx_date: Optional[date] = None
    vitals: Optional[Dict[str, Any]] = None
    chief_complaints: Optional[str] = None
    diagnosis: Optional[str] = None
    medicines: Optional[List[Dict[str, Any]]] = None
    advice: Optional[str] = None
    follow_up_date: Optional[date] = None

    @field_validator('follow_up_date', 'rx_date', mode='before')
    def parse_empty_dates(cls, v):
        if v == "" or v is None:
            return None
        return v

class PrescriptionResponse(BaseModel):
    id: str
    clinic_id: str
    patient_id: str
    doctor_id: Optional[str] = None
    rx_date: date
    vitals: Optional[Dict[str, Any]] = None
    chief_complaints: Optional[str] = None
    diagnosis: Optional[str] = None
    medicines: Optional[List[Dict[str, Any]]] = None
    advice: Optional[str] = None
    follow_up_date: Optional[date] = None

    class Config:
        from_attributes = True


class PrescriptionUpdate(BaseModel):
    rx_date: Optional[date] = None
    vitals: Optional[Dict[str, Any]] = None
    chief_complaints: Optional[str] = None
    diagnosis: Optional[str] = None
    medicines: Optional[List[Dict[str, Any]]] = None
    advice: Optional[str] = None
    follow_up_date: Optional[date] = None

    @field_validator('follow_up_date', 'rx_date', mode='before')
    def parse_empty_dates(cls, v):
        if v == "" or v is None:
            return None
        return v

    

class SetupRegister(BaseModel):
    clinic_name: str = Field(min_length=2, max_length=200)
    short_name: Optional[str] = Field(default=None, max_length=50)
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    admin_name: str = Field(min_length=2, max_length=150)
    admin_email: EmailStr
    admin_phone: Optional[str] = None
    password: str = Field(min_length=8, max_length=128)
    currency: str = "₹"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class UserOut(ORM):
    id: str
    full_name: str
    email: Optional[EmailStr]
    phone: Optional[str]
    is_active: bool

class ClinicOut(ORM):
    id: str
    name: str
    short_name: Optional[str]
    phone: Optional[str]
    email: Optional[EmailStr]
    address: Optional[str]
    currency: str
    is_active: bool

class ClinicCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    short_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    currency: str = "₹"

class ClinicUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None

class MemberCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(min_length=8, max_length=128)
    role: str
    specialty: Optional[str] = None
    degrees: Optional[str] = None
    license_number: Optional[str] = None
    department_id: Optional[str] = None

class MemberUpdate(BaseModel):
    full_name: Optional[str] = None
    department_id: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    specialty: Optional[str] = None
    degrees: Optional[str] = None
    license_number: Optional[str] = None

class Assignment(BaseModel):
    clinic_id: str
    role: str
    department_id: Optional[str] = None

class ScheduleCreate(BaseModel):
    date: date
    start_time: time
    end_time: time
    slot_minutes: int = 15
    notes: Optional[str] = None

class ScheduleIn(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    slot_minutes: int = Field(default=15, ge=5, le=240)
    notes: Optional[str] = None

class LeaveIn(BaseModel):
    clinic_id: str
    from_date: date
    to_date: date
    leave_type: str = "leave"
    reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.to_date < self.from_date:
            raise ValueError("to_date must be on or after from_date")
        return self

class PatientCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    medical_notes: Optional[str] = None

class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    medical_notes: Optional[str] = None
    last_visit: Optional[date] = None
    is_active: Optional[bool] = None

class PatientOut(PatientCreate, ORM):
    id: str
    clinic_id: str
    last_visit: Optional[date]
    is_active: bool
    created_at: datetime

class PatientResponse(BaseModel):
    id: str
    patient_number: Optional[str] = None
    clinic_id: str
    full_name: str
    phone: str | None = None
    email: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    address: str | None = None
    medical_notes: str | None = None
    last_visit: date | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AppointmentCreate(ORM):
    clinic_id: str
    patient_id: str
    doctor_id: str
    appointment_date: date
    appointment_time: time
    visit_type: str = "new"
    reason: Optional[str] = None
    notes: Optional[str] = None
    status: str = "scheduled"
    department_id: Optional[str] = None


class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    doctor_id: Optional[str] = None
    clinic_id: Optional[str] = None
    visit_type: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    department_id: Optional[str] = None


class AppointmentOut(AppointmentCreate):
    id: str
    auto_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AppointmentResponse(AppointmentOut):
    pass


class BillItemIn(BaseModel):
    description: str
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(ge=0)

class BillCreate(BaseModel):
    clinic_id: str
    patient_id: str
    doctor_id: Optional[str] = None
    bill_date: date = Field(default_factory=date.today)
    items: List[BillItemIn] = Field(min_length=1)
    discount: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)
    status: Optional[str] = "due"  # Allows UI to set 'due'/'unpaid' or 'paid' upon creation
    payment_mode: Optional[str] = None  # Saves selected payment mode when creating as 'paid'
    notes: Optional[str] = None

class PatientOut(BaseModel):
    id: str
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True

class BillItemOut(BillItemIn):
    id: str
    amount: float

    class Config:
        from_attributes = True

class BillItemSchema(BaseModel):
    description: str
    quantity: int
    unit_price: float

class BillUpdate(BaseModel):
    clinic_id: str
    patient_id: str
    doctor_id: Optional[str] = None
    bill_date: date
    discount: float = 0.0
    tax: float = 0.0
    status: Optional[str] = "due"
    notes: Optional[str] = None
    items: List[BillItemSchema]

class PaymentOut(BaseModel):
    id: str
    amount: float
    payment_mode: str
    paid_at: datetime

    class Config:
        from_attributes = True

class DoctorOut(BaseModel):
    id: str
    full_name: str
    email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class BillOut(BaseModel):
    id: str
    clinic_id: str
    patient_id: str
    doctor_id: Optional[str] = None
    invoice_number: str
    bill_date: date
    subtotal: float
    discount: float
    tax: float
    total: float
    status: str
    notes: Optional[str] = None
    items: List[BillItemOut]
    payments: List[PaymentOut] = []
    patient: Optional[PatientOut] = None
    doctor: Optional[DoctorOut] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    payment_mode: str
    reference: Optional[str] = None
    notes: Optional[str] = None

class ReminderCreate(BaseModel):
    clinic_id: str
    patient_id: str
    appointment_id: Optional[str] = None
    reminder_type: str
    channel: str
    message: str = Field(min_length=1)

class ReminderOut(ReminderCreate, ORM):
    id: str
    status: str
    sent_at: Optional[datetime]
    provider_message_id: Optional[str]
    error_message: Optional[str]

class AuditOut(ORM):
    id: str
    clinic_id: Optional[str]
    actor_user_id: Optional[str]
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    details: Optional[str]
    created_at: datetime

class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    subject: str
    message: str

class ContactResponse(BaseModel):
    id: int
    name: str
    email: str
    subject: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
