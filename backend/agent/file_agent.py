# backend/agent/file_agent.py — safe, scoped file operations.
#
# All paths are resolved under the user's home or the Atlas project directory.
# Searches never crawl system folders, and deletions are reversible via the
# Recycle Bin when send2trash is available. Cloud runs ask for the laptop
# connector instead of touching the Render container's filesystem.

from __future__ import annotations

import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from .advanced_common import clean_text, find_existing_path, human_bytes, resolve_path
from .agent_i18n import tr
from .base_agent import BaseAgent

try:
    from send2trash import send2trash
except Exception:  # pragma: no cover
    send2trash = None

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "site-packages",
    "AppData", "Windows", "Program Files", "Program Files (x86)", "$Recycle.Bin",
}
LOCATIONS = {
    "downloads": ("Downloads", "download", "ডাউনলোড", "ডাউনলোডস"),
    "desktop": ("Desktop", "ডেস্কটপ"),
    "documents": ("Documents", "docs", "ডকুমেন্ট", "ডকুমেন্টস"),
    "pictures": ("Pictures", "photos", "images", "ছবি", "ফটো"),
    "music": ("Music", "গান", "মিউজিক"),
    "videos": ("Videos", "video", "ভিডিও"),
}


class FileAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="File Agent", description="Safe file search, listing, organizing and cleanup")
        self.home = Path.home()
        self.downloads = self.home / "Downloads"
        self.documents = self.home / "Documents"
        self.desktop = self.home / "Desktop"

    def get_capabilities(self) -> List[str]:
        return [
            "file_organize", "file_search", "file_create", "file_read", "file_delete",
            "file_copy", "file_move", "file_rename", "file_list", "file_info",
            "disk_usage", "file_cleanup",
        ]

    @staticmethod
    def _is_cloud() -> bool:
        return bool(getattr(config, "ATLAS_CLOUD", False))

    # ---------------- path safety ----------------
    def _roots(self) -> List[Path]:
        roots = [self.home / name for name in ("Downloads", "Documents", "Desktop", "Pictures", "Music", "Videos")]
        roots.append(Path(config.BASE_DIR))
        return [root for root in roots if root.exists()]

    def resolve(self, raw: str, must_exist: bool = False) -> Optional[Path]:
        value = clean_text(raw).strip("\"'")
        if not value:
            return None
        # Friendly folder names.
        key = value.lower()
        for name, aliases in LOCATIONS.items():
            if any(key == alias.lower() for alias in aliases):
                candidate = self.home / name
                return candidate if candidate.exists() or not must_exist else None
        candidate = resolve_path(value, base=self.home)
        if candidate is None:
            return None
        try:
            candidate = candidate.resolve()
        except Exception:
            return candidate
        allowed = [Path(root).resolve() for root in self._roots()]
        if not any(candidate == root or root in candidate.parents for root in allowed):
            # Explicit absolute paths outside the sandbox are allowed only when
            # the user typed them and they exist; otherwise refuse.
            if not (candidate.is_absolute() and candidate.exists()):
                return None
        if must_exist and not candidate.exists():
            return None
        return candidate

    def _location_name(self, text: str) -> str:
        lower = str(text or "").lower()
        for name, aliases in LOCATIONS.items():
            if any(alias.lower() in lower for alias in aliases):
                return name
        return "downloads"

    # ---------------- basics (legacy bool API kept) ----------------
    def create_file(self, path: str, content: str = "") -> bool:
        return bool(self._write_file(path, content, create=True).get("success"))

    def _write_file(self, path: str, content: str = "", create: bool = True) -> Dict[str, Any]:
        candidate = self.resolve(path, must_exist=not create)
        if candidate is None:
            # Bare name: put it in Documents with .txt.
            name = clean_text(path)
            if not name:
                return {"success": False, "error": "file path required"}
            if not Path(name).suffix:
                name += ".txt"
            candidate = self.documents / name
        if candidate.exists() and candidate.is_dir():
            return {"success": False, "error": "path is a folder"}
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_text(str(content or ""), encoding="utf-8")
            return {"success": True, "path": str(candidate), "size": candidate.stat().st_size}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def read_file(self, path: str, limit: int = 100_000) -> Optional[str]:
        candidate = self.resolve(path, must_exist=True)
        if not candidate or not candidate.is_file():
            return None
        try:
            return candidate.read_text(encoding="utf-8", errors="replace")[:limit]
        except Exception:
            return None

    def _trash(self, path: Path) -> Dict[str, Any]:
        try:
            if send2trash is not None:
                send2trash(str(path))
                return {"success": True, "method": "recycle_bin", "path": str(path)}
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            return {"success": True, "method": "permanent", "path": str(path)}
        except Exception as exc:
            return {"success": False, "error": str(exc), "path": str(path)}

    def delete_file(self, path: str) -> bool:
        return bool(self.delete_path(path).get("success"))

    def delete_path(self, path: str) -> Dict[str, Any]:
        candidate = self.resolve(path, must_exist=True)
        if candidate is None:
            return {"success": False, "error": "file not found or outside allowed folders", "path": path}
        if candidate in (self.home, Path(config.BASE_DIR)):
            return {"success": False, "error": "refusing to delete a root folder"}
        return self._trash(candidate)

    def copy_file(self, src: str, dst: str) -> bool:
        return bool(self._copy(src, dst).get("success"))

    def _copy(self, src: str, dst: str) -> Dict[str, Any]:
        source = self.resolve(src, must_exist=True)
        if source is None:
            return {"success": False, "error": f"source not found: {src}"}
        target = self.resolve(dst)
        if target is None:
            # Treat as a destination folder name under Documents.
            target = self.documents / clean_text(dst)
        if target and target.is_dir():
            target = target / source.name
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                shutil.copy2(source, target)
            return {"success": True, "source": str(source), "destination": str(target)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def move_file(self, src: str, dst: str) -> bool:
        return bool(self._move(src, dst).get("success"))

    def _move(self, src: str, dst: str) -> Dict[str, Any]:
        source = self.resolve(src, must_exist=True)
        if source is None:
            return {"success": False, "error": f"source not found: {src}"}
        target = self.resolve(dst)
        if target is None:
            target = self.documents / clean_text(dst)
        if target and target.is_dir():
            target = target / source.name
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            return {"success": True, "source": str(source), "destination": str(target)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def rename_file(self, path: str, new_name: str) -> bool:
        return bool(self._rename(path, new_name).get("success"))

    def _rename(self, path: str, new_name: str) -> Dict[str, Any]:
        source = self.resolve(path, must_exist=True)
        name = clean_text(new_name).strip("\"'")
        if source is None:
            return {"success": False, "error": f"file not found: {path}"}
        if not name:
            return {"success": False, "error": "new name required"}
        target = source.parent / Path(name).name
        try:
            source.rename(target)
            return {"success": True, "path": str(target)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def create_folder(self, path: str) -> bool:
        candidate = self.resolve(path)
        if candidate is None:
            return False
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    # ---------------- listing / search ----------------
    def list_folder(self, path: str = None) -> List[Dict]:
        folder = self.resolve(path or "Downloads")
        if folder is None or not folder.is_dir():
            return []
        items = []
        try:
            for item in sorted(folder.iterdir(), key=lambda entry: (entry.is_file(), entry.name.lower()))[:200]:
                try:
                    stat = item.stat()
                except Exception:
                    continue
                items.append({
                    "name": item.name,
                    "type": "folder" if item.is_dir() else "file",
                    "size": stat.st_size,
                    "size_human": human_bytes(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
        except Exception:
            return []
        return items

    def search_files(self, query: str, directory: str = None, limit: int = 30) -> List[str]:
        needle = clean_text(query).lower()
        if not needle:
            return []
        roots: List[Path] = []
        if directory:
            target = self.resolve(directory)
            if target and target.is_dir():
                roots = [target]
        if not roots:
            roots = [self.home / name for name in ("Downloads", "Documents", "Desktop", "Pictures")]
            roots.append(Path(config.BASE_DIR))
        roots = [root for root in roots if root.exists()]

        tokens = [token for token in needle.replace("_", " ").split() if token]
        results: List[str] = []
        for root in roots:
            for current, dirs, files in os.walk(root):
                dirs[:] = [name for name in dirs if name.lower() not in {item.lower() for item in SKIP_DIRS}]
                depth = len(Path(current).relative_to(root).parts)
                if depth >= 7:
                    dirs[:] = []
                for name in files + dirs:
                    lowered = name.lower()
                    if all(token in lowered for token in tokens):
                        results.append(str(Path(current) / name))
                        if len(results) >= limit:
                            return results
        return results

    # ---------------- disk / organize ----------------
    def get_disk_usage(self, path: str = "/") -> Dict:
        probe = self.resolve(path) if path and path not in ("/", "\\") else None
        target = str(probe or self.home)
        try:
            usage = shutil.disk_usage(target)
            return {
                "path": target,
                "total": human_bytes(usage.total),
                "used": human_bytes(usage.used),
                "free": human_bytes(usage.free),
                "percent": round(usage.used / usage.total * 100, 1),
            }
        except Exception:
            return {}

    def organize_downloads(self, location: str = "downloads") -> Dict[str, int]:
        folder = self.home / (location.title() if location in LOCATIONS else "Downloads")
        if not folder.exists():
            return {}
        categories = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".heic"],
            "Documents": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".md"],
            "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
            "Video": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Code": [".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".xml", ".java", ".cpp", ".sh"],
            "Installers": [".exe", ".msi", ".dmg", ".apk", ".deb"],
        }
        result: Dict[str, int] = {}
        for file in list(folder.iterdir()):
            if not file.is_file():
                continue
            category = next(
                (name for name, extensions in categories.items() if file.suffix.lower() in extensions),
                "Others",
            )
            destination = folder / category
            try:
                destination.mkdir(exist_ok=True)
                shutil.move(str(file), str(destination / file.name))
                result[category] = result.get(category, 0) + 1
            except Exception:
                continue
        return result

    def get_file_info(self, path: str) -> Optional[Dict]:
        candidate = self.resolve(path, must_exist=True)
        if candidate is None:
            return None
        try:
            stat = candidate.stat()
            return {
                "name": candidate.name,
                "path": str(candidate),
                "type": "folder" if candidate.is_dir() else "file",
                "size": stat.st_size,
                "size_human": human_bytes(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(timespec="seconds"),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            }
        except Exception:
            return None

    # ---------------- dispatch ----------------
    def handle(self, intent: str, entities: Dict = None) -> Dict:
        entities = dict(entities or {})
        intent_lower = str(intent or "").lower()
        command = str(entities.get("_command", ""))
        lower = command.lower()

        if self._is_cloud():
            return {"success": False, "action": "file_needs_connector", "agent": "file",
                    "needs_connector": True,
                    "message": tr(command,
                                  "📁 File operations run on your laptop, not the cloud server. "
                                  "Start the laptop connector, then ask again.",
                                  "📁 ফাইল কাজ আপনার ল্যাপটপে চলে, ক্লাউড সার্ভারে নয়। "
                                  "ল্যাপটপ connector চালু করে আবার বলুন।")}

        query = clean_text(entities.get("query") or entities.get("name") or "")
        path = str(entities.get("path") or entities.get("source") or "")
        destination = str(entities.get("destination") or entities.get("target") or "")
        location = str(entities.get("location") or self._location_name(command))

        if not path:
            found = find_existing_path(command, base=self.home)
            path = str(found) if found else ""
        if not query and "search" in intent_lower:
            query = path or clean_text(
                re.sub(r"^.*?\b(?:find|search|locate)\b\s*(?:for\s+)?(?:a\s+|the\s+)?(?:file|folder)?\s*", "", command, flags=re.I)
            )

        try:
            if "organize" in intent_lower or re.search(r"\b(?:organize|sort|tidy|arrange)\b|গোছাও|সাজাও", lower):
                counts = self.organize_downloads(location)
                total = sum(counts.values())
                detail = ", ".join(f"{name}: {count}" for name, count in counts.items()) or "nothing to move"
                return {"success": True, "action": "file_organize", "agent": "file",
                        "message": tr(command, f"📦 Organized {total} file(s) in {location} — {detail}.",
                                      f"📦 {location}-এ {total}টি ফাইল গোছানো হয়েছে — {detail}।"),
                        "counts": counts, "total": total}

            if "disk" in intent_lower or re.search(r"\b(?:disk|storage)\s*(?:usage|space|status)\b", lower):
                usage = self.get_disk_usage(path or str(self.home))
                if not usage:
                    return {"success": False, "action": "disk_usage", "agent": "file",
                            "message": tr(command, "Could not read disk usage.", "ডিস্ক ব্যবহার পড়া যায়নি।")}
                return {"success": True, "action": "disk_usage", "agent": "file",
                        "message": tr(command,
                                      f"💾 {usage['used']} of {usage['total']} used ({usage['percent']}%), {usage['free']} free.",
                                      f"💾 {usage['total']} এর মধ্যে {usage['used']} ব্যবহৃত ({usage['percent']}%), খালি {usage['free']}।"),
                        "data": usage}

            if "search" in intent_lower or "find" in intent_lower or re.search(r"\b(?:find|search|locate|where\s+is)\b", lower):
                needle = query or path
                directory = str(entities.get("directory") or "") or None
                if location and location != "downloads":
                    directory = directory or str(self.home / location.title())
                results = self.search_files(needle, directory=directory)
                if not results:
                    return {"success": False, "action": "file_search", "agent": "file",
                            "message": tr(command, f"🔎 No file found matching “{needle}”.",
                                          f"🔎 “{needle}” নামে কোনো ফাইল পাওয়া যায়নি।"),
                            "query": needle, "results": []}
                lines = "\n".join(f"• {item}" for item in results[:10])
                return {"success": True, "action": "file_search", "agent": "file",
                        "message": tr(command, f"🔎 {len(results)} file(s) found for “{needle}”:\n{lines}",
                                      f"🔎 “{needle}” এর {len(results)}টি ফাইল পাওয়া গেছে:\n{lines}"),
                        "query": needle, "results": results, "count": len(results)}

            if "list" in intent_lower or re.search(r"\b(?:list|show)\s+(?:the\s+)?(?:files|contents|folders)\b", lower):
                folder = path or location
                items = self.list_folder(folder)
                if not items:
                    return {"success": True, "action": "file_list", "agent": "file",
                            "message": tr(command, f"📁 {folder} is empty or unavailable.",
                                          f"📁 {folder} খালি বা পাওয়া যায়নি।"),
                            "path": folder, "items": []}
                lines_list = []
                for item in items[:15]:
                    suffix = "/" if item["type"] == "folder" else f" ({item['size_human']})"
                    lines_list.append(f"• {item['name']}{suffix}")
                lines = "\n".join(lines_list)
                return {"success": True, "action": "file_list", "agent": "file",
                        "message": tr(command, f"📁 {folder} — {len(items)} item(s):\n{lines}",
                                      f"📁 {folder} — {len(items)}টি আইটেম:\n{lines}"),
                        "path": folder, "items": items}

            if "create" in intent_lower or re.search(r"\b(?:create|make|new)\s+(?:a\s+)?(?:new\s+)?file\b", lower):
                if not path:
                    match = re.search(r"\b(?:create|make|new)\s+(?:a\s+)?(?:new\s+)?file\s+(.+)$", command, re.I)
                    path = match.group(1).strip() if match else ""
                result = self._write_file(path, str(entities.get("content") or ""), create=True)
                if not result.get("success"):
                    return {"success": False, "action": "file_create", "agent": "file",
                            "message": tr(command, f"Could not create file: {result.get('error')}",
                                          f"ফাইল তৈরি হয়নি: {result.get('error')}")}
                return {"success": True, "action": "file_create", "agent": "file",
                        "message": tr(command, f"📄 File created: {result['path']}",
                                      f"📄 ফাইল তৈরি: {result['path']}"),
                        "path": result["path"]}

            if "delete" in intent_lower or re.search(r"\b(?:delete|remove)\b.*\bfile\b", lower):
                if not path:
                    match = re.search(r"\b(?:delete|remove)\s+(?:the\s+)?file\s+(.+)$", command, re.I)
                    path = match.group(1).strip() if match else ""
                result = self.delete_path(path)
                if not result.get("success"):
                    return {"success": False, "action": "file_delete", "agent": "file",
                            "message": tr(command, f"Could not delete: {result.get('error')}",
                                          f"ডিলিট করা যায়নি: {result.get('error')}")}
                method = "Recycle Bin" if result.get("method") == "recycle_bin" else "permanently"
                return {"success": True, "action": "file_delete", "agent": "file",
                        "message": tr(command, f"🗑️ Deleted {result.get('path')} ({method}).",
                                      f"🗑️ {result.get('path')} ডিলিট হয়েছে ({method})।"),
                        **result}

            if "copy" in intent_lower:
                result = self._copy(path, destination)
                return {"success": bool(result.get("success")), "action": "file_copy", "agent": "file",
                        "message": tr(command, f"📋 Copied to {result.get('destination')}.",
                                      f"📋 কপি হয়েছে: {result.get('destination')}।") if result.get("success")
                        else tr(command, f"Copy failed: {result.get('error')}", f"কপি ব্যর্থ: {result.get('error')}"),
                        **result}

            if "move" in intent_lower:
                result = self._move(path, destination)
                return {"success": bool(result.get("success")), "action": "file_move", "agent": "file",
                        "message": tr(command, f"📦 Moved to {result.get('destination')}.",
                                      f"📦 সরানো হয়েছে: {result.get('destination')}।") if result.get("success")
                        else tr(command, f"Move failed: {result.get('error')}", f"মুভ ব্যর্থ: {result.get('error')}"),
                        **result}

            if "rename" in intent_lower:
                new_name = str(entities.get("new_name") or "")
                if not new_name:
                    match = re.search(r"\brename\s+(?:the\s+)?file\s+.+?\s+(?:to|as)\s+(.+)$", command, re.I)
                    new_name = match.group(1).strip() if match else ""
                result = self._rename(path, new_name)
                return {"success": bool(result.get("success")), "action": "file_rename", "agent": "file",
                        "message": tr(command, f"✏️ Renamed to {Path(result.get('path', '')).name}.",
                                      f"✏️ নতুন নাম: {Path(result.get('path', '')).name}।") if result.get("success")
                        else tr(command, f"Rename failed: {result.get('error')}", f"নাম বদলানো ব্যর্থ: {result.get('error')}"),
                        **result}

            if "info" in intent_lower or "details" in lower:
                info = self.get_file_info(path)
                if not info:
                    return {"success": False, "action": "file_info", "agent": "file",
                            "message": tr(command, "File not found. Give a full path.",
                                          "ফাইল পাওয়া যায়নি। সম্পূর্ণ path দিন।")}
                return {"success": True, "action": "file_info", "agent": "file",
                        "message": tr(command,
                                      f"📄 {info['name']} — {info['size_human']}, modified {info['modified']}.",
                                      f"📄 {info['name']} — {info['size_human']}, শেষ পরিবর্তন {info['modified']}।"),
                        "data": info}

            return {"success": False, "action": "file_unknown", "agent": "file",
                    "message": tr(command,
                                  "File command not understood. Examples: “find file report”, “list downloads”, “organize downloads”.",
                                  "ফাইল কমান্ড বোঝা যায়নি। উদাহরণ: “find file report”, “list downloads”, “organize downloads”।")}
        except Exception as exc:
            return {"success": False, "action": "file_error", "agent": "file",
                    "message": tr(command, f"File Agent error: {exc}", f"ফাইল এজেন্টে সমস্যা: {exc}")}

    # ---------------- self test ----------------
    def test(self) -> Dict[str, Any]:
        probe = config.DATA_DIR / f"_file_selftest_{uuid.uuid4().hex[:8]}.txt"
        checks: Dict[str, Any] = {}
        try:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            probe.write_text("atlas file self test", encoding="utf-8")
            checks["write"] = probe.exists()
            checks["read"] = self.read_file(str(probe)) == "atlas file self test"
            found = self.search_files(probe.name, directory=str(config.DATA_DIR))
            checks["search"] = str(probe) in found
            usage = self.get_disk_usage(str(config.DATA_DIR))
            checks["disk_usage"] = bool(usage.get("total"))
            self.delete_path(str(probe))
            checks["delete"] = not probe.exists()
            return {"success": all(checks.values()), "agent": "file",
                    "message": "File write/read/search/delete verified.",
                    "checks": checks}
        except Exception as exc:
            return {"success": False, "agent": "file", "message": f"File self test failed: {exc}"}
        finally:
            try:
                if probe.exists():
                    probe.unlink()
            except Exception:
                pass


file_agent = FileAgent()
