import enum
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Date, Text
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
    full_name = Column(String, nullable=False)
    dob = Column(Date, nullable=False)
    
    user = relationship("User", back_populates="patient_profile")

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
