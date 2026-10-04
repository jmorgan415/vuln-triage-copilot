#!/usr/bin/env python3
"""Record a fix PR's verification history for the dashboard.

Runs the verify stage on every non-merge commit in the PR that touches
sample-app, and records each result alongside the commit's author, its
app-code change, and the matching Verify Fixes CI run. The dashboard uses
this to show a PR going red and then being repaired.

    python3 scripts/pr_history.py --pr 3
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def sh(*cmd, check=True) -> str:
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"[history] failed: {' '.join(cmd)}\n{proc.stderr[-1500:]}")
    return proc.stdout


def app_diff(sha: str) -> list[str]:
    out = sh("git", "diff", "--unified=0", f"{sha}^", sha, "--", "sample-app/app")
    return [
        line for line in out.splitlines()
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]


def ci_run(sha: str) -> dict:
    runs = json.loads(sh(
        "gh", "run", "list", "--commit", sha, "--workflow", "Verify Fixes",
        "--json", "url,conclusion,event", check=False) or "[]")
    runs = [r for r in runs if r.get("event") == "pull_request"] or runs
    return {"url": runs[0]["url"], "conclusion": runs[0]["conclusion"]} if runs else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--base", default="main", help="ref with the original pins "
                    "(falls back to origin/main when there is no local branch)")
    ap.add_argument("--out", type=Path, default=REPO / "data" / "pr_history.json")
    ap.add_argument("--append", action="store_true",
                    help="keep entries for other PRs (default: the file holds this PR only)")
    args = ap.parse_args()

    pr = json.loads(sh("gh", "pr", "view", str(args.pr), "--json",
                       "number,title,url,headRefName,commits"))
    # refs/pull/N/head exists for fork PRs too, and for a deleted head branch,
    # where the head repository's branch name either is absent from origin or
    # names an unrelated branch of the same name.
    sh("git", "fetch", "-q", "origin", f"refs/pull/{args.pr}/head")

    steps = []
    for c in pr["commits"]:
        sha = c["oid"]
        parents = sh("git", "rev-list", "--parents", "-n", "1", sha).split()[1:]
        if len(parents) > 1:
            continue
        if not subprocess.run(["git", "diff", "--quiet", f"{sha}^", sha, "--", "sample-app"],
                              cwd=REPO).returncode:
            continue
        print(f"[history] verifying {sha[:7]} {c['messageHeadline']}")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "v.json"
            subprocess.run([sys.executable, str(REPO / "scripts" / "verify_fixes.py"),
                            "--ref", sha, "--base", args.base, "--out", str(out)],
                           cwd=REPO, capture_output=True, text=True)
            if not out.exists():
                raise SystemExit(f"[history] verify produced no report for {sha[:7]}")
            v = json.loads(out.read_text())
        author = (c.get("authors") or [{}])[0]
        steps.append({
            "commit": sha[:7],
            "headline": c["messageHeadline"],
            "author": author.get("login") or author.get("name") or "unknown",
            "app_diff": app_diff(sha),
            "ci": ci_run(sha),
            "gate": v["gate"],
            "python": v["meta"]["python"],
            "tests": {
                "ran": v["tests"]["ran"],
                "passed": v["tests"]["passed"],
                "errors": sorted({e for m in v["tests"]["modules"].values()
                                  for e in m.get("error_lines", [])}),
            },
            "rescan": {k: v["rescan"][k] for k in ("before", "after", "introduced")},
            "fixes": [{k: f[k] for k in ("package", "from", "to", "status")} for f in v["fixes"]],
        })
        print(f"[history]   gate {'passed' if v['gate']['passed'] else 'FAILED'}")

    entry = {"pr": pr["number"], "title": pr["title"], "url": pr["url"], "steps": steps}
    if args.append:
        history = json.loads(args.out.read_text()) if args.out.exists() else []
        history = [h for h in history if h["pr"] != entry["pr"]] + [entry]
        history.sort(key=lambda h: h["pr"])
    else:
        # The dashboard renders one panel per entry, so a regeneration for the
        # demo PR replaces the file rather than leaving stale PRs on the board.
        history = [entry]
    args.out.write_text(json.dumps(history, indent=2) + "\n")
    print(f"[history] wrote {len(steps)} step(s) for PR #{entry['pr']} to "
          f"{args.out.relative_to(REPO) if args.out.is_relative_to(REPO) else args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
