# backend/agent/coding_agent.py — Coding Copilot Agent
# Read-only repo analysis by default. File edits require explicit apply=true.
from __future__ import annotations

import ast
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import config
from .advanced_common import (
    ask,
    clean_text,
    data_file,
    extract_after,
    fail,
    find_existing_path,
    human_bytes,
    now_iso,
    ok,
    resolve_path,
    slugify,
    truncate,
    write_json,
)

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".gradle", ".idea", ".next", "site-packages", "android", "ios",
}
TEXT_EXT = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".cs", ".go", ".rs",
    ".c", ".h", ".cpp", ".hpp", ".html", ".css", ".scss", ".json", ".yml",
    ".yaml", ".toml", ".ini", ".md", ".txt", ".sh", ".ps1", ".bat", ".sql",
}
SECRET_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"][^'\"]{12,}"), "hardcoded API key/token"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key in source"),
    (re.compile(r"(?i)password\s*[:=]\s*['\"][^'\"]{6,}"), "hardcoded password"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "OpenAI-style secret key"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"), "GitHub token"),
]
DANGEROUS_PATTERNS = [
    (re.compile(r"\beval\s*\("), "eval() on untrusted input"),
    (re.compile(r"\bexec\s*\("), "exec() on untrusted input"),
    (re.compile(r"pickle\.loads?\s*\("), "unsafe pickle deserialization"),
    (re.compile(r"os\.system\s*\("), "os.system shell call"),
    (re.compile(r"subprocess\.(?:Popen|run|call)\s*\([^)]*shell\s*=\s*True"), "shell=True subprocess"),
]


