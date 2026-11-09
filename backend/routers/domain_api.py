# backend/routers/domain_api.py — Phase-1 domain API
# analytics / security / study / bangladesh / media
# প্রতিটা handler আলাদা try/except করে — একটা domain fail করলে server বা অন্য route ভাঙবে না

from __future__ import annotations

import importlib
import traceback
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["domains"])


# ===== HELPERS =====

def _svc(module_path: str, attr: str):
    """Lazy import — module না থাকলেও server start হবে"""
    mod = importlib.import_module(module_path)
    return getattr(mod, attr)


def _ok(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict) and "success" in data:
        return data
    if isinstance(data, dict):
        return {"success": True, **data}
    return {"success": True, "data": data}


def _fail(e: Exception, where: str = "") -> JSONResponse:
    print(f"❌ [domain_api] {where}: {e}")
    traceback.print_exc(limit=3)
    return JSONResponse(
        status_code=200,
        content={"success": False, "error": f"{type(e).__name__}: {e}"},
    )


# ===== DOMAIN REGISTRY =====

_DOMAINS = {
    "analytics": [
        ("backend.analytics.personal_analytics", "personal_analytics"),
        ("backend.analytics.weekly_report", "weekly_report"),
        ("backend.analytics.app_tracker", "app_tracker"),
        ("backend.analytics.study_analytics", "study_analytics"),
        ("backend.analytics.habit_predictor", "habit_predictor"),
        ("backend.analytics.spending_analytics", "spending_analytics"),
        ("backend.analytics.goal_probability", "goal_tracker"),
        ("backend.analytics.productivity_score", "productivity_score"),
        ("backend.analytics.focus_score", "focus_score"),
    ],
    "security": [
        ("backend.security.malware_scanner", "malware_scanner"),
        ("backend.security.network_monitor", "network_monitor"),
        ("backend.security.password_manager", "password_manager"),
        ("backend.security.breach_detector", "breach_detector"),
        ("backend.security.two_fa_manager", "two_fa"),
        ("backend.security.privacy_mode", "privacy_mode"),
        ("backend.security.fake_screen", "fake_screen"),
        ("backend.security.screen_watermark", "screen_watermark"),
        ("backend.security.self_destruct", "self_destruct"),
    ],
    "study": [
        ("backend.study.flashcard", "flashcards"),
        ("backend.study.spaced_repetition", "spaced_repetition"),
        ("backend.study.concept_map", "concept_map"),
        ("backend.study.note_mindmap", "note_mindmap"),
        ("backend.study.citation_gen", "citations"),
        ("backend.study.exam_prep", "exam_prep"),
        ("backend.study.past_paper", "past_papers"),
        ("backend.study.teacher_mode", "teacher"),
        ("backend.study.youtube_ai", "youtube_ai"),
    ],
    "bangladesh": [
        ("backend.bangladesh.bd_news", "bd_news"),
        ("backend.bangladesh.bd_currency", "currency"),
        ("backend.bangladesh.bd_stock", "bd_stock"),
        ("backend.bangladesh.prayer_calendar", "prayer_calendar"),
        ("backend.bangladesh.bangla_ocr", "bangla_ocr"),
        ("backend.bangladesh.exam_helper", "exam_helper"),
    ],
    "media": [
        ("backend.media.music_player", "music_player"),
        ("backend.media.image_generator", "image_generator"),
        ("backend.media.meme_generator", "meme_generator"),
        ("backend.media.background_remover", "background_remover"),
        ("backend.media.subtitle_gen", "subtitle_generator"),
        ("backend.media.video_downloader", "video_downloader"),
        ("backend.media.podcast_creator", "podcast_creator"),
    ],
}


@router.get("/domains/status")
def domains_status():
    """কোন domain এর কোন service import হচ্ছে — debug/verify এর জন্য"""
    report: Dict[str, Any] = {}
    for domain, entries in _DOMAINS.items():
        services = {}
        for module_path, attr in entries:
            try:
                svc = _svc(module_path, attr)
                services[attr] = "ok" if svc is not None else "none"
            except Exception as e:
                services[attr] = f"error: {type(e).__name__}: {e}"
        report[domain] = services
    return {"success": True, "domains": report}


