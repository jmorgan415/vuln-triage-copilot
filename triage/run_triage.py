#!/usr/bin/env python3
"""Reach triage pipeline: scanner output in, prioritized queue out.

Usage:
    python3 triage/run_triage.py --backend cached          # replay golden verdicts
    python3 triage/run_triage.py --backend droid --max-workers 3   # live sessions
"""
import argparse
import datetime as dt
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage.backends import VERDICT_FIELDS, BackendError, get_backend  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

# Priya's measured average for a manual per-finding investigation
# (read the advisory, grep the codebase, decide, write it up).
MANUAL_MINUTES_PER_FINDING = 6


def load_scan(path: Path) -> list[dict]:
    """Flatten trivy's JSON report into one record per finding."""
    scan = json.loads(path.read_text())
    findings, seen = [], set()
    for result in scan.get("Results", []):
        for vuln in result.get("Vulnerabilities") or []:
            key = (vuln.get("VulnerabilityID"), vuln.get("PkgName"))
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                {
                    "id": vuln.get("VulnerabilityID", "unknown"),
                    "package": vuln.get("PkgName", "unknown"),
                    "installed": vuln.get("InstalledVersion", "?"),
                    "fixed": vuln.get("FixedVersion") or "",
                    "severity": (vuln.get("Severity") or "UNKNOWN").upper(),
                    "title": vuln.get("Title") or "",
                    "description": vuln.get("Description") or "",
                    "primary_url": vuln.get("PrimaryURL") or "",
                    "target": result.get("Target", ""),
                }
            )
    return findings


LANE_ORDER = {"act_now": 0, "monitor": 1, "dismiss": 2}
SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["cached", "droid"], default="cached")
    ap.add_argument("--scan", type=Path, default=REPO_ROOT / "data" / "raw_scan.json")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "triage_results.json")
    ap.add_argument("--max-workers", type=int, default=3, help="live backend parallelism")
    ap.add_argument("--only", help="comma-separated vulnerability ids to triage")
    args = ap.parse_args()

    findings = load_scan(args.scan)
    if args.only:
        wanted = {c.strip() for c in args.only.split(",")}
        findings = [f for f in findings if f["id"] in wanted]
    if not findings:
        print(f"no findings in {args.scan}", file=sys.stderr)
        return 1

    try:
        backend = get_backend(args.backend)
    except BackendError as exc:
        print(f"backend error: {exc}", file=sys.stderr)
        return 2

    print(f"[reach] triaging {len(findings)} findings via '{backend.name}' backend")
    if args.backend == "droid":
        with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
            verdicts = list(pool.map(backend.triage, findings))
    else:
        verdicts = [backend.triage(f) for f in findings]

    merged = []
    for finding, verdict in zip(findings, verdicts):
        record = dict(finding)
        record.update({k: verdict.get(k) for k in VERDICT_FIELDS})
        record["triaged_by"] = backend.name
        merged.append(record)

    merged.sort(
        key=lambda r: (
            LANE_ORDER.get(r["verdict"], 3),
            SEV_ORDER.get(r["severity"], 9),
            r["package"],
        )
    )

    summary = {
        lane: sum(1 for r in merged if r["verdict"] == lane)
        for lane in ("act_now", "monitor", "dismiss", "untriaged")
    }
    payload = {
        "meta": {
            "product": "Reach",
            "customer": "Northgate Financial",
            "target": "sample-app — northgate platform-worker",
            "scanner": "trivy",
            "backend": backend.name,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(
                timespec="seconds"
            ),
            "assumptions": {
                "manual_minutes_per_finding": MANUAL_MINUTES_PER_FINDING,
                "note": "manual baseline: read advisory, grep codebase, decide, write up",
            },
            "summary": summary,
            "manual_minutes_baseline": len(merged) * MANUAL_MINUTES_PER_FINDING,
            "review_minutes_estimate": summary["act_now"] * 4 + summary["monitor"] * 2,
        },
        "findings": merged,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"[reach] wrote {args.out}")
    print(f"[reach] act_now={summary['act_now']} monitor={summary['monitor']} "
          f"dismiss={summary['dismiss']} untriaged={summary['untriaged']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
