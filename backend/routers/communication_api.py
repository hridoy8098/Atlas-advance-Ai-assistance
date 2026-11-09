# backend/routers/communication_api.py — contacts, WhatsApp calls and receptionist

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException

from backend.communication import contact_resolver
from backend.communication.call_receptionist_agent import call_receptionist_agent
from backend.communication.whatsapp_call_agent import whatsapp_call_agent

router = APIRouter(prefix="/api/communication", tags=["communication"])


# ---------------- contacts ----------------
@router.get("/contacts")
def list_contacts():
    contacts = contact_resolver.load_contacts()
    return {"success": True, "contacts": contacts, "count": len(contacts)}


@router.post("/contacts")
def add_contact(payload: Dict[str, Any] = Body(default={})):
    result = contact_resolver.add_contact(
        name=str(payload.get("name", "")),
        phone=str(payload.get("phone", "")),
        aliases=payload.get("aliases") if isinstance(payload.get("aliases"), list) else [],
        whatsapp=bool(payload.get("whatsapp", True)),
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Could not save contact"))
    return result


@router.delete("/contacts/{name}")
def delete_contact(name: str):
    result = contact_resolver.delete_contact(name)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Contact not found"))
    return result


# ---------------- WhatsApp call ----------------
@router.post("/whatsapp/call")
def whatsapp_call(payload: Dict[str, Any] = Body(default={})):
    contact = str(payload.get("contact") or payload.get("name") or "").strip()
    if not contact:
        raise HTTPException(status_code=400, detail="contact is required")
    platform_name = str(payload.get("platform", "desktop")).lower()
    return whatsapp_call_agent.place_call(contact, platform_name)


# ---------------- receptionist ----------------
@router.get("/receptionist/status")
def receptionist_status():
    return call_receptionist_agent.status()


@router.post("/receptionist/busy")
def receptionist_busy(payload: Dict[str, Any] = Body(default={})):
    return call_receptionist_agent.set_busy(bool(payload.get("busy", True)))


@router.post("/receptionist/simulate")
def receptionist_simulate(payload: Dict[str, Any] = Body(default={})):
    return call_receptionist_agent.simulate_call(
        caller_name=str(payload.get("caller_name", "Test Caller")),
        caller_number=str(payload.get("caller_number", "+8801000000000")),
        message=str(payload.get("message", "Please call me back.")),
        urgency=str(payload.get("urgency", "normal")),
    )


@router.get("/receptionist/calls")
def receptionist_calls(limit: int = 50):
    return call_receptionist_agent.list_calls(limit=limit)


@router.post("/receptionist/callback")
def receptionist_callback(payload: Dict[str, Any] = Body(default={})):
    return call_receptionist_agent.callback(
        str(payload.get("call_id", "")),
        platform=str(payload.get("platform", "desktop")),
    )
