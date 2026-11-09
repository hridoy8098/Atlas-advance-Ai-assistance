# server.py — Atlas 7.0 FastAPI Server

import sys
import os
import threading
import time
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import uvicorn

import config

app = FastAPI(title="Atlas 7.0 API", version="7.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://localhost:3000", "http://localhost:8000",
        "https://localhost", "capacitor://localhost", "http://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== CLOUD AUTH GATE =====
# Local installs (ATLAS_CLOUD=0) stay open. A public deployment requires a
# valid PIN session for every API call except health and the login endpoint.
CLOUD_AUTH_PUBLIC = {"/api/auth/pin", "/api/health"}
PIN_ATTEMPTS = {}
PIN_ATTEMPTS_LOCK = threading.Lock()
PIN_MAX_ATTEMPTS = 5
PIN_WINDOW_SECONDS = 300


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


def _pin_attempts_for(ip: str):
    now = time.time()
    with PIN_ATTEMPTS_LOCK:
        attempts = [t for t in PIN_ATTEMPTS.get(ip, []) if now - t < PIN_WINDOW_SECONDS]
        if attempts:
            PIN_ATTEMPTS[ip] = attempts
        else:
            PIN_ATTEMPTS.pop(ip, None)
    return attempts


def _record_pin_failure(ip: str) -> None:
    with PIN_ATTEMPTS_LOCK:
        PIN_ATTEMPTS.setdefault(ip, []).append(time.time())


def _clear_pin_failures(ip: str) -> None:
    with PIN_ATTEMPTS_LOCK:
        PIN_ATTEMPTS.pop(ip, None)


def _bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return ""


@app.middleware("http")
async def cloud_auth_gate(request: Request, call_next):
    if not getattr(config, "ATLAS_CLOUD", False) or not request.url.path.startswith("/api/"):
        return await call_next(request)

    path = request.url.path
    if path in CLOUD_AUTH_PUBLIC:
        if path == "/api/auth/pin" and request.method == "POST":
            if len(_pin_attempts_for(_client_ip(request))) >= PIN_MAX_ATTEMPTS:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many PIN attempts. Try again in 5 minutes."},
                )
        return await call_next(request)

    token = _bearer_token(request)
    if not token or session_manager is None or not session_manager.is_valid(token):
        return JSONResponse(status_code=401, content={"detail": "Authentication required"})
    return await call_next(request)

# ===== Global error handler =====
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ Error on {request.url}: {exc}")
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"error": str(exc)})

# ===== DOMAIN ROUTES (analytics/security/study/bangladesh/media) =====
try:
    from backend.routers.domain_api import router as domain_router
    app.include_router(domain_router)
    print("✅ Domain API router loaded")
except Exception as e:
    print(f"⚠️ Domain API router not loaded: {e}")

try:
    from backend.routers.agents_api import router as agents_router
    app.include_router(agents_router)
    print("✅ Agents API router loaded")
except Exception as e:
    print(f"⚠️ Agents API router not loaded: {e}")

try:
    from backend.routers.communication_api import router as communication_router
    app.include_router(communication_router)
    print("✅ Communication API router loaded")
except Exception as e:
    print(f"⚠️ Communication API router not loaded: {e}")

try:
    from backend.routers.connector_api import router as connector_router
    app.include_router(connector_router)
    print("✅ Connector API router loaded")
except Exception as e:
    print(f"⚠️ Connector API router not loaded: {e}")

# ===== LAZY IMPORTS (error হলেও server চলবে) =====
ai_engine = None
language_detector = None
memory_manager = None
command_parser = None
context_engine = None
pin_auth = None
session_manager = None
auth_logger = None
voice_output = None
VOICE_AVAILABLE = False
FACE_AUTH_AVAILABLE = False

