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

router = APIRouter(prefix="/api/doctor", tags=["doctor"])

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
