from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import current_user, membership_for
from app.models.audit import AuditLog

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/")
def list_audit_logs(
    clinic_id: str = Query(...),
    action: Optional[str] = Query(None, description="Filter by action type (e.g. member.created)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g. User, Appointment)"),
    entity_id: Optional[str] = Query(None, description="Filter by specific entity ID"),
    actor_user_id: Optional[str] = Query(None, description="Filter by the user who performed the action"),
    limit: int = Query(50, ge=1, le=500, description="Number of logs to return (max 500)"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    # Verify clinic membership and admin permissions
    m = membership_for(db, user.id, clinic_id)
    if not m or str(m.role).upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin permission required")

    # Base query filtered by clinic
    query = db.query(AuditLog).filter(AuditLog.clinic_id == clinic_id)

    # Apply optional search filters
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if actor_user_id:
        query = query.filter(AuditLog.actor_user_id == actor_user_id)

    # Fetch total count before pagination
    total = query.count()

    # Execute paginated query ordered by newest first
    items = (
        query.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }