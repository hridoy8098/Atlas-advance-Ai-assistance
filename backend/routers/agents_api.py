# backend/routers/agents_api.py — Agent Control Panel API

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from backend.agent.agent_registry import AGENT_MAP, agent_registry

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
def list_agents():
    return {"success": True, **agent_registry.summary()}


@router.get("/health")
def agents_health():
    return agent_registry.health_report()


@router.post("/bulk-toggle")
def bulk_toggle(payload: Dict[str, Any] = Body(default={})):
    enabled = bool(payload.get("enabled", True))
    category = payload.get("category")
    return agent_registry.bulk_toggle(enabled=enabled, category=category)


@router.post("/{agent_id}/toggle")
def toggle_agent(agent_id: str, payload: Dict[str, Any] = Body(default={})):
    if agent_id not in AGENT_MAP:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    if "enabled" in payload:
        return agent_registry.set_enabled(agent_id, bool(payload["enabled"]))
    return agent_registry.toggle(agent_id)


@router.get("/{agent_id}")
def get_agent(agent_id: str):
    info = agent_registry.get_agent(agent_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    return {"success": True, "agent": info}


@router.post("/{agent_id}/test")
def test_agent(agent_id: str):
    if agent_id not in AGENT_MAP:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    return agent_registry.test(agent_id)