def load_modules():
    global ai_engine, language_detector, memory_manager, command_parser
    global context_engine, pin_auth, session_manager, auth_logger
    global voice_output, VOICE_AVAILABLE, FACE_AUTH_AVAILABLE

    try:
        from backend.core.ai_engine import ai_engine as _ae
        ai_engine = _ae
        print("✅ AI Engine loaded")
    except Exception as e:
        print(f"⚠️ AI Engine: {e}")

    try:
        from backend.core.language import language_detector as _ld
        language_detector = _ld
    except Exception as e:
        print(f"⚠️ Language detector: {e}")

    try:
        from backend.core.memory import memory_manager as _mm
        memory_manager = _mm
    except Exception as e:
        print(f"⚠️ Memory: {e}")

    try:
        from backend.core.command_parser import command_parser as _cp
        command_parser = _cp
    except Exception as e:
        print(f"⚠️ Command parser: {e}")

    try:
        from backend.core.context_engine import context_engine as _ce
        context_engine = _ce
    except Exception as e:
        print(f"⚠️ Context engine: {e}")

    try:
        from backend.auth.pin_auth import pin_auth as _pa
        pin_auth = _pa
        print("✅ PIN Auth loaded")
    except Exception as e:
        print(f"⚠️ PIN Auth: {e}")

    try:
        from backend.auth.session_manager import session_manager as _sm
        session_manager = _sm
    except Exception as e:
        print(f"⚠️ Session manager: {e}")

    try:
        from backend.auth.auth_logger import auth_logger as _al
        auth_logger = _al
    except Exception as e:
        print(f"⚠️ Auth logger: {e}")

    try:
        from backend.core.voice_output import voice_output as _vo
        voice_output = _vo
        VOICE_AVAILABLE = True
        print("✅ Voice loaded")
    except Exception as e:
        print(f"⚠️ Voice: {e}")

    try:
        from backend.auth.face_auth import face_auth_engine
        FACE_AUTH_AVAILABLE = True
        print("✅ Face auth loaded")
    except Exception as e:
        print(f"⚠️ Face auth: {e}")

# ===== MODELS =====
class CommandRequest(BaseModel):
    command: str
    platform: str = "desktop"
    target: str = "auto"

class PinRequest(BaseModel):
    pin: str

# ===== AUTH =====
@app.post("/api/auth/pin")
async def verify_pin(req: PinRequest, request: Request):
    client_ip = _client_ip(request)
    try:
        if pin_auth is None:
            return {"success": False, "reason": "Auth module not loaded"}

        success, msg = pin_auth.verify(req.pin)
        if success:
            _clear_pin_failures(client_ip)
            token = "atlas_session_token"
            if session_manager:
                try:
                    token = session_manager.create_session("main_user", "pin")
                except:
                    pass
            if auth_logger:
                try:
                    auth_logger.log_success("main_user", "pin")
                except:
                    pass
            return {"success": True, "user_id": "main_user", "session_token": token}

        _record_pin_failure(client_ip)
        if auth_logger:
            try:
                auth_logger.log_failure("pin", msg)
            except:
                pass
        return {"success": False, "reason": msg}

    except Exception as e:
        print(f"❌ PIN verify error: {e}")
        traceback.print_exc()
        return {"success": False, "reason": f"Server error: {str(e)}"}

@app.post("/api/auth/logout")
async def logout():
    try:
        if session_manager:
            session_manager.end_all_sessions()
    except:
        pass
    return {"success": True}

# ===== COMMAND =====
@app.post("/api/command")
async def take_command(req: CommandRequest):
    try:
        command = req.command.strip()
        if not command:
            return {"response": None}

        print(f"\n📝 User: {command}")

        if ai_engine is None or language_detector is None:
            load_modules()

        from command_handler import get_command_response

        # Cloud deployment: run PC/desktop work on the paired laptop.
        # Phone-only agents (WhatsApp call / receptionist) stay here.
        relayed = None
        try:
            from backend.connector.connector_manager import connector_manager, is_phone_only
            cloud = os.getenv("ATLAS_CLOUD", "0") == "1"
            want_relay = req.target == "laptop" or (
                req.target != "local" and cloud and connector_manager.connected
            )
            if want_relay and not is_phone_only(command):
                relayed = await connector_manager.execute(command, req.platform)
        except Exception as exc:
            print(f"⚠️ Connector relay error: {exc}")

        result = relayed if relayed is not None else get_command_response(command, platform=req.platform)
        response = result.get("response")
        lang = result.get("language", "en")

        if response:
            print(f"🤖 Atlas: {str(response)[:100]}")
            # A cloud server has no speaker; only play voice on the local desktop.
            if VOICE_AVAILABLE and voice_output and os.getenv("ATLAS_CLOUD", "0") != "1":
                threading.Thread(
                    target=voice_output.speak,
                    args=(response, "auto"),
                    daemon=True
                ).start()

        return {
            "response": response,
            "language": lang,
            "intent": result.get("intent"),
            "confidence": result.get("confidence"),
            "method": result.get("method"),
            "entities": result.get("entities", {}),
            "action": result.get("action"),
            "agent": result.get("agent"),
            "phone": result.get("phone"),
            "contact": result.get("contact"),
            "deep_link": result.get("deep_link"),
            "requires_bridge": result.get("requires_bridge", False),
            "requires_manual_tap": result.get("requires_manual_tap", False),
            "call": result.get("call"),
            "query": result.get("query"),
            "hint": result.get("hint"),
            "relayed": relayed is not None,
            "agent_result": result.get("agent_result"),
        }

    except Exception as e:
        print(f"❌ Command error: {e}")
        traceback.print_exc()
        return {"response": f"❌ Error: {str(e)}", "language": "en"}

