# backend/bangladesh/bangla_ocr.py — Bangla text extraction from images via Gemini vision

from pathlib import Path

_PROMPT = (
    "Extract ALL text from this image exactly as written. "
    "If the text is Bangla, return Bangla. Keep line breaks. Do not translate."
)


class BanglaOCR:
    def extract(self, source):
        if not source:
            raise ValueError("image path required")

        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"image not found: {source}")

        image_bytes = path.read_bytes()
        try:
            from backend.core.ai_engine import ai_engine
        except Exception as e:
            return {"success": False, "text": "", "error": f"AI engine unavailable: {e}"}

        text = ai_engine.chat_vision(image_bytes, prompt=_PROMPT)
        if not text or text.lower().startswith(("vision features not available", "vision analysis failed")):
            return {"success": False, "text": text or "", "error": "vision unavailable"}
        return {"success": True, "text": text.strip(), "source": str(path)}


bangla_ocr = BanglaOCR()