class CodingAgent:
    name = "Coding Copilot Agent"

    def get_capabilities(self) -> List[str]:
        return [
            "coding_review", "coding_scan", "coding_explain", "coding_fix",
            "coding_test", "repo_summary",
        ]

    # ---------------- command router ----------------
    def handle(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        entities = entities or {}
        intent_lower = str(intent or "").lower()
        command = str(entities.get("_command", ""))
        path = self._resolve_target(command, entities)

        try:
            if "test" in intent_lower or re.search(r"\b(run|chalao|cholao)\b.*\btest", command, re.I):
                return self.run_tests(path, entities)
            if any(word in intent_lower for word in ("fix", "patch", "repair")):
                issue = str(entities.get("issue") or extract_after(command, ["bug", "fix", "problem", "issue"]))
                return self.propose_fix(path, issue, entities)
            if "explain" in intent_lower or "explain" in command.lower():
                question = str(entities.get("question") or extract_after(command, ["explain", "ব্যাখ্যা"]))
                return self.explain_file(path, question)
            if "summary" in intent_lower or "summarize" in command.lower():
                return self.review(path, summarize=True)
            return self.review(path)
        except Exception as exc:
            return fail("coding", f"Coding Agent error: {exc}")

    # ---------------- actions ----------------
    def review(self, target: Path | None, summarize: bool = False) -> Dict[str, Any]:
        if target is None or not target.exists():
            return fail(
                "coding",
                "কোন file/folder পেলাম না। উদাহরণ: “code review backend/agent/pc_agent.py”।",
                hint="Path দিন, অথবা entity path ব্যবহার করুন।",
            )

        started = datetime.now()
        files: List[Path] = []
        if target.is_file():
            files = [target]
        else:
            for dirpath, dirnames, filenames in os.walk(target):
                dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
                for filename in filenames:
                    if Path(filename).suffix.lower() in TEXT_EXT:
                        files.append(Path(dirpath) / filename)
                        if len(files) >= 500:
                            break
                if len(files) >= 500:
                    break

        issues: List[Dict[str, str]] = []
        extension_counts: Dict[str, int] = {}
        total_bytes = 0
        syntax_errors = 0

        for file_path in files:
            suffix = file_path.suffix.lower() or "(none)"
            extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
            try:
                total_bytes += file_path.stat().st_size
            except Exception:
                continue

            if file_path.suffix.lower() not in TEXT_EXT:
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")[:250_000]
            except Exception:
                continue

            rel = self._relative(file_path, target)
            for line_no, line in enumerate(text.splitlines(), 1):
                upper = line.upper()
                if "TODO" in upper or "FIXME" in upper or "HACK" in upper:
                    issues.append({"file": rel, "line": str(line_no), "type": "todo", "detail": truncate(line.strip(), 160)})

            for pattern, label in SECRET_PATTERNS:
                if pattern.search(text):
                    issues.append({"file": rel, "line": "-", "type": "secret", "detail": label})
            for pattern, label in DANGEROUS_PATTERNS:
                if pattern.search(text):
                    issues.append({"file": rel, "line": "-", "type": "risk", "detail": label})

            if file_path.suffix.lower() == ".py":
                try:
                    ast.parse(text)
                except SyntaxError as exc:
                    syntax_errors += 1
                    issues.append({
                        "file": rel,
                        "line": str(exc.lineno or "?"),
                        "type": "syntax",
                        "detail": truncate(exc.msg, 160),
                    })

        issues = issues[:80]
        summary = self._summary_text(target, len(files), total_bytes, issues, extension_counts)
        ai_summary = ""
        if summarize and files:
            ai_summary = ask(
                "Review this repository snapshot and give the top 5 concrete improvements.\n"
                f"Target: {target}\nFiles: {len(files)}\nIssues:\n"
                + "\n".join(f"- {i['file']}:{i['line']} [{i['type']}] {i['detail']}" for i in issues[:30]),
                system_prompt="You are a senior software engineer. Be concise and practical.",
            )

        payload = {
            "target": str(target),
            "files_scanned": len(files),
            "total_size": human_bytes(total_bytes),
            "extensions": dict(sorted(extension_counts.items(), key=lambda kv: kv[1], reverse=True)[:12]),
            "issue_count": len(issues),
            "syntax_errors": syntax_errors,
            "issues": issues,
            "duration_ms": int((datetime.now() - started).total_seconds() * 1000),
            "summary": summary,
        }
        if ai_summary:
            payload["ai_review"] = ai_summary
        return ok("coding", summary, **payload)

    def explain_file(self, target: Path | None, question: str = "") -> Dict[str, Any]:
        if target is None or not target.exists() or not target.is_file():
            return fail("coding", "Explanation-এর জন্য একটি file path দিন।")
        try:
            text = target.read_text(encoding="utf-8", errors="ignore")[:120_000]
        except Exception as exc:
            return fail("coding", f"File পড়া যায়নি: {exc}")

        prompt = (
            f"Explain this file clearly for a developer.\nFile: {target}\n"
            f"Question: {question or 'What does it do, and what are the risks?'}\n\n{text}"
        )
        explanation = ask(prompt, system_prompt="You explain code precisely with examples. Reply in the user's language.")
        if not explanation:
            lines = text.count("\n") + 1
            imports = re.findall(r"^\s*(?:import|from)\s+([\w.]+)", text, flags=re.M)[:20]
            explanation = f"AI explanation unavailable. The file has {lines} lines. Imports: {', '.join(imports) or 'none'}."
        return ok("coding", f"📘 {target.name} explained.", path=str(target), explanation=explanation, size=human_bytes(len(text.encode('utf-8', errors='ignore'))))

    def propose_fix(self, target: Path | None, issue: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        if target is None or not target.exists() or not target.is_file():
            return fail("coding", "Fix-এর জন্য একটি file path দিন।")
        if target.stat().st_size > 300_000:
            return fail("coding", "File অনেক বড় (300KB+)। ছোট file বা নির্দিষ্ট snippet দিন।")

        original = target.read_text(encoding="utf-8", errors="ignore")
        prompt = (
            f"Fix the described issue in this file.\nIssue: {issue or 'find and fix the main bug'}\n"
            f"File: {target}\nReturn ONLY the complete corrected file between <FILE> and </FILE>.\n\n{original}"
        )
        response = ask(prompt, system_prompt="You are a careful senior engineer. Preserve unrelated behavior.")
        corrected = ""
        match = re.search(r"<FILE>\s*(.*?)\s*</FILE>", response or "", flags=re.S)
        if match:
            corrected = match.group(1)

        patch_dir = data_file("coding/pending")
        patch_dir.mkdir(parents=True, exist_ok=True)
        patch_path = patch_dir / f"{slugify(target.stem)}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        patch_path.write_text(
            f"# Coding patch proposal\n\nFile: {target}\nIssue: {issue or '(general)'}\n\n"
            f"## AI response\n\n{response or '(no response)'}\n\n"
            + (f"## Proposed file content\n\n```\n{corrected}\n```\n" if corrected else ""),
            encoding="utf-8",
        )

        apply = bool(entities.get("apply") or entities.get("confirm"))
        if apply and corrected:
            backup = data_file(f"coding/backups/{target.name}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak")
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
            target.write_text(corrected, encoding="utf-8")
            return ok(
                "coding",
                f"✅ Patch applied to {target.name}. Backup: {backup}",
                applied=True,
                file=str(target),
                backup=str(backup),
                patch_report=str(patch_path),
            )

        return ok(
            "coding",
            "🧪 Patch proposal তৈরি হয়েছে; এখনো apply হয়নি। apply=true দিলে backup সহ লেখা হবে।",
            applied=False,
            file=str(target),
            patch_report=str(patch_path),
            proposal=truncate(response or "", 2500),
        )

    def run_tests(self, target: Path | None, entities: Dict[str, Any]) -> Dict[str, Any]:
        root = target if target and target.is_dir() else (target.parent if target and target.exists() else config.BASE_DIR)
        command = str(entities.get("command") or "").strip()

        if not command:
            if (root / "package.json").exists():
                command = "npm test -- --runInBand"
            elif (root / "pytest.ini").exists() or (root / "tests").exists() or list(root.glob("test_*.py")):
                command = f'"{sys.executable}" -m pytest -q'
            else:
                return fail("coding", f"{root}-এ test setup পাওয়া যায়নি। command entity দিয়ে নির্দিষ্ট test command দিন।")

        try:
            started = datetime.now()
            completed = subprocess.run(
                command,
                shell=True,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=180,
            )
            duration = int((datetime.now() - started).total_seconds() * 1000)
            output = (completed.stdout or completed.stderr or "").strip()
            return {
                "success": completed.returncode == 0,
                "agent": "coding",
                "message": ("✅ Tests passed." if completed.returncode == 0 else f"❌ Tests failed (exit {completed.returncode})."),
                "command": command,
                "cwd": str(root),
                "exit_code": completed.returncode,
                "output": truncate(output, 6000),
                "duration_ms": duration,
            }
        except subprocess.TimeoutExpired:
            return fail("coding", "Test command 180s-এ শেষ হয়নি (timeout)।")
        except Exception as exc:
            return fail("coding", f"Test চালানো যায়নি: {exc}")

    def test(self) -> Dict[str, Any]:
        return {
            "success": True,
            "agent": "coding",
            "python": sys.version.split()[0],
            "git": bool(shutil.which("git")),
            "pytest": bool(importlib.util.find_spec("pytest")),
            "default_root": str(config.BASE_DIR),
            "message": "Coding Copilot ready (read-only review by default).",
        }

    # ---------------- helpers ----------------
    @staticmethod
    def _resolve_target(command: str, entities: Dict[str, Any]) -> Path | None:
        raw = entities.get("path") or entities.get("repo") or entities.get("file")
        if raw:
            return resolve_path(raw)
        found = find_existing_path(command)
        if found:
            return found
        quoted = re.search(r"[\"“”']([^\"“”']{2,})[\"“”']", command)
        if quoted:
            return resolve_path(quoted.group(1))
        return None

    @staticmethod
    def _relative(file_path: Path, target: Path) -> str:
        try:
            return str(file_path.relative_to(target)) if target.is_dir() else file_path.name
        except Exception:
            return str(file_path)

    @staticmethod
    def _summary_text(target: Path, files: int, total_bytes: int, issues: List[Dict[str, str]], extensions: Dict[str, int]) -> str:
        kind = "folder" if target.is_dir() else "file"
        top_ext = ", ".join(f"{ext} ({count})" for ext, count in sorted(extensions.items(), key=lambda kv: kv[1], reverse=True)[:5])
        return (
            f"🔎 {kind} scan: {files} files, {human_bytes(total_bytes)}. "
            f"Top types: {top_ext or 'none'}. "
            f"Found {len(issues)} issue(s)."
        )


coding_agent = CodingAgent()