# ===== SYSTEM =====
@app.get("/api/system/metrics")
async def get_metrics():
    try:
        import time as _time
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        bat = psutil.sensors_battery()
        return {
            "cpu": round(cpu, 1),
            "mem_used": round(mem.used / (1024**2)),
            "mem_percent": round(mem.percent, 1),
            "mem_total": round(mem.total / (1024**2)),
            "disk_percent": round(disk.percent, 1),
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "uptime_seconds": int(_time.time() - psutil.boot_time()),
            "cpu_cores": psutil.cpu_count(logical=True),
            "bat_percent": round(bat.percent, 1) if bat else -1,
            "bat_charging": bat.power_plugged if bat else False,
        }
    except Exception as e:
        return {"cpu": 0, "mem_used": 0, "mem_percent": 0, "mem_total": 0,
                "disk_percent": 0, "disk_used_gb": 0, "disk_total_gb": 0,
                "uptime_seconds": 0, "cpu_cores": 0,
                "bat_percent": -1, "bat_charging": False}

@app.get("/api/system/weather")
async def get_weather():
    try:
        import requests as req_lib
        api_key = config.WEATHER_API_KEY
        if api_key and "your" not in api_key.lower() and "xxx" not in api_key.lower():
            url = f"https://api.openweathermap.org/data/2.5/weather?q={config.DEFAULT_CITY}&appid={api_key}&units=metric"
            resp = req_lib.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "temp": round(data["main"]["temp"], 1),
                    "feels_like": round(data["main"].get("feels_like", data["main"]["temp"]), 1),
                    "desc": data["weather"][0]["description"],
                    "icon": data["weather"][0].get("icon", ""),
                    "humidity": data["main"]["humidity"],
                    "wind": data["wind"]["speed"],
                    "city": config.DEFAULT_CITY
                }
    except:
        pass
    return {"temp": 30, "feels_like": 30, "desc": "Partly Cloudy", "humidity": 65, "wind": 12, "city": config.DEFAULT_CITY}

@app.get("/api/system/prayer-times")
async def get_prayer_times():
    try:
        import requests as req_lib
        url = f"https://api.aladhan.com/v1/timingsByCity?city={config.PRAYER_CITY}&country={config.PRAYER_COUNTRY}&method=1"
        r = req_lib.get(url, timeout=5)
        if r.status_code == 200:
            t = r.json()["data"]["timings"]
            return {
                "fajr": t["Fajr"], "dhuhr": t["Dhuhr"],
                "asr": t["Asr"], "maghrib": t["Maghrib"], "isha": t["Isha"],
                "city": config.PRAYER_CITY
            }
    except:
        pass
    return {"error": "Could not fetch prayer times"}

@app.get("/api/system/groq-status")
async def groq_status():
    try:
        if ai_engine:
            status = ai_engine.get_key_status()
            return status.get("groq", [])
    except:
        pass
    return []

# ===== AGENTS =====
@app.post("/api/agent/optimize-pc")
async def optimize_pc():
    try:
        from backend.agent.pc_agent import pc_agent
        return pc_agent.optimize_pc()
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/agent/clean-temp")
async def clean_temp():
    try:
        from backend.agent.pc_agent import pc_agent
        return pc_agent.clean_temp()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/agent/list-files")
async def list_files(path: str = ""):
    try:
        from backend.agent.file_agent import file_agent
        return file_agent.list_folder(path or str(file_agent.home))
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/agent/search-files")
async def search_files(query: str):
    try:
        from backend.agent.file_agent import file_agent
        return file_agent.search_files(query)
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/agent/organize-downloads")
async def organize_downloads():
    try:
        from backend.agent.file_agent import file_agent
        return file_agent.organize_downloads()
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/agent/execute")
async def execute_command(body: dict):
    try:
        from backend.agent.terminal_agent import terminal_agent
        result = terminal_agent.execute_safe(body.get("cmd", ""))
        return {"output": result['stdout'] if result['success'] else result['stderr']}
    except Exception as e:
        return {"error": str(e)}

# ===== CONFIG =====
@app.get("/api/config")
async def get_config():
    return {
        "app_name": config.APP_NAME,
        "app_version": config.APP_VERSION,
        "user_name": config.USER_NAME,
        "atlas_name": config.ATLAS_NAME,
        "default_city": config.DEFAULT_CITY,
        "theme_color": config.THEME_COLOR,
        "face_available": FACE_AUTH_AVAILABLE,
        "voice_available": VOICE_AVAILABLE,
    }

