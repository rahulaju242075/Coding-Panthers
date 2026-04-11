from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from typing import Dict, List, Any

from database import SessionLocal
import models


def _default_state() -> Dict[str, Any]:
    return {
        "vitals": {"bp": "120/80", "hr": "72", "rhythm": "Normal Sinus Rhythm"},
        "followUp": {"days": 3, "doctor": "Dr. Sarah Chen"},
        "notification": {
            "visible": True,
            "message": "Dr. Sanctuary added Loratadine 10mg"
        },
        "timeline": [
            {
                "date": "2024-03-12",
                "title": "Annual Physical Examination",
                "notes": "Overall health is excellent. Recommended increasing Vitamin D intake during winter months. All vitals within normal range."
            },
            {
                "date": "2024-01-05",
                "title": "Seasonal Influenza Vaccination",
                "notes": "Routine booster administered by Dr. Sanctuary. No adverse reactions reported during observation."
            },
            {
                "date": "2023-11-18",
                "title": "Dermatology Consult",
                "notes": "Minor eczema flare-up treated with topical corticosteroids. Condition resolved in 7 days."
            }
        ],
        "diagnoses": [
            {"code": "J30.1", "name": "Allergic Rhinitis", "status": "Confirmed March 2024"},
            {"code": "E67.3", "name": "Hypervitaminosis D", "status": "Monitoring Since Nov 2023"}
        ],
        "medications": [
            {"icon": "pill", "name": "Loratadine 10mg", "schedule": "1 tablet daily (Morning)", "tag": "Refill Available"},
            {"icon": "vaccines", "name": "Vitamin D3 2000IU", "schedule": "1 softgel daily (Evening)", "tag": ""}
        ],
        "reports": [
            {"file": "Blood_Panel_Oct23.pdf", "size": "2.4 MB", "when": "Uploaded Today"}
        ]
    }


def _default_permissions() -> Dict[str, Any]:
    return {
        "historyGranted": False,
        "reportsGranted": False,
        "grantedBy": "",
        "grantedAt": "",
    }


def _load_state(entity: models.PatientClinicalState | None) -> Dict[str, Any]:
    if entity is None:
        return _default_state()
    try:
        parsed = json.loads(entity.state_json)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return _default_state()


def _save_state(db, blockchain_id: str, state: Dict[str, Any]) -> models.PatientClinicalState:
    entity = db.query(models.PatientClinicalState).filter(models.PatientClinicalState.blockchain_id == blockchain_id).first()
    payload = json.dumps(state)
    if entity is None:
        entity = models.PatientClinicalState(blockchain_id=blockchain_id, state_json=payload)
        db.add(entity)
    else:
        entity.state_json = payload
    return entity


def ensure_patient_state(blockchain_id: str) -> None:
    db = SessionLocal()
    try:
        state_entity = db.query(models.PatientClinicalState).filter(models.PatientClinicalState.blockchain_id == blockchain_id).first()
        if state_entity is None:
            _save_state(db, blockchain_id, _default_state())

        perm_entity = db.query(models.PatientAccessPermission).filter(models.PatientAccessPermission.blockchain_id == blockchain_id).first()
        if perm_entity is None:
            db.add(models.PatientAccessPermission(blockchain_id=blockchain_id, **{
                "history_granted": False,
                "reports_granted": False,
                "granted_by": "",
                "granted_at": "",
            }))
        db.commit()
    finally:
        db.close()


def get_clinical_state(blockchain_id: str) -> Dict[str, Any]:
    ensure_patient_state(blockchain_id)
    db = SessionLocal()
    try:
        entity = db.query(models.PatientClinicalState).filter(models.PatientClinicalState.blockchain_id == blockchain_id).first()
        return deepcopy(_load_state(entity))
    finally:
        db.close()


