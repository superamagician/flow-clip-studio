#!/usr/bin/env python3
"""One-time migration: move the old single-user flat-file data (.env,
characters.json, outputs/manifest.json + files, activity_log.jsonl) into the
new multi-user SQLite DB, under a fresh "admin" user account.

Run once:
    python migrate_legacy.py
"""
from __future__ import annotations
import json
import shutil
from pathlib import Path

import db

ROOT = Path(__file__).resolve().parent
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "changeme123"  # change this via a future "change password" feature


def load_env(path: Path) -> dict:
    result = {}
    if not path.exists():
        return result
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def main():
    db.init_db()

    existing = db.verify_user(ADMIN_USERNAME, ADMIN_PASSWORD)
    if existing:
        print(f"User '{ADMIN_USERNAME}' already exists (id={existing['id']}) - reusing it.")
        admin_id = existing["id"]
    else:
        admin_id = db.create_user(ADMIN_USERNAME, ADMIN_PASSWORD)
        print(f"Created user '{ADMIN_USERNAME}' (id={admin_id}), password: {ADMIN_PASSWORD}")

    user_root = ROOT / "userdata" / str(admin_id)
    user_outputs = user_root / "outputs"
    user_thumbs = user_outputs / "thumbnails"
    user_jobs = user_outputs / "jobs"
    user_uploads = user_root / "uploads"
    for d in (user_outputs, user_thumbs, user_jobs, user_uploads):
        d.mkdir(parents=True, exist_ok=True)

    # 1) credentials from .env
    env_vars = load_env(ROOT / ".env")
    for key in ("USEAPI_TOKEN", "GOOGLE_FLOW_EMAIL", "TIKTOK_ACCESS_TOKEN"):
        if env_vars.get(key):
            db.set_credential(admin_id, key, env_vars[key])
            print(f"Migrated credential: {key}")

    # 2) characters.json
    chars_path = ROOT / "characters.json"
    if chars_path.exists():
        characters = json.loads(chars_path.read_text(encoding="utf-8"))
        for char in characters:
            db.add_character(admin_id, char)
        print(f"Migrated {len(characters)} characters")

    # 3) outputs/manifest.json + actual video/thumbnail files
    old_outputs = ROOT / "outputs"
    manifest_path = old_outputs / "manifest.json"
    moved_files = 0
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for clip in manifest:
            src_file = old_outputs / clip["file"]
            if src_file.exists():
                dest_file = user_outputs / clip["file"]
                if not dest_file.exists():
                    shutil.copy2(src_file, dest_file)
                    moved_files += 1
            if clip.get("thumbnail"):
                src_thumb = old_outputs / clip["thumbnail"]
                if src_thumb.exists():
                    dest_thumb = user_outputs / clip["thumbnail"]
                    dest_thumb.parent.mkdir(parents=True, exist_ok=True)
                    if not dest_thumb.exists():
                        shutil.copy2(src_thumb, dest_thumb)
            if not db.clip_exists(admin_id, clip["file"]):
                db.add_clip(admin_id, clip)
        print(f"Migrated {len(manifest)} manifest entries ({moved_files} new files copied)")

    # 3b) job logs (needed for credit-balance lookups)
    old_jobs = old_outputs / "jobs"
    if old_jobs.exists():
        count = 0
        for job_file in old_jobs.glob("*.json"):
            dest = user_jobs / job_file.name
            if not dest.exists():
                shutil.copy2(job_file, dest)
                count += 1
        print(f"Migrated {count} job log files")

    # 4) activity_log.jsonl
    log_path = old_outputs / "activity_log.jsonl"
    if log_path.exists():
        count = 0
        for line in log_path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            action = entry.pop("action", "unknown")
            entry.pop("ts", None)
            db.log_event(admin_id, action, **entry)
            count += 1
        print(f"Migrated {count} activity log entries")

    print(f"\nDone. Log in at http://localhost:5000/login with username='{ADMIN_USERNAME}' "
          f"password='{ADMIN_PASSWORD}' (change this password once a change-password feature exists).")


if __name__ == "__main__":
    main()
