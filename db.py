#!/usr/bin/env python3
"""Postgres (Supabase)-backed multi-user data layer.

Same function signatures as the original SQLite version, so app.py doesn't
need to change how it calls into this module. Connection comes from the
DATABASE_URL env var (Supabase: Project Settings -> Database -> Connection
string -> URI). The Fernet master key for encrypting stored credentials comes
from the MASTER_KEY env var in production (falls back to a local file for
local dev, matching the Phase-1 behavior).
"""
from __future__ import annotations
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
import psycopg2.extras
from cryptography.fernet import Fernet
from werkzeug.security import check_password_hash, generate_password_hash

ROOT = Path(__file__).resolve().parent
MASTER_KEY_PATH = ROOT / ".master.key"


def _get_or_create_master_key() -> bytes:
    env_key = os.environ.get("MASTER_KEY")
    if env_key:
        return env_key.encode("utf-8") if isinstance(env_key, str) else env_key
    if MASTER_KEY_PATH.exists():
        return MASTER_KEY_PATH.read_bytes()
    key = Fernet.generate_key()
    MASTER_KEY_PATH.write_bytes(key)
    try:
        os.chmod(MASTER_KEY_PATH, 0o600)
    except OSError:
        pass
    return key


_FERNET = Fernet(_get_or_create_master_key())


def encrypt(plaintext: str) -> str:
    return _FERNET.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    return _FERNET.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


