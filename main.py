import os
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import User, Facility, Patient, Pregnancy, Visit, Appointment, Alert

app = FastAPI(title="MaterGui API", version="0.1.0", description="Plateforme Nationale Numérique de Suivi de la Santé Maternelle en Guinée")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Utilities
# -----------------------------

def generate_matergui_id() -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    from secrets import randbelow
    suffix = f"{randbelow(10**6):06d}"
    return f"MGU-{today}-{suffix}"


def ensure_db():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available. Ensure DATABASE_URL and DATABASE_NAME are set.")


# -----------------------------
# Health & Schema
# -----------------------------
@app.get("/")
def read_root():
    return {"name": "MaterGui API", "status": "ok", "timestamp": datetime.utcnow()}


@app.get("/schema")
def get_schema_definitions():
    # Simple schema exposure for client tooling
    return {
        "collections": [
            "user", "facility", "patient", "pregnancy", "visit", "appointment", "alert"
        ]
    }


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = os.getenv("DATABASE_NAME") or "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:20]
            except Exception as e:
                response["database"] = f"⚠️ Connected but error listing collections: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# -----------------------------
# Patients
# -----------------------------
class PatientCreate(Patient):
    pass


@app.post("/patients")
def create_patient(payload: PatientCreate):
    ensure_db()
    data = payload.model_dump()
    if not data.get("matergui_id"):
        data["matergui_id"] = generate_matergui_id()
    # uniq by national_id or phone + name could be added later
    new_id = create_document("patient", data)
    return {"id": new_id, "matergui_id": data["matergui_id"]}


@app.get("/patients")
def list_patients(limit: int = 50):
    ensure_db()
    docs = get_documents("patient", {}, limit=limit)
    return docs


# -----------------------------
# Pregnancies
# -----------------------------
class PregnancyCreate(Pregnancy):
    pass


@app.post("/pregnancies")
def create_pregnancy(payload: PregnancyCreate):
    ensure_db()
    # verify patient exists
    from bson import ObjectId
    patient_id = payload.patient_id
    try:
        pid = ObjectId(patient_id)
    except Exception:
        raise HTTPException(status_code=400, detail="patient_id invalide")
    patient = db["patient"].find_one({"_id": pid})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    new_id = create_document("pregnancy", payload)
    return {"id": new_id}


@app.get("/pregnancies")
def list_pregnancies(limit: int = 50):
    ensure_db()
    docs = get_documents("pregnancy", {}, limit=limit)
    return docs


# -----------------------------
# Visits
# -----------------------------
class VisitCreate(Visit):
    pass


@app.post("/visits")
def create_visit(payload: VisitCreate):
    ensure_db()
    # verify pregnancy exists
    from bson import ObjectId
    try:
        preg = db["pregnancy"].find_one({"_id": ObjectId(payload.pregnancy_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="pregnancy_id invalide")
    if not preg:
        raise HTTPException(status_code=404, detail="Grossesse introuvable")
    new_id = create_document("visit", payload)
    return {"id": new_id}


@app.get("/visits")
def list_visits(limit: int = 50):
    ensure_db()
    docs = get_documents("visit", {}, limit=limit)
    return docs


# -----------------------------
# Appointments & Alerts (minimal)
# -----------------------------
class AppointmentCreate(Appointment):
    pass


@app.post("/appointments")
def create_appointment(payload: AppointmentCreate):
    ensure_db()
    new_id = create_document("appointment", payload)
    return {"id": new_id}


class AlertCreate(Alert):
    pass


@app.post("/alerts")
def create_alert(payload: AlertCreate):
    ensure_db()
    new_id = create_document("alert", payload)
    return {"id": new_id}


# -----------------------------
# Analytics / Dashboard
# -----------------------------
@app.get("/stats")
def get_stats():
    ensure_db()
    def count(col: str) -> int:
        try:
            return db[col].count_documents({})
        except Exception:
            return 0

    # simplified EDD calculation distribution
    recent_pregnancies = list(db["pregnancy"].find({}, {"expected_due_date": 1}).limit(200))
    due_this_month = 0
    if recent_pregnancies:
        today = date.today()
        for p in recent_pregnancies:
            edd = p.get("expected_due_date")
            if isinstance(edd, datetime):
                edd = edd.date()
            if edd and edd.year == today.year and edd.month == today.month:
                due_this_month += 1

    regions = db["facility"].aggregate([
        {"$group": {"_id": "$region", "count": {"$sum": 1}}}
    ]) if "facility" in db.list_collection_names() else []

    return {
        "patients": count("patient"),
        "pregnancies": count("pregnancy"),
        "visits": count("visit"),
        "appointments": count("appointment"),
        "alerts": count("alert"),
        "due_this_month": due_this_month,
        "facilities_by_region": list(regions) if regions else []
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
