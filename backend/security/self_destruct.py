# backend/security/self_destruct.py — guarded data wipe (dry-run by default)

import shutil
from pathlib import Path

import config

CONFIRM_PHRASE = "DELETE-ATLAS-DATA"


class SelfDestruct:
    def _targets(self):
        root = Path(config.DATA_DIR)
        if not root.exists():
            return []
        return [p for p in root.rglob("*") if p.is_file()]

    def wipe(self, confirm: str = "", dry_run: bool = True):
        targets = self._targets()
        preview = [str(p) for p in targets[:50]]
        report = {
            "dry_run": dry_run,
            "target_count": len(targets),
            "targets": preview,
            "confirm_phrase": CONFIRM_PHRASE,
        }
        if dry_run:
            report["success"] = True
            report["message"] = "Dry run — nothing was deleted"
            return report

        if confirm != CONFIRM_PHRASE:
            report["success"] = False
            report["message"] = f"Refused: confirm must be '{CONFIRM_PHRASE}'"
            return report

        deleted = errors = 0
        for path in targets:
            try:
                path.unlink()
                deleted += 1
            except Exception:
                errors += 1
        for sub in Path(config.DATA_DIR).iterdir():
            if sub.is_dir():
                try:
                    shutil.rmtree(sub, ignore_errors=True)
                except Exception:
                    pass
        report.update({"success": True, "deleted": deleted, "errors": errors,
                       "message": f"Deleted {deleted} file(s)"})
        return report


self_destruct = SelfDestruct()
