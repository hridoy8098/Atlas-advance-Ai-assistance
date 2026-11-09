# backend/media/background_remover.py — corner flood-fill background removal

from datetime import datetime
from pathlib import Path

import config

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    Image = None

_MEDIA = config.DOWNLOADS_DIR / "media" / "nobg"


class BackgroundRemover:
    def remove(self, image_path: str, tolerance: int = 30, out: str = None):
        if Image is None:
            return {"success": False, "error": "Pillow not installed"}
        if not image_path:
            raise ValueError("image_path required")
        source = Path(image_path)
        if not source.exists():
            raise FileNotFoundError(f"image not found: {image_path}")

        image = Image.open(source).convert("RGB")
        mask = image.copy()
        marker = (255, 0, 255)
        corners = [(0, 0), (image.width - 1, 0), (0, image.height - 1), (image.width - 1, image.height - 1)]
        for corner in corners:
            if mask.getpixel(corner) != marker:
                ImageDraw.floodfill(mask, corner, marker, thresh=max(0, min(int(tolerance), 120)))

        rgba = image.convert("RGBA")
        pixels = rgba.load()
        filled = 0
        for y in range(rgba.height):
            for x in range(rgba.width):
                if mask.getpixel((x, y)) == marker:
                    pixels[x, y] = (255, 255, 255, 0)
                    filled += 1

        _MEDIA.mkdir(parents=True, exist_ok=True)
        target = Path(out) if out else _MEDIA / f"{source.stem}_nobg_{datetime.now():%H%M%S}.png"
        rgba.save(target)
        return {
            "success": True,
            "output": str(target),
            "removed_pixels": filled,
            "total_pixels": rgba.width * rgba.height,
        }


background_remover = BackgroundRemover()
