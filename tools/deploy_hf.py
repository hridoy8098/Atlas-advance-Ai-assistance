"""Deploy Atlas 7.0 to a Hugging Face Docker Space.

The Space is built from the files tracked by Git, so nothing that is ignored
(`.env`, `data/` databases, build output, APKs) ever leaves your machine.

Usage (PowerShell):

    $env:HF_TOKEN = "hf_..."
    python tools/deploy_hf.py --space atlas-7

The script prints the PIN and the connector pairing token at the end. Keep them
somewhere safe: the Space only stores their values, not a copy you can read back.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FRONT_MATTER = """---
title: Atlas 7.0
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

"""

# These must never be uploaded to a public Space.
FORBIDDEN = re.compile(
    r"(^|/)(\.env($|\.)|node_modules|\.git|\.venv|venv)(/|$)"
    r"|^data/(?!\.gitkeep$)"
    r"|^logs/(?!\.gitkeep$)"
    r"|(^|/)local\.properties$"
    r"|\.(db|db-shm|db-wal|sqlite|sqlite3|apk|aab|jks|keystore|p12)$",
    re.IGNORECASE,
)

# Copied from .env to Space secrets. Anything not listed here stays local.
SECRET_KEYS = [
    "GEMINI_API_KEY",
    "GEMINI_API_KEY_2",
    "GEMINI_API_KEY_3",
    "GROQ_KEY_1", "GROQ_KEY_2", "GROQ_KEY_3", "GROQ_KEY_4", "GROQ_KEY_5",
    "GROQ_KEY_6", "GROQ_KEY_7", "GROQ_KEY_8", "GROQ_KEY_9", "GROQ_KEY_10",
    "WEATHER_API_KEY", "VIRUSTOTAL_API_KEY", "HIBP_API_KEY", "NEWS_API_KEY",
    "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER",
    "ATLAS_IMAP_HOST", "ATLAS_IMAP_USER", "ATLAS_IMAP_PASS", "ATLAS_IMAP_PORT",
    "ATLAS_IMAP_FOLDER", "ATLAS_IMAP_SSL", "AI_PRIMARY", "USER_NAME",
]


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            values[key] = value
    return values


def tracked_files() -> list[str]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    files = [name for name in output.decode("utf-8").split("\0") if name]
    if not files:
        raise SystemExit("git ls-files returned nothing; run this from the project root.")
    return files


def stage_project() -> Path:
    staging = Path(tempfile.mkdtemp(prefix="atlas-hf-space-")) / "space"
    staging.mkdir(parents=True)
    bad: list[str] = []
    copied = 0

    for relative in tracked_files():
        if FORBIDDEN.search(relative.replace("\\", "/")):
            bad.append(relative)
            continue
        source = ROOT / relative
        if not source.exists():
            continue
        destination = staging / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1

    if bad:
        raise SystemExit("Refusing to upload forbidden files:\n  " + "\n  ".join(bad))

    readme = staging / "README.md"
    text = readme.read_text(encoding="utf-8")
    if not text.startswith("---"):
        readme.write_text(FRONT_MATTER + text, encoding="utf-8")

    print(f"staged {copied} files in {staging}")
    return staging


def wait_for_space(api, repo_id: str, url: str, minutes: int = 30) -> bool:
    deadline = time.time() + minutes * 60
    last_stage = ""
    while time.time() < deadline:
        try:
            runtime = api.get_space_runtime(repo_id)
            stage = str(runtime.stage)
        except Exception as error:
            stage = f"query failed: {error}"
        if stage != last_stage:
            print(f"  space stage: {stage}")
            last_stage = stage
        if stage.lower().endswith("running"):
            break
        if stage.lower().endswith(("build_error", "runtime_error", "stopped")):
            print("  build/runtime error; opening the Space page for logs is recommended")
            return False
        time.sleep(20)

    health_url = f"{url}/api/health"
    for _ in range(30):
        try:
            with urllib.request.urlopen(health_url, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("status") == "ok":
                print(f"  health: {payload}")
                return True
        except Exception:
            pass
        time.sleep(10)
    print(f"  health check did not pass yet: {health_url}")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy Atlas to a Hugging Face Docker Space")
    parser.add_argument("--space", default="atlas-7", help="Space name (default: atlas-7)")
    parser.add_argument("--user", default="", help="HF username (default: from the token)")
    parser.add_argument("--private", action="store_true", help="Private Space (paid accounts)")
    parser.add_argument("--no-wait", action="store_true", help="Do not poll the build")
    parser.add_argument("--secrets-only", action="store_true", help="Only update secrets")
    parser.add_argument("--pin", default="", help="6-digit login PIN (default: reuse or generate)")
    parser.add_argument("--pair-token", default="", help="Connector pair token (default: reuse or generate)")
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set HF_TOKEN first (a Hugging Face write token).")

    try:
        from huggingface_hub import HfApi
    except ImportError:
        raise SystemExit("pip install huggingface_hub")

    api = HfApi(token=token)
    user = args.user or api.whoami().get("name", "")
    if not user:
        raise SystemExit("Could not determine the Hugging Face user.")
    repo_id = f"{user}/{args.space}"
    url = f"https://{user}-{args.space}.hf.space".replace("_", "-")

    print(f"target: {repo_id}")
    try:
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            private=args.private,
            exist_ok=True,
        )
    except Exception as error:
        text = str(error)
        if "402" in text or "Payment Required" in text:
            raise SystemExit(
                "Hugging Face now requires a PRO subscription to create Docker or Gradio\n"
                "Spaces on free cpu-basic (Static Spaces are still free, but Atlas needs\n"
                "a Python server).\n\n"
                "Options:\n"
                "  1. Upgrade the account at https://huggingface.co/pro and rerun this script.\n"
                "  2. Use a free Cloudflare quick tunnel or a small VPS instead; see the\n"
                "     'Deploy to Hugging Face Spaces' section in README.md."
            )
        raise

    if not args.secrets_only:
        staging = stage_project()
        print("uploading files...")
        api.upload_folder(
            folder_path=str(staging),
            repo_id=repo_id,
            repo_type="space",
            commit_message="Deploy Atlas 7.0",
        )

    env = read_env(ROOT / ".env")
    credentials = Path(tempfile.gettempdir()) / "atlas_hf_credentials.txt"
    previous = credentials.read_text(encoding="utf-8") if credentials.exists() else ""
    previous_pin = previous_pair = ""
    if f"Space: {url}" in previous:
        for line in previous.splitlines():
            if line.startswith("PIN: "):
                previous_pin = line[5:].strip()
            elif line.startswith("Pair token: "):
                previous_pair = line[12:].strip()

    pin = args.pin or previous_pin
    if not pin:
        pin = "".join(str(secrets.randbelow(10)) for _ in range(6))
        if pin in ("000000", "123456"):
            pin = "7" + pin[1:]
    if len(pin) != 6 or not pin.isdigit():
        raise SystemExit("The PIN must be exactly 6 digits.")

    pair_token = args.pair_token or previous_pair or secrets.token_hex(24)

    print("setting secrets...")
    for key in SECRET_KEYS:
        if key in env:
            api.add_space_secret(repo_id=repo_id, key=key, value=env[key])

    api.add_space_secret(repo_id=repo_id, key="AUTH_PIN", value=pin)
    api.add_space_secret(repo_id=repo_id, key="ATLAS_PAIR_TOKEN", value=pair_token)
    api.add_space_secret(repo_id=repo_id, key="ATLAS_CLOUD", value="1")
    api.add_space_secret(repo_id=repo_id, key="ATLAS_VOICE_AUTOSTART", value="0")

    credentials = Path(tempfile.gettempdir()) / "atlas_hf_credentials.txt"
    credentials.write_text(
        f"Space: {url}\nPIN: {pin}\nPair token: {pair_token}\n",
        encoding="utf-8",
    )
    print()
    print("=" * 58)
    print(f"Space URL : {url}")
    print(f"Login PIN : {pin}")
    print(f"Pair token: {pair_token}")
    print(f"Saved to  : {credentials}")
    print("=" * 58)

    if not args.no_wait:
        print("waiting for the first build (this can take 5-20 minutes)...")
        ok = wait_for_space(api, repo_id, url)
        print("deploy finished" if ok else "deploy started, but the health check is not green yet")


if __name__ == "__main__":
    main()
