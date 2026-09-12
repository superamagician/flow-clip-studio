#!/usr/bin/env python3
"""Local multi-user web app: create-clip form + live generation + gallery.

Run:
    python app.py
Then open http://localhost:5000/

Phase 1 of "hosted service" plan: each registered user has their OWN encrypted
API credentials (useapi.net token, Google Flow email, TikTok token, etc.), own
character roster, own clip gallery, own activity log, and own output folder —
fully isolated in SQLite (db.py) + per-user folders under userdata/<user_id>/.
Still runs on one machine (no cloud hosting / billing yet — that's Phase 2).
"""
from __future__ import annotations
import csv
import functools
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from flask import (Flask, jsonify, request, render_template, send_from_directory,
                    session, redirect, url_for, flash, Response)

ROOT = Path(__file__).resolve().parent
USERDATA_DIR = ROOT / "userdata"


def _load_dotenv(path: Path) -> None:
    """Load .env into os.environ before importing db (which reads DATABASE_URL/
    MASTER_KEY at call time / first import) — local dev only; a real deploy sets
    these as actual environment variables in the host's dashboard instead."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")

import db  # noqa: E402  (must come after _load_dotenv so DATABASE_URL/MASTER_KEY are set)
import storage  # noqa: E402
import ai_copywriter  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import build_batch_from_brief as bbf  # noqa: E402
import caption_writer  # noqa: E402
import google_flow_rest as gfr  # noqa: E402

def _default_ffmpeg_bin() -> str | None:
    win_bin = (Path(r"C:\Users\KJ\AppData\Local\Microsoft\WinGet\Packages") /
               "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe" /
               "ffmpeg-9.0.1-full_build" / "bin")
    return str(win_bin) if win_bin.exists() else None


_FFMPEG_BIN = os.environ.get("FFMPEG_BIN") or _default_ffmpeg_bin()
FFPROBE = str(Path(_FFMPEG_BIN) / "ffprobe.exe") if _FFMPEG_BIN else "ffprobe"
FFMPEG = str(Path(_FFMPEG_BIN) / "ffmpeg.exe") if _FFMPEG_BIN else "ffmpeg"
# On Linux containers, ffmpeg/ffprobe are on PATH (no .exe) and a Thai-capable font
# must be installed via the Dockerfile (fonts-thai-tlwg) rather than pointing at Windows Fonts.
if os.name != "nt":
    FFPROBE, FFMPEG = "ffprobe", "ffmpeg"
    FONT_PATH = os.environ.get("FONT_PATH", "/usr/share/fonts/truetype/tlwg/Garuda.ttf")
else:
    FONT_PATH = r"C:\Windows\Fonts\tahoma.ttf"

app = Flask(__name__)
app.secret_key = db._get_or_create_master_key()  # local phase: reuse the encryption key file as session secret
LOCK = threading.Lock()

DEFAULT_CHARACTERS = [
    {"id": "nong_mind", "name": "น้องมายด์", "gender": "female", "age_range": "20-25",
     "style_archetype": "trendy streetwear",
     "appearance": "Long dark hair with soft curtain bangs, slim build, bright expressive eyes, small hoop earrings.",
     "wardrobe": "Oversized graphic tees, trendy streetwear, layered accessories.", "energy": "playful",
     "presenter_desc": "a playful young Thai woman in her early twenties with long dark hair and curtain bangs, wearing trendy oversized streetwear and small hoop earrings, energetic and bubbly expression",
     "best_for": "beauty, fashion, food, TikTok-native products"},
    {"id": "phi_boy", "name": "พี่บอย", "gender": "male", "age_range": "30-40",
     "style_archetype": "corporate/professional",
     "appearance": "Short neat black hair, clean-shaven, thin-frame glasses, average build, calm friendly face.",
     "wardrobe": "Button-up shirts or smart-casual polo, minimal accessories.", "energy": "calm/warm",
     "presenter_desc": "a calm and warm Thai man in his early thirties, short neat hair, clean-shaven, thin-frame glasses, wearing a smart-casual button-up shirt, trustworthy professional demeanor",
     "best_for": "tech, home goods, finance-adjacent, general household products"},
    {"id": "je_maem", "name": "เจ๊แหม่ม", "gender": "female", "age_range": "45+",
     "style_archetype": "mom/dad-next-door",
     "appearance": "Short curly hair, warm round face, average-plus build, wears a simple apron over homewear.",
     "wardrobe": "Comfortable homewear, apron when in kitchen/cleaning scenes.", "energy": "warm",
     "presenter_desc": "a warm middle-aged Thai housekeeper aunty with short curly hair, wearing a simple apron over comfortable homewear, cheerful and nurturing expression",
     "best_for": "home cleaning, cooking, household products"},
    {"id": "nong_pun", "name": "น้องปั้น", "gender": "male", "age_range": "20-25",
     "style_archetype": "gamer/tech-enthusiast",
     "appearance": "Short black hair, thick black-framed glasses, slim build, casual gamer look.",
     "wardrobe": "Dark t-shirts, gaming-brand hoodies, seated at a gaming desk setup.", "energy": "energetic",
     "presenter_desc": "a young Thai man in his early twenties with short black hair and thick black-framed glasses, casual gamer style dark t-shirt, seated at a gaming desk setup, energetic and enthusiastic expression",
     "best_for": "gaming, tech gadgets, electronics"},
    {"id": "kru_koi", "name": "ครูก้อย", "gender": "female", "age_range": "30-40",
     "style_archetype": "elegant/minimalist",
     "appearance": "Long straight dark hair, no glasses, slim build, clear smooth skin, poised posture.",
     "wardrobe": "Minimalist neutral-tone blouses, subtle jewelry.", "energy": "professional/calm",
     "presenter_desc": "an elegant Thai woman in her mid-thirties with long straight dark hair, no glasses, wearing a minimalist neutral-tone blouse, poised and calm professional demeanor",
     "best_for": "beauty, skincare, health, premium products"},
    {"id": "bang_pao", "name": "บังเปา", "gender": "male", "age_range": "30-40",
     "style_archetype": "sporty/active",
     "appearance": "Short buzzed hair, athletic muscular build, visible tattoo on forearm, tanned skin.",
     "wardrobe": "Athletic wear, sports tank tops or fitted t-shirts.", "energy": "energetic",
     "presenter_desc": "an athletic Thai man in his mid-thirties with short buzzed hair, muscular build, a visible tattoo on his forearm, tanned skin, wearing athletic sportswear, energetic and confident demeanor",
     "best_for": "fitness, outdoor gear, sports products"},
]

CATEGORY_KEYWORDS = {
    "gaming": ["เกม", "เกมมิ่ง", "จอย", "คีย์บอร์ด", "เมาส์", "การ์ดจอ"],
    "tech": ["หูฟัง", "มือถือ", "แกดเจ็ต", "ไมค์", "สายชาร์จ", "พาวเวอร์แบงค์", "ลำโพง", "อิเล็กทรอนิกส์", "ขาตั้ง"],
    "electronics": ["หูฟัง", "มือถือ", "แกดเจ็ต", "อิเล็กทรอนิกส์"],
    "beauty": ["ครีม", "เซรั่ม", "ผิว", "ความงาม", "แต่งหน้า", "ลิป", "กันแดด", "คอลลาเจน", "มาส์ก"],
    "skincare": ["ครีม", "เซรั่ม", "ผิว", "กันแดด", "มาส์กหน้า"],
    "health": ["วิตามิน", "อาหารเสริม", "สุขภาพ"],
    "home cleaning": ["น้ำยา", "ถูพื้น", "ซัก", "ทำความสะอาด", "ผงซักฟอก"],
    "cooking": ["ครัว", "หม้อ", "กระทะ", "จาน", "กาแฟ", "เครื่องชง", "เตา"],
    "household products": ["เฟอร์นิเจอร์", "เก้าอี้", "โต๊ะ", "เครื่องใช้ไฟฟ้า", "ของใช้ในบ้าน"],
    "home goods": ["เฟอร์นิเจอร์", "เก้าอี้", "โต๊ะ", "เครื่องใช้ไฟฟ้า"],
    "fitness": ["ฟิตเนส", "ออกกำลังกาย", "โยคะ", "ดัมเบล", "วิ่ง", "โปรตีน"],
    "sports": ["กีฬา", "ฟิตเนส", "ออกกำลังกาย"],
    "outdoor gear": ["เดินป่า", "แคมป์ปิ้ง", "กลางแจ้ง"],
    "fashion": ["เสื้อผ้า", "แฟชั่น", "กระเป๋า", "รองเท้า", "ชุดชั้นใน", "บรา"],
    "food": ["ขนม", "อาหาร", "ช็อกโกแลต", "เครื่องดื่ม", "ของหวาน"],
}


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_user_id() -> int:
    return session["user_id"]


def user_dir(user_id: int) -> Path:
    d = USERDATA_DIR / str(user_id)
    for sub in ("outputs", "outputs/thumbnails", "outputs/jobs", "uploads"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def get_client(user_id: int) -> gfr.Client:
    return gfr.Client(db.get_credential(user_id, "USEAPI_TOKEN"))


def raw_get(user_id: int, url: str) -> dict | None:
    token = db.get_credential(user_id, "USEAPI_TOKEN")
    if not token:
        return None
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/json",
        "User-Agent": "google-flow-rest-skill/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None


def record_flow_credits(user_id: int, api_result: dict) -> None:
    """Persist the credit balance embedded in a useapi.net response, if any,
    to the DB - so it survives a Render redeploy instead of only living in
    the (ephemeral, wiped-on-deploy) cached job JSON files."""
    credits = (api_result or {}).get("response", {}).get("remainingCredits")
    if credits is not None:
        db.set_flow_credits(user_id, credits)


def latest_flow_credits(user_id: int) -> int | None:
    stored = db.get_flow_credits(user_id)
    if stored is not None:
        return stored
    # Fallback for rows created before flow_credits existed / local dev.
    best_time, best_credits = "", None
    for job_file in (user_dir(user_id) / "outputs" / "jobs").glob("*.json"):
        try:
            data = json.loads(job_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        credits = data.get("response", {}).get("remainingCredits")
        updated = data.get("updated") or data.get("created") or ""
        if credits is not None and updated > best_time:
            best_time, best_credits = updated, credits
    return best_credits


def ffprobe_info(path: Path) -> dict:
    result = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-show_entries", "stream=width,height,codec_type", "-of", "json", str(path)],
        capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    width = height = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width, height = stream.get("width"), stream.get("height")
            break
    duration = float(data.get("format", {}).get("duration", 0))
    return {"duration": round(duration, 1), "width": width, "height": height}


def make_thumbnail(video_path: Path, thumb_path: Path) -> None:
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [FFMPEG, "-y", "-ss", "1", "-i", str(video_path), "-vframes", "1",
         "-vf", "scale=320:-1", str(thumb_path)],
        capture_output=True, check=True)


def apply_watermark(input_path: Path, watermark: dict) -> None:
    text = (watermark or {}).get("text", "").strip()
    logo = (watermark or {}).get("logo", "").strip()
    if not text and not logo:
        return
    position = (watermark or {}).get("position") or "bottom-right"
    opacity = float((watermark or {}).get("opacity") or 0.6)
    tmp_path = input_path.with_name(f"_wm_{uuid.uuid4().hex}.mp4")

    if logo and Path(logo).exists():
        pos_overlay = {
            "top-left": "10:10", "top-right": "W-w-10:10",
            "bottom-left": "10:H-h-10", "bottom-right": "W-w-10:H-h-10",
            "center": "(W-w)/2:(H-h)/2",
        }.get(position, "W-w-10:H-h-10")
        filter_complex = (f"[1:v]format=rgba,colorchannelmixer=aa={opacity}[wm];"
                           f"[0:v][wm]overlay={pos_overlay}")
        cmd = [FFMPEG, "-y", "-i", str(input_path), "-i", logo,
               "-filter_complex", filter_complex, "-codec:a", "copy", str(tmp_path)]
    else:
        pos_text = {
            "top-left": "x=10:y=10", "top-right": "x=w-text_w-10:y=10",
            "bottom-left": "x=10:y=h-text_h-10", "bottom-right": "x=w-text_w-10:y=h-text_h-10",
            "center": "x=(w-text_w)/2:y=(h-text_h)/2",
        }.get(position, "x=w-text_w-10:y=h-text_h-10")
        escaped = text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        font_arg = FONT_PATH.replace("\\", "/").replace(":", "\\:")
        vf = (f"drawtext=fontfile='{font_arg}':text='{escaped}':fontsize=28:"
              f"fontcolor=white@{opacity}:{pos_text}:shadowcolor=black@0.5:shadowx=1:shadowy=1")
        cmd = [FFMPEG, "-y", "-i", str(input_path), "-vf", vf, "-codec:a", "copy", str(tmp_path)]

    subprocess.run(cmd, capture_output=True, check=True, text=True)
    tmp_path.replace(input_path)


def upload_clip_to_storage(uid: int, video_path: Path, thumb_path: Path | None) -> dict:
    """Best-effort upload of a finished clip + thumbnail to Supabase Storage so
    it survives the next Render redeploy (local disk is wiped every deploy).
    Returns {} when Storage isn't configured, or on upload failure - the local
    /outputs/ copy still serves fine for this container's lifetime either way."""
    if not storage.enabled():
        return {}
    result = {}
    try:
        result["storage_url"] = storage.upload(video_path, f"{uid}/{video_path.name}")
        if thumb_path and thumb_path.exists():
            result["thumbnail_storage_url"] = storage.upload(thumb_path, f"{uid}/thumbnails/{thumb_path.name}")
    except Exception as exc:  # noqa: BLE001
        db.log_event(uid, "storage_upload_failed", file=video_path.name, error=str(exc))
    return result


