"""
MaterGui Database Schemas

Each Pydantic model corresponds to a MongoDB collection.
Class name lowercased = collection name.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import date, datetime

# -----------------------------
# Core Identity & Access
# -----------------------------
class User(BaseModel):
    full_name: str = Field(..., description="Nom complet")
    email: Optional[str] = Field(None, description="Adresse email")
    phone: Optional[str] = Field(None, description="Téléphone")
    role: Literal["agent", "medecin", "sage_femme", "patiente", "admin", "ministere"] = "agent"
    facility_id: Optional[str] = Field(None, description="Référence de la structure sanitaire")
    is_active: bool = True

class Facility(BaseModel):
    name: str
    type: Literal["centre_sante", "hopital", "clinique_privee", "clinique_publique", "autre"] = "centre_sante"
    region: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    code: Optional[str] = Field(None, description="Code unique de la structure")

# -----------------------------
# Patient & Maternal Care
# -----------------------------
class Patient(BaseModel):
    matergui_id: Optional[str] = Field(None, description="Identifiant unique généré par le système")
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    national_id: Optional[str] = Field(None, description="NIN/Numéro d'identification")
    facility_id: Optional[str] = Field(None, description="Structure d'enrôlement")
    # Biometrics placeholders (to be integrated later)
    face_template_id: Optional[str] = None
    fingerprint_template_id: Optional[str] = None

class Pregnancy(BaseModel):
    patient_id: str = Field(..., description="ID du document patient")
    lmp: Optional[date] = Field(None, description="Date des dernières règles")
    expected_due_date: Optional[date] = None
    parity: Optional[int] = Field(0, ge=0)
    gravida: Optional[int] = Field(1, ge=1)
    risk_level: Literal["faible", "modere", "eleve"] = "faible"
    status: Literal["en_cours", "accouchement", "terminee"] = "en_cours"

class Visit(BaseModel):
    pregnancy_id: str
    visit_date: date = Field(default_factory=lambda: date.today())
    blood_pressure_systolic: Optional[int] = Field(None, ge=50, le=250)
    blood_pressure_diastolic: Optional[int] = Field(None, ge=30, le=150)
    weight_kg: Optional[float] = Field(None, ge=20, le=250)
    fundal_height_cm: Optional[float] = Field(None, ge=0, le=60)
    foetal_heart_rate: Optional[int] = Field(None, ge=60, le=200)
    symptoms: Optional[str] = None
    notes: Optional[str] = None
    prescriptions: Optional[List[str]] = None

class Appointment(BaseModel):
    patient_id: str
    appointment_date: datetime
    reason: Optional[str] = None
    status: Literal["planifie", "honore", "annule", "manque"] = "planifie"

class Alert(BaseModel):
    patient_id: str
    type: Literal["urgence", "rappel", "risque"] = "rappel"
    message: str
    created_by: Optional[str] = None

# The schema viewer in this environment can introspect these models to help CRUD.