# ===== ANALYTICS =====

@router.get("/analytics/overview")
def analytics_overview(days: int = Query(7, ge=1, le=90)):
    try:
        data = _svc("backend.analytics.personal_analytics", "personal_analytics").overview(days=days)
        return _ok(data)
    except Exception as e:
        return _fail(e, "analytics/overview")


@router.get("/analytics/weekly")
def analytics_weekly(days: int = Query(7, ge=1, le=90)):
    try:
        data = _svc("backend.analytics.weekly_report", "weekly_report").generate(days=days)
        return _ok(data)
    except Exception as e:
        return _fail(e, "analytics/weekly")


@router.post("/analytics/track")
def analytics_track(payload: Dict[str, Any] = Body(default={})):
    try:
        tracker = _svc("backend.analytics.app_tracker", "app_tracker")
        app = payload.get("app") or payload.get("name") or ""
        if not app:
            return JSONResponse(content={"success": False, "error": "app name required"})
        result = tracker.log(app, title=payload.get("title"), minutes=payload.get("minutes"))
        return _ok(result)
    except Exception as e:
        return _fail(e, "analytics/track")


@router.get("/analytics/tracker")
def analytics_tracker():
    try:
        tracker = _svc("backend.analytics.app_tracker", "app_tracker")
        return _ok({"running": tracker.is_running(), "usage": tracker.usage(days=1)})
    except Exception as e:
        return _fail(e, "analytics/tracker")