def clip_view(clip: dict, outputs_dir: Path) -> dict:
    """Add ready-to-use url/thumbnail_url/exists fields to a clip row - prefers
    the persistent Storage URL (survives redeploys) and falls back to the
    local /outputs/ copy (only guaranteed for this container's lifetime)."""
    local_exists = (outputs_dir / clip["file"]).exists()
    url = clip.get("storage_url") or (f"/outputs/{clip['file']}" if local_exists else None)
    thumb = clip.get("thumbnail")
    thumb_url = clip.get("thumbnail_storage_url") or (
        f"/outputs/{thumb}" if thumb and (outputs_dir / thumb).exists() else None)
    return {**clip, "url": url, "thumbnail_url": thumb_url, "exists": bool(url)}


# ---------------------------------------------------------------------------
# Clip retention (Storage/DB usage grows forever otherwise - see Supabase
# free/Pro plan capacity planning: a 30-day rolling window keeps footprint
# roughly constant instead of accumulating every clip ever generated).
# ---------------------------------------------------------------------------

CLIP_RETENTION_DAYS = int(os.getenv("CLIP_RETENTION_DAYS", "30") or 0)


def cleanup_old_clips() -> int:
    """Delete clips older than CLIP_RETENTION_DAYS from local disk, Supabase
    Storage, and the DB. Returns how many were deleted. No-op if
    CLIP_RETENTION_DAYS <= 0 (retention disabled)."""
    if CLIP_RETENTION_DAYS <= 0:
        return 0
    cutoff = (datetime.now() - timedelta(days=CLIP_RETENTION_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    deleted = 0
    for clip in db.list_stale_clips(cutoff):
        uid = clip["user_id"]
        outputs_dir = user_dir(uid) / "outputs"
        for rel in (clip["file"], clip.get("thumbnail")):
            if rel:
                try:
                    (outputs_dir / rel).unlink(missing_ok=True)
                except OSError:
                    pass
        if clip.get("storage_url"):
            try:
                storage.delete(f"{uid}/{clip['file']}")
            except Exception:  # noqa: BLE001
                pass
        if clip.get("thumbnail_storage_url") and clip.get("thumbnail"):
            try:
                storage.delete(f"{uid}/{clip['thumbnail']}")
            except Exception:  # noqa: BLE001
                pass
        db.delete_clip(uid, clip["id"])
        db.log_event(uid, "clip_auto_deleted", file=clip["file"], retention_days=CLIP_RETENTION_DAYS)
        deleted += 1
    return deleted


def _retention_loop() -> None:
    while True:
        time.sleep(6 * 3600)
        try:
            cleanup_old_clips()
        except Exception:  # noqa: BLE001
            pass  # next tick tries again - a missed cleanup pass isn't urgent


threading.Thread(target=_retention_loop, daemon=True).start()


def slugify(name: str) -> str:
    ascii_only = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return ascii_only or "product"


AI_COPY_FIELDS = ["hook_line_1", "hook_line_2", "feature_tag_1", "feature_tag_2",
                   "feature_tag_3", "upgrade_hook_1", "upgrade_hook_2", "cta_text"]
AI_FILL_FIELDS = AI_COPY_FIELDS + ["presenter_desc"]


def autofill(brief: dict, uid: int | None = None) -> dict:
    brief = dict(brief)
    name = (brief.get("product_name") or "").strip() or "สินค้านี้"
    if not brief.get("product_id"):
        brief["product_id"] = slugify(name)
    if not brief.get("product_visual_desc"):
        brief["product_visual_desc"] = (
            f'the product exactly as shown in the attached reference photo (a product called '
            f'"{name}"), matching its real colors, materials, shape, and label/logo design precisely')

    # Reuse a previous autofill() result for this exact product_id first (e.g. the
    # user's own earlier preview of the same not-yet-generated product) so the copy
    # the customer approved in preview is exactly what ends up in the actual
    # generation - without this, calling the AI again at generate time would very
    # likely produce different text than what was just shown. Only trust a cached
    # brief for this if it was itself produced by the AI (_ai_copy_used) - a brief
    # saved before this feature existed (or from a static-fallback run) has the old
    # generic filler baked into every field, which would otherwise look identical
    # to "already resolved" and permanently block the AI from ever running again
    # for that product_id.
    if uid and any(not brief.get(f) for f in AI_FILL_FIELDS):
        cached = db.get_brief(uid, brief["product_id"])
        if cached and cached.get("_ai_copy_used"):
            for field in AI_FILL_FIELDS:
                if not brief.get(field) and cached.get(field):
                    brief[field] = cached[field]

    needs_ai_copy = any(not brief.get(f) for f in AI_FILL_FIELDS)
    ai_copy = ai_copywriter.generate_copy(name, brief.get("product_visual_desc", "")) \
        if needs_ai_copy and ai_copywriter.enabled() else None
    if ai_copy:
        brief["_ai_copy_used"] = True

    if not brief.get("presenter_desc"):
        scene = ai_copy["scene_setting_desc"] if ai_copy else "a bright clean modern room"
        brief["presenter_desc"] = ("a friendly, good-looking young Asian presenter with a warm "
                                    f"genuine smile, in {scene}")

    for field in AI_COPY_FIELDS:
        if not brief.get(field) and ai_copy:
            brief[field] = ai_copy[field]

    # Static fallback - always applied last, so a disabled/failed AI call (or one
    # that only returned some fields) never leaves anything blank.
    if not brief.get("hook_line_1"):
        brief["hook_line_1"] = f"ยังไม่มี {name}?"
    if not brief.get("hook_line_2"):
        brief["hook_line_2"] = "พลาดแล้วจะเสียใจ"
    if not brief.get("feature_tag_1"):
        brief["feature_tag_1"] = "คุณภาพดี"
    if not brief.get("feature_tag_2"):
        brief["feature_tag_2"] = "ใช้งานง่าย"
    if not brief.get("feature_tag_3"):
        brief["feature_tag_3"] = "คุ้มราคาสุดๆ"
    if not brief.get("upgrade_hook_1"):
        brief["upgrade_hook_1"] = f"อัปเกรด{name}"
    if not brief.get("upgrade_hook_2"):
        brief["upgrade_hook_2"] = "ให้ชีวิตดีขึ้น"
    if not brief.get("cta_text"):
        brief["cta_text"] = "พิกัดตะกร้าด้านล่างเลย"

    if uid and ai_copy:
        db.save_brief(uid, brief["product_id"], name, brief)
    return brief


def suggest_character(user_id: int, product_text: str) -> dict | None:
    characters = db.list_characters(user_id)
    text = product_text.lower()
    matched_categories = {cat for cat, keywords in CATEGORY_KEYWORDS.items()
                           if any(kw in text for kw in keywords)}
    if not matched_categories:
        return None
    best_char, best_score = None, 0
    for char in characters:
        best_for = (char.get("best_for") or "").lower()
        score = sum(1 for cat in matched_categories if cat in best_for)
        if score > best_score:
            best_char, best_score = char, score
    return best_char


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("กรอกชื่อผู้ใช้และรหัสผ่านให้ครบ")
            return render_template("register.html")
        try:
            user_id = db.create_user(username, password)
        except Exception:  # noqa: BLE001
            flash("ชื่อผู้ใช้นี้มีคนใช้แล้ว")
            return render_template("register.html")
        for char in DEFAULT_CHARACTERS:
            db.add_character(user_id, char)
        user_dir(user_id)
        session["user_id"] = user_id
        session["username"] = username
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.verify_user(username, password)
        if not user:
            flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            return render_template("login.html")
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Settings (per-user credentials)
# ---------------------------------------------------------------------------

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    uid = current_user_id()
    if request.method == "POST":
        for service in ("USEAPI_TOKEN", "GOOGLE_FLOW_EMAIL", "TIKTOK_ACCESS_TOKEN"):
            value = request.form.get(service, "").strip()
            if value:
                db.set_credential(uid, service, value)
        flash("บันทึกแล้ว")
        return redirect(url_for("settings"))
    connected_services = set(db.list_credential_services(uid))
    return render_template("settings.html", active="settings",
                            has_useapi="USEAPI_TOKEN" in connected_services,
                            has_flow_email="GOOGLE_FLOW_EMAIL" in connected_services,
                            has_tiktok="TIKTOK_ACCESS_TOKEN" in connected_services)


# ---------------------------------------------------------------------------
# Main pages
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def index():
    return render_template("create.html", genres=list(bbf.GENRES.keys()), active="create")


@app.route("/gallery")
@login_required
def gallery():
    return render_template("gallery.html", active="gallery")


@app.route("/log")
@login_required
def log_page():
    return render_template("log.html", active="log")


@app.route("/downloads")
@login_required
def downloads_page():
    return render_template("downloads.html", active="downloads")


ADMIN_USERNAMES = {u.strip() for u in os.getenv("ADMIN_USERNAMES", "").split(",") if u.strip()}


@app.context_processor
def inject_is_admin():
    return {"is_admin": session.get("username") in ADMIN_USERNAMES}


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        user = db.get_user(current_user_id())
        if not user or user["username"] not in ADMIN_USERNAMES:
            return jsonify({"error": "ไม่มีสิทธิ์เข้าถึงหน้านี้"}), 403
        return view(*args, **kwargs)
    return wrapped


@app.route("/admin")
@login_required
@admin_required
def admin_page():
    return render_template("admin.html", active="admin")


@app.route("/api/admin/overview")
@login_required
@admin_required
def api_admin_overview():
    return jsonify(db.admin_overview())


@app.route("/reports")
@login_required
def reports_page():
    return render_template("reports.html", active="reports")


@app.route("/guide")
@login_required
def guide_page():
    return render_template("guide.html", active="guide")


@app.route("/api/downloads")
@login_required
def api_downloads():
    uid = current_user_id()
    outputs_dir = user_dir(uid) / "outputs"
    clips = db.list_clips(uid)
    total_bytes = 0
    result = []
    for clip in clips:
        path = outputs_dir / clip["file"]
        size = path.stat().st_size if path.exists() else 0
        total_bytes += size
        result.append({**clip_view(clip, outputs_dir), "size_bytes": size})
    return jsonify({"clips": result, "total_bytes": total_bytes,
                     "retention_days": CLIP_RETENTION_DAYS})


@app.route("/api/downloads/<int:clip_id>", methods=["DELETE"])
@login_required
def api_delete_clip(clip_id: int):
    uid = current_user_id()
    clip = db.get_clip(uid, clip_id)
    if not clip:
        return jsonify({"error": "ไม่พบคลิปนี้"}), 404
    outputs_dir = user_dir(uid) / "outputs"
    for rel in (clip["file"], clip.get("thumbnail")):
        if rel:
            path = outputs_dir / rel
            if path.exists():
                path.unlink()
    db.delete_clip(uid, clip_id)
    db.log_event(uid, "clip_deleted", file=clip["file"], category=clip.get("category"))
    return jsonify({"ok": True})


def _read_clip_bytes(clip: dict, outputs_dir: Path) -> bytes | None:
    local_path = outputs_dir / clip["file"]
    if local_path.exists():
        return local_path.read_bytes()
    if clip.get("storage_url"):
        try:
            with urllib.request.urlopen(clip["storage_url"], timeout=60) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            return None
    return None


@app.route("/api/downloads/zip", methods=["POST"])
@login_required
def api_downloads_zip():
    uid = current_user_id()
    outputs_dir = user_dir(uid) / "outputs"
    clip_ids = (request.get_json(force=True) or {}).get("clip_ids") or []
    if not clip_ids:
        return jsonify({"error": "ไม่ได้เลือกไฟล์"}), 400

    buf = io.BytesIO()
    used_names: set[str] = set()
    added = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for clip_id in clip_ids:
            clip = db.get_clip(uid, clip_id)
            if not clip:
                continue
            data = _read_clip_bytes(clip, outputs_dir)
            if data is None:
                continue
            name = clip["file"]
            if name in used_names:  # defensive - clip filenames are unique in practice
                name = f"{clip_id}_{name}"
            used_names.add(name)
            zf.writestr(name, data)
            added += 1

    if not added:
        return jsonify({"error": "ไม่พบไฟล์ที่เลือกเลย (อาจถูกลบ/หมดอายุไปแล้ว)"}), 404

    db.log_event(uid, "downloads_zip", clip_count=added)
    buf.seek(0)
    return Response(buf.read(), mimetype="application/zip",
                     headers={"Content-Disposition": "attachment; filename=clips.zip"})


def _job_generation_seconds(logs: list[dict]) -> list[float]:
    """Pair job_submitted -> job_completed log entries by job_id to get real
    wall-clock generation time per clip (logs come back newest-first)."""
    submitted_at: dict[str, str] = {}
    seconds = []
    for entry in reversed(logs):
        jid = entry.get("job_id")
        if not jid:
            continue
        if entry["action"] == "job_submitted":
            submitted_at[jid] = entry["ts"]
        elif entry["action"] == "job_completed":
            start = submitted_at.pop(jid, None)
            if start:
                delta = (datetime.strptime(entry["ts"], "%Y-%m-%d %H:%M:%S") -
                          datetime.strptime(start, "%Y-%m-%d %H:%M:%S")).total_seconds()
                if delta > 0:
                    seconds.append(delta)
    return seconds


@app.route("/api/reports")
@login_required
def api_reports():
    uid = current_user_id()
    clips = db.list_clips(uid)
    logs = db.list_log(uid, limit=2000)

    by_category: dict[str, dict] = {}
    total_duration = 0.0
    for c in clips:
        cat = c.get("category") or "ไม่ระบุ"
        entry = by_category.setdefault(cat, {"count": 0, "duration": 0.0})
        entry["count"] += 1
        entry["duration"] += float(c.get("duration") or 0)
        total_duration += float(c.get("duration") or 0)

    by_day: dict[str, int] = {}
    for c in clips:
        day = (c.get("created_at") or "")[:10]
        if day:
            by_day[day] = by_day.get(day, 0) + 1

    action_counts: dict[str, int] = {}
    for entry in logs:
        action_counts[entry["action"]] = action_counts.get(entry["action"], 0) + 1

    submitted = action_counts.get("job_submitted", 0)
    completed = action_counts.get("job_completed", 0)
    failed = action_counts.get("job_failed", 0) + action_counts.get("job_submit_failed", 0)

    gen_seconds = _job_generation_seconds(logs)
    avg_gen_seconds = round(sum(gen_seconds) / len(gen_seconds), 1) if gen_seconds else None

    return jsonify({
        "total_clips": len(clips),
        "total_duration": round(total_duration, 1),
        "by_category": [{"category": k, **v} for k, v in
                         sorted(by_category.items(), key=lambda kv: -kv[1]["count"])],
        "by_day": [{"day": k, "count": v} for k, v in sorted(by_day.items())],
        "jobs_submitted": submitted,
        "jobs_completed": completed,
        "jobs_failed": failed,
        "success_rate": round(completed / submitted * 100, 1) if submitted else None,
        "avg_generation_seconds": avg_gen_seconds,
        "flow_remaining_credits": latest_flow_credits(uid),
    })


# ---------------------------------------------------------------------------
# API: preview / captions / characters
# ---------------------------------------------------------------------------

@app.route("/api/preview", methods=["POST"])
@login_required
def api_preview():
    uid = current_user_id()
    brief = autofill(request.get_json(force=True), uid)
    try:
        rows = bbf.build_rows(brief)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400
    db.log_event(uid, "preview", category=brief.get("product_name"), genre=brief.get("genre"))
    return jsonify({"segments": [
        {"id": r["id"], "prompt": r["prompt"], "model": r["model"],
         "aspect_ratio": r["aspect_ratio"], "resolution": r["resolution"], "duration": r["duration"]}
        for r in rows
    ]})


@app.route("/api/captions", methods=["POST"])
@login_required
def api_captions():
    uid = current_user_id()
    payload = request.get_json(force=True)
    brief = autofill(payload.get("brief") or {}, uid)
    platforms = payload.get("platforms") or ["tiktok", "facebook", "shopee"]
    result = caption_writer.generate(brief, platforms)
    db.log_event(uid, "captions_generated", category=brief.get("product_name"), platforms=platforms)
    return jsonify(result)


@app.route("/api/briefs")
@login_required
def api_briefs():
    """Products this user has generated before, newest first - lets captions
    (or a re-generate) be created later without retyping the whole brief."""
    return jsonify(db.list_briefs(current_user_id()))


@app.route("/api/briefs/<path:product_id>")
@login_required
def api_brief(product_id: str):
    brief = db.get_brief(current_user_id(), product_id)
    if not brief:
        return jsonify({"error": "ไม่พบข้อมูลสินค้านี้"}), 404
    return jsonify(brief)


@app.route("/api/characters")
@login_required
def api_characters():
    return jsonify(db.list_characters(current_user_id()))


@app.route("/api/suggest_character", methods=["POST"])
@login_required
def api_suggest_character():
    payload = request.get_json(force=True)
    text = f"{payload.get('product_name', '')} {payload.get('product_visual_desc', '')}"
    return jsonify({"character": suggest_character(current_user_id(), text)})


ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
UNSUPPORTED_IMAGE_MSG = ("รองรับเฉพาะไฟล์รูป .jpg .jpeg .png .webp เท่านั้น — ถ้าถ่ายจาก iPhone "
                          "แล้วได้ไฟล์ .heic ให้เปลี่ยนตั้งค่ากล้องเป็น \"Most Compatible\" "
                          "(Settings > Camera > Formats) แล้วถ่ายใหม่ หรือแปลงไฟล์เป็น .jpg ก่อนอัปโหลด")


@app.route("/api/upload_reference", methods=["POST"])
@login_required
def api_upload_reference():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file uploaded"}), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return jsonify({"error": UNSUPPORTED_IMAGE_MSG}), 400
    dest = user_dir(current_user_id()) / "uploads" / f"{uuid.uuid4().hex}{ext}"
    file.save(dest)
    return jsonify({"path": str(dest)})


@app.route("/api/flow_accounts")
@login_required
def api_flow_accounts():
    client = get_client(current_user_id())
    if not client.token:
        return jsonify({"emails": []})
    try:
        accounts = client.accounts()
    except Exception:  # noqa: BLE001
        return jsonify({"emails": []})
    return jsonify({"emails": list(accounts.keys())})


# ---------------------------------------------------------------------------
# API: generate / concatenate / status
# ---------------------------------------------------------------------------

def submit_brief_segments(uid: int, brief: dict, segment_ids: set[str]) -> list[dict]:
    """Core submission loop shared by the single-product form and batch upload.
    Returns a list of {segment_id, job_id, status} or {segment_id, error}."""
    category = brief.get("product_name") or brief.get("product_id") or "ไม่ระบุสินค้า"
    variant = brief.get("variant_label", "")
    watermark = {
        "text": brief.get("watermark_text", ""),
        "logo": brief.get("watermark_logo", ""),
        "position": brief.get("watermark_position") or "bottom-right",
        "opacity": brief.get("watermark_opacity") or 0.6,
    }
    account_email = brief.get("account_email") or db.get_credential(uid, "GOOGLE_FLOW_EMAIL")
    db.save_brief(uid, brief.get("product_id") or category, category, brief)

    rows = bbf.build_rows(brief)
    client = get_client(uid)
    outputs_dir = user_dir(uid) / "outputs"
    db.log_event(uid, "generate_request", category=category, segment_ids=sorted(segment_ids),
                 account_email=account_email, has_watermark=bool(watermark["text"] or watermark["logo"]))

    # Multiple genres for the same product produce multiple 3-segment sets in one
    # go (see build_rows' `genres` field) - label each with its genre so the
    # gallery/downloads pages can tell them apart instead of showing "3 clips"
    # with no way to know which style is which.
    multi_genre = len({r.get("genre") for r in rows if r.get("genre")}) > 1

    results = []
    for row in rows:
        if row["id"] not in segment_ids:
            continue
        row_variant = variant or (row.get("genre", "") if multi_genre else "")
        references = [row["reference_images"]] if row.get("reference_images") else []
        try:
            gfr.validate(row["model"], row["aspect_ratio"], row["resolution"],
                         int(row["duration"]), int(row["count"]))
            gfr_payload = gfr.build_payload(
                client, row["prompt"], row["model"], row["aspect_ratio"],
                row["resolution"], int(row["duration"]), int(row["count"]),
                account_email, "", references, do_upload=True)
            api_result = client.submit(gfr_payload)
            record_flow_credits(uid, api_result)
            jid = gfr.get_job_id(api_result)
            if not jid:
                raise RuntimeError("Submission returned no job ID")
            safe_name = gfr.safe_filename(jid)
            gfr.save_json(api_result, outputs_dir / "jobs" / f"{safe_name}.json")
            segment_label = {"a": "A - Hook", "b": "B - Feature", "c": "C - CTA"}.get(
                row["id"].rsplit("_", 1)[-1], row["id"])
            db.set_pending_job(jid, uid, category, segment_label, row_variant, watermark)
            db.log_event(uid, "job_submitted", job_id=jid, segment_id=row["id"], category=category)
            results.append({"segment_id": row["id"], "job_id": jid, "status": "submitted"})
        except Exception as exc:  # noqa: BLE001
            db.log_event(uid, "job_submit_failed", segment_id=row["id"], category=category, error=str(exc))
            results.append({"segment_id": row["id"], "error": str(exc)})
    return results


@app.route("/api/generate", methods=["POST"])
@login_required
def api_generate():
    uid = current_user_id()
    payload = request.get_json(force=True)
    brief = autofill(payload.get("brief") or {}, uid)
    segment_ids = set(payload.get("segment_ids") or [])

    client = get_client(uid)
    if not client.token:
        return jsonify({"error": "ยังไม่ได้ตั้งค่า USEAPI_TOKEN — ไปที่หน้า ตั้งค่า ก่อน"}), 400

    try:
        results = submit_brief_segments(uid, brief, segment_ids)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400

    return jsonify({"results": results})


# ---------------------------------------------------------------------------
# Batch (multiple products in one CSV upload)
# ---------------------------------------------------------------------------

BATCH_FIELDS = ["product_id", "product_name", "product_visual_desc", "presenter_desc",
                "hook_line_1", "hook_line_2", "feature_tag_1", "feature_tag_2", "feature_tag_3",
                "upgrade_hook_1", "upgrade_hook_2", "cta_text", "genre", "genres", "duration",
                "reference_image_filename", "product_link"]

BATCH_EXAMPLE_ROW = {
    "product_id": "my_product_01", "product_name": "หูฟังเกมมิ่ง XYZ",
    "product_visual_desc": "a black gaming headset with blue LED accents",
    "presenter_desc": "", "hook_line_1": "เสียงไม่อิน?", "hook_line_2": "ไมค์ไม่มา?",
    "feature_tag_1": "เสียงชัด", "feature_tag_2": "ใส่สบาย", "feature_tag_3": "ไฟสวย",
    "upgrade_hook_1": "อัปเกรดชุดเกม", "upgrade_hook_2": "ให้ได้เปรียบกว่าเดิม",
    "cta_text": "พิกัดตะกร้าด้านล่างเลย", "genre": "hook_feature_cta", "genres": "", "duration": "10",
    "reference_image_filename": "my_product_01.jpg", "product_link": "https://shopee.co.th/product/...",
}


def _read_batch_csv(file_storage) -> list[dict]:
    text = file_storage.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _batch_row_to_brief(row: dict, image_map: dict[str, str], uid: int | None = None) -> dict:
    brief = {k: (row.get(k) or "").strip() for k in BATCH_FIELDS if k != "reference_image_filename"}
    ref_name = (row.get("reference_image_filename") or "").strip()
    if ref_name and ref_name in image_map:
        brief["reference_image"] = image_map[ref_name]
    return autofill(brief, uid)


@app.route("/batch")
@login_required
def batch_page():
    return render_template("batch.html", active="batch")


@app.route("/api/batch_template")
@login_required
def api_batch_template():
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=BATCH_FIELDS)
    writer.writeheader()
    writer.writerow(BATCH_EXAMPLE_ROW)
    return Response(
        buf.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=batch_template.csv"})


@app.route("/api/batch_preview", methods=["POST"])
@login_required
def api_batch_preview():
    uid = current_user_id()
    file = request.files.get("csv")
    if not file:
        return jsonify({"error": "ไม่พบไฟล์ CSV"}), 400
    try:
        rows = _read_batch_csv(file)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"อ่านไฟล์ CSV ไม่ได้: {exc}"}), 400
    if not rows:
        return jsonify({"error": "ไฟล์ CSV ไม่มีข้อมูล"}), 400
    if len(rows) > 30:
        return jsonify({"error": f"รองรับสูงสุด 30 สินค้าต่อรอบ (ไฟล์นี้มี {len(rows)})"}), 400

    products = []
    total_segments = 0
    for row in rows:
        brief = _batch_row_to_brief(row, {}, uid)
        try:
            segment_count = len(bbf.build_rows(brief))
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": f"สินค้า {brief.get('product_id')}: {exc}"}), 400
        total_segments += segment_count
        products.append({
            "product_id": brief["product_id"],
            "product_name": brief["product_name"],
            "segment_count": segment_count,
            "has_reference_filename": bool((row.get("reference_image_filename") or "").strip()),
        })
    return jsonify({"products": products, "total_segments": total_segments})


