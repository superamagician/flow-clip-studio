#!/usr/bin/env python3
"""Optional persistent object storage (Supabase Storage) for generated clips.

Render's web service runs on ephemeral local disk: every deploy/restart
recreates the container from the Docker image, wiping anything saved only
under userdata/<user_id>/outputs/. That's what made old clips disappear
from the gallery after a routine bug-fix deploy.

When SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are set, finished clips and
thumbnails are also uploaded to a Supabase Storage bucket and served from
a stable public URL that survives redeploys. When they're not set (e.g.
local dev), upload() is a no-op and the app just keeps serving from the
local /outputs/ route as before.
"""
from __future__ import annotations
import os
import urllib.error
import urllib.request
from pathlib import Path

EXT_MIME = {".mp4": "video/mp4", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def _config() -> tuple[str, str, str]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "clips")
    return url, key, bucket


def enabled() -> bool:
    url, key, _ = _config()
    return bool(url and key)


def public_url(object_path: str) -> str | None:
    url, _, bucket = _config()
    if not url:
        return None
    return f"{url}/storage/v1/object/public/{bucket}/{object_path}"


def upload(local_path: Path, object_path: str) -> str | None:
    """Upload local_path to Supabase Storage at object_path. Returns the
    public URL on success, or None if Storage isn't configured. Raises on
    a real upload failure so the caller can log it — the local copy still
    works for the lifetime of this container either way."""
    url, key, bucket = _config()
    if not url or not key:
        return None
    mime = EXT_MIME.get(local_path.suffix.lower(), "application/octet-stream")
    endpoint = f"{url}/storage/v1/object/{bucket}/{object_path}"
    req = urllib.request.Request(
        endpoint, data=local_path.read_bytes(), method="POST",
        headers={"Authorization": f"Bearer {key}", "apikey": key,
                 "Content-Type": mime, "x-upsert": "true"})
    try:
        with urllib.request.urlopen(req, timeout=120):
            pass
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase Storage upload failed: HTTP {exc.code} {detail}") from exc
    return public_url(object_path)
