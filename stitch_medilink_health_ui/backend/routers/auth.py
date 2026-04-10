from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import bcrypt
import jwt
from datetime import datetime, timedelta
import os
import pydantic
import uuid
import random

from database import get_db
import models, schemas

router = APIRouter(prefix="/api/auth", tags=["auth"])

SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-key-for-hackathon-only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/register/patient", response_model=schemas.TokenResponse)
def register_patient(patient: schemas.PatientRegister, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == patient.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create User
    new_user = models.User(
        email=patient.email,
        hashed_password=get_password_hash(patient.password),
        role=models.UserRole.PATIENT
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate a unique blockchain-style ID (e.g. ML-A1B2-C3D4)
    bid_part1 = ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=4))
    bid_part2 = ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=4))
    blockchain_id = f"ML-{bid_part1}-{bid_part2}"

    # Create Profile
    new_profile = models.PatientProfile(
        user_id=new_user.id,
        blockchain_id=blockchain_id,
        full_name=patient.full_name,
        dob=patient.dob,
        blood_type=patient.blood_type,
        allergies=patient.allergies,
        organ_donor=patient.organ_donor,
        emergency_contact_name=patient.emergency_contact_name,
        emergency_contact_phone=patient.emergency_contact_phone
    )
    db.add(new_profile)
    db.commit()
    
    # Generate Token
    access_token = create_access_token(data={"sub": new_user.email, "role": "patient"})
    return {"access_token": access_token, "token_type": "bearer", "role": new_user.role}

@router.post("/register/doctor", response_model=schemas.TokenResponse)
def register_doctor(doctor: schemas.DoctorRegister, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == doctor.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = models.User(
        email=doctor.email,
        hashed_password=get_password_hash(doctor.password),
        role=models.UserRole.DOCTOR
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    new_profile = models.DoctorProfile(
        user_id=new_user.id,
        full_name=doctor.full_name,
        degree=doctor.degree,
        experience_years=doctor.experience_years,
        specialty=doctor.specialty,
        verification_status="pending"
    )
    db.add(new_profile)
    db.commit()
    
    access_token = create_access_token(data={"sub": new_user.email, "role": "doctor"})
    return {"access_token": access_token, "token_type": "bearer", "role": new_user.role}

@router.post("/register/pharmacy", response_model=schemas.TokenResponse)
def register_pharmacy(pharmacy: schemas.PharmacyRegister, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == pharmacy.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = models.User(
        email=pharmacy.email,
        hashed_password=get_password_hash(pharmacy.password),
        role=models.UserRole.PHARMACY
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    new_profile = models.PharmacyProfile(
        user_id=new_user.id,
        store_name=pharmacy.store_name,
        drug_license_number=pharmacy.drug_license_number,
        verification_status="pending"
    )
    db.add(new_profile)
    db.commit()
    
    access_token = create_access_token(data={"sub": new_user.email, "role": "pharmacy"})
    return {"access_token": access_token, "token_type": "bearer", "role": new_user.role}

@router.post("/login", response_model=schemas.TokenResponse)
def login(login_req: schemas.LoginRequest, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == login_req.email).first()
    if not db_user or not verify_password(login_req.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token = create_access_token(
        data={"sub": db_user.email, "role": db_user.role.value},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer", "role": db_user.role}
