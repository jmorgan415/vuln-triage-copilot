#!/usr/bin/env python3
"""Verify a remediation branch before a human reviews it.

For the given git ref this script:
  1. checks the ref out into an isolated worktree,
  2. installs its pinned requirements into a fresh venv on the pinned Python,
  3. maps each changed package to the tests that exercise it and runs them,
  4. rescans with Trivy and diffs against the original scan,
  5. writes data/fix_verification.json and exits non-zero if the gate fails.

Gate: every test passes, no act_now finding survives for a package the ref
changes, and no new findings appear.

    python3 scripts/verify_fixes.py                          # fix branch vs main
    python3 scripts/verify_fixes.py --ref HEAD --base origin/main   # in CI
"""
import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APP_DIR = "sample-app"
DEFAULT_REF = "fix/reach-act-now-remediation"

# Distribution name -> import name, where they differ.
IMPORT_NAMES = {"pyyaml": "yaml", "pillow": "PIL"}

# Runs one test module inside the target venv and reports counts as JSON.
RUNNER = r"""
import io, json, sys, unittest
stream = io.StringIO()
suite = unittest.defaultTestLoader.discover("tests", pattern=sys.argv[1])
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
print(json.dumps({
    "ran": result.testsRun,
    "failures": len(result.failures),
    "errors": len(result.errors),
    "skipped": len(result.skipped),
    "failed_tests": [t.id() for t, _ in result.failures + result.errors],
    "error_lines": sorted({tb.strip().splitlines()[-1] for _, tb in result.failures + result.errors}),
    "log_tail": stream.getvalue()[-2000:],
}))
"""


def run(cmd, cwd=None, check=True):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"[verify] command failed: {' '.join(map(str, cmd))}\n{proc.stderr[-2000:]}")
    return proc


def parse_requirements(text: str) -> dict[str, tuple[str, str]]:
    """Return {normalized name: (display name, version)} for name==version pins."""
    pins = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*==\s*([^\s;]+)", line)
        if m:
            pins[m.group(1).lower()] = (m.group(1), m.group(2))
    return pins


def import_name(dist: str) -> str:
    return IMPORT_NAMES.get(dist, dist.replace("-", "_"))


def app_modules_importing(app_dir: Path, mod: str) -> list[str]:
    pattern = re.compile(rf"^\s*(?:import|from)\s+{re.escape(mod)}\b", re.M)
    return sorted(p.stem for p in (app_dir / "app").glob("*.py") if pattern.search(p.read_text()))


def tests_covering(test_sources: dict[str, str], mod: str, app_mods: list[str]) -> list[str]:
    """A test covers a fix if it imports an affected app module or names the package."""
    hits = []
    for name, text in test_sources.items():
        if any(re.search(rf"\bapp\.{m}\b", text) for m in app_mods) or re.search(
            rf"\b{re.escape(mod.lower())}\b", text.lower()
        ):
            hits.append(name)
    return hits


def scan_keys(report: dict) -> set[str]:
    return {
        f"{v['VulnerabilityID']}:{v['PkgName']}"
        for r in report.get("Results", [])
        for v in r.get("Vulnerabilities") or []
    }


