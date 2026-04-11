from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
import os
import datetime

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