def set_clinical_state(blockchain_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    ensure_patient_state(blockchain_id)
    db = SessionLocal()
    try:
        _save_state(db, blockchain_id, deepcopy(state))
        db.commit()
        return deepcopy(state)
    finally:
        db.close()


def add_timeline_entry(blockchain_id: str, title: str, notes: str, date_value: str | None = None) -> Dict[str, Any]:
    ensure_patient_state(blockchain_id)
    db = SessionLocal()
    try:
        entity = db.query(models.PatientClinicalState).filter(models.PatientClinicalState.blockchain_id == blockchain_id).first()
        state = _load_state(entity)
        state["timeline"].insert(0, {
            "date": date_value or datetime.utcnow().date().isoformat(),
            "title": title,
            "notes": notes,
        })
        state["timeline"] = state["timeline"][:20]
        _save_state(db, blockchain_id, state)
        db.commit()
        return deepcopy(state)
    finally:
        db.close()


def add_diagnosis(blockchain_id: str, code: str, name: str, status: str) -> Dict[str, Any]:
    ensure_patient_state(blockchain_id)
    db = SessionLocal()
    try:
        entity = db.query(models.PatientClinicalState).filter(models.PatientClinicalState.blockchain_id == blockchain_id).first()
        state = _load_state(entity)
        state["diagnoses"].insert(0, {"code": code, "name": name, "status": status})
        state["diagnoses"] = state["diagnoses"][:20]
        _save_state(db, blockchain_id, state)
        db.commit()
        return deepcopy(state)
    finally:
        db.close()


def add_prescription(blockchain_id: str, name: str, schedule: str, doctor_name: str) -> Dict[str, Any]:
    ensure_patient_state(blockchain_id)
    db = SessionLocal()
    try:
        entity = db.query(models.PatientClinicalState).filter(models.PatientClinicalState.blockchain_id == blockchain_id).first()
        state = _load_state(entity)
        state["medications"].insert(0, {
            "icon": "pill",
            "name": name,
            "schedule": schedule,
            "tag": "Refill Available"
        })
        state["medications"] = state["medications"][:20]
        state["notification"] = {
            "visible": True,
            "message": f"{doctor_name} added {name}"
        }
        _save_state(db, blockchain_id, state)
        db.commit()
        return deepcopy(state)
    finally:
        db.close()


def add_report(
    blockchain_id: str,
    file_name: str,
    size_text: str = "1.9 MB",
    when_text: str = "Uploaded Now",
    url: str = "",
) -> Dict[str, Any]:
    ensure_patient_state(blockchain_id)
    db = SessionLocal()
    try:
        entity = db.query(models.PatientClinicalState).filter(models.PatientClinicalState.blockchain_id == blockchain_id).first()
        state = _load_state(entity)
        state.setdefault("reports", [])
        state["reports"].insert(0, {"file": file_name, "size": size_text, "when": when_text, "url": url})
        state["reports"] = state["reports"][:20]
        _save_state(db, blockchain_id, state)
        db.commit()
        return deepcopy(state)
    finally:
        db.close()


def update_vitals(blockchain_id: str, bp: str, hr: str, rhythm: str) -> Dict[str, Any]:
    ensure_patient_state(blockchain_id)
    db = SessionLocal()
    try:
        entity = db.query(models.PatientClinicalState).filter(models.PatientClinicalState.blockchain_id == blockchain_id).first()
        state = _load_state(entity)
        state.setdefault("vitals", {})
        state["vitals"]["bp"] = bp
        state["vitals"]["hr"] = hr
        state["vitals"]["rhythm"] = rhythm
        _save_state(db, blockchain_id, state)
        db.commit()
        return deepcopy(state)
    finally:
        db.close()


def get_permissions(blockchain_id: str) -> Dict[str, Any]:
    ensure_patient_state(blockchain_id)
    db = SessionLocal()
    try:
        entity = db.query(models.PatientAccessPermission).filter(models.PatientAccessPermission.blockchain_id == blockchain_id).first()
        if entity is None:
            return _default_permissions()
        return {
            "historyGranted": bool(entity.history_granted),
            "reportsGranted": bool(entity.reports_granted),
            "grantedBy": entity.granted_by or "",
            "grantedAt": entity.granted_at or "",
        }
    finally:
        db.close()


def create_access_request(blockchain_id: str, doctor_name: str, req_type: str, label: str) -> Dict[str, Any]:
    ensure_patient_state(blockchain_id)
    db = SessionLocal()
    try:
        request_id = f"{int(datetime.utcnow().timestamp() * 1000)}_{req_type}"
        payload = models.PatientAccessRequest(
            request_id=request_id,
            blockchain_id=blockchain_id,
            request_type=req_type,
            status="pending",
            doctor=doctor_name,
            label=label,
            created_at=datetime.utcnow().isoformat(),
            resolved_at=None,
        )
        db.add(payload)
        db.commit()
        return {
            "id": request_id,
            "type": req_type,
            "status": "pending",
            "doctor": doctor_name,
            "patientId": blockchain_id,
            "label": label,
            "createdAt": payload.created_at,
        }
    finally:
        db.close()


def get_notifications(blockchain_id: str) -> List[Dict[str, Any]]:
    ensure_patient_state(blockchain_id)
    db = SessionLocal()
    try:
        rows = db.query(models.PatientAccessRequest).filter(models.PatientAccessRequest.blockchain_id == blockchain_id).order_by(models.PatientAccessRequest.id.desc()).all()
        out = []
        for row in rows:
            out.append({
                "id": row.request_id,
                "type": row.request_type,
                "status": row.status,
                "doctor": row.doctor,
                "patientId": row.blockchain_id,
                "label": row.label,
                "createdAt": row.created_at,
                "resolvedAt": row.resolved_at,
            })
        return out
    finally:
        db.close()


def resolve_notification(blockchain_id: str, request_id: str, decision: str) -> Dict[str, Any] | None:
    ensure_patient_state(blockchain_id)
    db = SessionLocal()
    try:
        target = db.query(models.PatientAccessRequest).filter(
            models.PatientAccessRequest.blockchain_id == blockchain_id,
            models.PatientAccessRequest.request_id == request_id,
        ).first()
        if target is None:
            return None

        target.status = "approved" if decision == "accept" else "rejected"
        target.resolved_at = datetime.utcnow().isoformat()

        if decision == "accept":
            perms = db.query(models.PatientAccessPermission).filter(models.PatientAccessPermission.blockchain_id == blockchain_id).first()
            if perms is None:
                perms = models.PatientAccessPermission(blockchain_id=blockchain_id)
                db.add(perms)
            if target.request_type == "history":
                perms.history_granted = True
            if target.request_type == "reports":
                perms.reports_granted = True
            perms.granted_by = "Patient"
            perms.granted_at = datetime.utcnow().date().isoformat()

        db.commit()
        return {
            "id": target.request_id,
            "type": target.request_type,
            "status": target.status,
            "doctor": target.doctor,
            "patientId": target.blockchain_id,
            "label": target.label,
            "createdAt": target.created_at,
            "resolvedAt": target.resolved_at,
        }
    finally:
        db.close()


def create_pharmacy_demand_request(
    patient_blockchain_id: str,
    patient_name: str,
    pharmacy_user_id: int,
    pharmacy_store_name: str,
    medicine_name: str,
    quantity: str,
    notes: str,
) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        request_id = f"{int(datetime.utcnow().timestamp() * 1000)}_pharmacy"
        row = models.PharmacyDemandRequest(
            request_id=request_id,
            patient_blockchain_id=patient_blockchain_id,
            patient_name=patient_name,
            pharmacy_user_id=pharmacy_user_id,
            pharmacy_store_name=pharmacy_store_name,
            medicine_name=medicine_name,
            quantity=quantity,
            notes=notes,
            status="pending",
            created_at=datetime.utcnow().isoformat(),
            resolved_at=None,
            response_message=None,
        )
        db.add(row)
        db.commit()
        return {
            "id": request_id,
            "patientBlockChainId": patient_blockchain_id,
            "patientName": patient_name,
            "pharmacyUserId": pharmacy_user_id,
            "pharmacyStoreName": pharmacy_store_name,
            "medicineName": medicine_name,
            "quantity": quantity,
            "notes": notes,
            "status": "pending",
            "createdAt": row.created_at,
            "resolvedAt": None,
            "responseMessage": None,
        }
    finally:
        db.close()


def list_pharmacy_demand_requests(pharmacy_user_id: int) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = db.query(models.PharmacyDemandRequest).filter(
            models.PharmacyDemandRequest.pharmacy_user_id == pharmacy_user_id
        ).order_by(models.PharmacyDemandRequest.id.desc()).all()
        return [
            {
                "id": row.request_id,
                "patientBlockChainId": row.patient_blockchain_id,
                "patientName": row.patient_name,
                "pharmacyUserId": row.pharmacy_user_id,
                "pharmacyStoreName": row.pharmacy_store_name,
                "medicineName": row.medicine_name,
                "quantity": row.quantity,
                "notes": row.notes or "",
                "status": row.status,
                "createdAt": row.created_at,
                "resolvedAt": row.resolved_at,
                "responseMessage": row.response_message or "",
            }
            for row in rows
        ]
    finally:
        db.close()


def resolve_pharmacy_demand_request(request_id: str, decision: str, response_message: str = "") -> Dict[str, Any] | None:
    db = SessionLocal()
    try:
        row = db.query(models.PharmacyDemandRequest).filter(models.PharmacyDemandRequest.request_id == request_id).first()
        if row is None:
            return None
        row.status = "accepted" if decision == "accept" else "rejected"
        row.resolved_at = datetime.utcnow().isoformat()
        row.response_message = response_message or ("Ready for pickup" if decision == "accept" else "Out of stock")
        db.commit()
        return {
            "id": row.request_id,
            "patientBlockChainId": row.patient_blockchain_id,
            "patientName": row.patient_name,
            "pharmacyUserId": row.pharmacy_user_id,
            "pharmacyStoreName": row.pharmacy_store_name,
            "medicineName": row.medicine_name,
            "quantity": row.quantity,
            "notes": row.notes or "",
            "status": row.status,
            "createdAt": row.created_at,
            "resolvedAt": row.resolved_at,
            "responseMessage": row.response_message or "",
        }
    finally:
        db.close()


def list_patient_pharmacy_demand_requests(patient_blockchain_id: str) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = db.query(models.PharmacyDemandRequest).filter(
            models.PharmacyDemandRequest.patient_blockchain_id == patient_blockchain_id
        ).order_by(models.PharmacyDemandRequest.id.desc()).all()
        return [
            {
                "id": row.request_id,
                "patientBlockChainId": row.patient_blockchain_id,
                "patientName": row.patient_name,
                "pharmacyUserId": row.pharmacy_user_id,
                "pharmacyStoreName": row.pharmacy_store_name,
                "medicineName": row.medicine_name,
                "quantity": row.quantity,
                "notes": row.notes or "",
                "status": row.status,
                "createdAt": row.created_at,
                "resolvedAt": row.resolved_at,
                "responseMessage": row.response_message or "",
            }
            for row in rows
        ]
    finally:
        db.close()


def list_pharmacies() -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = db.query(models.PharmacyProfile, models.User).join(models.User, models.PharmacyProfile.user_id == models.User.id).all()
        return [
            {
                "userId": user.id,
                "email": user.email,
                "storeName": profile.store_name,
                "license": profile.drug_license_number,
                "verificationStatus": profile.verification_status,
            }
            for profile, user in rows
        ]
    finally:
        db.close()
