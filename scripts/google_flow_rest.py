#!/usr/bin/env python3
"""Safe, dependency-free useapi.net Google Flow REST client."""

from __future__ import annotations
import argparse, csv, json, os, re, sys, time
from pathlib import Path
import urllib.error, urllib.parse, urllib.request

BASE = "https://api.useapi.net/v1/google-flow"
MODELS = {"veo-3.1-quality", "veo-3.1-fast", "veo-3.1-lite",
          "veo-3.1-lite-low-priority", "omni-flash"}
ASPECTS = {"landscape", "portrait", "1:1", "4:3", "3:4"}
TERMINAL = {"completed", "failed"}
EXT_MIME_MAP = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp", ".mp4": "video/mp4"}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class Client:
    def __init__(self, token: str):
        self.token = token
        self._upload_cache: dict[str, str] = {}

    def request(self, method: str, path: str, body=None, content_type="application/json", timeout=660):
        if not self.token:
            raise SystemExit("Missing USEAPI_TOKEN in the selected .env file")
        data = None if body is None else (
            body if isinstance(body, bytes) else json.dumps(body).encode("utf-8"))
        req = urllib.request.Request(BASE + path, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Content-Type": content_type,
            "Accept": "application/json",
            "User-Agent": "google-flow-rest-skill/1.0",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"error": raw}
            raise RuntimeError(f"HTTP {exc.code}: {json.dumps(parsed, ensure_ascii=False)}") from exc

    def accounts(self):
        return self.request("GET", "/accounts")

    def upload(self, file_path: Path, email="") -> str:
        path = file_path.expanduser().resolve()
        cache_key = f"{email}:{path}"
        cached = self._upload_cache.get(cache_key)
        if cached:
            return cached
        if not path.is_file():
            raise ValueError(f"Reference not found: {path}")
        # Use an explicit extension->mime map rather than mimetypes.guess_type(),
        # which reads OS-provided mime.types files and is inconsistent across
        # platforms (observed returning None for plain .png files on a minimal
        # Linux container even though the same code works fine on Windows).
        mime = EXT_MIME_MAP.get(path.suffix.lower())
        if mime not in {"image/png", "image/jpeg", "image/webp", "video/mp4"}:
            raise ValueError(f"Unsupported reference type: {mime or 'unknown'} (file: {path.name})")
        endpoint = "/assets" + (
            "/" + urllib.parse.quote(email, safe="") if email else "")
        result = self.request("POST", endpoint, path.read_bytes(), mime)
        asset = result.get("mediaGenerationId")
        if isinstance(asset, dict):
            asset = asset.get("mediaGenerationId")
        if not asset:
            raise RuntimeError("Upload returned no mediaGenerationId")
        asset = str(asset)
        # Same product reference image gets reused across every segment of a
        # brief (and every genre, when multiple are requested) - caching here
        # turns N redundant uploads of identical bytes into 1 per (file, email),
        # which matters a lot for request latency: each upload is a real
        # network round-trip, and multi-genre submits used to serialize N of
        # them inside a single Flask request, risking the gunicorn worker
        # timeout on Render's slower CPU.
        self._upload_cache[cache_key] = asset
        return asset

    def submit(self, payload):
        return self.request("POST", "/videos", payload)

    def job(self, job_id):
        # Called every ~8s per in-progress segment from the browser's poll loop,
        # so a slow/stuck response here must fail fast rather than tying up a
        # gunicorn worker for minutes - with only 2 workers, a few stuck status
        # calls were enough to make the whole site unresponsive for every user.
        return self.request(
            "GET", "/jobs/" + urllib.parse.quote(job_id, safe=":@"), timeout=20)


