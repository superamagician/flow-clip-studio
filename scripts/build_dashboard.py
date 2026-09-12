#!/usr/bin/env python3
"""Build a local dashboard (manifest.json + thumbnails) for all generated clips.

Usage:
    python build_dashboard.py

Run from the project root (where outputs/ lives). Writes:
    outputs/manifest.json
    outputs/thumbnails/<clip>.jpg
    outputs/index.html  (static dashboard page)

Then serve it locally:
    cd outputs
    python -m http.server 8000
    # open http://localhost:8000/
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

_FFMPEG_BIN = (Path(r"C:\Users\KJ\AppData\Local\Microsoft\WinGet\Packages") /
               "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe" /
               "ffmpeg-9.0.1-full_build" / "bin")
FFPROBE = str(_FFMPEG_BIN / "ffprobe.exe")
FFMPEG = str(_FFMPEG_BIN / "ffmpeg.exe")

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
THUMBS_DIR = OUTPUTS_DIR / "thumbnails"

# Hand-maintained catalog: job-id prefix (as it appears in the downloaded filename)
# -> display metadata. Add a new entry here every time a new product/job is generated.
CATALOG = [
    # KOTION EACH G2000 gaming headset
    {"prefix": "j0912062620321278481", "category": "หูฟังเกมมิ่ง KOTION EACH G2000",
     "segment": "A - Hook", "variant": ""},
    {"prefix": "j0912063124096591242", "category": "หูฟังเกมมิ่ง KOTION EACH G2000",
     "segment": "B - Feature", "variant": ""},
    {"prefix": "j0912063142645826435", "category": "หูฟังเกมมิ่ง KOTION EACH G2000",
     "segment": "C - CTA", "variant": ""},
    # Duchess CM4200 espresso machine
    {"prefix": "j0912065329330243006", "category": "เครื่องชงกาแฟ Duchess CM4200",
     "segment": "A - Hook", "variant": ""},
    {"prefix": "j0912065343679153171", "category": "เครื่องชงกาแฟ Duchess CM4200",
     "segment": "B - Feature", "variant": ""},
    {"prefix": "j0912065400591562000", "category": "เครื่องชงกาแฟ Duchess CM4200",
     "segment": "C - CTA", "variant": ""},
    # Magiclean floor cleaner
    {"prefix": "j0912065906514974872", "category": "น้ำยาถูพื้น Magiclean ลาเวนเดอร์",
     "segment": "A - Hook", "variant": ""},
    {"prefix": "j0912065921373153365", "category": "น้ำยาถูพื้น Magiclean ลาเวนเดอร์",
     "segment": "B - Feature", "variant": ""},
    {"prefix": "j0912065934942335116", "category": "น้ำยาถูพื้น Magiclean ลาเวนเดอร์",
     "segment": "C - CTA", "variant": ""},
    # Samsinte rocking chair - v1 (no reference image)
    {"prefix": "j0912070429003491707", "category": "เก้าอี้โยก Samsinte",
     "segment": "A - Hook", "variant": "ไม่มี reference image"},
    {"prefix": "j0912070442318350374", "category": "เก้าอี้โยก Samsinte",
     "segment": "B - Feature", "variant": "ไม่มี reference image"},
    {"prefix": "j0912070458403776630", "category": "เก้าอี้โยก Samsinte",
     "segment": "C - CTA", "variant": "ไม่มี reference image"},
    # Samsinte rocking chair - v2 (with reference image, matched product)
    {"prefix": "j0912071134208736540", "category": "เก้าอี้โยก Samsinte",
     "segment": "A - Hook", "variant": "มี reference image (ตรงปก)"},
    {"prefix": "j0912071413900233317", "category": "เก้าอี้โยก Samsinte",
     "segment": "B - Feature", "variant": "มี reference image (ตรงปก)"},
    {"prefix": "j0912071435816899574", "category": "เก้าอี้โยก Samsinte",
     "segment": "C - CTA", "variant": "มี reference image (ตรงปก)"},
    # LYO hair set - v1 (full promo poster as reference, weak product match)
    {"prefix": "j0912072220771739862", "category": "LYO เซตแก้ผมร่วง",
     "segment": "A - Hook", "variant": "reference = โปสเตอร์เต็ม (ไม่ตรงปก)"},
    # LYO hair set - v2 (cropped single-bottle reference, strong match)
    {"prefix": "j0912072912981090875", "category": "LYO เซตแก้ผมร่วง",
     "segment": "A - Hook", "variant": "reference = ครอปขวดเดี่ยว (ตรงปก)"},
    {"prefix": "j0912073211883047722", "category": "LYO เซตแก้ผมร่วง",
     "segment": "B - Feature", "variant": "reference = ครอปขวดเดี่ยว (ตรงปก)"},
    {"prefix": "j0912073232867607657", "category": "LYO เซตแก้ผมร่วง",
     "segment": "C - CTA", "variant": "reference = ครอปขวดเดี่ยว (ตรงปก)"},
]

COMBINED_CATALOG = {
    "combined_ABC_30s.mp4": "หูฟังเกมมิ่ง KOTION EACH G2000",
    "lyo_combined_30s.mp4": "LYO เซตแก้ผมร่วง",
}


def ffprobe_info(path: Path) -> dict:
    result = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-show_entries", "stream=width,height,codec_type",
         "-of", "json", str(path)],
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


def main():
    if not OUTPUTS_DIR.exists():
        raise SystemExit(f"outputs/ not found at {OUTPUTS_DIR}")

    by_prefix = {entry["prefix"]: entry for entry in CATALOG}
    manifest = []

    for mp4 in sorted(OUTPUTS_DIR.glob("*.mp4")):
        info = ffprobe_info(mp4)
        thumb_name = mp4.stem + ".jpg"
        thumb_path = THUMBS_DIR / thumb_name
        if not thumb_path.exists():
            try:
                make_thumbnail(mp4, thumb_path)
            except subprocess.CalledProcessError:
                thumb_name = None

        if mp4.name in COMBINED_CATALOG:
            manifest.append({
                "file": mp4.name,
                "thumbnail": f"thumbnails/{thumb_name}" if thumb_name else None,
                "category": COMBINED_CATALOG[mp4.name],
                "segment": "คลิปรวม 30 วินาที",
                "variant": "",
                **info,
            })
            continue

        entry = next((e for prefix, e in by_prefix.items() if prefix in mp4.name), None)
        if entry is None:
            manifest.append({
                "file": mp4.name,
                "thumbnail": f"thumbnails/{thumb_name}" if thumb_name else None,
                "category": "ยังไม่จัดหมวด",
                "segment": mp4.name,
                "variant": "",
                **info,
            })
            continue

        manifest.append({
            "file": mp4.name,
            "thumbnail": f"thumbnails/{thumb_name}" if thumb_name else None,
            "category": entry["category"],
            "segment": entry["segment"],
            "variant": entry["variant"],
            **info,
        })

    manifest_path = OUTPUTS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(manifest)} clips to {manifest_path}")


if __name__ == "__main__":
    main()
