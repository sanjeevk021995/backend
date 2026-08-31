from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import Request
from app.models.audit import AuditLog


def audit(
    db: Session,
    action: str,
    user_id: Optional[str] = None,
    clinic_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """
    Creates and stages an AuditLog record. Supports optional request tracking,
    system-triggered actions, and flexible metadata payloads.
    """
    ip_address = None
    user_agent = None
    request_path = None
    http_method = None

    if request:
        # Extract client IP (checking potential reverse proxy headers first)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()
        elif request.client:
            ip_address = request.client.host

        user_agent = request.headers.get("user-agent")
        request_path = request.url.path
        http_method = request.method

    # Enrich details dictionary with request metadata if provided
    metadata = details or {}
    if request_path or http_method:
        metadata["_http"] = {
            "method": http_method,
            "path": request_path,
            "user_agent": user_agent,
        }

    row = AuditLog(
        actor_user_id=user_id,
        clinic_id=clinic_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=metadata,  # Store as dict directly if using JSON/JSONB column type
        ip_address=ip_address,
    )

    db.add(row)
    return row