def validate(model, aspect, resolution, duration, count):
    if model not in MODELS:
        raise ValueError(f"Unsupported model in this client: {model}")
    if aspect not in ASPECTS:
        raise ValueError(f"Unsupported aspect ratio: {aspect}")
    if resolution not in {"360p", "720p"}:
        raise ValueError("Resolution must be 360p or 720p")
    if duration not in {4, 6, 8, 10}:
        raise ValueError("Duration must be 4, 6, 8, or 10 seconds")
    if not 1 <= count <= 4:
        raise ValueError("Count must be between 1 and 4")
    if model == "veo-3.1-quality" and duration != 8:
        raise ValueError("veo-3.1-quality supports 8 seconds only")
    if model != "omni-flash" and duration == 10:
        raise ValueError("10 seconds is supported by omni-flash only")
    if resolution == "360p" and model != "omni-flash":
        raise ValueError("360p is supported by omni-flash only")


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_filename(job_id: str) -> str:
    return re.sub(r'[:\\/*?"<>|]', "_", job_id)


def get_job_id(data):
    return str(data.get("jobid") or data.get("jobId") or "")


def get_media(data):
    response = data.get("response") if isinstance(data.get("response"), dict) else {}
    value = data.get("media") or response.get("media") or []
    return value if isinstance(value, list) else []


def download(url, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url, headers={"User-Agent": "google-flow-rest-skill/1.0"})
    with urllib.request.urlopen(request, timeout=240) as response:
        path.write_bytes(response.read())


def split_refs(value):
    return [item.strip() for item in value.split(";") if item.strip()]


def build_payload(client, prompt, model, aspect, resolution, duration, count,
                  email="", start_image="", references=None, do_upload=False):
    references = references or []
    validate(model, aspect, resolution, duration, count)
    payload = {"prompt": prompt, "model": model, "aspectRatio": aspect,
               "resolution": resolution, "duration": duration,
               "count": count, "async": True}
    if email:
        payload["email"] = email
    if len(references) > 7:
        raise ValueError("At most seven reference images are supported")
    if start_image:
        payload["startImage"] = (
            client.upload(Path(start_image), email) if do_upload
            else f"<upload on confirmation: {Path(start_image).expanduser().resolve()}>")
    for index, value in enumerate(references, 1):
        payload[f"referenceImage_{index}"] = (
            client.upload(Path(value), email) if do_upload
            else f"<upload on confirmation: {Path(value).expanduser().resolve()}>")
    return payload


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path, fields, rows):
    for name in ("job_id", "error"):
        if name not in fields:
            fields.append(name)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def row_payload(client, row, do_upload):
    return build_payload(
        client, row["prompt"], row.get("model") or "veo-3.1-fast",
        row.get("aspect_ratio") or "portrait",
        row.get("resolution") or "720p", int(row.get("duration") or 8),
        int(row.get("count") or 1),
        row.get("email") or os.getenv("GOOGLE_FLOW_EMAIL", ""),
        row.get("start_image", ""), split_refs(row.get("reference_images", "")),
        do_upload)


def cmd_accounts(args, client):
    print(json.dumps(client.accounts(), ensure_ascii=False, indent=2))


def cmd_submit(args, client):
    payload = build_payload(
        client, args.prompt, args.model, args.aspect_ratio, args.resolution,
        args.duration, args.count, args.email or os.getenv("GOOGLE_FLOW_EMAIL", ""),
        args.start_image, args.reference_image, args.confirm_spend)
    if not args.confirm_spend:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit("Dry run only. Add --confirm-spend after explicit approval.")
    result = client.submit(payload)
    jid = get_job_id(result)
    if not jid:
        raise RuntimeError("Submission returned no job ID")
    save_json(result, args.output_dir / "jobs" / f"{safe_filename(jid)}.json")
    print(json.dumps({"job_id": jid, "status": result.get("status")},
                     ensure_ascii=False))


