# Demo talk track — 30 minutes

Interview demo script. Timings assume the MVP walkthrough; the
discussion section covers the second 30 minutes.

## Pre-flight (before the call)

```bash
make validate   # expect: OK — every verdict cites real, matching code
make triage     # expect: act_now=5 monitor=6 dismiss=45 untriaged=0
make serve      # second terminal; open http://localhost:8765
```

Optional, if you want a live-agent moment and the network is good:

```bash
make triage-live   # or: python3 triage/run_triage.py --backend droid --only CVE-2020-14343
```

(Fallback if it's slow: show `data/live_smoke.json` from the build
session and say "this is a fresh Droid session re-deriving the verdict
from scratch.")

## Beat 1 — Persona and pain (3 min)

"I'm demoing for Priya, a security engineer at Northgate Financial —
120 engineers, security team of three. Here's her Monday: the scanner
just produced 56 findings on one internal service. Not our biggest
service. 56.

What she needs to know isn't 'what's the CVSS' — it's whether the
vulnerable code path is actually reachable in *our* code, and what to
do about it. Today she answers that by hand: open the advisory, grep
the codebase, decide, write it up. Six minutes per finding, best case.
Five and a half hours, mostly spent proving negatives.

Reach gives that loop to an agent — and gives Priya the output as a
queue with receipts."

## Beat 2 — The wall of noise (2 min)

Open the dashboard. Click **"Show the raw scanner queue."**

"This is exactly what the scanner hands her. 56 rows. Three CRITICALs —
which sound terrifying. Nothing in this view tells you that two of those
three CRITICALs are an API this codebase never calls. Click any row and
you just get the advisory text — the same Google-able prose, no code, no
decision."

Click one CRITICAL row (CVE-2022-22817, Pillow) to show the raw advisory
feel. Then click **"Back to the triaged board."**

## Beat 3 — What Reach does (5 min)

"Architecture is deliberately boring: Trivy scans, a per-finding agent
triage step, JSON in between, a dashboard on top. The interesting part is
the middle box.

For each finding, a Droid session reads the advisory, greps and reads
the codebase, and reasons about whether the vulnerable *conditions*
hold — attacker-controlled input, proxy configuration, redirects,
specific loaders, flag-specific triggers. Not just 'is the package
imported,' but 'can this service ever end up on the vulnerable path.'

Two backends: cached replays the verdicts Droid authored when we built
this; live spins up one `droid exec` session per finding and re-derives
everything from scratch. Same prompt, same output shape."

Run `make triage` in the terminal (it's seconds) and show the summary.

"56 findings: 5 act-now, 6 monitor, 45 dismissed — with evidence."

## Beat 4 — The cards that sell it (8 min)

**Act Now — PyYAML (the code-change story).**
Open the card. "Admin-uploaded YAML parsed with FullLoader — that's the
RCE, and line 18 is the call. Notice the in-code comment: FullLoader was
chosen in 2021 for `!!merge` tag support, not for object constructors.
So the fix is two-part — bump *and* a safe_load migration with an
explicit merge constructor. A version bump alone leaves the unsafe load
semantics in place. That's the difference between patch state and
actual security."

**Act Now — sqlparse ×3 (the precision story).**
"Three separate advisories, and each one triggers on an option that is
literally in our call site — `strip_comments=True`, `reindent=True`.
The scanner said '9 findings on sqlparse.' The agent says: three of
them name your code, all nine close with one bump to 0.6.0. One PR,
nine findings gone."

**Act Now — Pillow libwebp (the customer-impact story).**
"Customer avatars hit Image.open, Pillow 9.0.0 bundles the vulnerable
WebP decoder, and this CVE was exploited in the wild in 2023. Reachable
from any customer upload. This is the strongest card in the scan — and
note it sits next to two CRITICALs that turned out to be unreachable."

**Monitor — the Pillow decode cluster.**
"Reachable DoS-class issues from avatar uploads — GIF bombs, GD/JPEG2000
allocation. Real, but batched into the same Pillow bump. Monitor exists
so the act-now lane means something."

**Dismiss — requests Proxy-Authorization (the honest-negative story).**
"This is my favorite dismissal pattern: the vulnerable condition is a
proxy with auth on a redirect, and this codebase configures no proxies —
the docstring even says egress is direct. Dismissed — but look at the
'revisit' clause: the day Northgate adopts an egress proxy, this flips.
That's what a good senior engineer writes in the margin. Reach writes
it automatically."

**Dismiss — Jinja2 ×5 (the hygiene story).**
"Never imported anywhere — a pin left over from a retired console.
The recommendation isn't 'upgrade,' it's 'delete the pin,' which
permanently removes 5 findings from every future scan. Scanners don't
tell you that. Agents reading the code do."

**The punchline.** "Four PRs — three version bumps and one pin
deletion — close 36 of 56 findings. The remaining 20 need no code
change, and each carries its reason. Priya's Monday on this service:
5.6 hours to about 32 minutes."

## Beat 5 — Why this output is trustworthy (4 min)

Run `make validate`, then point at the green "Fix PR verified" strip
(or run `make verify` live, about a minute).

"And the fixes are checked, not just the verdicts. Before anyone reviews
the fix PR, the pinned dependencies install into a clean environment on
this service's Python, each fix's tests run on their own, and a rescan
has to show the act-now findings gone with nothing new introduced. The
same check runs in CI on every fix PR. It already earned its keep: the
clean install showed the old urllib3 pin can't even import on Python
3.14, which is why the service's Python version is now pinned."

"Every evidence quote in every card is checked against the actual file,
line for line — the pipeline refuses to ship a verdict that doesn't cite
real code. This is the answer to 'what about hallucinations': don't
trust the prose, trust the citations, and check them mechanically.

Also: confidence labels are visible. Open the Pillow PDF one — medium
confidence, because the parser exists in the package even though our
flow never touches it. The agent hedges where the evidence is thin,
which is what you want."

Point at the metrics strip: "The 6-minutes-per-finding baseline is a
declared constant in the pipeline — it's an assumption you can argue
with, not a number we invented in a deck."

## Beat 5b — When a fix breaks (3 min; take it from Beat 4)

Open PR #3 ("bump Pillow 9.0.0 -> 12.3.0") and walk its history top to
bottom. Don't trigger anything live; the history is the demo.

1. **The bump.** "This is the PR a dependency bot opens: one version
   line. It closes the reachable libwebp overflow plus 20 other Pillow
   findings."
2. **The red check.** Open the first failed Verify Fixes run. "Four
   thumbnail tests fail: `module 'PIL.Image' has no attribute
   'ANTIALIAS'`. Pillow 10 removed it, and our avatar code still used
   it. Merging this would have fixed a CVE and broken every avatar
   upload." Point at the merge box: blocked, because `verify` is a
   required check, even for admins.
3. **Droid's comment.** "CI Steward ran automatically on the failure,
   read the job log, and named the exact line and the fix. The Droid
   review on the PR said the same thing independently."
4. **Droid's commit.** Open `fix(ci): use Pillow 12 resampling enum for
   thumbnails` by factory-droid[bot]. One line: `Image.ANTIALIAS` ->
   `Image.Resampling.LANCZOS`. "It fixed the app, not the test."
5. **Green.** The rerun: 5/5 tests, 56 -> 35 findings, 0 introduced,
   gate passed. Merge button unlocked; a human still clicks it.

The guardrails, if asked (all in `.github/droid-ci.yml`, read from
main only, so a PR can't loosen them):

- Tests, dependency pins, workflows, and pipeline code are protected
  paths. Edits to them are reverted after the run, so Droid can't make
  the check green by deleting a test or undoing the upgrade.
- It only fixes failures the PR caused: Verify Fixes must be green on
  the PR's base commit, or it diagnoses and stops.
- At most 2 consecutive fix commits and 6 runs per PR, then a human.
- On this public repo, GitHub held Droid's push for maintainer approval
  before CI ran it: one more human checkpoint.

Honest build notes, if asked: getting here took two config fixes, both
caught by Steward's own guardrails. It first stayed diagnosis-only
because Verify Fixes had never run on main (no baseline), then it fixed
the code but couldn't commit because the runner had no git identity.
Both fixes landed as PRs #4 and #5.

## Beat 6 — The Factory story (5 min)

"The whole thing was built in one Droid session, comfortably inside the
4-hour timebox, including these docs. The golden verdicts *are* agent
output — Droid read the scan data and the codebase and wrote every card.

And the live backend already proved itself during the build. The first
live run disagreed with golden on the PyYAML finding — the fresh session
had traced the job envelope one hop further and found the fixture was
JSON-laundering the console upload, which made the 'reachable' RCE
unreachable as written. The agent was right. We fixed the code, not the
agent. `data/live_smoke_run1.json` holds the receipts — if you want to
see a model earn its keep, that file is the demo.

The live backend is the product bet: per-finding triage is
embarrassingly parallel — one session per finding, 56 sessions, a
thread pool. This is exactly the kind of fan-out Factory is built for,
and exactly the loop you'd schedule as a Factory automation: Monday
6am, every service, before Priya's coffee. Same pattern, org-wide.

And the loop is closed on GitHub: the remediation PRs carry tests, a
required Verify Fixes check proves them, Droid reviews them, and when an
upgrade breaks the app, CI Steward repairs the PR itself (PR #3).
Triage, remediation, verification, and repair as one agent-driven
pipeline, with a human on the merge button."

## Beat 7 — Value and next steps (3 min)

"For Northgate: this service's Monday queue drops from 5.6 hours to 32
minutes, and those 32 minutes are spent on the 11 findings that matter.
Multiply honestly across their services — Reach doesn't remove the
security engineer's judgment; it removes the hours spent proving
negatives, and it turns 'trust me, it doesn't apply' into a cited,
reviewable artifact.

Roadmap: scheduled automation with Slack/Jira digests, auto-opened
patch PRs with Droid review, incremental re-triage keyed by call-site
hash, and an org rollup that spots the packages worth a golden
remediation PR."

## Anticipated questions (the discussion 30)

**"Why not just auto-merge Dependabot bumps?"**
Version bumps answer *upgradeability*; Reach answers *reachability and
priority*. Bumps close the sqlparse/Pillow noise, but they can't tell you
PyYAML needs a code migration, can't tell you the two CRITICALs are
unreachable, and can't produce the revisit triggers. And blanket
auto-merge in a fintech isn't a policy anyone will sign off on.

**"What stops hallucinated reachability claims?"**
The validator — every citation is checked against the real file on every
run, and the dashboard shows exact quotes a reviewer can eyeball against
the code in seconds. Verdicts without valid citations can't ship.

**"Is the scan real?"**
Yes — Trivy 0.75 with its live vuln DB, `make scan` reruns it. The app
is a fixture so the demo has controlled ground truth; the pipeline
consumes any Trivy JSON. Point it at a real repo and it works unchanged.

**"What about transitive dependencies?"**
That's most of the wall of noise — urllib3, certifi, idna come in via
requests. Reachability reasoning is precisely what resolves them: the
agent asks what those packages ever actually *see* (one fixed URL, no
attacker-controlled input) and dismisses with that reasoning.

**"How would you scale this to 200 services?"**
Factory automation on a schedule, one fan-out per service, results keyed
by call-site hash for incremental re-runs, rollup dashboard per team,
patch PRs auto-opened with Droid review. The demo is one service
because the timebox was 4 hours; nothing in the pipeline is
single-service.

**"What would you do differently with more time?"**
In order: scheduled runs, the patch-PR loop, incremental re-triage,
and a second opinion pass — a second model re-checking dismiss verdicts
before they're published, because a wrongly-dismissed reachable
finding is the one failure mode that matters.
