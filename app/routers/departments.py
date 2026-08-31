from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import current_user, membership_for
from app.models.department import Department
from app.models.membership import ClinicMembership
from app.models.user import User
from app.schemas import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    AssignStaffDepartmentRequest,
    MemberStaffResponse,
)
from app.services.audit import audit

router = APIRouter(prefix="/departments", tags=["Departments"])


def access(db, user, clinic_id):
    m = membership_for(db, user.id, clinic_id)
    if not m:
        raise HTTPException(status_code=403, detail="No clinic access")
    return m


@router.get("/", response_model=list[DepartmentResponse])
def list_departments(
    clinic_id: str = Query(...),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    access(db, user, clinic_id)

    departments = (
        db.query(Department)
        .filter(
            Department.clinic_id == clinic_id,
            Department.is_active.is_(True),
        )
        .order_by(Department.name)
        .all()
    )

    result = []
    for dept in departments:
        member_count = (
            db.query(ClinicMembership)
            .filter(
                ClinicMembership.department_id == dept.id,
                ClinicMembership.is_active.is_(True),
            )
            .count()
        )
        res = DepartmentResponse.model_validate(dept)
        res.member_count = member_count
        result.append(res)

    return result


@router.post("/", response_model=DepartmentResponse, status_code=201)
def create_department(
    payload: DepartmentCreate,
    clinic_id: str = Query(...),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    access(db, user, clinic_id)

    dept = Department(
        clinic_id=clinic_id,
        **payload.model_dump(),
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)

    audit(db, user.id, clinic_id, "department.created", "Department", dept.id)
    return dept


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: str,
    payload: DepartmentUpdate,
    clinic_id: str = Query(...),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    access(db, user, clinic_id)

    dept = db.get(Department, department_id)
    if not dept or dept.clinic_id != clinic_id:
        raise HTTPException(status_code=404, detail="Department not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, val in updates.items():
        setattr(dept, key, val)

    audit(db, user.id, clinic_id, "department.updated", "Department", dept.id)
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/{department_id}/members", response_model=list[MemberStaffResponse])
def get_department_members(
    department_id: str,
    clinic_id: str = Query(...),
    include_inactive: bool = Query(False, description="Include deactivated staff members"),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    """Lists doctors and staff assigned to a specific department."""
    access(db, user, clinic_id)

    query = db.query(ClinicMembership).filter(
        ClinicMembership.clinic_id == clinic_id,
        ClinicMembership.department_id == department_id,
    )

    # Filter out inactive staff unless explicitly requested
    if not include_inactive:
        query = query.filter(ClinicMembership.is_active.is_(True))

    memberships = query.all()

    out = []
    for m in memberships:
        u = m.user
        doc_prof = getattr(u, "doctor_profile", None)
        out.append(
            MemberStaffResponse(
                membership_id=m.id,
                user_id=u.id,
                full_name=u.full_name,
                email=u.email,
                phone=u.phone,
                role=m.role,
                is_active=m.is_active,
                specialty=doc_prof.specialty if doc_prof else None,
            )
        )
    return out


@router.post("/assign-staff")
def assign_staff_to_department(
    payload: AssignStaffDepartmentRequest,
    clinic_id: str = Query(...),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    """Assigns or reassigns a staff member/doctor to a department within the clinic."""
    access(db, user, clinic_id)

    membership = (
        db.query(ClinicMembership)
        .filter(
            ClinicMembership.user_id == payload.user_id,
            ClinicMembership.clinic_id == clinic_id,
        )
        .first()
    )

    if not membership:
        raise HTTPException(status_code=404, detail="Staff membership not found in this clinic")

    if payload.department_id:
        dept = db.get(Department, payload.department_id)
        if not dept or dept.clinic_id != clinic_id:
            raise HTTPException(status_code=404, detail="Target department not found")

    membership.department_id = payload.department_id

    audit(
        db,
        user.id,
        clinic_id,
        "staff.department_assigned",
        "ClinicMembership",
        membership.id,
    )
    db.commit()

    return {"message": "Staff department updated successfully"}