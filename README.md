# Reach — reachability-first vulnerability triage copilot

A customer-facing MVP built with **Factory** (Droid, in a single session).

> **Persona:** Priya Sharma, security engineer at **Northgate Financial** —
> a fintech with ~120 engineers and a security team of three.
>
> **Problem:** Her dependency scanner produces 56 findings on *one* small
> internal service. CVSS tells her nothing about whether the vulnerable
> code path is actually reachable from what this service does. Her Monday
> is spent proving negatives: open each advisory, grep the codebase,
> decide, write it up. Six minutes per finding, best case — 5.6 hours for
> this service alone, mostly to conclude "doesn't apply."
>
> **What Reach does:** hands every finding to a Droid session that reads
> the advisory, greps and reads the codebase, reasons about whether the
> vulnerable *conditions* hold (attacker-controlled input, proxies,
> redirects, specific loaders, flag-specific triggers), and returns a
> verdict with file:line evidence, an attack-surface statement, and a
> patch hint. Priya reviews 5 cards instead of 56 alerts.
>
> **Result on the demo fixture:** 56 findings → 5 act-now · 6 monitor ·
> 45 dismissed with evidence. Four fixes in one PR close 36 of them; the
> other 20 need no code change, each carrying its reason and revisit
> trigger.

## Architecture

```
            make scan                make triage                 make serve
Trivy ─────────────────▶ raw_scan.json ────────▶ triage_results.json ────────▶ dashboard/
   (real vuln DB)          (56 findings)      (verdicts + evidence)          (kanban + drawer)
                                                    ▲
                                    ┌───────────────┴───────────────┐
                                    │  cached backend (golden)      │  fast, deterministic —
                                    │  data/golden/verdicts.json    │  verdicts authored by
                                    │                               │  Droid sessions
                                    │  droid backend (live)         │
                                    │  one `droid exec` session per │  fresh reachability
                                    │  finding, thread-pooled       │  analysis, from scratch
                                    └───────────────────────────────┘
```

- `sample-app/` — the "customer" codebase: a small Python job worker with
  deliberately planted reachability (unsafe YAML load, flag-triggering
  sqlparse calls, avatar image decode, an outbound webhook, and a dead
  Jinja2 pin). ~100 lines of app code, 8 pinned packages, real Trivy
  findings — small, but shaped like a real mid-2020s internal service.
- `triage/` — the pipeline. Stdlib only, zero install.
- `dashboard/` — vanilla HTML/CSS/JS. No build step, no dependencies.
- `scripts/validate.py` — every evidence quote is checked against the
  cited file, line for line. Agent output that can't cite real code is
  worthless; the pipeline refuses to ship it.

## Quickstart

```bash
make scan       # trivy fs scan → data/raw_scan.json (needs trivy; brew install trivy)
make triage     # cached backend: replay Droid-authored golden verdicts (seconds)
make triage-live  # live backend: one `droid exec` session per finding (minutes)
make validate   # self-check: citations match the code, counts match reality
make serve      # http://localhost:8765 → dashboard
```

The live backend finds the CLI on `PATH`, falling back to the binary
bundled with the Factory desktop app
(`/Applications/Factory.app/Contents/Resources/bin/droid`). Override
with `REACH_AGENT_CMD='droid exec --cwd /abs/path/to/app'` if needed.

## The findings, summarized

| Package | Findings | Act now | Story |
|---|---|---|---|
| PyYAML | 1 | 1 | `yaml.load(FullLoader)` on admin-uploaded configs → RCE. Fix needs a safe_load migration, not just a bump. |
| sqlparse | 9 | 3 | Three advisories trigger on the *exact flags* in our call site (`strip_comments=True`, `reindent=True`). One bump to 0.6.0 closes all 9. |
| Pillow | 21 | 1 | WebP heap overflow reachable from customer avatars (exploited in the wild, 2023). The two CRITICAL-rated ImageMath RCEs are **unreachable** — `ImageMath` is never called. 21 findings → one bump. |
| Jinja2 | 5 | 0 | Never imported anywhere. Recommendation: delete the dead pin — permanently clears 5 findings from every future scan. |
| requests | 4 | 0 | Proxy-auth leak needs a proxy (none exists); `extract_zipped_paths()` is a utility we never call — the advisory itself says standard usage is unaffected. |
| urllib3 | 11 | 0 | Decompression bombs and redirect leaks need a hostile server or redirects; the sole TLS peer is the internal ledger on the service mesh. |
| certifi | 3 | 0 | Trust-store hygiene only matters for external validation; this service validates one internal mesh host. |
| idna | 2 | 0 | The only hostname ever parsed is a fixed literal. |

Headline numbers (all computed by the pipeline, not hand-waved):