@contextmanager
def get_conn():
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Point it at your Supabase Postgres connection "
            "string (Project Settings -> Database -> Connection string -> URI).")
    conn = psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS credentials (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            service TEXT NOT NULL,
            encrypted_value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, service)
        );

        CREATE TABLE IF NOT EXISTS characters (
            id TEXT NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            gender TEXT, age_range TEXT, style_archetype TEXT,
            appearance TEXT, wardrobe TEXT, energy TEXT,
            presenter_desc TEXT, best_for TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (id, user_id)
        );

        CREATE TABLE IF NOT EXISTS clips (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            file TEXT NOT NULL,
            thumbnail TEXT,
            category TEXT, segment TEXT, variant TEXT,
            duration REAL, width INTEGER, height INTEGER,
            created_at TEXT NOT NULL,
            storage_url TEXT,
            thumbnail_storage_url TEXT,
            product_id TEXT
        );
        ALTER TABLE clips ADD COLUMN IF NOT EXISTS storage_url TEXT;
        ALTER TABLE clips ADD COLUMN IF NOT EXISTS thumbnail_storage_url TEXT;
        ALTER TABLE clips ADD COLUMN IF NOT EXISTS product_id TEXT;

        CREATE TABLE IF NOT EXISTS activity_log (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            ts TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT
        );

        CREATE TABLE IF NOT EXISTS pending_jobs (
            job_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            category TEXT, segment TEXT, variant TEXT, watermark TEXT,
            created_at TEXT NOT NULL,
            product_id TEXT
        );
        ALTER TABLE pending_jobs ADD COLUMN IF NOT EXISTS product_id TEXT;

        -- Latest known Flow credit balance per user. Previously this was
        -- read live from cached job JSON files under userdata/<uid>/outputs/jobs/,
        -- which lives on Render's ephemeral disk and disappears on every
        -- deploy just like clip files did - hence the credits pill going
        -- blank after a redeploy even though nothing was actually wrong.
        CREATE TABLE IF NOT EXISTS flow_credits (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            credits INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Full brief (hook lines, feature tags, CTA, etc.) saved every time a
        -- product is generated, keyed by product_id - lets captions (or a
        -- re-generate) be created later for a past product without retyping
        -- everything from scratch.
        CREATE TABLE IF NOT EXISTS briefs (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            product_id TEXT NOT NULL,
            category TEXT,
            brief_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, product_id)
        );

        -- clips/activity_log have no user_id-leading key (clips/activity_log PK is
        -- just id; characters' PK leads with id not user_id) so every per-user
        -- listing query does a full table scan without these.
        CREATE INDEX IF NOT EXISTS idx_clips_user_id ON clips (user_id);
        CREATE INDEX IF NOT EXISTS idx_activity_log_user_id ON activity_log (user_id);
        CREATE INDEX IF NOT EXISTS idx_characters_user_id ON characters (user_id);
        """)
        conn.commit()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def create_user(username: str, password: str) -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (%s, %s, %s) RETURNING id",
            (username, generate_password_hash(password), time.strftime("%Y-%m-%d %H:%M:%S")))
        user_id = cur.fetchone()["id"]
        conn.commit()
        return user_id


def verify_user(username: str, password: str) -> dict | None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        if row and check_password_hash(row["password_hash"], password):
            return dict(row)
        return None


def get_user(user_id: int) -> dict | None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Credentials (encrypted at rest)
# ---------------------------------------------------------------------------

def set_credential(user_id: int, service: str, value: str) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO credentials (user_id, service, encrypted_value, updated_at) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (user_id, service) DO UPDATE SET encrypted_value = EXCLUDED.encrypted_value, "
            "updated_at = EXCLUDED.updated_at",
            (user_id, service, encrypt(value), time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()


def get_credential(user_id: int, service: str) -> str:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT encrypted_value FROM credentials WHERE user_id = %s AND service = %s",
            (user_id, service))
        row = cur.fetchone()
        return decrypt(row["encrypted_value"]) if row else ""


def list_credential_services(user_id: int) -> list[str]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT service FROM credentials WHERE user_id = %s", (user_id,))
        return [r["service"] for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Characters
# ---------------------------------------------------------------------------

def list_characters(user_id: int) -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM characters WHERE user_id = %s ORDER BY created_at", (user_id,))
        return [dict(r) for r in cur.fetchall()]


def add_character(user_id: int, char: dict) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO characters (id, user_id, name, gender, age_range, style_archetype, "
            "appearance, wardrobe, energy, presenter_desc, best_for, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (id, user_id) DO UPDATE SET name=EXCLUDED.name, gender=EXCLUDED.gender, "
            "age_range=EXCLUDED.age_range, style_archetype=EXCLUDED.style_archetype, "
            "appearance=EXCLUDED.appearance, wardrobe=EXCLUDED.wardrobe, energy=EXCLUDED.energy, "
            "presenter_desc=EXCLUDED.presenter_desc, best_for=EXCLUDED.best_for",
            (char["id"], user_id, char["name"], char.get("gender", ""), char.get("age_range", ""),
             char.get("style_archetype", ""), char.get("appearance", ""), char.get("wardrobe", ""),
             char.get("energy", ""), char.get("presenter_desc", ""), char.get("best_for", ""),
             char.get("created") or time.strftime("%Y-%m-%d")))
        conn.commit()


# ---------------------------------------------------------------------------
# Clips / manifest
# ---------------------------------------------------------------------------

def add_clip(user_id: int, clip: dict) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO clips (user_id, file, thumbnail, category, segment, variant, "
            "duration, width, height, created_at, storage_url, thumbnail_storage_url, product_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (user_id, clip["file"], clip.get("thumbnail"), clip.get("category"),
             clip.get("segment"), clip.get("variant"), clip.get("duration"),
             clip.get("width"), clip.get("height"), time.strftime("%Y-%m-%d %H:%M:%S"),
             clip.get("storage_url"), clip.get("thumbnail_storage_url"), clip.get("product_id")))
        conn.commit()


def clip_exists(user_id: int, file: str) -> bool:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM clips WHERE user_id = %s AND file = %s", (user_id, file))
        return cur.fetchone() is not None


def get_clip(user_id: int, clip_id: int) -> dict | None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM clips WHERE user_id = %s AND id = %s", (user_id, clip_id))
        row = cur.fetchone()
        return dict(row) if row else None


def delete_clip(user_id: int, clip_id: int) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM clips WHERE user_id = %s AND id = %s", (user_id, clip_id))
        conn.commit()


def list_clips(user_id: int) -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM clips WHERE user_id = %s ORDER BY created_at", (user_id,))
        return [dict(r) for r in cur.fetchall()]


def list_stale_clips(cutoff_ts: str) -> list[dict]:
    """All clips (any user) older than cutoff_ts - for the retention cleanup job."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM clips WHERE created_at < %s", (cutoff_ts,))
        return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

def log_event(user_id: int, action: str, **details) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO activity_log (user_id, ts, action, details) VALUES (%s, %s, %s, %s)",
            (user_id, time.strftime("%Y-%m-%d %H:%M:%S"), action,
             json.dumps(details, ensure_ascii=False)))
        conn.commit()