@app.route("/api/batch_generate", methods=["POST"])
@login_required
def api_batch_generate():
    uid = current_user_id()
    client = get_client(uid)
    if not client.token:
        return jsonify({"error": "ยังไม่ได้ตั้งค่า USEAPI_TOKEN — ไปที่หน้า ตั้งค่า ก่อน"}), 400

    file = request.files.get("csv")
    if not file:
        return jsonify({"error": "ไม่พบไฟล์ CSV"}), 400
    try:
        rows = _read_batch_csv(file)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"อ่านไฟล์ CSV ไม่ได้: {exc}"}), 400
    if len(rows) > 30:
        return jsonify({"error": f"รองรับสูงสุด 30 สินค้าต่อรอบ (ไฟล์นี้มี {len(rows)})"}), 400

    # Validate all image formats up front - reject the whole batch before submitting
    # anything if any file is unsupported, rather than failing mid-way per product.
    image_files = [f for f in request.files.getlist("images") if f.filename]
    bad_files = [f.filename for f in image_files
                 if Path(f.filename).suffix.lower() not in ALLOWED_IMAGE_EXTS]
    if bad_files:
        return jsonify({"error": f"{UNSUPPORTED_IMAGE_MSG} (ไฟล์ที่มีปัญหา: {', '.join(bad_files)})"}), 400

    # Save uploaded reference images, keyed by their original filename
    image_map: dict[str, str] = {}
    for f in image_files:
        ext = Path(f.filename).suffix.lower()
        dest = user_dir(uid) / "uploads" / f"{uuid.uuid4().hex}{ext}"
        f.save(dest)
        image_map[f.filename] = str(dest)

    db.log_event(uid, "batch_generate_request", product_count=len(rows))

    all_results = []
    for row in rows:
        brief = _batch_row_to_brief(row, image_map, uid)
        try:
            segment_ids = {r["id"] for r in bbf.build_rows(brief)}
            product_results = submit_brief_segments(uid, brief, segment_ids)
        except Exception as exc:  # noqa: BLE001
            product_results = [{"segment_id": brief["product_id"], "error": str(exc)}]
        for r in product_results:
            r["product_id"] = brief["product_id"]
            r["product_name"] = brief["product_name"]
        all_results.extend(product_results)

    return jsonify({"results": all_results})


