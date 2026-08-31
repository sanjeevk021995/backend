from datetime import datetime, timezone
from typing import Tuple
from sqlalchemy.orm import Session
from app.models.reminder import Reminder
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.appointment import Appointment


def build_message_content(
    channel: str,
    patient_name: str,
    clinic_name: str,
    app_date: str = "N/A",
    app_time: str = "N/A",
    reason: str | None = None,
) -> str:
    """Generates pure text content stored in the reminder's message column."""
    reason_str = f" for {reason}" if reason else ""

    if channel == "whatsapp":
        return (
            f"Hello {patient_name}, this is a reminder from {clinic_name} "
            f"for your appointment{reason_str} on {app_date} at {app_time}."
        )
    elif channel == "email":
        return (
            f"Subject: Appointment Reminder - {clinic_name}\n\n"
            f"Dear {patient_name},\n\n"
            f"You have an upcoming appointment at {clinic_name}{reason_str}.\n"
            f"Date: {app_date}\n"
            f"Time: {app_time}\n"
        )
    return f"Reminder for {patient_name} at {clinic_name} on {app_date} at {app_time}."


def dispatch_provider_message(channel: str, recipient: str, message: str) -> Tuple[bool, str | None, str | None]:
    """
    Mock dispatch integration for external message delivery services.
    Returns: (success_boolean, provider_message_id, error_message)
    """
    try:
        if channel == "whatsapp":
            # Replace with Meta API / Twilio call
            print(f"[WhatsApp API] Sending to {recipient}: {message}")
            return True, "wa_msg_123456789", None

        elif channel == "email":
            # Replace with SendGrid / AWS SES call
            print(f"[Email API] Sending to {recipient}: {message}")
            return True, "email_msg_987654321", None

        return False, None, f"Unsupported channel: {channel}"

    except Exception as err:
        return False, None, str(err)


def send_reminder(db: Session, reminder: Reminder, recipient: str) -> Reminder:
    """Backend orchestrator to prepare message content, dispatch, and track model status."""
    patient = db.get(Patient, reminder.patient_id)
    clinic = db.get(Clinic, reminder.clinic_id)
    appointment = db.get(Appointment, reminder.appointment_id) if reminder.appointment_id else None

    patient_name = patient.full_name if patient else "Patient"
    clinic_name = clinic.name if clinic else "Clinic"
    app_date = str(appointment.appointment_date) if appointment else "N/A"
    app_time = str(appointment.appointment_time) if appointment else "N/A"
    reason = getattr(appointment, "reason", None) if appointment else None

    # Populate message text if empty
    if not reminder.message:
        reminder.message = build_message_content(
            channel=reminder.channel,
            patient_name=patient_name,
            clinic_name=clinic_name,
            app_date=app_date,
            app_time=app_time,
            reason=reason,
        )

    # Attempt dispatch
    success, provider_id, error_detail = dispatch_provider_message(
        channel=reminder.channel,
        recipient=recipient,
        message=reminder.message,
    )

    if success:
        reminder.status = "sent"
        reminder.sent_at = datetime.now(timezone.utc)
        reminder.provider_message_id = provider_id
        reminder.error_message = None
    else:
        reminder.status = "failed"
        reminder.error_message = error_detail

    db.add(reminder)
    return reminder