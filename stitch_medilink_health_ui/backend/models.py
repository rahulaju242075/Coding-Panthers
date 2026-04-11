import enum
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Date, Text, DateTime, Boolean
import datetime
from sqlalchemy.orm import relationship
from database import Base

class UserRole(str, enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    PHARMACY = "pharmacy"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)

    patient_profile = relationship("PatientProfile", back_populates="user", uselist=False)
    doctor_profile = relationship("DoctorProfile", back_populates="user", uselist=False)
    pharmacy_profile = relationship("PharmacyProfile", back_populates="user", uselist=False)

class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    blockchain_id = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    dob = Column(Date, nullable=False)
    
    blood_type = Column(String, nullable=True)
    allergies = Column(String, nullable=True)
    organ_donor = Column(String, nullable=True) # "Yes" or "No"
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    profile_picture_url = Column(String, nullable=True)
    
    user = relationship("User", back_populates="patient_profile")

class ClinicalReport(Base):
    __tablename__ = "clinical_reports"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    blood_pressure = Column(String, nullable=True)
    heart_rate = Column(Integer, nullable=True)
    report_date = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])

class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    full_name = Column(String, nullable=False)
    degree = Column(String, nullable=False)
    experience_years = Column(Integer, nullable=False)
    specialty = Column(String, nullable=True)
    verification_status = Column(String, default="pending") # pending, verified, rejected
    
    user = relationship("User", back_populates="doctor_profile")

class PharmacyProfile(Base):
    __tablename__ = "pharmacy_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    store_name = Column(String, nullable=False)
    drug_license_number = Column(String, nullable=False)
    verification_status = Column(String, default="pending") # pending, verified, rejected
    
    user = relationship("User", back_populates="pharmacy_profile")


class PatientClinicalState(Base):
    __tablename__ = "patient_clinical_states"

    id = Column(Integer, primary_key=True, index=True)
    blockchain_id = Column(String, unique=True, index=True, nullable=False)
    state_json = Column(Text, nullable=False)


class PatientAccessPermission(Base):
    __tablename__ = "patient_access_permissions"

    id = Column(Integer, primary_key=True, index=True)
    blockchain_id = Column(String, unique=True, index=True, nullable=False)
    history_granted = Column(Boolean, default=False)
    reports_granted = Column(Boolean, default=False)
    granted_by = Column(String, default="")
    granted_at = Column(String, default="")


class PatientAccessRequest(Base):
    __tablename__ = "patient_access_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True, nullable=False)
    blockchain_id = Column(String, index=True, nullable=False)
    request_type = Column(String, nullable=False)  # history | reports
    status = Column(String, default="pending")  # pending | approved | rejected
    doctor = Column(String, nullable=False)
    label = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    resolved_at = Column(String, nullable=True)


class PharmacyDemandRequest(Base):
    __tablename__ = "pharmacy_demand_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True, nullable=False)
    patient_blockchain_id = Column(String, index=True, nullable=False)
    patient_name = Column(String, nullable=False)
    pharmacy_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    pharmacy_store_name = Column(String, nullable=False)
    medicine_name = Column(String, nullable=False)
    quantity = Column(String, nullable=False)
    notes = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending | accepted | rejected
    created_at = Column(String, nullable=False)
    resolved_at = Column(String, nullable=True)
    response_message = Column(String, nullable=True)

    pharmacy = relationship("User", foreign_keys=[pharmacy_user_id])
