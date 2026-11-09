# Hugging Face Spaces deployment — Atlas 7.0

This folder documents the first live deployment. The actual `Dockerfile` and
`requirements-hf.txt` live at the repository root because Hugging Face builds a
Space from the root of its repository.

## 1. Create the Space

- Hugging Face → New Space → **Docker** → Blank.
- Name: `atlas-7` (or your choice).
- Hardware: CPU basic is enough for the UI + simulator demo.

## 2. Add Space metadata

Put this block at the top of the Space repository's `README.md`:

```yaml
---
title: Atlas 7.0
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---
```

## 3. Push the project

From the project root:

```bash
git init
git add .
git commit -m "Atlas 7.0 — agents, calls, HF deploy"
git remote add space https://huggingface.co/spaces/<user>/<space>
git push space main
```

Do **not** commit `.env`. Add secrets in **Space → Settings → Variables and secrets**:

| Secret | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | yes | Primary AI |
| `GROQ_KEY_1` | recommended | Fallback AI |
| `ATLAS_CLOUD` | yes (cloud) | `1` = relay PC/desktop agents to the paired laptop |
| `ATLAS_PAIR_TOKEN` | yes (cloud) | Pairing code the laptop connector sends |
| `DATABASE_URL` | later | Postgres for persistent call data |
| `TWILIO_ACCOUNT_SID` | later | Real receptionist calls |
| `TWILIO_AUTH_TOKEN` | later | Real receptionist calls |
| `TWILIO_PHONE_NUMBER` | later | Virtual number |

## 4. Connect the laptop

Phone-only agents (WhatsApp Call, AI Receptionist) run on the Space. All PC,
file, coding, screen, email and meeting work runs on the laptop through one
outbound WebSocket — no port forwarding needed:

```bash
python connector/atlas_laptop.py --server https://<user>-<space>.hf.space --token <ATLAS_PAIR_TOKEN>
```

The connector prints `Connected` and the Space's Agent panel footer shows the
laptop as online. Set `target=laptop` (or omit it in cloud mode) to relay.

## 4. What works on the free Space

- Agent Control Panel with on/off persistence (22 agents)
- Chat + command routing (if AI keys are set)
- Contacts + WhatsApp deep-link handoff
- AI receptionist **simulator**, call inbox and callback queue
- Health checks and “agent disabled” gating
- 12 advanced agents: Coding Copilot, Screen Vision RPA, Deep Research,
  Document Intelligence, Exam Coach, YouTube Learning, Presentation Builder,
  Email Triage, Meeting Autopilot, Personal Finance, Security Sentinel and
  Privacy Guardian

## 5. What needs an always-on server

Real incoming phone calls cannot rely on a free Space that sleeps:

- Twilio/SIP webhook cold starts can drop a call.
- Media streaming needs a stable WebSocket.
- Recordings need persistent object storage.

Move to a VPS (or paid always-on Space) for Phase 3. Keep the same environment
variables and Docker image; only the host changes.

## 6. Important limits

- Hugging Face free storage is ephemeral. Agent settings survive in the image
  but new toggles reset on rebuild unless you set `DATABASE_URL`.
- WhatsApp Web / Playwright should run on the **laptop connector**, not on the
  Space, because the QR session needs a persistent browser profile.
- iOS has no third-party WhatsApp UI automation. Use Siri/Shortcuts + one tap.