def cmd_status(args, client):
    result = client.job(args.job_id)
    save_json(result, args.output_dir / "jobs" / f"{safe_filename(args.job_id)}.json")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_wait(args, client):
    deadline = time.monotonic() + args.timeout
    while True:
        result = client.job(args.job_id)
        status = str(result.get("status", "unknown")).lower()
        save_json(result, args.output_dir / "jobs" / f"{safe_filename(args.job_id)}.json")
        print(f"{args.job_id}: {status}", flush=True)
        if status in TERMINAL:
            if status == "completed" and args.download:
                for index, item in enumerate(get_media(result), 1):
                    if item.get("videoUrl"):
                        download(item["videoUrl"],
                                 args.output_dir / f"{safe_filename(args.job_id)}_{index:02d}.mp4")
            return
        if time.monotonic() >= deadline:
            raise SystemExit("Timed out; remote job may still be processing")
        time.sleep(args.interval)


def cmd_batch(args, client):
    fields, rows = read_csv(args.csv)
    ready = [row for row in rows
             if row.get("status", "").strip().lower() == "ready"
             and not row.get("job_id", "").strip()]
    if args.max_jobs is not None:
        ready = ready[:args.max_jobs]
    if not ready:
        raise SystemExit("No unsubmitted rows with status Ready")
    previews = []
    for row in ready:
        payload = row_payload(client, row, False)
        previews.append({"id": row.get("id", ""), **payload})
    print(json.dumps({"ready_count": len(ready), "jobs": previews},
                     ensure_ascii=False, indent=2))
    if not args.confirm_spend:
        raise SystemExit("Dry run only. Add --confirm-spend after explicit approval.")
    for row in ready:
        try:
            result = client.submit(row_payload(client, row, True))
            jid = get_job_id(result)
            if not jid:
                raise RuntimeError("Submission returned no job ID")
            row.update(status="Submitted", job_id=jid, error="")
            save_json(result, args.output_dir / "jobs" / f"{safe_filename(jid)}.json")
            print(f"Submitted {row.get('id', '')}", flush=True)
        except Exception as exc:
            row.update(status="Failed", error=str(exc))
            write_csv(args.csv, fields, rows)
            print(f"Failed {row.get('id', '')}: {exc}", file=sys.stderr)
            raise
        write_csv(args.csv, fields, rows)


def add_output(parser):
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=Path(".env"))
    sub = parser.add_subparsers(dest="command", required=True)
    accounts = sub.add_parser("accounts"); add_output(accounts)
    submit = sub.add_parser("submit"); add_output(submit)
    submit.add_argument("--prompt", required=True)
    submit.add_argument("--model", default="veo-3.1-fast", choices=sorted(MODELS))
    submit.add_argument("--aspect-ratio", default="portrait", choices=sorted(ASPECTS))
    submit.add_argument("--resolution", default="720p", choices=["360p", "720p"])
    submit.add_argument("--duration", type=int, default=8)
    submit.add_argument("--count", type=int, default=1)
    submit.add_argument("--email", default="")
    submit.add_argument("--start-image", default="")
    submit.add_argument("--reference-image", action="append", default=[])
    submit.add_argument("--confirm-spend", action="store_true")
    status = sub.add_parser("status"); add_output(status)
    status.add_argument("job_id")
    wait = sub.add_parser("wait"); add_output(wait)
    wait.add_argument("job_id")
    wait.add_argument("--interval", type=int, default=15)
    wait.add_argument("--timeout", type=int, default=900)
    wait.add_argument("--download", action="store_true")
    batch = sub.add_parser("batch"); add_output(batch)
    batch.add_argument("csv", type=Path)
    batch.add_argument("--max-jobs", type=int)
    batch.add_argument("--confirm-spend", action="store_true")
    args = parser.parse_args()
    load_env(args.env)
    client = Client(os.getenv("USEAPI_TOKEN", ""))
    {"accounts": cmd_accounts, "submit": cmd_submit, "status": cmd_status,
     "wait": cmd_wait, "batch": cmd_batch}[args.command](args, client)


if __name__ == "__main__":
    main()
