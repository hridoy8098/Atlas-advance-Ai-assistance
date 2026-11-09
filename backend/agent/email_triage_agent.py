# backend/agent/email_triage_agent.py — Email Triage Agent
# Real IMAP fetch + AI classification. Drafts are saved for approval; nothing is auto-sent.
from __future__ import annotations

import email
import imaplib
import os
import re
import ssl
from datetime import datetime
from email.header import decode_header
from email.message import Message
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import config
from .advanced_common import (
    ask,
    ask_json,
    clean_text,
    data_file,
    fail,
    ok,
    read_json,
    truncate,
    write_json,
)

STATE_FILE = data_file("email_triage.json")
DRAFT_FILE = data_file("email_drafts.json")

_URGENT = ("urgent", "asap", "immediately", "deadline", "today", "now", "জরুরি", "দ্রুত", "আজই")
_BILLING = ("invoice", "payment", "bill", "receipt", "ইনভয়েস", "বিল", "পেমেন্ট")
_MEETING = ("meeting", "schedule", "calendar", "zoom", "মিটিং", "অ্যাপয়েন্টমেন্ট")
_SPAM = ("unsubscribe", "promotion", "offer", "discount", "sale", "win", "lottery")


class EmailTriageAgent:
    name = "Email Triage Agent"

    def get_capabilities(self) -> List[str]:
        return ["email_inbox", "email_triage", "email_draft", "email_analyze", "email_status"]

    def handle(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        entities = entities or {}
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()
        lower = command.lower()

        try:
            if "setup" in intent_lower or "status" in intent_lower or "configure" in lower:
                return self.status()
            if "draft" in intent_lower or "reply" in lower:
                return self.draft_reply(str(entities.get("context") or command), str(entities.get("tone") or "professional"))
            if "analyze" in intent_lower and (entities.get("path") or entities.get("file")):
                path = Path(str(entities.get("path") or entities.get("file"))).expanduser()
                return self.analyze_file(path)
            limit = int(entities.get("limit") or 10)
            return self.triage(limit=max(1, min(limit, 25)), create_drafts=("draft" in lower or "reply" in lower))
        except Exception as exc:
            return fail("email_triage", f"Email Agent error: {exc}")

    # ---------------- triage ----------------
    def triage(self, limit: int = 10, create_drafts: bool = False) -> Dict[str, Any]:
        credentials = self._credentials()
        if not credentials:
            return fail(
                "email_triage",
                "Email inbox connect করা যায়নি — IMAP credentials নেই।",
                setup={
                    "env": [
                        "ATLAS_IMAP_HOST=imap.gmail.com",
                        "ATLAS_IMAP_USER=you@gmail.com",
                        "ATLAS_IMAP_PASS=your-app-password  (Gmail App Password)",
                    ],
                    "note": "Gmail-এ 2FA থাকলে App Password তৈরি করুন। Password কোথাও log হয় না।",
                },
                message_bn="Credentials ছাড়া শুধু .eml file analyze করা যাবে।",
            )

        messages, error = self._fetch_messages(credentials, limit)
        if error:
            return fail("email_triage", f"Inbox fetch failed: {error}", setup_hint="IMAP host/port/app-password যাচাই করুন।")
        if not messages:
            return ok("email_triage", "📭 নতুন email নেই।", emails=[], count=0)

        classified = self._classify(messages, create_drafts=create_drafts)
        state = read_json(STATE_FILE, {"history": []})
        state.setdefault("history", []).append({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "count": len(classified),
            "urgent": sum(1 for item in classified if item.get("urgency") == "urgent"),
        })
        state["history"] = state["history"][-30:]
        write_json(STATE_FILE, state)

        urgent_count = sum(1 for item in classified if item.get("urgency") == "urgent")
        return ok(
            "email_triage",
            f"📬 {len(classified)} email triaged — {urgent_count} urgent.",
            count=len(classified),
            urgent=urgent_count,
            emails=classified,
            drafts_saved=create_drafts,
            note="কোনো email পাঠানো হয়নি; drafts approval-এর জন্য saved।",
        )

    def _fetch_messages(self, credentials: Dict[str, Any], limit: int) -> Tuple[List[Dict[str, Any]], str]:
        host = credentials["host"]
        port = credentials["port"]
        use_ssl = credentials["ssl"]
        try:
            if use_ssl:
                connection = imaplib.IMAP4_SSL(host, port, ssl_context=ssl.create_default_context())
            else:
                connection = imaplib.IMAP4(host, port)
            connection.login(credentials["user"], credentials["password"])
            connection.select(credentials.get("folder") or "INBOX", readonly=True)
            status, data = connection.search(None, "UNSEEN")
            ids = (data[0] or b"").split()
            if not ids:
                status, data = connection.search(None, "ALL")
                ids = (data[0] or b"").split()
            ids = ids[-limit:][::-1]

            messages = []
            for message_id in ids:
                status, payload = connection.fetch(message_id, "(RFC822)")
                if status != "OK" or not payload:
                    continue
                raw = payload[0][1]
                parsed = email.message_from_bytes(raw)
                messages.append(self._parse_message(parsed, message_id.decode(errors="ignore")))
            connection.logout()
            return messages, ""
        except Exception as exc:
            return [], f"{type(exc).__name__}: {exc}"

    def _classify(self, messages: List[Dict[str, Any]], create_drafts: bool = False) -> List[Dict[str, Any]]:
        summaries = [
            {
                "index": index,
                "from": message.get("from", ""),
                "subject": message.get("subject", ""),
                "body": truncate(message.get("body", ""), 1400),
            }
            for index, message in enumerate(messages)
        ]
        data = ask_json(
            "Classify these emails. Reply JSON only: "
            '{"emails":[{"index":0,"urgency":"urgent|normal|low","category":"work|personal|billing|meeting|promotion|other",'
            '"summary":"one line","needs_reply":true,"draft_reply":""}]}\n\n'
            + "\n\n".join(
                f"[{item['index']}] From: {item['from']}\nSubject: {item['subject']}\nBody: {item['body']}"
                for item in summaries
            ),
            system_prompt="You triage email. Be strict about urgency. JSON only.",
            fallback=None,
        )
        classified_map = {}
        if isinstance(data, dict) and isinstance(data.get("emails"), list):
            for item in data["emails"]:
                try:
                    classified_map[int(item.get("index"))] = item
                except Exception:
                    continue

        results = []
        drafts = []
        for index, message in enumerate(messages):
            info = classified_map.get(index) or self._heuristic(message)
            result = {
                **message,
                "urgency": str(info.get("urgency") or "normal").lower(),
                "category": str(info.get("category") or "other").lower(),
                "summary": clean_text(info.get("summary") or message.get("subject") or ""),
                "needs_reply": bool(info.get("needs_reply")),
            }
            if create_drafts and result["needs_reply"]:
                draft = clean_text(info.get("draft_reply") or "") or self._draft_for(result)
                result["draft_reply"] = draft
                drafts.append({
                    "to": result.get("from"),
                    "subject": "Re: " + (result.get("subject") or ""),
                    "body": draft,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                })
            results.append(result)

        if drafts:
            stored = read_json(DRAFT_FILE, {"drafts": []})
            stored.setdefault("drafts", []).extend(drafts)
            stored["drafts"] = stored["drafts"][-100:]
            write_json(DRAFT_FILE, stored)
        return results

    def draft_reply(self, context: str, tone: str = "professional") -> Dict[str, Any]:
        if not clean_text(context):
            return fail("email_triage", "Draft-এর জন্য email content/context দিন।")
        draft = ask(
            f"Write a {tone} email reply.\nContext:\n{context}\n\n"
            "Return only the email body. Do not invent commitments, prices, or dates.",
            system_prompt="You draft careful business emails. Reply in the sender's language.",
        )
        if not draft:
            return fail("email_triage", "Draft তৈরি করা যায়নি (AI unavailable)।")
        stored = read_json(DRAFT_FILE, {"drafts": []})
        entry = {"subject": "", "body": draft, "tone": tone, "created_at": datetime.now().isoformat(timespec="seconds")}
        stored.setdefault("drafts", []).append(entry)
        stored["drafts"] = stored["drafts"][-100:]
        write_json(DRAFT_FILE, stored)
        return ok("email_triage", "✍️ Draft saved for approval.", draft=draft, drafts_file=str(DRAFT_FILE))

    def analyze_file(self, path: Path) -> Dict[str, Any]:
        if not path.exists() or not path.is_file():
            return fail("email_triage", f"File পাওয়া যায়নি: {path}")
        try:
            raw = path.read_bytes()
            parsed = email.message_from_bytes(raw)
            message = self._parse_message(parsed, "file")
            results = self._classify([message], create_drafts=False)
            return ok("email_triage", "📧 Email analyzed.", email=results[0] if results else message)
        except Exception as exc:
            return fail("email_triage", f".eml analyze failed: {exc}")

    def status(self) -> Dict[str, Any]:
        credentials = self._credentials()
        state = read_json(STATE_FILE, {"history": []})
        drafts = read_json(DRAFT_FILE, {"drafts": []}).get("drafts") or []
        return ok(
            "email_triage",
            "📬 Email agent configured." if credentials else "⚙️ Email agent needs IMAP credentials.",
            configured=bool(credentials),
            host=(credentials or {}).get("host", ""),
            user=(credentials or {}).get("user", ""),
            last_runs=(state.get("history") or [])[-5:],
            pending_drafts=len(drafts),
            setup_env=[
                "ATLAS_IMAP_HOST", "ATLAS_IMAP_USER", "ATLAS_IMAP_PASS",
                "ATLAS_IMAP_PORT (optional)", "ATLAS_IMAP_FOLDER (optional)",
            ],
            note="Drafts are never sent automatically.",
        )

    # ---------------- parsing helpers ----------------
    def _parse_message(self, message: Message, message_id: str) -> Dict[str, Any]:
        subject = self._decode(message.get("Subject", ""))
        sender = self._decode(message.get("From", ""))
        date = message.get("Date", "")
        body = self._body_text(message)
        return {
            "id": message_id,
            "from": sender,
            "subject": subject,
            "date": date,
            "body": truncate(body, 5000),
        }

    @staticmethod
    def _decode(value: str) -> str:
        try:
            parts = decode_header(value or "")
            out = ""
            for part, encoding in parts:
                if isinstance(part, bytes):
                    out += part.decode(encoding or "utf-8", errors="ignore")
                else:
                    out += part
            return clean_text(out)
        except Exception:
            return clean_text(value)

    @staticmethod
    def _body_text(message: Message) -> str:
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition") or "")
                if "attachment" in disposition.lower():
                    continue
                if content_type == "text/plain":
                    try:
                        return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                    except Exception:
                        continue
            for part in message.walk():
                if part.get_content_type() == "text/html":
                    try:
                        raw = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                        return re.sub(r"<[^>]+>", " ", raw)
                    except Exception:
                        continue
            return ""
        try:
            return message.get_payload(decode=True).decode(message.get_content_charset() or "utf-8", errors="ignore")
        except Exception:
            return str(message.get_payload() or "")

    @staticmethod
    def _heuristic(message: Dict[str, Any]) -> Dict[str, Any]:
        text = f"{message.get('subject', '')} {message.get('body', '')}".lower()
        urgency = "urgent" if any(word in text for word in _URGENT) else "normal"
        if any(word in text for word in _SPAM):
            category = "promotion"
        elif any(word in text for word in _MEETING):
            category = "meeting"
        elif any(word in text for word in _BILLING):
            category = "billing"
        else:
            category = "other"
        needs_reply = urgency == "urgent" or category in ("meeting", "billing") or "?" in text
        return {
            "urgency": urgency,
            "category": category,
            "summary": truncate(message.get("subject") or "Email", 160),
            "needs_reply": needs_reply,
            "draft_reply": "",
        }

    @staticmethod
    def _draft_for(message: Dict[str, Any]) -> str:
        sender = (message.get("from") or "").split("<")[0].strip() or "there"
        return (
            f"Hello {sender},\n\nThank you for your email. I have received your message and will review it. "
            "I will get back to you with a proper response soon.\n\nBest regards,\nAtlas"
        )

    @staticmethod
    def _credentials() -> Optional[Dict[str, Any]]:
        host = os.getenv("ATLAS_IMAP_HOST") or os.getenv("EMAIL_HOST") or os.getenv("IMAP_HOST")
        user = os.getenv("ATLAS_IMAP_USER") or os.getenv("EMAIL_USER") or os.getenv("IMAP_USER") or os.getenv("GMAIL_USER")
        password = os.getenv("ATLAS_IMAP_PASS") or os.getenv("EMAIL_PASS") or os.getenv("IMAP_PASS") or os.getenv("GMAIL_APP_PASSWORD")
        if not (host and user and password):
            config_file = read_json(config.DATA_DIR / "imap.json", {})
            if isinstance(config_file, dict) and config_file.get("host") and config_file.get("user") and config_file.get("password"):
                host = config_file["host"]
                user = config_file["user"]
                password = config_file["password"]
        if not (host and user and password):
            return None
        return {
            "host": host,
            "port": int(os.getenv("ATLAS_IMAP_PORT", "993")),
            "user": user,
            "password": password,
            "folder": os.getenv("ATLAS_IMAP_FOLDER", "INBOX"),
            "ssl": os.getenv("ATLAS_IMAP_SSL", "1") not in ("0", "false", "False"),
        }

    def test(self) -> Dict[str, Any]:
        status = self.status()
        return {
            "success": True,
            "agent": "email_triage",
            "configured": status.get("configured"),
            "pending_drafts": status.get("pending_drafts"),
            "message": status.get("message"),
        }


email_triage_agent = EmailTriageAgent()
