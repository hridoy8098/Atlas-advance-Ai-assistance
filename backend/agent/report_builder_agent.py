# backend/agent/report_builder_agent.py — Presentation / Report Builder Agent
# AI outline -> Markdown + HTML + PPTX (when python-pptx is available).
from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import config
from .advanced_common import (
    ask_json,
    clean_text,
    extract_after,
    fail,
    ok,
    slugify,
    write_json,
)

REPORT_DIR = config.DATA_DIR / "reports"


class ReportBuilderAgent:
    name = "Presentation Builder Agent"

    def get_capabilities(self) -> List[str]:
        return ["presentation_build", "report_build", "outline_generate", "pptx_export", "html_export"]

    def handle(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        entities = entities or {}
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()

        try:
            if "list" in intent_lower:
                return self.list_reports()
            topic = str(
                entities.get("topic")
                or entities.get("title")
                or self._topic(command)
                or ""
            ).strip()
            if not topic:
                return fail("report_builder", "কোন topic নিয়ে report/presentation বানাব? যেমন: “presentation on AI in education”।")
            return self.build(
                topic,
                slides=int(entities.get("slides") or self._slide_count(command) or 7),
                audience=str(entities.get("audience") or "general"),
            )
        except Exception as exc:
            return fail("report_builder", f"Report Builder error: {exc}")

    def build(self, topic: str, slides: int = 7, audience: str = "general") -> Dict[str, Any]:
        topic = clean_text(topic)
        slides = max(3, min(int(slides), 20))

        outline = ask_json(
            f"Create a {slides}-slide presentation outline on '{topic}' for a {audience} audience. "
            'Reply JSON only: {"title":"...","subtitle":"...","slides":[{"title":"...","bullets":["..."],"notes":"..."}]}. '
            "Each slide must have 2-5 short bullets.",
            system_prompt="You are a presentation designer. Reply with JSON only.",
            fallback=None,
        )
        if not isinstance(outline, dict) or not outline.get("slides"):
            outline = self._fallback_outline(topic, slides)

        outline["slides"] = [
            {
                "title": clean_text(slide.get("title")) or f"Slide {index + 1}",
                "bullets": [clean_text(item) for item in (slide.get("bullets") or []) if clean_text(item)][:6],
                "notes": clean_text(slide.get("notes") or ""),
            }
            for index, slide in enumerate(outline.get("slides", [])[:slides])
        ]
        title = clean_text(outline.get("title")) or topic
        subtitle = clean_text(outline.get("subtitle")) or f"Prepared by Atlas 7.0 · {datetime.now().strftime('%d %b %Y')}"

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        base = slugify(topic)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        md_path = REPORT_DIR / f"{base}-{stamp}.md"
        html_path = REPORT_DIR / f"{base}-{stamp}.html"
        md_path.write_text(self._markdown(title, subtitle, outline["slides"]), encoding="utf-8")
        html_path.write_text(self._html(title, subtitle, outline["slides"]), encoding="utf-8")

        files = [{"type": "markdown", "path": str(md_path)}, {"type": "html", "path": str(html_path)}]
        pptx_error = ""
        try:
            pptx_path = REPORT_DIR / f"{base}-{stamp}.pptx"
            self._pptx(str(pptx_path), title, subtitle, outline["slides"])
            files.append({"type": "pptx", "path": str(pptx_path)})
        except Exception as exc:
            pptx_error = str(exc)

        manifest = config.DATA_DIR / "reports" / "index.json"
        try:
            from .advanced_common import read_json
            history = read_json(manifest, {"reports": []})
            history.setdefault("reports", []).append({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "topic": topic,
                "title": title,
                "files": files,
            })
            history["reports"] = history["reports"][-50:]
            write_json(manifest, history)
        except Exception:
            pass

        message = f"📊 “{title}” তৈরি — {len(files)} file(s)."
        if pptx_error:
            message += f" PPTX export skipped ({pptx_error})."
        return ok(
            "report_builder",
            message,
            title=title,
            subtitle=subtitle,
            slides=outline["slides"],
            files=files,
            pptx_error=pptx_error or None,
        )

    def list_reports(self) -> Dict[str, Any]:
        from .advanced_common import read_json
        history = read_json(REPORT_DIR / "index.json", {"reports": []}).get("reports") or []
        return ok("report_builder", f"📚 {len(history)} report/presentation found.", reports=history[-20:])

    # ---------------- exporters ----------------
    @staticmethod
    def _markdown(title: str, subtitle: str, slides: List[Dict[str, Any]]) -> str:
        lines = [f"# {title}", "", f"_{subtitle}_", ""]
        for index, slide in enumerate(slides, 1):
            lines.append(f"## {index}. {slide['title']}")
            lines.append("")
            for bullet in slide.get("bullets", []):
                lines.append(f"- {bullet}")
            if slide.get("notes"):
                lines.append("")
                lines.append(f"> Speaker notes: {slide['notes']}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _html(title: str, subtitle: str, slides: List[Dict[str, Any]]) -> str:
        blocks = []
        for index, slide in enumerate(slides, 1):
            bullets = "".join(f"<li>{html.escape(item)}</li>" for item in slide.get("bullets", []))
            notes = (
                f'<p class="notes">{html.escape(slide["notes"])}</p>'
                if slide.get("notes") else ""
            )
            blocks.append(
                f'<section><span class="num">{index:02d}</span><h2>{html.escape(slide["title"])}</h2>'
                f"<ul>{bullets}</ul>{notes}</section>"
            )
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
:root{{--bg:#07111f;--card:#0d2037;--ink:#e9f2ff;--muted:#8fb3d9;--accent:#19d3c5}}
*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(160deg,#050b14,var(--bg));color:var(--ink);
font-family:Segoe UI,system-ui,sans-serif;padding:48px 24px}}
header{{max-width:900px;margin:0 auto 36px}}h1{{font-size:42px;margin:0 0 8px}}
.sub{{color:var(--muted)}}section{{max-width:900px;margin:16px auto;background:var(--card);border:1px solid #1c3a5a;
border-radius:18px;padding:26px 30px;position:relative}}
.num{{color:var(--accent);font-weight:700;letter-spacing:.12em;font-size:12px}}
h2{{margin:8px 0 14px}}li{{margin:8px 0;line-height:1.5}}.notes{{color:var(--muted);font-size:13px;margin-top:14px}}
</style></head><body><header><h1>{html.escape(title)}</h1><p class="sub">{html.escape(subtitle)}</p></header>
{''.join(blocks)}</body></html>"""

    @staticmethod
    def _pptx(path: str, title: str, subtitle: str, slides: List[Dict[str, Any]]) -> None:
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.util import Inches, Pt

        presentation = Presentation()
        presentation.slide_width = Inches(13.333)
        presentation.slide_height = Inches(7.5)

        title_slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        background = title_slide.background.fill
        background.solid()
        background.fore_color.rgb = RGBColor(7, 17, 31)

        box = title_slide.shapes.add_textbox(Inches(0.9), Inches(2.2), Inches(11.5), Inches(1.4))
        frame = box.text_frame
        frame.text = title
        paragraph = frame.paragraphs[0]
        paragraph.font.size = Pt(40)
        paragraph.font.bold = True
        paragraph.font.color.rgb = RGBColor(233, 242, 255)

        sub = title_slide.shapes.add_textbox(Inches(0.95), Inches(3.7), Inches(11), Inches(0.8))
        sub_frame = sub.text_frame
        sub_frame.text = subtitle
        sub_frame.paragraphs[0].font.size = Pt(18)
        sub_frame.paragraphs[0].font.color.rgb = RGBColor(143, 179, 217)

        for slide_data in slides:
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            fill = slide.background.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(10, 26, 45)

            heading = slide.shapes.add_textbox(Inches(0.7), Inches(0.5), Inches(12), Inches(0.9))
            heading.text_frame.text = slide_data["title"]
            heading.text_frame.paragraphs[0].font.size = Pt(30)
            heading.text_frame.paragraphs[0].font.bold = True
            heading.text_frame.paragraphs[0].font.color.rgb = RGBColor(25, 211, 197)

            body = slide.shapes.add_textbox(Inches(0.9), Inches(1.6), Inches(11.7), Inches(5.1))
            body_frame = body.text_frame
            body_frame.word_wrap = True
            for index, bullet in enumerate(slide_data.get("bullets", [])):
                paragraph = body_frame.paragraphs[0] if index == 0 else body_frame.add_paragraph()
                paragraph.text = f"• {bullet}"
                paragraph.font.size = Pt(20)
                paragraph.font.color.rgb = RGBColor(233, 242, 255)
                paragraph.space_after = Pt(10)

            if slide_data.get("notes"):
                notes = slide.notes_slide.notes_text_frame
                notes.text = slide_data["notes"]

        presentation.save(path)

    @staticmethod
    def _fallback_outline(topic: str, slides: int) -> Dict[str, Any]:
        sections = ["Introduction", "Why it matters", "Key concepts", "Current landscape",
                    "Challenges", "Opportunities", "Case study", "Recommendations", "Next steps", "Conclusion"]

        def bullets_for(name: str) -> List[str]:
            return [
                f"Core idea behind {name.lower()} in {topic}",
                "Key evidence and practical example",
                "What to watch next / action point",
            ]

        return {
            "title": topic.title(),
            "subtitle": f"Atlas 7.0 briefing · {datetime.now().strftime('%d %b %Y')}",
            "slides": [
                {"title": sections[index % len(sections)], "bullets": bullets_for(sections[index % len(sections)]), "notes": ""}
                for index in range(slides)
            ],
        }

    # ---------------- parsing ----------------
    @staticmethod
    def _topic(command: str) -> str:
        return extract_after(
            command,
            ["presentation on", "presentation about", "slides on", "report on", "report about",
             "ppt on", "প্রেজেন্টেশন", "রিপোর্ট", "slide ban", "presentation"],
        )

    @staticmethod
    def _slide_count(command: str) -> int:
        match = re.search(r"(\d{1,2})\s*(?:slide|স্লাইড|page|পেজ)", command, flags=re.I)
        return int(match.group(1)) if match else 0

    def test(self) -> Dict[str, Any]:
        try:
            import pptx  # noqa: F401
            pptx_ok = True
        except Exception:
            pptx_ok = False
        return {
            "success": True,
            "agent": "report_builder",
            "pptx": pptx_ok,
            "message": "Report Builder ready (Markdown + HTML + PPTX).",
        }


report_builder_agent = ReportBuilderAgent()
