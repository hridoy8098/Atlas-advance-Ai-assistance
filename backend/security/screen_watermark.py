# backend/security/screen_watermark.py — tiled watermark on screenshot or image

from datetime import datetime
from pathlib import Path

import config

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    Image = None


class ScreenWatermark:
    def apply(self, image_path: str = None, text: str = "ATLAS", out_path: str = None,
              opacity: int = 48, tile: bool = True):
        if Image is None:
            return {"success": False, "error": "Pillow not installed"}

        if image_path:
            image = Image.open(image_path).convert("RGBA")
            stem = Path(image_path).stem
        else:
            from PIL import ImageGrab
            image = ImageGrab.grab().convert("RGBA")
            stem = "screen"

        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font = self._font(max(18, image.width // 40))
        stamp = f"{text}  {datetime.now():%Y-%m-%d %H:%M}"
        step_x = max(320, int(image.width / 3))
        step_y = max(160, int(image.height / 5))

        for y in range(0, image.height, step_y if tile else max(image.height, 1)):
            for x in range(0, image.width, step_x if tile else max(image.width, 1)):
                draw.text((x, y), stamp, fill=(255, 255, 255, max(8, min(opacity * 4, 255))), font=font)

        combined = Image.alpha_composite(image, overlay).convert("RGB")
        media_dir = config.DOWNLOADS_DIR / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        target = Path(out_path) if out_path else media_dir / f"{stem}_watermarked.png"
        combined.save(target)
        return {"success": True, "output": str(target), "text": text}

    @staticmethod
    def _font(size):
        for name in ("arialbd.ttf", "arial.ttf", "segoeui.ttf", "DejaVuSans-Bold.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()


screen_watermark = ScreenWatermark()