@app.route("/api/status/<path:job_id>")
@login_required
def api_job_status(job_id: str):
    uid = current_user_id()
    outputs_dir = user_dir(uid) / "outputs"
    client = get_client(uid)
    result = client.job(job_id)
    record_flow_credits(uid, result)
    status = str(result.get("status", "unknown")).lower()
    safe_name = gfr.safe_filename(job_id)
    gfr.save_json(result, outputs_dir / "jobs" / f"{safe_name}.json")

    file_url = None
    if status == "completed":
        try:
            media = gfr.get_media(result)
            existing = list(outputs_dir.glob(f"{safe_name}_*.mp4"))
            if existing:
                file_url = f"/outputs/{existing[0].name}"
            elif media and media[0].get("videoUrl"):
                out_path = outputs_dir / f"{safe_name}_01.mp4"
                gfr.download(media[0]["videoUrl"], out_path)
                file_url = f"/outputs/{out_path.name}"

            if file_url:
                fname = Path(file_url).name
                if not db.clip_exists(uid, fname):
                    video_path = outputs_dir / fname
                    meta = db.peek_pending_job(job_id) or {
                        "category": "ทดสอบ", "segment": fname, "variant": "", "watermark": {}}
                    try:
                        apply_watermark(video_path, meta.get("watermark"))
                    except subprocess.CalledProcessError as exc:
                        db.log_event(uid, "watermark_failed", job_id=job_id,
                                     error=exc.stderr[-300:] if exc.stderr else str(exc))

                    info = ffprobe_info(video_path)
                    thumb_name = video_path.stem + ".jpg"
                    thumb_path = outputs_dir / "thumbnails" / thumb_name
                    try:
                        make_thumbnail(video_path, thumb_path)
                    except subprocess.CalledProcessError:
                        thumb_name = None
                    storage_urls = upload_clip_to_storage(
                        uid, video_path, thumb_path if thumb_name else None)
                    db.add_clip(uid, {
                        "file": fname, "thumbnail": f"thumbnails/{thumb_name}" if thumb_name else None,
                        "category": meta["category"], "segment": meta["segment"],
                        "variant": meta["variant"], **info, **storage_urls,
                    })
                    db.delete_pending_job(job_id)
                    db.log_event(uid, "job_completed", job_id=job_id, category=meta["category"],
                                 segment=meta["segment"], file=fname, duration=info["duration"])
                    if storage_urls.get("storage_url"):
                        file_url = storage_urls["storage_url"]
        except Exception as exc:  # noqa: BLE001
            # The Flow job itself finished - only OUR post-processing (download /
            # ffmpeg / DB write) failed, often a transient network blip on Render.
            # Report back as still-processing so the frontend keeps polling and
            # retries automatically instead of this endpoint 500ing, which used
            # to silently kill the browser's poll loop for that one segment
            # (uncaught fetch/json errors there have no retry logic).
            db.log_event(uid, "status_processing_failed", job_id=job_id, error=str(exc))
            return jsonify({"status": "processing", "file_url": None})
    elif status == "failed":
        db.log_event(uid, "job_failed", job_id=job_id)

    return jsonify({"status": status, "file_url": file_url})