# ===== WEBSOCKET =====
class ConnectionManager:
    def __init__(self):
        self.active = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if getattr(config, "ATLAS_CLOUD", False):
        token = websocket.query_params.get("token", "")
        if not token or session_manager is None or not session_manager.is_valid(token):
            await websocket.close(code=1008)
            return
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ===== VOICE =====
VOICE_LISTEN_LOCK = threading.Lock()
VOICE_LISTEN_CANCEL = threading.Event()

@app.get("/api/voice/speaking")
async def voice_speaking():
    try:
        speaking = bool(VOICE_AVAILABLE and voice_output and getattr(voice_output, "is_speaking", False))
    except Exception:
        speaking = False
    return {"speaking": speaking}

@app.post("/api/voice/stop")
async def voice_stop():
    try:
        if VOICE_AVAILABLE and voice_output:
            voice_output.stop_speaking()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/voice/listen")
async def voice_listen(duration: int = 5, language: str = None):
    """Record from the server microphone and transcribe with Whisper.

    This is the fallback for browsers/webviews that deny microphone access.
    """
    try:
        from backend.core.voice_input import voice_input as vi
    except Exception as e:
        return {"success": False, "error": f"Voice input unavailable: {e}"}

    seconds = max(2, min(int(duration), 12))

    if not VOICE_LISTEN_LOCK.acquire(blocking=False):
        return {"success": False, "error": "Microphone is already in use"}

    VOICE_LISTEN_CANCEL.clear()

    def _capture_and_transcribe():
        try:
            audio = vi.record_audio(duration=seconds, silent=True, cancel_event=VOICE_LISTEN_CANCEL)
            if not audio:
                return {"success": False, "error": "No audio captured. Check the microphone."}
            text = vi.transcribe(audio, language)
            if not text:
                return {"success": False, "error": "Could not understand the audio. Try again."}
            return {"success": True, "text": text, "duration": seconds}
        except Exception as e:
            print(f"❌ Voice listen error: {e}")
            return {"success": False, "error": str(e)}
        finally:
            VOICE_LISTEN_LOCK.release()

    return await run_in_threadpool(_capture_and_transcribe)

@app.post("/api/voice/listen/stop")
async def voice_listen_stop():
    try:
        from backend.core.voice_input import voice_input as vi
        VOICE_LISTEN_CANCEL.set()
        vi.is_recording = False
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===== HEALTH =====
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": config.APP_VERSION,
        "auth_required": bool(getattr(config, "ATLAS_CLOUD", False)),
        "pin_auth": pin_auth is not None,
        "ai_engine": ai_engine is not None,
        "voice": VOICE_AVAILABLE,
    }

# ===== STARTUP =====
@app.on_event("startup")
async def startup_event():
    print("🔧 Loading modules...")
    load_modules()
    # Start continuous voice listening (if available) and route to command handler
    try:
        from backend.core.voice_input import voice_input as _voice_input
        from command_handler import get_command_response as _get_command_response

        def _voice_callback(cmd: str):
            try:
                if not cmd:
                    return
                # Route recognized text to command processing
                resp = _get_command_response(cmd)
                # Speak response if voice output available
                if voice_output and resp and isinstance(resp, dict):
                    threading.Thread(target=voice_output.speak, args=(resp.get("response", ""), "auto"), daemon=True).start()
            except Exception as e:
                print(f"⚠️ Voice callback error: {e}")

        # Start background listening (ATLAS_VOICE_AUTOSTART=0 diye bondho kora jay)
        if os.getenv("ATLAS_VOICE_AUTOSTART", "1") == "0":
            print("ℹ️ Voice continuous listening disabled (ATLAS_VOICE_AUTOSTART=0)")
        else:
            try:
                _voice_input.start_continuous_listening(callback=_voice_callback)
                print("✅ Voice continuous listening started")
            except Exception as e:
                print(f"⚠️ Could not start voice listening: {e}")
    except Exception as e:
        print(f"⚠️ Voice listening not initialized: {e}")
    print("✅ Atlas 7.0 ready!")

# ===== STATIC FRONTEND (production / Hugging Face) =====
FRONTEND_DIST = config.FRONTEND_DIR / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
    print("✅ Frontend dist mounted")

# ===== MAIN =====
if __name__ == "__main__":
    # Windows: ProactorEventLoop মাঝে মাঝে "WinError 64" accept crash করে (network hiccup-এ
    # server-এর listener মরে যায়) — SelectorEventLoop এটা handle করে ভালোভাবে
    if sys.platform == "win32":
        import asyncio
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass

    print("=" * 60)
    print("🚀 Atlas 7.0 — FastAPI Server")
    print("=" * 60)
    print("   API:  http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False, log_level="info")