@router.post("/analytics/study-session")
def analytics_study_session(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.analytics.study_analytics", "study_analytics")
        result = svc.log_session(
            subject=payload.get("subject", "General"),
            minutes=int(payload.get("minutes", 25)),
            notes=payload.get("notes"),
        )
        return _ok(result)
    except Exception as e:
        return _fail(e, "analytics/study-session")


@router.get("/analytics/study")
def analytics_study(days: int = Query(7, ge=1, le=90)):
    try:
        return _ok(_svc("backend.analytics.study_analytics", "study_analytics").stats(days=days))
    except Exception as e:
        return _fail(e, "analytics/study")


@router.post("/analytics/habit")
def analytics_habit_add(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.analytics.habit_predictor", "habit_predictor")
        return _ok(svc.add(name=payload.get("name", "habit")))
    except Exception as e:
        return _fail(e, "analytics/habit")


@router.post("/analytics/habit/log")
def analytics_habit_log(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.analytics.habit_predictor", "habit_predictor")
        return _ok(svc.log(name=payload.get("name", "habit")))
    except Exception as e:
        return _fail(e, "analytics/habit/log")


@router.get("/analytics/habits")
def analytics_habits():
    try:
        return _ok(_svc("backend.analytics.habit_predictor", "habit_predictor").stats())
    except Exception as e:
        return _fail(e, "analytics/habits")


@router.post("/analytics/expense")
def analytics_expense(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.analytics.spending_analytics", "spending_analytics")
        return _ok(svc.add(
            amount=float(payload.get("amount", 0)),
            category=payload.get("category", "general"),
            note=payload.get("note"),
        ))
    except Exception as e:
        return _fail(e, "analytics/expense")


@router.get("/analytics/spending")
def analytics_spending(days: int = Query(30, ge=1, le=365)):
    try:
        return _ok(_svc("backend.analytics.spending_analytics", "spending_analytics").summary(days=days))
    except Exception as e:
        return _fail(e, "analytics/spending")


@router.post("/analytics/goal")
def analytics_goal_add(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.analytics.goal_probability", "goal_tracker")
        result = svc.add(
            title=payload.get("title", "goal"),
            target=float(payload.get("target", 100)),
            deadline=payload.get("deadline"),
        )
        return _ok(result)
    except Exception as e:
        return _fail(e, "analytics/goal")


@router.post("/analytics/goal/progress")
def analytics_goal_progress(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.analytics.goal_probability", "goal_tracker")
        result = svc.update_progress(
            goal_id=payload.get("goal_id"),
            progress=float(payload.get("progress", 0)),
        )
        return _ok(result)
    except Exception as e:
        return _fail(e, "analytics/goal/progress")


# ===== SECURITY =====

@router.get("/security/overview")
def security_overview():
    out: Dict[str, Any] = {"success": True}
    try:
        nm = _svc("backend.security.network_monitor", "network_monitor")
        out["network"] = nm.summary()
    except Exception as e:
        out["network"] = {"error": f"{type(e).__name__}: {e}"}
    try:
        pm = _svc("backend.security.privacy_mode", "privacy_mode")
        out["privacy"] = pm.status()
    except Exception as e:
        out["privacy"] = {"error": f"{type(e).__name__}: {e}"}
    try:
        tfa = _svc("backend.security.two_fa_manager", "two_fa")
        out["two_fa"] = tfa.status()
    except Exception as e:
        out["two_fa"] = {"error": f"{type(e).__name__}: {e}"}
    return out


@router.post("/security/scan")
def security_scan(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.security.malware_scanner", "malware_scanner")
        result = svc.scan(
            paths=payload.get("paths"),
            max_files=int(payload.get("max_files", 2000)),
        )
        return _ok(result)
    except Exception as e:
        return _fail(e, "security/scan")


@router.post("/security/password")
def security_password(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.security.password_manager", "password_manager")
        pwd = payload.get("password", "")
        return _ok({"strength": svc.strength(pwd), "password": svc.generate()})
    except Exception as e:
        return _fail(e, "security/password")


@router.post("/security/breach")
def security_breach(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.security.breach_detector", "breach_detector")
        return _ok(svc.check(payload.get("email", "")))
    except Exception as e:
        return _fail(e, "security/breach")


@router.post("/security/2fa/setup")
def security_2fa_setup(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.security.two_fa_manager", "two_fa")
        secret = svc.generate_secret(account=payload.get("account", "atlas"))
        return _ok({
            "secret": secret,
            "uri": svc.provisioning_uri(secret, account=payload.get("account", "atlas")),
        })
    except Exception as e:
        return _fail(e, "security/2fa/setup")


@router.post("/security/2fa/verify")
def security_2fa_verify(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.security.two_fa_manager", "two_fa")
        return _ok({"valid": svc.verify(payload.get("secret", ""), payload.get("code", ""))})
    except Exception as e:
        return _fail(e, "security/2fa/verify")


@router.get("/security/2fa/status")
def security_2fa_status():
    try:
        return _ok(_svc("backend.security.two_fa_manager", "two_fa").status())
    except Exception as e:
        return _fail(e, "security/2fa/status")


@router.post("/security/privacy")
def security_privacy(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.security.privacy_mode", "privacy_mode")
        enabled = bool(payload.get("enable", True))
        result = svc.enable() if enabled else svc.disable()
        return _ok({"enabled": enabled, "result": result})
    except Exception as e:
        return _fail(e, "security/privacy")


@router.get("/security/privacy")
def security_privacy_status():
    try:
        return _ok(_svc("backend.security.privacy_mode", "privacy_mode").status())
    except Exception as e:
        return _fail(e, "security/privacy/status")


@router.post("/security/fake-screen")
def security_fake_screen(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.security.fake_screen", "fake_screen")
        show = bool(payload.get("show", True))
        result = svc.show() if show else svc.hide()
        return _ok({"visible": show, "result": result})
    except Exception as e:
        return _fail(e, "security/fake-screen")


@router.post("/security/watermark")
def security_watermark(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.security.screen_watermark", "screen_watermark")
        result = svc.apply(
            image_path=payload.get("image_path"),
            text=payload.get("text", "ATLAS"),
            out_path=payload.get("out_path"),
        )
        return _ok(result)
    except Exception as e:
        return _fail(e, "security/watermark")


@router.post("/security/self-destruct")
def security_self_destruct(payload: Dict[str, Any] = Body(default={})):
    """dry_run খালি preview; আসলে মুছতে confirm == DELETE-ATLAS-DATA লাগবে"""
    try:
        svc = _svc("backend.security.self_destruct", "self_destruct")
        result = svc.wipe(
            confirm=payload.get("confirm", ""),
            dry_run=bool(payload.get("dry_run", True)),
        )
        return _ok(result)
    except Exception as e:
        return _fail(e, "security/self-destruct")


# ===== STUDY =====

@router.get("/study/flashcards")
def study_flashcards_list(deck: Optional[str] = Query(None)):
    try:
        svc = _svc("backend.study.flashcard", "flashcards")
        return _ok({"cards": svc.list(deck=deck) if deck else svc.list()})
    except Exception as e:
        return _fail(e, "study/flashcards")


@router.post("/study/flashcards")
def study_flashcards_add(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.study.flashcard", "flashcards")
        return _ok(svc.add(
            question=payload.get("question", ""),
            answer=payload.get("answer", ""),
            deck=payload.get("deck", "default"),
        ))
    except Exception as e:
        return _fail(e, "study/flashcards/add")


@router.delete("/study/flashcards/{card_id}")
def study_flashcards_delete(card_id: int):
    try:
        svc = _svc("backend.study.flashcard", "flashcards")
        return _ok(svc.delete(card_id))
    except Exception as e:
        return _fail(e, "study/flashcards/delete")


@router.get("/study/due")
def study_due(limit: int = Query(20, ge=1, le=200)):
    try:
        svc = _svc("backend.study.spaced_repetition", "spaced_repetition")
        return _ok({"cards": svc.due(limit=limit)})
    except Exception as e:
        return _fail(e, "study/due")


@router.post("/study/review")
def study_review(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.study.spaced_repetition", "spaced_repetition")
        return _ok(svc.review(
            card_id=payload.get("card_id"),
            quality=int(payload.get("quality", 3)),
        ))
    except Exception as e:
        return _fail(e, "study/review")


@router.get("/study/stats")
def study_stats():
    try:
        return _ok(_svc("backend.study.spaced_repetition", "spaced_repetition").stats())
    except Exception as e:
        return _fail(e, "study/stats")


@router.post("/study/concept-map")
def study_concept_map(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.study.concept_map", "concept_map")
        return _ok(svc.generate(payload.get("topic", "")))
    except Exception as e:
        return _fail(e, "study/concept-map")


@router.post("/study/citation")
def study_citation(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.study.citation_gen", "citations")
        return _ok(svc.format(
            fields=payload.get("fields", {}),
            style=payload.get("style", "apa"),
        ))
    except Exception as e:
        return _fail(e, "study/citation")


@router.post("/study/plan")
def study_plan(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.study.exam_prep", "exam_prep")
        return _ok(svc.plan(
            subject=payload.get("subject", "General"),
            exam_date=payload.get("exam_date"),
            hours_per_day=float(payload.get("hours_per_day", 2)),
        ))
    except Exception as e:
        return _fail(e, "study/plan")


@router.post("/study/explain")
def study_explain(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.study.teacher_mode", "teacher")
        return _ok(svc.explain(
            topic=payload.get("topic", ""),
            level=payload.get("level", "medium"),
        ))
    except Exception as e:
        return _fail(e, "study/explain")


@router.post("/study/youtube")
def study_youtube(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.study.youtube_ai", "youtube_ai")
        return _ok(svc.summarize(payload.get("url") or payload.get("query", "")))
    except Exception as e:
        return _fail(e, "study/youtube")


# ===== BANGLADESH =====

@router.get("/bd/news")
def bd_news(limit: int = Query(10, ge=1, le=30)):
    try:
        return _ok({"news": _svc("backend.bangladesh.bd_news", "bd_news").latest(limit=limit)})
    except Exception as e:
        return _fail(e, "bd/news")


@router.get("/bd/currency")
def bd_currency(base: str = Query("BDT")):
    try:
        return _ok(_svc("backend.bangladesh.bd_currency", "currency").rates(base=base))
    except Exception as e:
        return _fail(e, "bd/currency")


@router.get("/bd/stock")
def bd_stock(limit: int = Query(10, ge=1, le=30)):
    try:
        return _ok({"stocks": _svc("backend.bangladesh.bd_stock", "bd_stock").top(limit=limit)})
    except Exception as e:
        return _fail(e, "bd/stock")


@router.get("/bd/prayer")
def bd_prayer(city: str = Query("Dhaka")):
    try:
        return _ok(_svc("backend.bangladesh.prayer_calendar", "prayer_calendar").today(city=city))
    except Exception as e:
        return _fail(e, "bd/prayer")


@router.get("/bd/prayer/month")
def bd_prayer_month(
    city: str = Query("Dhaka"),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
):
    try:
        svc = _svc("backend.bangladesh.prayer_calendar", "prayer_calendar")
        return _ok(svc.month(city=city, year=year, month=month))
    except Exception as e:
        return _fail(e, "bd/prayer/month")


# ===== MEDIA =====

@router.get("/media/library")
def media_library():
    try:
        return _ok({"tracks": _svc("backend.media.music_player", "music_player").library()})
    except Exception as e:
        return _fail(e, "media/library")


@router.get("/media/status")
def media_status():
    try:
        return _ok(_svc("backend.media.music_player", "music_player").status())
    except Exception as e:
        return _fail(e, "media/status")


@router.post("/media/play")
def media_play(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.media.music_player", "music_player")
        return _ok(svc.play(payload.get("path") or payload.get("track", "")))
    except Exception as e:
        return _fail(e, "media/play")


@router.post("/media/pause")
def media_pause():
    try:
        return _ok(_svc("backend.media.music_player", "music_player").pause())
    except Exception as e:
        return _fail(e, "media/pause")


@router.post("/media/resume")
def media_resume():
    try:
        return _ok(_svc("backend.media.music_player", "music_player").resume())
    except Exception as e:
        return _fail(e, "media/resume")


@router.post("/media/stop")
def media_stop():
    try:
        return _ok(_svc("backend.media.music_player", "music_player").stop())
    except Exception as e:
        return _fail(e, "media/stop")


@router.post("/media/meme")
def media_meme(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.media.meme_generator", "meme_generator")
        return _ok(svc.make(
            image_path=payload.get("image_path"),
            top=payload.get("top", ""),
            bottom=payload.get("bottom", ""),
            out=payload.get("out"),
        ))
    except Exception as e:
        return _fail(e, "media/meme")


@router.post("/media/remove-bg")
def media_remove_bg(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.media.background_remover", "background_remover")
        return _ok(svc.remove(
            image_path=payload.get("image_path"),
            tolerance=int(payload.get("tolerance", 30)),
            out=payload.get("out"),
        ))
    except Exception as e:
        return _fail(e, "media/remove-bg")


@router.post("/media/podcast")
def media_podcast(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.media.podcast_creator", "podcast_creator")
        return _ok(svc.create(
            script=payload.get("script", ""),
            voice=payload.get("voice"),
            out=payload.get("out"),
        ))
    except Exception as e:
        return _fail(e, "media/podcast")


@router.post("/media/subtitle")
def media_subtitle(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.media.subtitle_gen", "subtitle_generator")
        return _ok(svc.srt(payload.get("path", "")))
    except Exception as e:
        return _fail(e, "media/subtitle")


@router.post("/media/download-video")
def media_download_video(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.media.video_downloader", "video_downloader")
        return _ok(svc.download(
            url=payload.get("url", ""),
            out_dir=payload.get("out_dir"),
            audio_only=bool(payload.get("audio_only", False)),
        ))
    except Exception as e:
        return _fail(e, "media/download-video")


@router.post("/media/generate-image")
def media_generate_image(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _svc("backend.media.image_generator", "image_generator")
        return _ok(svc.generate(
            prompt=payload.get("prompt", ""),
            size=payload.get("size", "1024x1024"),
        ))
    except Exception as e:
        return _fail(e, "media/generate-image")
