#!/usr/bin/env python3
"""Self-check: the pipeline's citations must point at real code.

Verifies that data/triage_results.json is complete against the raw scan,
that lane counts match, and that every evidence quote matches the cited
file:lines exactly. This is what keeps the agent honest: a reviewer can
trust that every evidence card quotes the real codebase.

    python3 scripts/validate.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VALID_VERDICTS = {"act_now", "monitor", "dismiss", "untriaged"}
REQUIRED = (
    "verdict",
    "confidence",
    "one_line",
    "reasoning",
    "vulnerable_path",
    "attack_surface",
    "evidence",
    "recommended_action",
    "patch_hint",
    "effort",
)


def main() -> int:
    errs = []
    scan = json.loads((REPO / "data" / "raw_scan.json").read_text())
    results = json.loads((REPO / "data" / "triage_results.json").read_text())
    findings = results["findings"]

    # 1. completeness: every raw finding is triaged
    raw = {
        (v.get("VulnerabilityID"), v.get("PkgName"))
        for r in scan.get("Results", [])
        for v in (r.get("Vulnerabilities") or [])
    }
    triaged = {(f["id"], f["package"]) for f in findings}
    missing = raw - triaged
    if missing:
        errs.append(
            f"{len(missing)} raw findings missing from triage output: {sorted(missing)[:5]}"
        )

    # 2. summary counts match reality
    s = results["meta"]["summary"]
    for lane in ("act_now", "monitor", "dismiss", "untriaged"):
        actual = sum(1 for f in findings if f["verdict"] == lane)
        if s.get(lane) != actual:
            errs.append(f"summary.{lane}={s.get(lane)} but actual={actual}")

    # 3. required fields and verdict enum
    for f in findings:
        if f["verdict"] not in VALID_VERDICTS:
            errs.append(f"{f['id']}: bad verdict {f['verdict']}")
        for k in REQUIRED:
            if k not in f:
                errs.append(f"{f['id']}: missing field {k}")

    # 4. evidence citations match the real files, line for line
    checked = 0
    for f in findings:
        for ev in f.get("evidence") or []:
            p = REPO / ev["file"]
            if not p.exists():
                errs.append(f"{f['id']}: evidence file not found: {ev['file']}")
                continue
            lines = p.read_text().splitlines()
            if not (1 <= ev["line_start"] <= ev["line_end"] <= len(lines)):
                errs.append(
                    f"{f['id']}: lines {ev['line_start']}-{ev['line_end']} out of "
                    f"range for {ev['file']} ({len(lines)} lines)"
                )
                continue
            actual = "\n".join(lines[ev["line_start"] - 1 : ev["line_end"]])
            if actual != ev["quote"]:
                errs.append(
                    f"{f['id']}: evidence quote mismatch in "
                    f"{ev['file']}:{ev['line_start']}-{ev['line_end']}"
                )
            checked += 1

    print(f"[validate] {len(findings)} findings, {checked} evidence citations checked")
    if errs:
        print(f"[validate] FAILED with {len(errs)} problem(s):")
        for e in errs[:20]:
            print("  -", e)
        return 1
    print("[validate] OK — every verdict cites real, matching code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
