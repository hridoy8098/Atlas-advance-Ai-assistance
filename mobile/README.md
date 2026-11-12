# Atlas 7.0 — Mobile shell

The phone app is a Capacitor shell around the same React dashboard. It adds
native contacts, WhatsApp call hand-off, phone calls, SMS and the laptop
connection screen.

## What works where

| Feature | Android | iOS |
|---|---|---|
| Panel + toggles over laptop server | ✅ | ✅ |
| Read phone contacts for name resolution | ✅ | ✅ |
| Open WhatsApp chat with a contact | ✅ | ✅ |
| Automatically tap WhatsApp voice call | ✅ AccessibilityService (best effort) | ❌ one tap required |
| Normal phone call | ✅ direct `ACTION_CALL` | ⚠️ system confirmation |
| Send SMS | ✅ direct | ⚠️ composer opens |
| AI receptionist (real calls) | cloud number, later phase | cloud number, later phase |

iOS does not allow third-party WhatsApp UI automation. Atlas opens the chat and
the user taps the call button once. This is an OS restriction, not a missing
feature in Atlas.

## Voice input and replies

Android WebView has no usable Web Speech API, so the phone records audio itself
and lets the server do the speech work:

1. Tap the microphone. `MediaRecorder` starts and the UI shows the listening
   state. Recording stops automatically after ~1.4 s of silence, or after 12 s.
2. The clip is uploaded to `POST /api/voice/transcribe`. The server runs Groq
   Whisper `whisper-large-v3` twice in parallel, once with `language=bn` and
   once with `language=en`, then keeps the pass with the higher average
   log-probability. Forcing English on Bengali audio can produce a fluent
   English translation, so the confidence score is safer than checking the
   script of the text.
3. The transcript is sent to `POST /api/command` like a typed message. Time,
   date and weather are answered locally; everything else goes to the AI.
4. The reply is rendered to MP3 by `POST /api/voice/tts` (Edge TTS) and played
   through an `<audio>` element in the phone's speaker.

Settings -> **Voice language** has three choices:

- **Auto** (default): the dual-pass detector above. Best when you mix Bengali
  and English.
- **বাংলা**: sends `language=bn-BD`; one Whisper pass, slightly faster.
- **English**: sends `language=en-US`; one Whisper pass, slightly faster.

The microphone permission must be granted the first time. The phone does not
need the laptop microphone, and `ATLAS_VOICE_AUTOSTART` does not affect it.

## Android build

Requirements: JDK 17+ (21 works), Android SDK (platform 35, build-tools 35),
Node 20+.

```powershell
cd frontend
npm run build

cd ..\mobile
npm install
npx cap sync android

# One-time SDK setup (Windows, command-line tools)
#   sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0"
# Create android\local.properties:
#   sdk.dir=C\:\\Users\\<you>\\AppData\\Local\\Android\\Sdk

cd android
.\gradlew.bat assembleDebug
```

APK: `mobile/android/app/build/outputs/apk/debug/app-debug.apk`

Install on a USB-connected phone:

```powershell
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

## First run

1. Start the laptop server: `python server.py` (port 8000).
2. Connect the phone in one of three ways:
   - **Same WiFi:** enter `http://<laptop-LAN-IP>:8000` on the Connect screen.
   - **USB debug (different subnets work):** run `adb reverse tcp:8000 tcp:8000`
     and use `http://localhost:8000`.
   - **HF Space:** deploy `deploy/hf`, then enter the public
     `https://<user>-<space>.hf.space` URL.
3. Settings → Agents → enable **WhatsApp Call Agent** (or any advanced agent).
4. Add a contact in the agent panel, or let Atlas search the phone address book.
5. For automatic WhatsApp calls: Android Settings → Accessibility → **Atlas
   WhatsApp call assistant** → ON. Without it, Atlas opens the chat and you tap
   the call button once.

The laptop IP is shown by `ipconfig` (IPv4 Address) or in the server log.

## Agent list

15 of 22 agents are ON by default; toggle any agent from Settings → Agents.
The two call agents and the powerful/destructive ones (Coding, Screen RPA,
Email, Meeting, Security Sentinel) start OFF.

- Core: PC Control, File, Web Research, Media, Productivity, Security, App, Terminal
- Call: WhatsApp Call, AI Call Receptionist
- Advanced: Coding Copilot, Screen Vision RPA, Deep Research, Document
  Intelligence, Exam Coach, YouTube Learning, Presentation Builder, Email
  Triage, Meeting Autopilot, Personal Finance, Security Sentinel, Privacy Guardian

## WhatsApp automation risk

Android AccessibilityService automation of WhatsApp is not an official API.
WhatsApp's Terms of Service may restrict automated UI interaction and accounts
could be limited. The user enables the service explicitly. The service only
acts for 20 seconds after an Atlas call request and never reads messages.
Official WhatsApp Business Calling API is the compliant path for business
numbers.

## iOS build

iOS must be built on macOS with Xcode:

```bash
cd mobile
npm install
npx cap add ios
npx cap sync ios
npx cap open ios
```

Then:

1. Add `mobile/native/ios/AtlasNativePlugin.swift` to the App target.
2. Add `NSContactsUsageDescription` to Info.plist.
3. Set a signing team and build.

Siri Shortcuts can also expose “Call <contact> on WhatsApp” as a personal
shortcut, but there is still no public URL scheme for starting a WhatsApp
voice call directly.

## Why the laptop is required for PC agents

The phone app is the control surface. PC/file/terminal/media agents execute on
the paired laptop through the same FastAPI server. When the laptop is offline,
phone-only agents (call agents, panel, contacts) still work, but PC actions
return a connection error.
