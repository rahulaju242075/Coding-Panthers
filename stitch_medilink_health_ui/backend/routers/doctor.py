from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
import os
import datetime
from pathlib import Path
from uuid import uuid4

from database import get_db
import models
import schemas
from routers.patient import get_current_user_from_token
from realtime_store import (
    ensure_patient_state,
    get_clinical_state,
    get_permissions,
    create_access_request,
    add_timeline_entry,
    add_diagnosis,
    add_prescription,
    add_report,
    update_vitals,
)

router = APIRouter(prefix="/api/doctor", tags=["doctor"])


@router.get("/me")
def doctor_me(
    current_user: models.User = Depends(get_current_user_from_token),
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Not authorized as doctor")

    profile = current_user.doctor_profile
    return {
        "email": current_user.email,
        "full_name": profile.full_name if profile else "Doctor",
        "specialty": profile.specialty if profile and profile.specialty else "General Practitioner",
        "degree": profile.degree if profile else "",
        "experience_years": profile.experience_years if profile else 0,
    }

@router.get("/patient/{blockchain_id}", response_model=schemas.PatientDashboardResponse)
def lookup_patient(
    blockchain_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Not authorized as doctor")
        
    patient_profile = db.query(models.PatientProfile).filter(models.PatientProfile.blockchain_id == blockchain_id).first()
    if not patient_profile:
        raise HTTPException(status_code=404, detail="Patient pass not found")

    latest_report = db.query(models.ClinicalReport)\
        .filter(models.ClinicalReport.patient_id == patient_profile.user_id)\
        .order_by(models.ClinicalReport.report_date.desc())\
        .first()

    return {
        "full_name": patient_profile.full_name,
        "blockchain_id": patient_profile.blockchain_id,
        "dob": patient_profile.dob,
        "blood_type": patient_profile.blood_type or "Unknown",
        "allergies": patient_profile.allergies or "None reported",
        "organ_donor": patient_profile.organ_donor or "No",
        "emergency_contact_name": patient_profile.emergency_contact_name or "Not provided",
        "emergency_contact_phone": patient_profile.emergency_contact_phone or "Not provided",
        "profile_picture_url": patient_profile.profile_picture_url,
        "latest_blood_pressure": latest_report.blood_pressure if latest_report else "120/80",
        "latest_heart_rate": latest_report.heart_rate if latest_report else 72
    }


@router.post("/report")
def push_health_report(
    report_data: schemas.ClinicalReportCreate,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Not authorized as doctor")
    
    patient_profile = db.query(models.PatientProfile).filter(models.PatientProfile.blockchain_id == report_data.blockchain_id).first()
    if not patient_profile:
        raise HTTPException(status_code=404, detail="Patient block not found")

    new_report = models.ClinicalReport(
        patient_id=patient_profile.user_id,
        doctor_id=current_user.id,
        blood_pressure=report_data.blood_pressure,
        heart_rate=report_data.heart_rate,
        report_date=datetime.datetime.utcnow()
    )
    db.add(new_report)
    db.commit()
    
    return {"message": "Patient vitals updated successfully"}


def _get_patient_blockchain_or_404(blockchain_id: str, db: Session):
    profile = db.query(models.PatientProfile).filter(models.PatientProfile.blockchain_id == blockchain_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Patient pass not found")
    return profile


@router.get("/access-status/{blockchain_id}")
def access_status(
    blockchain_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Not authorized as doctor")
    _get_patient_blockchain_or_404(blockchain_id, db)
    ensure_patient_state(blockchain_id)
    return get_permissions(blockchain_id)


@router.post("/access-request")
def request_access(
    payload: dict,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Not authorized as doctor")

    blockchain_id = str(payload.get("blockchain_id", "")).strip()
    req_type = str(payload.get("type", "")).strip().lower()
    if not blockchain_id or req_type not in {"history", "reports"}:
        raise HTTPException(status_code=400, detail="Invalid access request payload")

    _get_patient_blockchain_or_404(blockchain_id, db)
    doctor_name = current_user.doctor_profile.full_name if current_user.doctor_profile else "Doctor"
    label = "Full Medical History access requested" if req_type == "history" else "Full Reports & Labs access requested"
    return create_access_request(blockchain_id, doctor_name, req_type, label)


@router.get("/clinical-state/{blockchain_id}")
def doctor_get_clinical_state(
    blockchain_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Not authorized as doctor")
    _get_patient_blockchain_or_404(blockchain_id, db)
    ensure_patient_state(blockchain_id)
    return get_clinical_state(blockchain_id)


@router.post("/clinical-state/{blockchain_id}/timeline")
def doctor_add_timeline(
    blockchain_id: str,
    payload: dict,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Not authorized as doctor")
    _get_patient_blockchain_or_404(blockchain_id, db)
    title = str(payload.get("title", "Clinical Note")).strip() or "Clinical Note"
    notes = str(payload.get("notes", "")).strip()
    if not notes:
        raise HTTPException(status_code=400, detail="Timeline notes are required")
    date_value = str(payload.get("date", "")).strip() or None
    return add_timeline_entry(blockchain_id, title, notes, date_value)


@router.post("/clinical-state/{blockchain_id}/diagnosis")
def doctor_add_diagnosis(
    blockchain_id: str,
    payload: dict,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Not authorized as doctor")
    _get_patient_blockchain_or_404(blockchain_id, db)
    code = str(payload.get("code", "")).strip() or "N/A"
    name = str(payload.get("name", "")).strip() or code
    status_text = str(payload.get("status", "Added by doctor")).strip() or "Added by doctor"
    state = add_diagnosis(blockchain_id, code, name, status_text)
    add_timeline_entry(
        blockchain_id,
        "Active Diagnosis",
        f"{name} ({code}) added by doctor. Status: {status_text}",
    )
    return state


@router.post("/clinical-state/{blockchain_id}/prescription")
def doctor_add_rx(
    blockchain_id: str,
    payload: dict,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Not authorized as doctor")
    _get_patient_blockchain_or_404(blockchain_id, db)
    name = str(payload.get("name", "")).strip()
    schedule = str(payload.get("schedule", "As directed")).strip() or "As directed"
    if not name:
        raise HTTPException(status_code=400, detail="Prescription name is required")
    doctor_name = current_user.doctor_profile.full_name if current_user.doctor_profile else "Doctor"
    state = add_prescription(blockchain_id, name, schedule, doctor_name)
    add_timeline_entry(blockchain_id, "Prescription Update", f"{name} prescribed ({schedule}).")
    return state


@router.post("/clinical-state/{blockchain_id}/report")
def doctor_add_lab_report(
    blockchain_id: str,
    payload: dict,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Not authorized as doctor")
    _get_patient_blockchain_or_404(blockchain_id, db)
    file_name = str(payload.get("file", "")).strip()
    if not file_name:
        raise HTTPException(status_code=400, detail="Report filename is required")
    size_text = str(payload.get("size", "1.9 MB")).strip() or "1.9 MB"
    when_text = str(payload.get("when", "Uploaded Now")).strip() or "Uploaded Now"
    return add_report(blockchain_id, file_name, size_text, when_text)


@router.post("/clinical-state/{blockchain_id}/report-upload")
async def doctor_upload_lab_report(
    blockchain_id: str,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Not authorized as doctor")
    _get_patient_blockchain_or_404(blockchain_id, db)

    original_name = (file.filename or "").strip()
    if not original_name:
        raise HTTPException(status_code=400, detail="Report filename is required")

    file_ext = Path(original_name).suffix.lower()
    allowed = {".pdf", ".dcm", ".dicom", ".jpg", ".jpeg", ".png"}
    if file_ext not in allowed:
        raise HTTPException(status_code=400, detail="Only PDF, DICOM, JPG, JPEG, PNG are allowed")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 25MB limit")

    reports_dir = Path("uploads") / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{blockchain_id}_{uuid4().hex}{file_ext}"
    disk_path = reports_dir / safe_name
    with open(disk_path, "wb") as f:
        f.write(content)

    mb = len(content) / (1024 * 1024)
    size_text = f"{mb:.1f} MB"
    when_text = "Uploaded Now"
    file_url = f"/api/files/reports/{safe_name}"
    state = add_report(blockchain_id, original_name, size_text, when_text, file_url)
    return {"message": "Report uploaded successfully", "report_url": file_url, "state": state}


@router.post("/clinical-state/{blockchain_id}/vitals")
def doctor_update_vitals(
    blockchain_id: str,
    payload: dict,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Not authorized as doctor")
    _get_patient_blockchain_or_404(blockchain_id, db)

    bp = str(payload.get("bp", "")).strip() or "120/80"
    hr_raw = str(payload.get("hr", "")).strip() or "72"
    rhythm = str(payload.get("rhythm", "")).strip()

    try:
        hr_int = int(hr_raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Heart rate must be a number")

    if hr_int < 30 or hr_int > 240:
        raise HTTPException(status_code=400, detail="Heart rate must be between 30 and 240")

    if not rhythm:
        if hr_int < 60:
            rhythm = "Bradycardia Trend"
        elif hr_int > 100:
            rhythm = "Tachycardia Trend"
        else:
            rhythm = "Normal Sinus Rhythm"

    state = update_vitals(blockchain_id, bp, str(hr_int), rhythm)
    return state
