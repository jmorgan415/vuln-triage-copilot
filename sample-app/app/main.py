"""Northgate platform worker: consumes job payloads from the queue spool.

Each JSON file in ./jobs/ is one work item (dev fixtures mirror what the
queue delivers in production). Run with:

    python3 -m app.main
"""
import base64
import json
import sys
from pathlib import Path

from app import config_service, image_thumbs, query_log, webhook_client

JOBS_DIR = Path(__file__).resolve().parent.parent / "jobs"


def handle_job(job: dict) -> dict:
    kind = job.get("kind", "")
    if kind == "tenant_config":
        # Queue envelope for the admin-console upload: the config bundle
        # exactly as the console accepted it, base64-encoded for transport.
        raw = base64.b64decode(job["config_b64"])
        return {"ok": bool(config_service.load_tenant_config(raw))}
    if kind == "settlement_notify":
        ok = webhook_client.notify_settlement(job["payment_id"], job["amount_cents"])
        return {"ok": ok}
    if kind == "slow_query_lookup":
        return {"query": query_log.normalize_query(job["sql_snippet"])}
    if kind == "avatar_thumbnail":
        thumb = image_thumbs.make_thumbnail(bytes.fromhex(job["image_hex"]))
        return {"bytes": len(thumb)}
    raise ValueError(f"unknown job kind: {kind}")


def main() -> int:
    jobs = sorted(JOBS_DIR.glob("*.json"))
    if not jobs:
        print("no jobs in spool", file=sys.stderr)
        return 1
    for path in jobs:
        job = json.loads(path.read_text())
        print(f"[worker] {path.name} -> {handle_job(job)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
