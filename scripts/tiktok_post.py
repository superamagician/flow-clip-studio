#!/usr/bin/env python3
"""Minimal TikTok Content Posting API client (Direct Post, FILE_UPLOAD method).

Prerequisites (you must do these yourself — see TikTok for Developers):
  1. Register an app at https://developers.tiktok.com
  2. Add the "Content Posting API" product to the app; enable Direct Post
  3. Complete OAuth for your own TikTok account with scope `video.publish`
  4. Put the resulting values in this project's .env:
       TIKTOK_ACCESS_TOKEN=...

Until your app passes TikTok's audit, every post is forced to SELF_ONLY
(private) regardless of what you request — this script defaults to
SELF_ONLY for that reason; only raise privacy_level after your app is audited
and you've confirmed the platform's content policies for what you're posting.

Usage:
    python tiktok_post.py --env .env publish path\to\clip.mp4 --title "..." [--privacy SELF_ONLY]
    python tiktok_post.py --env .env status PUBLISH_ID
"""
from __future__ import annotations
import argparse
import json
import os
import time
from pathlib import Path
import urllib.error
import urllib.request

BASE = "https://open.tiktokapis.com"
PRIVACY_LEVELS = {"PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY"}
TERMINAL = {"PUBLISH_COMPLETE", "FAILED"}
MAX_SINGLE_CHUNK = 64 * 1024 * 1024  # TikTok allows up to 64MB in one chunk for small files


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def request(method: str, path: str, token: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc


def init_post(token: str, video_path: Path, title: str, privacy_level: str) -> dict:
    if privacy_level not in PRIVACY_LEVELS:
        raise ValueError(f"privacy_level must be one of {PRIVACY_LEVELS}")
    size = video_path.stat().st_size
    body = {
        "post_info": {
            "title": title,
            "privacy_level": privacy_level,
            "disable_duet": False,
            "disable_stitch": False,
            "disable_comment": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": size,
            "total_chunk_count": 1,
        },
    }
    return request("POST", "/v2/post/publish/video/init/", token, body)


def upload_video(upload_url: str, video_path: Path) -> None:
    data = video_path.read_bytes()
    req = urllib.request.Request(upload_url, data=data, method="PUT", headers={
        "Content-Type": "video/mp4",
        "Content-Length": str(len(data)),
        "Content-Range": f"bytes 0-{len(data) - 1}/{len(data)}",
    })
    with urllib.request.urlopen(req, timeout=300) as resp:
        resp.read()


def check_status(token: str, publish_id: str) -> dict:
    return request("POST", "/v2/post/publish/status/fetch/", token, {"publish_id": publish_id})


def cmd_publish(args) -> None:
    token = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    if not token:
        raise SystemExit("Missing TIKTOK_ACCESS_TOKEN in the selected .env file")
    video_path = Path(args.video).expanduser().resolve()
    if not video_path.is_file():
        raise SystemExit(f"Video not found: {video_path}")
    if video_path.stat().st_size > MAX_SINGLE_CHUNK:
        raise SystemExit("File too large for single-chunk upload in this minimal client "
                          "(>64MB) — chunked multi-request upload not implemented here.")

    init_result = init_post(token, video_path, args.title, args.privacy)
    if init_result.get("error", {}).get("code") not in (None, "ok"):
        raise SystemExit(f"Init failed: {json.dumps(init_result, ensure_ascii=False)}")
    data = init_result["data"]
    publish_id = data["publish_id"]
    upload_url = data["upload_url"]

    upload_video(upload_url, video_path)
    print(json.dumps({"publish_id": publish_id, "status": "uploaded"}, ensure_ascii=False))


def cmd_status(args) -> None:
    token = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    if not token:
        raise SystemExit("Missing TIKTOK_ACCESS_TOKEN in the selected .env file")
    result = check_status(token, args.publish_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_wait(args) -> None:
    token = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    if not token:
        raise SystemExit("Missing TIKTOK_ACCESS_TOKEN in the selected .env file")
    deadline = time.monotonic() + args.timeout
    while True:
        result = check_status(token, args.publish_id)
        status = result.get("data", {}).get("status", "unknown")
        print(f"{args.publish_id}: {status}", flush=True)
        if status in TERMINAL:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        if time.monotonic() >= deadline:
            raise SystemExit("Timed out waiting for publish to complete")
        time.sleep(args.interval)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=Path(".env"))
    sub = parser.add_subparsers(dest="command", required=True)

    publish = sub.add_parser("publish")
    publish.add_argument("video")
    publish.add_argument("--title", default="")
    publish.add_argument("--privacy", default="SELF_ONLY", choices=sorted(PRIVACY_LEVELS))

    status = sub.add_parser("status")
    status.add_argument("publish_id")

    wait = sub.add_parser("wait")
    wait.add_argument("publish_id")
    wait.add_argument("--interval", type=int, default=5)
    wait.add_argument("--timeout", type=int, default=120)

    args = parser.parse_args()
    load_env(args.env)
    {"publish": cmd_publish, "status": cmd_status, "wait": cmd_wait}[args.command](args)


if __name__ == "__main__":
    main()
