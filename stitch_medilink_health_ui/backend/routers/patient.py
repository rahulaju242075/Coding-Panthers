from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
import os
import shutil

from database import get_db
import models

router = APIRouter(prefix="/api/patient", tags=["patient"])
security = HTTPBearer()

SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-key-for-hackathon-only")
ALGORITHM = "HS256"

def get_current_user_from_token(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@router.get("/dashboard")
def get_patient_dashboard(current_user: models.User = Depends(get_current_user_from_token)):
    if current_user.role != models.UserRole.PATIENT:
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
    if current_user.role != models.UserRole.PATIENT:
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
