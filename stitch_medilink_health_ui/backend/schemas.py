from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date
from models import UserRole

# Shared
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

# Patient
class PatientRegister(UserCreate):
    full_name: str
    dob: date
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    organ_donor: Optional[str] = "No"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

# Doctor
class DoctorRegister(UserCreate):
    full_name: str
    degree: str
    experience_years: int
    specialty: Optional[str] = None

# Pharmacy
class PharmacyRegister(UserCreate):
    store_name: str
    drug_license_number: str

# Login
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Token Return
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: UserRole

# Vitals & Reports
class ClinicalReportCreate(BaseModel):
    blockchain_id: str
    blood_pressure: Optional[str] = None
    heart_rate: Optional[int] = None

class PatientDashboardResponse(BaseModel):
    full_name: str
    blockchain_id: str
    dob: date
    blood_type: str
    allergies: str
    organ_donor: str
    emergency_contact_name: str
    emergency_contact_phone: str
    profile_picture_url: Optional[str] = None
    latest_blood_pressure: Optional[str] = None
    latest_heart_rate: Optional[int] = None
