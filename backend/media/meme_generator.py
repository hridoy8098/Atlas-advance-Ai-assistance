# backend/media/meme_generator.py — top/bottom text meme from an image

from datetime import datetime
from pathlib import Path

import config

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    Image = None

_MEDIA = config.DOWNLOADS_DIR / "media" / "memes"


class MemeGenerator:
    def make(self, image_path: str, top: str = "", bottom: str = "", out: str = None):
        if Image is None:
            return {"success": False, "error": "Pillow not installed"}
        if not image_path:
            raise ValueError("image_path required")
        source = Path(image_path)
        if not source.exists():
            raise FileNotFoundError(f"image not found: {image_path}")

        image = Image.open(source).convert("RGB")
        draw = ImageDraw.Draw(image)
        font = self._font(max(24, image.width // 12))

        if top:
            self._draw_line(draw, image, top, font, "top")
        if bottom:
            self._draw_line(draw, image, bottom, font, "bottom")

        _MEDIA.mkdir(parents=True, exist_ok=True)
        target = Path(out) if out else _MEDIA / f"meme_{datetime.now():%Y%m%d_%H%M%S}.png"
        image.save(target)
        return {"success": True, "output": str(target)}

    @staticmethod
    def _draw_line(draw, image, text, font, position):
        text = text.upper()
        bbox = draw.textbbox((0, 0), text, font=font)
        while bbox[2] - bbox[0] > image.width - 24 and len(text) > 3:
            text = text[:-2]
            bbox = draw.textbbox((0, 0), text, font=font)
        x = (image.width - (bbox[2] - bbox[0])) // 2
        y = 12 if position == "top" else image.height - (bbox[3] - bbox[1]) - 28
        draw.text((x, y), text, font=font, fill="white",
                  stroke_width=3, stroke_fill="black")

    @staticmethod
    def _font(size):
        for name in ("impact.ttf", "arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()


meme_generator = MemeGenerator()
