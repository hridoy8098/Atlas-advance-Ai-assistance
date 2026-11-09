# backend/routers/connector_api.py — pairing + laptop relay endpoints.

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from backend.connector.connector_manager import connector_manager

router = APIRouter(prefix="/api/connector", tags=["connector"])


@router.get("/status")
def connector_status() -> Dict[str, Any]:
    return connector_manager.status()


@router.get("/pairing")
def connector_pairing(request: Request) -> Dict[str, Any]:
    host = request.client.host if request.client else ""
    local = host in ("127.0.0.1", "::1", "localhost")
    show_code = local and not connector_manager.token_from_env
    return {
        "success": True,
        "configured": bool(connector_manager.token),
        "from_env": connector_manager.token_from_env,
        "pairing_code": connector_manager.token if show_code else "",
        "local_only": local,
        "hint": (
            "Set ATLAS_PAIR_TOKEN on the cloud server, then run the laptop connector "
            "with the same token."
        ),
    }


@router.websocket("/ws")
async def connector_ws(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token", "")
    if not connector_manager.check_token(token):
        await websocket.close(code=4401)
        return

    await websocket.accept()
    await connector_manager.attach(
        websocket,
        websocket.query_params.get("name", "laptop"),
    )
    try:
        while True:
            raw = await websocket.receive_text()
            connector_manager.handle_message(raw)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await connector_manager.detach(websocket)
