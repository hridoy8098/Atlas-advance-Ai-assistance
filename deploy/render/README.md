# Deploy the Atlas backend to Render (free tier)

The React UI is hosted separately on GitHub Pages. This service only runs the
FastAPI backend.

| Item | Value |
|---|---|
| Runtime | Docker (`Dockerfile.render`) |
| Plan | Free — 512 MB RAM, 0.1 CPU |
| Disk | Ephemeral |
| Sleep | After 15 minutes idle |
| Hours | 750 instance hours / month (account-wide) |
| Card | Not required |

## Why the requirements are trimmed

[`requirements-render.txt`](../../requirements-render.txt) omits desktop and
vector-memory packages that do not fit in 512 MB:

| Package | Why it is excluded |
|---|---|
| `opencv-python` | ~128 MB on disk, 100–150 MB RSS; camera features only |
| `chromadb` + `onnxruntime` | 150–250 MB RSS once the embedding model loads |
| `pygame` | Local audio playback only |
| `pyautogui` | Screen control only |
| `SpeechRecognition` / `pyaudio` | Server has no microphone |
| `pandas`, `matplotlib` | Not imported by the runtime code |

The code imports every one of these inside `try/except` or inside a function,
so a missing package produces a warning and a disabled feature, not a crash.
`memory.py` falls back to SQLite keyword search when ChromaDB is absent.

## Deploy

### Option A — Blueprint (recommended)

1. Push this repository to GitHub.
2. Open [render.com](https://render.com) → **New → Blueprint**.
3. Select the repository. Render reads [`render.yaml`](../../render.yaml).
4. Enter the secrets marked `sync: false`:
   - `AUTH_PIN` — 6 digits, not the default `123456`
   - `GEMINI_API_KEY`
   - `GROQ_KEY_1` (optional but recommended)
   - `WEATHER_API_KEY`, `NEWS_API_KEY`, `VIRUSTOTAL_API_KEY`, `HIBP_API_KEY` (optional)
5. **Apply** and wait for the first build (5–10 minutes).

### Option B — Manual web service

1. **New → Web Service** → connect the repository.
2. Language: **Docker**.
3. Dockerfile path: `./Dockerfile.render`.
4. Plan: **Free**. Region: **Singapore** (lowest latency from Bangladesh).
5. Health check path: `/api/health`.
6. Add the same environment variables, plus:
   - `ATLAS_CLOUD=1`
   - `ATLAS_VOICE_AUTOSTART=0`
7. Create the service.

## Verify

```bash
curl https://<service>.onrender.com/api/health
```

```json
{"status":"ok","version":"7.0.0","auth_required":true,...}
```

Without a token, a protected endpoint must return `401`:

```bash
curl -i https://<service>.onrender.com/api/agents
```

Log in and use the returned token:

```bash
curl -X POST https://<service>.onrender.com/api/auth/pin \
  -H "Content-Type: application/json" \
  -d '{"pin":"246810"}'
```

## Connect the UI

Open the GitHub Pages site. Because it is static, the **Connect Atlas server**
dialog asks for this service URL once. After connecting, the PIN screen appears.

## Known limits

- **Cold start**: the free instance sleeps after 15 minutes. The first request
  takes 30–60 seconds. A free cron ping every 10 minutes keeps it warm but uses
  the 750-hour monthly budget.
- **No persistent disk**: `data/atlas.db`, uploads and ChromaDB reset on every
  restart or deploy. Move to Postgres (Neon/Supabase free) for real data.
- **No WhatsApp bridge or call receptionist**: both need a long-running process
  and a persistent session, which the free plan cannot provide.
- **No browser automation**: Chromium does not fit in 512 MB.
- **500 MB image pull on every deploy** is normal; builds are cached by layer.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Build fails at `pip install` | A new package needs a compiler | Prefer wheels, or skip the package in `requirements-render.txt` |
| Service restarts randomly | Out of memory (512 MB) | Check logs for `Killed`; remove another heavy package |
| `401` on everything | Expected in cloud mode | Send `Authorization: Bearer <token>` |
| Browser shows a CORS error | Server was started without `ATLAS_CLOUD=1` | Set the variable and redeploy |
| UI cannot connect | Wrong URL or service asleep | Open `/api/health` directly first |
