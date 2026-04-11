from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
import os
import shutil

from database import get_db
import models
from realtime_store import (
    ensure_patient_state,
    get_clinical_state,
    set_clinical_state,
    add_timeline_entry,
    add_prescription,
    get_notifications,
    resolve_notification,
    get_permissions,
    create_pharmacy_demand_request,
    list_patient_pharmacy_demand_requests,
    list_pharmacies,
)

router = APIRouter(prefix="/api/patient", tags=["patient"])
security = HTTPBearer()

SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-key-for-hackathon-only")
ALGORITHM = "HS256"

def get_current_user_from_token(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not isinstance(email, str) or not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@router.get("/dashboard")
def get_patient_dashboard(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    role_value = current_user.role
    normalized_role = role_value.value if isinstance(role_value, models.UserRole) else str(role_value)
    if normalized_role != models.UserRole.PATIENT.value:
        raise HTTPException(status_code=403, detail="Not authorized as patient")

    profile = current_user.patient_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    latest_report = db.query(models.ClinicalReport)\
        .filter(models.ClinicalReport.patient_id == current_user.id)\
        .order_by(models.ClinicalReport.report_date.desc())\
        .first()
        
    bp = latest_report.blood_pressure if latest_report else "120/80"
    hr = latest_report.heart_rate if latest_report else 72

    return {
        "full_name": profile.full_name,
        "blockchain_id": profile.blockchain_id,
        "dob": profile.dob,
        "blood_type": profile.blood_type or "Unknown",
        "allergies": profile.allergies or "None reported",
        "organ_donor": profile.organ_donor or "No",
        "emergency_contact_name": profile.emergency_contact_name or "Not provided",
        "emergency_contact_phone": profile.emergency_contact_phone or "Not provided",
        "profile_picture_url": profile.profile_picture_url,
        "latest_blood_pressure": bp,
        "latest_heart_rate": hr
    }

@router.post("/upload_avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    role_value = current_user.role
    normalized_role = role_value.value if isinstance(role_value, models.UserRole) else str(role_value)
    if normalized_role != models.UserRole.PATIENT.value:
        raise HTTPException(status_code=403, detail="Not authorized as patient")
        
    profile = current_user.patient_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    os.makedirs("uploads/profiles", exist_ok=True)
    file_path = f"uploads/profiles/user_{current_user.id}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Create url for static sharing
    picture_url = f"/api/files/{file_path}"
    profile.profile_picture_url = picture_url
    db.commit()
    
    return {"message": "Avatar uploaded", "url": picture_url}


@router.get("/clinical-state")
def patient_get_clinical_state(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    role_value = current_user.role
    normalized_role = role_value.value if isinstance(role_value, models.UserRole) else str(role_value)
    if normalized_role != models.UserRole.PATIENT.value:
        raise HTTPException(status_code=403, detail="Not authorized as patient")

    profile = current_user.patient_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    ensure_patient_state(profile.blockchain_id)
    return get_clinical_state(profile.blockchain_id)


@router.put("/clinical-state")
def patient_set_clinical_state(
    payload: dict,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    role_value = current_user.role
    normalized_role = role_value.value if isinstance(role_value, models.UserRole) else str(role_value)
    if normalized_role != models.UserRole.PATIENT.value:
        raise HTTPException(status_code=403, detail="Not authorized as patient")

    profile = current_user.patient_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    return set_clinical_state(profile.blockchain_id, payload)


@router.post("/clinical-state/timeline")
def patient_add_timeline(
    payload: dict,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    role_value = current_user.role
    normalized_role = role_value.value if isinstance(role_value, models.UserRole) else str(role_value)
    if normalized_role != models.UserRole.PATIENT.value:
        raise HTTPException(status_code=403, detail="Not authorized as patient")

    profile = current_user.patient_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    title = str(payload.get("title", "Consultation Update")).strip() or "Consultation Update"
    notes = str(payload.get("notes", "")).strip()
    if not notes:
        raise HTTPException(status_code=400, detail="Timeline notes are required")
    date_value = str(payload.get("date", "")).strip() or None
    return add_timeline_entry(profile.blockchain_id, title, notes, date_value)


@router.post("/clinical-state/prescription")
def patient_add_prescription(
    payload: dict,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    role_value = current_user.role
    normalized_role = role_value.value if isinstance(role_value, models.UserRole) else str(role_value)
    if normalized_role != models.UserRole.PATIENT.value:
        raise HTTPException(status_code=403, detail="Not authorized as patient")

    profile = current_user.patient_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    name = str(payload.get("name", "")).strip()
    schedule = str(payload.get("schedule", "As directed")).strip() or "As directed"
    if not name:
        raise HTTPException(status_code=400, detail="Prescription name is required")

    return add_prescription(profile.blockchain_id, name, schedule, "Patient")


@router.get("/notifications")
def patient_get_notifications(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    role_value = current_user.role
    normalized_role = role_value.value if isinstance(role_value, models.UserRole) else str(role_value)
    if normalized_role != models.UserRole.PATIENT.value:
        raise HTTPException(status_code=403, detail="Not authorized as patient")

    profile = current_user.patient_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    ensure_patient_state(profile.blockchain_id)
    return get_notifications(profile.blockchain_id)


@router.post("/notifications/{request_id}/resolve")
def patient_resolve_notification(
    request_id: str,
    payload: dict,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    role_value = current_user.role
    normalized_role = role_value.value if isinstance(role_value, models.UserRole) else str(role_value)
    if normalized_role != models.UserRole.PATIENT.value:
        raise HTTPException(status_code=403, detail="Not authorized as patient")

    profile = current_user.patient_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    decision = str(payload.get("decision", "")).strip().lower()
    if decision not in {"accept", "reject"}:
        raise HTTPException(status_code=400, detail="decision must be accept or reject")

    resolved = resolve_notification(profile.blockchain_id, request_id, decision)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Notification request not found")
    return resolved


@router.get("/permissions")
def patient_get_permissions(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    role_value = current_user.role
    normalized_role = role_value.value if isinstance(role_value, models.UserRole) else str(role_value)
    if normalized_role != models.UserRole.PATIENT.value:
        raise HTTPException(status_code=403, detail="Not authorized as patient")

    profile = current_user.patient_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    ensure_patient_state(profile.blockchain_id)
    return get_permissions(profile.blockchain_id)


@router.get("/pharmacies")
def patient_list_pharmacies(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    role_value = current_user.role
    normalized_role = role_value.value if isinstance(role_value, models.UserRole) else str(role_value)
    if normalized_role != models.UserRole.PATIENT.value:
        raise HTTPException(status_code=403, detail="Not authorized as patient")
    return list_pharmacies()


@router.get("/pharmacy-requests")
def patient_list_pharmacy_requests(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    role_value = current_user.role
    normalized_role = role_value.value if isinstance(role_value, models.UserRole) else str(role_value)
    if normalized_role != models.UserRole.PATIENT.value:
        raise HTTPException(status_code=403, detail="Not authorized as patient")

    profile = current_user.patient_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    return list_patient_pharmacy_demand_requests(profile.blockchain_id)


@router.post("/pharmacy-request")
def patient_create_pharmacy_request(
    payload: dict,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    role_value = current_user.role
    normalized_role = role_value.value if isinstance(role_value, models.UserRole) else str(role_value)
    if normalized_role != models.UserRole.PATIENT.value:
        raise HTTPException(status_code=403, detail="Not authorized as patient")

    profile = current_user.patient_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    pharmacy_user_id = int(payload.get("pharmacy_user_id", 0) or 0)
    medicine_name = str(payload.get("medicine_name", "")).strip()
    quantity = str(payload.get("quantity", "1")).strip() or "1"
    notes = str(payload.get("notes", "")).strip()
    if pharmacy_user_id <= 0 or not medicine_name:
        raise HTTPException(status_code=400, detail="Pharmacy and medicine name are required")

    pharmacy_user = db.query(models.User).filter(models.User.id == pharmacy_user_id).first()
    if not pharmacy_user or (pharmacy_user.role.value if isinstance(pharmacy_user.role, models.UserRole) else str(pharmacy_user.role)) != models.UserRole.PHARMACY.value:
        raise HTTPException(status_code=404, detail="Pharmacy account not found")
    if not pharmacy_user.pharmacy_profile:
        raise HTTPException(status_code=404, detail="Pharmacy profile not found")

    resolved_pharmacy_user_id = int(getattr(pharmacy_user, "id", 0) or 0)

    patient_name = profile.full_name
    return create_pharmacy_demand_request(
        patient_blockchain_id=profile.blockchain_id,
        patient_name=patient_name,
        pharmacy_user_id=resolved_pharmacy_user_id,
        pharmacy_store_name=pharmacy_user.pharmacy_profile.store_name,
        medicine_name=medicine_name,
        quantity=quantity,
        notes=notes,
    )