- 56 findings → 5 act-now cards worth a human's attention
- 4 fixes in one PR close 36 findings (3 version bumps + 1 dead-pin deletion)
- Every fix is verified before a human reviews it (`make verify`, and the
  `Verify Fixes` workflow on every fix PR): the pinned requirements install
  into a fresh venv on the service's Python (3.11), each changed package's
  tests run on their own (13/13 pass), and a Trivy rescan must show the
  act-now findings gone with nothing new introduced (56 → 20, 0 new). The
  gate was checked against a deliberately regressed sqlparse pin and failed
  as intended. The dashboard shows the result on every affected card.
- `verify` is a required check on `main`, so a failing fix PR can't merge.
  When it fails, Factory's CI Steward reads the logs and commits a fix to
  the PR (`.github/workflows/ci-steward.yml`, policy in
  `.github/droid-ci.yml`). PR #9 is the worked example, and it carries the
  whole remediation for this service: the first commit moves the pins
  (PyYAML, sqlparse, Pillow) and migrates the YAML loader, but bumps Pillow
  without renaming `Image.ANTIALIAS`, which Pillow 10 removed. The required
  check goes red (`Pillow: tests_failed`, `test_image_thumbs.py: 1/5 passed`)
  while the other four packages verify clean, and Droid commits the one-line
  `Image.Resampling.LANCZOS` repair, after which all 13 tests pass and the
  gate is green (56 → 20, 0 introduced). Tests, pins, and workflows are
  protected paths, so the repair has to be in the app code. The dashboard's
  "Fix PR history" panel shows both commits side by side (`make history PR=9`
  re-verifies each one and writes `data/pr_history.json`).
- 20 findings need no code change, each with a documented reason and
  a revisit trigger ("revisit the day an egress proxy is adopted")
- Priya's Monday for this service: **5.6 h → ~32 min** (assumption is a
  declared constant in the pipeline, not a marketing number)

## How this was built with Factory

The entire MVP was built in one Droid session — one sitting, comfortably
inside the interview's 4-hour timebox:

1. Framed the persona and the demo narrative first (what should the
   dashboard say at minute 15?), then designed the fixture to produce
   that story honestly.
2. Wrote the sample app, ran a real Trivy scan, and had Droid read the
   advisory descriptions and triage all 56 findings against the
   codebase — the golden verdicts are agent output, not hand-written
   rule results.
3. Built the pipeline with two backends so the same verdicts are
   (a) instant and deterministic for the demo and (b) re-derivable
   from scratch by live Droid sessions.
4. The live backend earned its keep immediately. The first live smoke
   run disagreed with the golden PyYAML verdict: the fresh Droid
   session traced the job envelope one hop further and found the
   fixture was accidentally JSON-laundering the console upload
   (json.dumps neutralizes YAML constructor tags), which made the
   "reachable" RCE unreachable in the code as written. The agent was
   right, so we fixed the fixture, not the agent — its citations are
   preserved in `data/live_smoke_run1.json`, and the corrected flow
   is in `sample-app/app/main.py`. That is the product's core claim
   in miniature: run the agent, audit its citations, let it change
   your mind.
5. Wrote the validator because the product's entire value claim is
   "trustworthy, cited reasoning" — so the pipeline checks its own
   citations.
6. Dashboard, docs, and this README, same session.

Where the human stayed in the loop: lane policy (what counts as
act_now), trust-boundary calls (mesh peers excluded from threat model),
and the baseline assumptions. Where the agent ran: fixture design,
per-finding reachability analysis, all code, validation logic.

## Honest limitations

- The sample app is a fixture. It has controllable ground truth, which a
  demo needs. The pipeline consumes any Trivy JSON — point `--scan` at
  a real repository and nothing changes.
- The "6 min/finding" manual baseline is a declared assumption
  (`MANUAL_MINUTES_PER_FINDING` in `triage/run_triage.py`). It models
  read-advisory → grep → decide → write-up. Tune it to your org.
- The live backend was smoke-tested on one finding; a full 56-finding
  live run costs 56 Droid sessions (minutes, not hours — and it's the
  natural home for a scheduled Factory automation).
- The remediation PRs are deliberately left unmerged. `main` is the
  vulnerable baseline the walkthrough starts from, and PR #9 only shows the
  red-to-green repair history while it is open.

## What's next

- Scheduled triage (Monday 6am) via a Factory automation, posting a
  Slack/Jira digest per team.
- Auto-open remediation PRs from the patch hints, with Droid review on
  the PR (closing the loop this MVP started).
- Incremental re-triage: key verdicts by call-site hash so only changed
  code paths re-run.
- Org-wide rollup: which findings repeat across services → golden
  remediation PRs batched per package.