def pick_python(app_dir: Path, override: str | None) -> str:
    if override:
        return override
    pinned = app_dir / ".python-version"
    if pinned.exists():
        want = f"python{pinned.read_text().strip()}"
        found = shutil.which(want)
        if not found:
            raise SystemExit(f"[verify] {want} (from {APP_DIR}/.python-version) not found on PATH")
        return found
    return sys.executable


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default=DEFAULT_REF, help="git ref with the fixes")
    ap.add_argument("--base", default="main", help="git ref with the original pins")
    ap.add_argument("--python", help="interpreter for the venv (default: sample-app/.python-version)")
    ap.add_argument("--out", type=Path, default=REPO / "data" / "fix_verification.json")
    args = ap.parse_args()

    if not shutil.which("trivy"):
        raise SystemExit("[verify] trivy not found on PATH")

    commit = run(["git", "rev-parse", "--short", args.ref], cwd=REPO).stdout.strip()
    base_reqs = parse_requirements(
        run(["git", "show", f"{args.base}:{APP_DIR}/requirements.txt"], cwd=REPO).stdout
    )
    triage = json.loads((REPO / "data" / "triage_results.json").read_text())["findings"]
    act_now = {f"{f['id']}:{f['package']}" for f in triage if f["verdict"] == "act_now"}
    before = scan_keys(json.loads((REPO / "data" / "raw_scan.json").read_text()))

    # No pin changes means no fix to verify. Installing anyway would also fail:
    # the original pins (e.g. Pillow 9.0.0) have no wheels for the service's
    # pinned Python, so only upgraded pin sets are installable.
    ref_reqs = parse_requirements(
        run(["git", "show", f"{args.ref}:{APP_DIR}/requirements.txt"], cwd=REPO).stdout
    )
    if ref_reqs == base_reqs:
        payload = {
            "meta": {"ref": args.ref, "base": args.base, "commit": commit, "python": None,
                     "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                     "note": "no dependency changes; nothing to verify"},
            "gate": {"passed": True, "reasons": []},
            "tests": {"ran": 0, "passed": 0, "skipped": 0, "modules": {}},
            "rescan": {"before": len(before), "after": len(before), "resolved": 0,
                       "introduced": [], "act_now_remaining": []},
            "fixes": [],
            "findings": {},
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"[verify] {args.ref} @ {commit} changes no pinned dependencies; nothing to verify")
        print("[verify] GATE PASSED")
        return 0

    tmp = Path(tempfile.mkdtemp(prefix="reach-verify-"))
    worktree = tmp / "wt"
    run(["git", "worktree", "add", "--detach", str(worktree), args.ref], cwd=REPO)
    try:
        app_dir = worktree / APP_DIR
        fix_reqs = parse_requirements((app_dir / "requirements.txt").read_text())
        python = pick_python(app_dir, args.python)
        py_version = run([python, "-c", "import platform; print(platform.python_version())"]).stdout.strip()

        print(f"[verify] {args.ref} @ {commit} on Python {py_version}")
        venv = tmp / "venv"
        run([python, "-m", "venv", str(venv)])
        vpy = venv / "bin" / "python"
        run([str(vpy), "-m", "pip", "install", "-q", "--disable-pip-version-check",
             "-r", str(app_dir / "requirements.txt")])

        test_files = sorted((app_dir / "tests").glob("test_*.py"))
        test_sources = {tf.name: tf.read_text() for tf in test_files}
        tests = {}
        for tf in test_files:
            proc = run([str(vpy), "-c", RUNNER, tf.name], cwd=app_dir, check=False)
            try:
                res = json.loads(proc.stdout.strip().splitlines()[-1])
            except (IndexError, json.JSONDecodeError):
                res = {"ran": 0, "failures": 0, "errors": 1, "skipped": 0,
                       "failed_tests": [tf.name], "error_lines": [],
                       "log_tail": proc.stderr[-2000:]}
            # Reports get committed; keep throwaway checkout paths out of them.
            for prefix in {str(app_dir), str(app_dir.resolve())}:
                res["log_tail"] = res["log_tail"].replace(prefix + "/", "")
            res["passed"] = res["ran"] - res["failures"] - res["errors"] - res["skipped"]
            res["ok"] = res["ran"] > 0 and not res["failures"] and not res["errors"]
            tests[tf.name] = res
            print(f"[verify]   {tf.name}: {res['passed']}/{res['ran']} passed"
                  + ("" if res["ok"] else "  <-- FAILED"))

        print("[verify] rescanning with trivy")
        scan_out = tmp / "rescan.json"
        run(["trivy", "fs", "--quiet", "--scanners", "vuln", "--format", "json",
             "-o", str(scan_out), str(app_dir)])
        after = scan_keys(json.loads(scan_out.read_text()))
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=REPO,
                       capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)

    resolved = before - after
    introduced = sorted(after - before)

    fixes, finding_status = [], {}
    for name in sorted(set(base_reqs) | set(fix_reqs)):
        old, new = base_reqs.get(name), fix_reqs.get(name)
        if old == new:
            continue
        display = (old or new)[0]
        mod = import_name(name)
        app_mods = app_modules_importing(REPO / APP_DIR, mod) if old else []
        covering = tests_covering(test_sources, mod, app_mods)
        closes = sorted(k for k in before if k.split(":", 1)[1].lower() == name)
        closed = [k for k in closes if k in resolved]
        if not covering:
            status = "untested"
        elif not all(tests[t]["ok"] for t in covering):
            status = "tests_failed"
        elif len(closed) < len(closes):
            status = "not_resolved"
        else:
            status = "verified"
        fixes.append({
            "package": display,
            "from": old[1] if old else None,
            "to": new[1] if new else None,
            "change": "removed" if not new else ("added" if not old else "upgraded"),
            "app_modules": app_mods,
            "tests": covering,
            "tests_passed": sum(tests[t]["passed"] for t in covering),
            "tests_ran": sum(tests[t]["ran"] for t in covering),
            "findings_closed": closed,
            "findings_open": [k for k in closes if k not in resolved],
            "status": status,
        })
        for k in closes:
            finding_status[k] = {"package": display, "status": status}

    reasons = []
    failing = [t for t, r in tests.items() if not r["ok"]]
    if fixes and not tests:
        reasons.append("no tests found in the fix branch")
    if failing:
        reasons.append(f"failing test modules: {', '.join(failing)}")
    # Only packages this ref changes are in scope, so a single-package fix PR
    # isn't blocked by act_now findings that belong to other fixes.
    changed = {f["package"].lower() for f in fixes}
    surviving = sorted(k for k in act_now & after if k.split(":", 1)[1].lower() in changed)
    if surviving:
        reasons.append(f"act_now findings still present: {', '.join(surviving)}")
    if introduced:
        reasons.append(f"{len(introduced)} new finding(s) introduced: {', '.join(introduced[:5])}")

    payload = {
        "meta": {
            "ref": args.ref,
            "base": args.base,
            "commit": commit,
            "python": py_version,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        },
        "gate": {"passed": not reasons, "reasons": reasons},
        "tests": {
            "ran": sum(r["ran"] for r in tests.values()),
            "passed": sum(r["passed"] for r in tests.values()),
            "skipped": sum(r["skipped"] for r in tests.values()),
            "modules": tests,
        },
        "rescan": {
            "before": len(before),
            "after": len(after),
            "resolved": len(resolved),
            "introduced": introduced,
            "act_now_remaining": surviving,
        },
        "fixes": fixes,
        "findings": finding_status,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")

    t = payload["tests"]
    print(f"[verify] tests {t['passed']}/{t['ran']} passed · findings {len(before)} -> {len(after)} "
          f"· {len(introduced)} introduced")
    for f in fixes:
        print(f"[verify]   {f['package']}: {f['status']} ({f['tests_passed']}/{f['tests_ran']} tests, "
              f"{len(f['findings_closed'])} findings closed)")
    print(f"[verify] wrote {args.out.relative_to(REPO) if args.out.is_relative_to(REPO) else args.out}")
    if reasons:
        print("[verify] GATE FAILED:\n  - " + "\n  - ".join(reasons))
        return 1
    print("[verify] GATE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
