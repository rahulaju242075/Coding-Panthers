from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
from routers.patient import get_current_user_from_token
from realtime_store import (
    list_pharmacy_demand_requests,
    resolve_pharmacy_demand_request,
)

router = APIRouter(prefix="/api/pharmacy", tags=["pharmacy"])


def _normalized_role(user: models.User) -> str:
    role_value = user.role
    return role_value.value if isinstance(role_value, models.UserRole) else str(role_value)


def _current_user_id(user: models.User) -> int:
    return int(getattr(user, "id", 0) or 0)


@router.get("/me")
def pharmacy_me(current_user: models.User = Depends(get_current_user_from_token)):
    if _normalized_role(current_user) != models.UserRole.PHARMACY.value:
        raise HTTPException(status_code=403, detail="Not authorized as pharmacy")
    profile = current_user.pharmacy_profile
    return {
        "email": current_user.email,
        "user_id": current_user.id,
        "store_name": profile.store_name if profile else "Pharmacy",
        "license": profile.drug_license_number if profile else "",
        "verification_status": profile.verification_status if profile else "pending",
    }


@router.get("/requests")
def pharmacy_requests(
    current_user: models.User = Depends(get_current_user_from_token),
):
    if _normalized_role(current_user) != models.UserRole.PHARMACY.value:
        raise HTTPException(status_code=403, detail="Not authorized as pharmacy")
    return list_pharmacy_demand_requests(_current_user_id(current_user))


@router.post("/requests/{request_id}/resolve")
def pharmacy_resolve_request(
    request_id: str,
    payload: dict,
    current_user: models.User = Depends(get_current_user_from_token),
):
    if _normalized_role(current_user) != models.UserRole.PHARMACY.value:
        raise HTTPException(status_code=403, detail="Not authorized as pharmacy")

    decision = str(payload.get("decision", "")).strip().lower()
    response_message = str(payload.get("response_message", "")).strip()
    if decision not in {"accept", "reject"}:
        raise HTTPException(status_code=400, detail="decision must be accept or reject")

    resolved = resolve_pharmacy_demand_request(request_id, decision, response_message)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Demand request not found")
    return resolved