@app.route("/api/concatenate", methods=["POST"])
@login_required
def api_concatenate():
    uid = current_user_id()
    outputs_dir = user_dir(uid) / "outputs"
    payload = request.get_json(force=True)
    file_urls = payload.get("file_urls") or []
    category = payload.get("category") or "ไม่ระบุสินค้า"
    product_id = payload.get("product_id") or slugify(category)

    if len(file_urls) < 2:
        return jsonify({"error": "ต้องมีอย่างน้อย 2 คลิปถึงจะต่อได้"}), 400

    filenames = [Path(u).name for u in file_urls]
    for fname in filenames:
        if not (outputs_dir / fname).exists():
            return jsonify({"error": f"ไม่พบไฟล์ {fname}"}), 400

    list_lines = "\n".join(f"file '{(outputs_dir / f).resolve()}'" for f in filenames) + "\n"
    list_path = outputs_dir / f"_concat_{uuid.uuid4().hex}.txt"
    list_path.write_text(list_lines, encoding="utf-8")

    out_name = f"{product_id}_combined_{uuid.uuid4().hex[:8]}.mp4"
    out_path = outputs_dir / out_name
    try:
        subprocess.run(
            [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
             "-c", "copy", str(out_path)],
            capture_output=True, check=True, text=True)
    except subprocess.CalledProcessError as exc:
        return jsonify({"error": f"ffmpeg ต่อคลิปล้มเหลว: {exc.stderr[-400:]}"}), 500
    finally:
        list_path.unlink(missing_ok=True)

    info = ffprobe_info(out_path)
    thumb_name = out_path.stem + ".jpg"
    thumb_path = outputs_dir / "thumbnails" / thumb_name
    try:
        make_thumbnail(out_path, thumb_path)
    except subprocess.CalledProcessError:
        thumb_name = None

    storage_urls = upload_clip_to_storage(uid, out_path, thumb_path if thumb_name else None)
    db.add_clip(uid, {
        "file": out_name, "thumbnail": f"thumbnails/{thumb_name}" if thumb_name else None,
        "category": category, "segment": f"คลิปรวม {round(info['duration'])} วินาที",
        "variant": "", **info, **storage_urls,
    })
    db.log_event(uid, "concatenate", category=category, files=filenames, output=out_name, duration=info["duration"])

    file_url = storage_urls.get("storage_url") or f"/outputs/{out_name}"
    return jsonify({"file_url": file_url, **info})


