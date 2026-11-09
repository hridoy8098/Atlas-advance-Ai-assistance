"""Build docs/demo/atlas-demo.gif from the captured screenshots.

Run from the project root:
    python tools/build_demo_gif.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "docs" / "demo"
OUT = DEMO / "atlas-demo.gif"

WIDTH = 1200
SHOT_HEIGHT = 750
BAR = 70
TOTAL_HEIGHT = SHOT_HEIGHT + BAR

BG = (7, 19, 31)
LINE = (56, 189, 248)
TEXT = (219, 234, 245)
DIM = (123, 149, 171)
ACCENT = (125, 211, 252)

CAPTIONS = [
    ("01-dashboard.png", "Dashboard - live system stats, weather and the Atlas core"),
    ("02-agent-panel.png", "Agent Control Panel - switch any of the 22 agents on or off"),
    ("03-call-agents.png", "Call agents - WhatsApp Call and AI Call Receptionist"),
    ("04-agent-detail.png", "Agent detail - health, permissions and saved contacts"),
    ("05-chat-command.png", "Chat - one command, and the right agent runs it on your PC"),
]

FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/segoeuib.ttf"),
    Path("C:/Windows/Fonts/seguisb.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def fit_caption(text: str, font, max_width: int) -> str:
    if font.getlength(text) <= max_width:
        return text
    while text and font.getlength(text + "...") > max_width:
        text = text[:-1]
    return text + "..."


def caption_frame(name: str, caption: str, index: int) -> Image.Image:
    shot = Image.open(DEMO / name).convert("RGB")
    shot = shot.resize((WIDTH, SHOT_HEIGHT), Image.Resampling.LANCZOS)

    frame = Image.new("RGB", (WIDTH, TOTAL_HEIGHT), BG)
    frame.paste(shot, (0, 0))
    draw = ImageDraw.Draw(frame)
    draw.line([(0, SHOT_HEIGHT), (WIDTH, SHOT_HEIGHT)], fill=LINE, width=2)
    draw.rectangle([(0, SHOT_HEIGHT + 3), (WIDTH, TOTAL_HEIGHT)], fill=BG)

    body = load_font(26)
    meta = load_font(18)
    label = fit_caption(caption, body, WIDTH - 190)
    draw.text((26, SHOT_HEIGHT + 20), label, font=body, fill=TEXT)
    draw.text(
        (WIDTH - 150, SHOT_HEIGHT + 25),
        f"{index:02d} / {len(CAPTIONS):02d}",
        font=meta,
        fill=ACCENT,
    )
    return frame


def title_frame() -> Image.Image:
    shot = Image.open(DEMO / "01-dashboard.png").convert("RGB")
    shot = shot.resize((WIDTH, SHOT_HEIGHT), Image.Resampling.LANCZOS)
    # Darken the dashboard so the wordmark stays readable.
    overlay = Image.new("RGBA", shot.size, (4, 12, 20, 214))
    shot = Image.alpha_composite(shot.convert("RGBA"), overlay).convert("RGB")

    frame = Image.new("RGB", (WIDTH, TOTAL_HEIGHT), BG)
    frame.paste(shot, (0, 0))
    draw = ImageDraw.Draw(frame)

    huge = load_font(96)
    sub = load_font(30)
    small = load_font(20)

    title = "ATLAS 7.0"
    subtitle = "A multi-agent AI assistant for your PC and phone"
    link = "github.com/hridoy8098/Atlas-advance-Ai-assistance"

    def center(text: str, font, y: int, fill) -> None:
        width = draw.textlength(text, font=font)
        draw.text(((WIDTH - width) / 2, y), text, font=font, fill=fill)

    center(title, huge, 250, (240, 249, 255))
    draw.line([(WIDTH / 2 - 130, 372), (WIDTH / 2 + 130, 372)], fill=LINE, width=2)
    center(subtitle, sub, 396, TEXT)
    center(link, small, 448, DIM)

    draw.rectangle([(0, TOTAL_HEIGHT - 4), (WIDTH, TOTAL_HEIGHT)], fill=BG)
    return frame


def main() -> None:
    if not all((DEMO / name).exists() for name, _ in CAPTIONS):
        raise SystemExit("Run tools/capture_demo.py first: screenshots are missing.")

    print("title card")
    frames = [title_frame()]
    durations = [2200]

    for index, (name, caption) in enumerate(CAPTIONS, start=1):
        print(f"{index}/{len(CAPTIONS)} {name}")
        frames.append(caption_frame(name, caption, index))
        durations.append(4000 if index == len(CAPTIONS) else 3200)

    palette = [frame.quantize(colors=192, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG) for frame in frames]
    palette[0].save(
        OUT,
        save_all=True,
        append_images=palette[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=1,
    )
    size_mb = OUT.stat().st_size / (1024 * 1024)
    print(f"wrote {OUT.relative_to(ROOT)} ({size_mb:.2f} MB, {len(palette)} frames)")


if __name__ == "__main__":
    main()
