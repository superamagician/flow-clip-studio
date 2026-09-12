#!/usr/bin/env python3
"""One-time migration: copy the Phase-1 local SQLite DB (app.db) into the new
Supabase Postgres DB (db.py, now Postgres-only).

Prerequisite: DATABASE_URL must be set (in .env or the shell environment)
pointing at your Supabase Postgres connection string.

Run once:
    python migrate_sqlite_to_supabase.py
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path

import db  # the new Postgres-backed module

ROOT = Path(__file__).resolve().parent
SQLITE_PATH = ROOT / "app.db"


def main():
    if not SQLITE_PATH.exists():
        raise SystemExit(f"No local SQLite DB found at {SQLITE_PATH} - nothing to migrate.")

    db.init_db()  # create tables in Postgres if they don't exist yet

    src = sqlite3.connect(SQLITE_PATH)
    src.row_factory = sqlite3.Row

    # 1) users - re-insert with the SAME password hash so existing passwords keep working
    user_id_map: dict[int, int] = {}
    users = src.execute("SELECT * FROM users").fetchall()
    with db.get_conn() as conn, conn.cursor() as cur:
        for u in users:
            cur.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (%s, %s, %s) "
                "ON CONFLICT (username) DO UPDATE SET username=EXCLUDED.username RETURNING id",
                (u["username"], u["password_hash"], u["created_at"]))
            user_id_map[u["id"]] = cur.fetchone()["id"]
        conn.commit()
    print(f"Migrated {len(users)} users")

    # 2) credentials (already encrypted with the SAME master key -> copy ciphertext as-is)
    creds = src.execute("SELECT * FROM credentials").fetchall()
    with db.get_conn() as conn, conn.cursor() as cur:
        for c in creds:
            new_uid = user_id_map[c["user_id"]]
            cur.execute(
                "INSERT INTO credentials (user_id, service, encrypted_value, updated_at) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (user_id, service) DO UPDATE SET "
                "encrypted_value=EXCLUDED.encrypted_value, updated_at=EXCLUDED.updated_at",
                (new_uid, c["service"], c["encrypted_value"], c["updated_at"]))
        conn.commit()
    print(f"Migrated {len(creds)} credentials "
          f"(IMPORTANT: MASTER_KEY in the new environment must match the old .master.key file "
          f"or these will fail to decrypt)")

    # 3) characters
    chars = src.execute("SELECT * FROM characters").fetchall()
    for c in chars:
        db.add_character(user_id_map[c["user_id"]], dict(c))
    print(f"Migrated {len(chars)} characters")

    # 4) clips (metadata only - actual video files still need to move to Supabase Storage
    # or stay on the deployed server's disk; see the storage-migration follow-up)
    clips = src.execute("SELECT * FROM clips").fetchall()
    for c in clips:
        db.add_clip(user_id_map[c["user_id"]], dict(c))
    print(f"Migrated {len(clips)} clip records (metadata only - copy the actual video files separately)")

    # 5) activity_log
    logs = src.execute("SELECT * FROM activity_log ORDER BY id").fetchall()
    with db.get_conn() as conn, conn.cursor() as cur:
        for entry in logs:
            cur.execute(
                "INSERT INTO activity_log (user_id, ts, action, details) VALUES (%s, %s, %s, %s)",
                (user_id_map[entry["user_id"]], entry["ts"], entry["action"], entry["details"]))
        conn.commit()
    print(f"Migrated {len(logs)} activity log entries")

    src.close()
    print("\nDone. Verify by logging in with your existing admin username/password against "
          "the new DATABASE_URL.")


if __name__ == "__main__":
    main()
