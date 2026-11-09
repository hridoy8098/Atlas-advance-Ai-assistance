# backend/agent/file_agent.py — Atlas 6.0 File Operations

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict


class FileAgent:
    """File and folder operations"""
    
    def __init__(self):
        self.home = Path.home()
        self.downloads = self.home / "Downloads"
        self.documents = self.home / "Documents"
        self.desktop = self.home / "Desktop"
        
        print(f"📁 File Agent initialized")
    
    # ===== FILE OPERATIONS =====
    
    def create_file(self, path: str, content: str = "") -> bool:
        """Create new file"""
        try:
            filepath = Path(path)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"📄 Created: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Create error: {e}")
            return False
    
    def read_file(self, path: str) -> Optional[str]:
        """Read file content"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return None
    
    def delete_file(self, path: str) -> bool:
        """Delete file"""
        try:
            os.remove(path)
            print(f"🗑️ Deleted: {path}")
            return True
        except:
            return False
    
    def move_file(self, src: str, dst: str) -> bool:
        """Move file"""
        try:
            shutil.move(src, dst)
            print(f"📦 Moved: {src} → {dst}")
            return True
        except:
            return False
    
    def copy_file(self, src: str, dst: str) -> bool:
        """Copy file"""
        try:
            shutil.copy2(src, dst)
            print(f"📋 Copied: {src} → {dst}")
            return True
        except:
            return False
    
    def rename_file(self, path: str, new_name: str) -> bool:
        """Rename file"""
        try:
            filepath = Path(path)
            new_path = filepath.parent / new_name
            filepath.rename(new_path)
            print(f"✏️ Renamed: {filepath.name} → {new_name}")
            return True
        except:
            return False
    
    # ===== FOLDER OPERATIONS =====
    
    def create_folder(self, path: str) -> bool:
        """Create folder"""
        try:
            os.makedirs(path, exist_ok=True)
            print(f"📁 Created folder: {path}")
            return True
        except:
            return False
    
    def delete_folder(self, path: str) -> bool:
        """Delete folder"""
        try:
            shutil.rmtree(path)
            print(f"🗑️ Deleted folder: {path}")
            return True
        except:
            return False
    
    def list_folder(self, path: str = None) -> List[Dict]:
        """List folder contents"""
        path = path or str(self.home)
        items = []
        
        try:
            for item in Path(path).iterdir():
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "type": "folder" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                })
        except:
            pass
        
        return sorted(items, key=lambda x: (x['type'], x['name']))
    
    def search_files(self, query: str, directory: str = None) -> List[str]:
        """Search files by name"""
        directory = directory or str(self.home)
        results = []
        
        try:
            for root, dirs, files in os.walk(directory):
                for name in files + dirs:
                    if query.lower() in name.lower():
                        results.append(os.path.join(root, name))
                if len(results) > 50:
                    break
        except:
            pass
        
        return results[:20]
    
    def get_file_info(self, path: str) -> Optional[Dict]:
        """Get file details"""
        try:
            stat = os.stat(path)
            return {
                "name": Path(path).name,
                "size": stat.st_size,
                "size_human": self._human_size(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except:
            return None
    
    # ===== ORGANIZE =====
    
    def organize_downloads(self) -> Dict:
        """Organize Downloads folder by file type"""
        categories = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
            "Documents": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx"],
            "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
            "Video": [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Code": [".py", ".js", ".html", ".css", ".json", ".xml", ".java", ".cpp"],
            "Others": []
        }
        
        result = {}
        downloads = str(self.downloads)
        
        for file in Path(downloads).iterdir():
            if file.is_file():
                ext = file.suffix.lower()
                category = "Others"
                for cat, exts in categories.items():
                    if ext in exts:
                        category = cat
                        break
                
                dest_dir = Path(downloads) / category
                dest_dir.mkdir(exist_ok=True)
                
                try:
                    shutil.move(str(file), str(dest_dir / file.name))
                    result[category] = result.get(category, 0) + 1
                except:
                    pass
        
        print(f"📦 Organized downloads: {result}")
        return result
    
    # ===== AGENT INTERFACE =====

    def get_capabilities(self) -> List[str]:
        return [
            "file_organize", "file_search", "file_create", "file_read",
            "file_delete", "file_copy", "file_move", "file_rename",
            "file_list", "file_info", "file_backup", "disk_usage",
        ]

    def handle(self, intent: str, entities: Dict = None) -> Dict:
        entities = entities or {}
        intent_lower = str(intent or "").lower()
        command = str(entities.get("_command", ""))
        query = entities.get("query") or entities.get("name") or ""
        path = entities.get("path") or entities.get("source") or ""
        destination = entities.get("destination") or entities.get("target") or ""

        try:
            if intent_lower in ("file_organize", "organize_downloads") or "organize" in command.lower() or "গোছাও" in command:
                result = self.organize_downloads()
                return {"success": True, "action": "file_organize", "message": f"📦 Downloads organized: {result}", "data": result}

            if intent_lower in ("file_search", "search_files") or "search file" in command.lower() or "find file" in command.lower():
                results = self.search_files(str(query))
                return {"success": True, "action": "file_search", "message": f"🔎 {len(results)} file(s) found.", "results": results}

            if intent_lower in ("file_list", "list_files") or "list files" in command.lower():
                items = self.list_folder(str(path) if path else None)
                return {"success": True, "action": "file_list", "message": f"📁 {len(items)} item(s).", "items": items}

            if intent_lower in ("file_create", "create_file"):
                ok = self.create_file(str(path), str(entities.get("content", "")))
                return {"success": ok, "action": "file_create", "message": "📄 File created." if ok else "Could not create file."}

            if intent_lower in ("file_delete", "delete_file"):
                ok = self.delete_file(str(path))
                return {"success": ok, "action": "file_delete", "message": "🗑️ File deleted." if ok else "Could not delete file."}

            if intent_lower in ("file_copy", "copy_file"):
                ok = self.copy_file(str(path), str(destination))
                return {"success": ok, "action": "file_copy", "message": "📋 File copied." if ok else "Could not copy file."}

            if intent_lower in ("file_move", "move_file"):
                ok = self.move_file(str(path), str(destination))
                return {"success": ok, "action": "file_move", "message": "📦 File moved." if ok else "Could not move file."}

            if intent_lower in ("file_rename", "rename_file"):
                ok = self.rename_file(str(path), str(entities.get("new_name", "")))
                return {"success": ok, "action": "file_rename", "message": "✏️ File renamed." if ok else "Could not rename file."}

            if intent_lower in ("file_info", "file_details"):
                info = self.get_file_info(str(path))
                return {"success": bool(info), "action": "file_info", "message": "File details.", "data": info}

            if intent_lower in ("disk_usage", "file_disk_usage"):
                return {"success": True, "action": "disk_usage", "message": "Disk usage.", "data": self.get_disk_usage(str(path) if path else "/")}

            return {
                "success": False,
                "action": "file_unknown",
                "message": "File command বুঝিনি। উদাহরণ: 'organize downloads', 'search file report'।",
            }
        except Exception as exc:
            return {"success": False, "action": "file_error", "message": f"File Agent error: {exc}"}

    # ===== HELPERS =====
    
    def _human_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    
    def get_disk_usage(self, path: str = "/") -> Dict:
        """Get disk usage"""
        try:
            import shutil
            usage = shutil.disk_usage(path)
            return {
                "total": self._human_size(usage.total),
                "used": self._human_size(usage.used),
                "free": self._human_size(usage.free),
                "percent": round(usage.used / usage.total * 100, 1)
            }
        except:
            return {}


# Singleton
file_agent = FileAgent()