def admin_overview(days: int = 30) -> dict:
    """Platform-wide counts for the admin monitoring page - deliberately
    cheap (no byte-size accounting; check the Supabase dashboard directly
    for exact Storage/DB usage against plan quotas)."""
    since = (datetime_now_minus_days(days))
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM users")
        total_users = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) AS n FROM clips")
        total_clips = cur.fetchone()["n"]

        cur.execute(
            "SELECT action, COUNT(*) AS n FROM activity_log "
            "WHERE ts > %s AND action IN "
            "('job_submitted', 'job_completed', 'job_failed', 'job_submit_failed', 'clip_auto_deleted') "
            "GROUP BY action", (since,))
        action_counts = {r["action"]: r["n"] for r in cur.fetchall()}

        cur.execute(
            "SELECT a.ts, a.action, a.details, u.username FROM activity_log a "
            "JOIN users u ON u.id = a.user_id "
            "WHERE a.action IN ('job_failed', 'job_submit_failed', 'storage_upload_failed') "
            "ORDER BY a.id DESC LIMIT 25")
        recent_failures = [
            {"ts": r["ts"], "action": r["action"], "username": r["username"],
             **json.loads(r["details"] or "{}")}
            for r in cur.fetchall()]

    return {
        "total_users": total_users,
        "total_clips": total_clips,
        "window_days": days,
        "jobs_submitted": action_counts.get("job_submitted", 0),
        "jobs_completed": action_counts.get("job_completed", 0),
        "jobs_failed": action_counts.get("job_failed", 0) + action_counts.get("job_submit_failed", 0),
        "clips_auto_deleted": action_counts.get("clip_auto_deleted", 0),
        "recent_failures": recent_failures,
    }


def datetime_now_minus_days(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def list_log(user_id: int, limit: int = 200) -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM activity_log WHERE user_id = %s ORDER BY id DESC LIMIT %s",
            (user_id, limit))
        result = []
        for r in cur.fetchall():
            entry = {"ts": r["ts"], "action": r["action"]}
            entry.update(json.loads(r["details"] or "{}"))
            result.append(entry)
        return result


# ---------------------------------------------------------------------------
# Pending jobs (persisted across restarts, unlike the old in-memory dict)
# ---------------------------------------------------------------------------

def set_pending_job(job_id: str, user_id: int, category: str, segment: str,
                     variant: str, watermark: dict, product_id: str = "") -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pending_jobs (job_id, user_id, category, segment, variant, watermark, "
            "created_at, product_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (job_id) DO UPDATE SET category=EXCLUDED.category, segment=EXCLUDED.segment, "
            "variant=EXCLUDED.variant, watermark=EXCLUDED.watermark, product_id=EXCLUDED.product_id",
            (job_id, user_id, category, segment, variant, json.dumps(watermark or {}),
             time.strftime("%Y-%m-%d %H:%M:%S"), product_id))
        conn.commit()


def pop_pending_job(job_id: str) -> dict | None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM pending_jobs WHERE job_id = %s", (job_id,))
        row = cur.fetchone()
        if not row:
            return None
        cur.execute("DELETE FROM pending_jobs WHERE job_id = %s", (job_id,))
        conn.commit()
        result = dict(row)
        result["watermark"] = json.loads(result.get("watermark") or "{}")
        return result


def peek_pending_job(job_id: str) -> dict | None:
    """Like pop_pending_job but doesn't delete - lets the caller finish all
    processing (download/ffmpeg/DB write) before removing it, so a retry
    after a mid-way failure still has the real category/segment/watermark
    instead of falling back to a generic placeholder."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM pending_jobs WHERE job_id = %s", (job_id,))
        row = cur.fetchone()
        if not row:
            return None
        result = dict(row)
        result["watermark"] = json.loads(result.get("watermark") or "{}")
        return result


def delete_pending_job(job_id: str) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM pending_jobs WHERE job_id = %s", (job_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# Flow credit balance (persisted so a Render redeploy doesn't blank it out -
# see flow_credits table comment in init_db)
# ---------------------------------------------------------------------------

def set_flow_credits(user_id: int, credits: int) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO flow_credits (user_id, credits, updated_at) VALUES (%s, %s, %s) "
            "ON CONFLICT (user_id) DO UPDATE SET credits = EXCLUDED.credits, updated_at = EXCLUDED.updated_at",
            (user_id, credits, time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()


def get_flow_credits(user_id: int) -> int | None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT credits FROM flow_credits WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return row["credits"] if row else None


# ---------------------------------------------------------------------------
# Saved briefs (for regenerating captions/clips for a past product later)
# ---------------------------------------------------------------------------

def save_brief(user_id: int, product_id: str, category: str, brief: dict) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO briefs (user_id, product_id, category, brief_json, updated_at) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (user_id, product_id) DO UPDATE SET category = EXCLUDED.category, "
            "brief_json = EXCLUDED.brief_json, updated_at = EXCLUDED.updated_at",
            (user_id, product_id, category, json.dumps(brief, ensure_ascii=False),
             time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()


def list_briefs(user_id: int) -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT product_id, category, updated_at FROM briefs "
            "WHERE user_id = %s ORDER BY updated_at DESC", (user_id,))
        return [dict(r) for r in cur.fetchall()]


def get_brief(user_id: int, product_id: str) -> dict | None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT brief_json FROM briefs WHERE user_id = %s AND product_id = %s",
            (user_id, product_id))
        row = cur.fetchone()
        return json.loads(row["brief_json"]) if row else None
