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