# ---------------------------------------------------------------------------
# API: account status / manifest / log
# ---------------------------------------------------------------------------

@app.route("/api/account_status")
@login_required
def api_account_status():
    uid = current_user_id()
    account = raw_get(uid, "https://api.useapi.net/v1/account") or {}
    connected = account.get("accounts", {})

    minimax_equity = None
    if "MiniMax API" in connected:
        minimax_equity = raw_get(uid, "https://api.useapi.net/v1/minimax/speech/equity")

    all_services = ["Google Flow API", "MiniMax API", "Flow Music API", "Dreamina API",
                     "Kling API", "Runway API", "PixVerse API", "Mureka API",
                     "TemPolor API", "InsightFaceSwap API"]
    services = [{"name": s, "connected": s in connected,
                 "accounts": connected.get(s, {}).get("total", 0)} for s in all_services]

    return jsonify({
        "email": account.get("email"),
        "subscription_active": account.get("subscriptionIsActive", False),
        "services": services,
        "flow_remaining_credits": latest_flow_credits(uid),
        "minimax_equity": minimax_equity,
    })


@app.route("/api/manifest")
@login_required
def api_manifest():
    uid = current_user_id()
    outputs_dir = user_dir(uid) / "outputs"
    return jsonify([clip_view(c, outputs_dir) for c in db.list_clips(uid)])


@app.route("/api/log")
@login_required
def api_log():
    limit = request.args.get("limit", type=int) or 200
    return jsonify(db.list_log(current_user_id(), limit))


@app.route("/outputs/<path:filename>")
@login_required
def serve_outputs(filename: str):
    return send_from_directory(user_dir(current_user_id()) / "outputs", filename)


if __name__ == "__main__":
    db.init_db()
    print("Local dashboard: http://localhost:5000/")
    print("Gallery:         http://localhost:5000/gallery")
    app.run(host="127.0.0.1", port=5000, debug=False)
