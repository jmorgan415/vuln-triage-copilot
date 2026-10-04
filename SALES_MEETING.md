# Interview 2 game plan: Northgate Financial pilot meeting

A playbook for running the second interview as a live customer meeting,
with Reach as the centerpiece. It goes with the 5-slide deck in
`outputs/northgate-pilot.pptx`.

**The one-sentence story:** Northgate's security team of three is losing
a third of its week proving that scanner findings don't apply. Copilot
helps developers write code, but nobody is at the keyboard for this work.
Factory runs agents that read the code, decide what matters, open the
fix, and review it, with every decision cited. A 6-week pilot on three
services proves it with Northgate's own data.

---

## 1. The scenario

**Company:** Northgate Financial. It is a Series C payments and lending
platform (fintech) with ~120 engineers and ~40 services, mostly Python
and TypeScript, on GitHub Enterprise Cloud. It is regulated: PCI DSS
for card data, SOC 2 Type II, and annual bank-partner audits.

**Where they are with AI tooling (the alternative):**
- **GitHub Copilot Enterprise**, rolled out to all 120 engineers 9 months
  ago. Developers like it. It is owned by Developer Productivity.
- **GitHub Advanced Security** with Dependabot alerts and security
  updates, CodeQL code scanning, and Copilot Autofix on CodeQL alerts.
- **An internal "agent platform" prototype**: two platform engineers
  built a Claude Code-based bot that summarizes Dependabot alerts in
  Slack. It works on demos and is not trusted for decisions.

**What happened on the prior call** (assume a 30-minute call two weeks
ago with Priya and Marcus):
- ~1,800 open dependency alerts across 40 repos. They grow every month.
- Internal policy: Critical within 15 days and High within 30 days
  (stricter than the PCI DSS one-month requirement for critical patches).
  Last quarter **38% of Critical/High findings breached that SLA**, and the
  bank-partner auditor wrote it up.
- Priya spends most of Monday triaging. The team's honest estimate is
  that "most" findings don't apply, but proving it takes the time.
- Copilot Autofix helps with CodeQL alerts in their own code. It doesn't
  answer "does this dependency CVE actually reach our code?"
- We agreed to come back with a working demo against a codebase shaped
  like theirs, and a pilot proposal. Marcus asked us to bring Dana (VP
  Eng) and Ravi (Dev Productivity), because "anything agentic goes
  through Ravi now."

**Why now (the compelling event):** a follow-up audit in ~5 months, and
the Copilot Enterprise renewal in Q1. Dana is consolidating the "AI dev
tools" budget line.

> **Before the interview:** send the panel the role cards below 24-48
> hours ahead. Each card has *hidden information* that a character only
> reveals if asked a good question. That rewards discovery and makes
> the panel's job easy.

---

## 2. Role cards (send to the panel)

Four roles. If the panel has only 2-3 people, merge Dana+Ravi and
Marcus+Priya.

### Dana Whitfield, VP Engineering (economic buyer)
- **Cares about:** roadmap velocity, engineering hours, budget, not adding tool sprawl.
- **Opening stance:** "We already pay for Copilot for every engineer. Why another tool?"
- **Hidden (reveal if asked about business impact or the audit):** the audit finding went to the board risk committee. She committed to "no SLA breaches by the next audit." Pulling feature engineers onto patching has already slipped one roadmap item this quarter.
- **Objections to raise:** tool sprawl, cost, "come back after the Copilot renewal."

### Marcus Chen, Director of Application Security (technical decision maker for security)
- **Cares about:** audit evidence, defensible decisions, data handling.
- **Opening stance:** cautiously interested and deeply skeptical of AI dismissing vulnerabilities.
- **Hidden (reveal if asked how dismissals are documented today):** most dismissals today are a one-line Jira comment ("not used"). The auditor flagged the *lack of evidence*, not just the breaches. He would welcome a cited, reviewable record.
- **Objections to raise:** "What if it dismisses something real?", "Where does our code go?", "How do I explain this to an auditor?"

### Priya Sharma, Staff Security Engineer (champion and daily user)
- **Cares about:** getting her Mondays back and doing threat modeling instead of grep.
- **Opening stance:** wants this to work, and has been burned by tools that create more noise.
- **Hidden (reveal if asked about remediation):** two blanket Dependabot bumps broke builds last quarter, so developers now ignore Dependabot PRs. She hand-picks which bumps to push.
- **Objections to raise:** "Does it work on real repos and not toy apps?", "Will it bury me in PRs?"

### Ravi Patel, Head of Developer Productivity (owns Copilot and the internal agent prototype)
- **Cares about:** platform consistency, developer experience, not being displaced.
- **Opening stance:** "My team can build this on Claude Code in two sprints."
- **Hidden (reveal if asked what's hard about the prototype):** the prototype has no evaluation, no citation checking, and no owner after Q1. One of its two engineers is moving teams. He also wants PR review automation org-wide and hasn't found a tool he trusts.
- **Objections to raise:** build vs buy, "Copilot coding agent will do this soon," model lock-in.

---

## 3. Run of show (60 minutes)

| Time | Segment | Goal | Assets |
|---|---|---|---|
| 0:00-0:04 | Open | Intros, recap, agenda, time check, confirm the outcome they want | Slide 1 |
| 0:04-0:14 | Discovery | Get numbers and pain from each person and earn the demo | Questions in §5 |
| 0:14-0:19 | Pitch | Frame the problem and the approach in their words | Slides 2-3 |
| 0:19-0:33 | Demo | Raw queue to triaged board to evidence to fix PR to Droid review and repair | Dashboard + PR #9 |
| 0:33-0:38 | Value | Rebuild the business case live with *their* discovery numbers | Slide 4 |
| 0:38-0:46 | Pilot | Scope, metrics, decision criteria, mutual plan | Slide 5 |
| 0:46-0:50 | Buffer | Absorb objections that came up earlier. Never skip the pilot for them | |
| 0:50-1:00 | Q&A | Reserved. Close with a concrete next step | |

**Meeting-control habits**
- State the agenda and **ask for permission**: "Does that work, or is there anything you need to cover today that I've missed?"
- Check time out loud at each transition: "We're at 19 minutes, right on plan."
- When an objection lands mid-demo, use the parking line: "Great question. I want to give it a real answer. Can I park it for 5 minutes? It's exactly what the next screen covers." Then **come back to it by name.**
- Address each person by name at least once. Bring in quiet panelists: "Ravi, you've been quiet. How does this land against what your team built?"
- If you run long in discovery, cut the demo down (Beat 4 to two cards) and **protect the pilot section.** The pilot is the ask.

---

## 4. Opening (0:00-0:04), word for word

> "Thanks for making the time, especially Dana and Ravi, joining for the
> first time. Quick recap so we're on the same page: two weeks ago Priya
> and Marcus told us about ~1,800 open dependency alerts, a 15/30-day SLA
> that breached on 38% of Criticals and Highs last quarter, and an
> auditor who noticed. We promised to come back with something working,
> not slides.
>
> Here's the plan for our hour: about ten minutes where I ask *you* some
> questions, since I've only heard half the room so far. Then a short
> framing, a live demo on a codebase shaped like yours, what it's worth
> to Northgate, and a pilot proposal. We'll keep the last ten minutes for
> your questions. Does that work?
>
> One more thing: what would make this hour a clear win for each of you?"

Write down each person's answer. **Use them in the close.**

---

## 5. Discovery (0:04-0:14)

Aim for 2-3 questions per person and listen 70% of the time. Each
question sets up a specific demo beat. Note the numbers on paper; you
will reuse them in the value section.

| To | Question | Listen for | Sets up |
|---|---|---|---|
| Priya | "Walk me through the last alert you closed, from the moment it fired to closed. Where did the time go?" | Advisory reading, grepping, "proving it doesn't apply" | Beat 1, the raw queue |
| Priya | "Of the alerts you closed last month, roughly what share needed a code change?" | "Maybe 1 in 10" | The 56 to 5 moment |
| Priya | "When a bump does need to go in, what happens next?" | Builds broke, developers ignore PRs *(hidden)* | Remediation PR with tests |
| Marcus | "When you dismiss a finding today, what gets written down, and who would ever check it?" | One-line Jira comment *(hidden)* | Evidence drawer + validator |
| Marcus | "What would an auditor need to see to accept 'not reachable' as a decision?" | Evidence, reviewer, repeatability | Validator, "every verdict cites real code" |
| Marcus | "What's the worst outcome if a tool wrongly dismissed a finding, and how do you guard against that with humans today?" | Fear of false negatives | Shadow-mode pilot, the false-dismiss gate |
| Dana | "Where does this problem show up for you: hours, roadmap, or the board?" | Roadmap slip, board risk committee *(hidden)* | Value section |
| Dana | "If we're sitting here in six months and this worked, what's different? Who notices?" | "No SLA breaches at the audit" | Pilot success metrics |
| Ravi | "What's working well with Copilot today? Where did you hope it would help with this and it didn't?" | Copilot is great in the editor and doesn't do triage | Positioning |
| Ravi | "What did your internal prototype get right, and what's been hardest to keep running?" | No evals, no owner after Q1 *(hidden)* | Build vs buy |
| Ravi | "Beyond security, where else do you want agents running without a developer at the keyboard?" | PR review org-wide *(hidden)* | Expansion: Droid review |
| Anyone | "Who else needs to sign off on an agent that touches code, and how does vendor security review work here?" | Process, timeline, procurement | Pilot week 0 |

**Adapt live:** if a hidden fact comes out, say it back in your own words
("So the auditor's real complaint was the *missing evidence*, not just
the late fixes?") and tie it to a specific demo screen. That move is
what the panel scores as "adapting to the customer."

**Transition to the pitch:** "That's really helpful. Let me play it
back: [three pains in their words]. Let me show you how we'd attack
exactly that."

---

## 6. Pitch (0:14-0:19): slides 2-3

**Slide 2, "The work nobody is at the keyboard for."**
> "Scanners are very good at listing what's *installed*. They can't say
> what's *reachable*. That gap gets filled by Priya, by hand, six
> minutes at a time. On one small service: 56 findings, 3 of them
> Critical, and only 5 actually matter. Two of the three Criticals are
> an API you never call. Meanwhile a High-rated one, libwebp, was
> exploited in the wild and *is* reachable from customer uploads.
> Severity sorting would have put it behind the noise."

**Slide 3, "Agents that do the work end to end, with receipts."**
> "Copilot is a great assistant for the developer at the keyboard. Keep
> it. This is different work: it runs on a schedule, fans out across
> every service, and nobody's typing. Factory runs Droids headless in
> your pipeline. One agent per finding reads the advisory and the code
> and decides with cited evidence. A second step opens the fix. Droid
> reviews the PR, including a security review. Every claim is checked
> mechanically against the code before anyone sees it."

Keep it under 5 minutes. **The demo is the pitch.**

---

## 7. Demo (0:19-0:33)

A tighter cut of `DEMO.md`, re-ordered around what *this* room cares
about. Name the person each beat is for.

1. **For Priya, the raw queue (2 min).** Click "Show the raw scanner
   queue." "This is your Monday. 56 rows, three Criticals. Which one
   would you start with?" *Let them answer.* That is a discovery
   moment inside the demo.
2. **The triaged board (2 min).** "Same 56 findings: 5 act now, 6
   monitor, 45 dismissed. Each one cites the code."
3. **For Marcus, evidence (4 min).** Open **PyYAML** (the call path
   across two files and a two-part fix), then **requests
   Proxy-Authorization** (a dismissal with a *revisit trigger*). "This
   is the record your auditor asked for: the reason, the lines, and
   when to look again."
4. **For Marcus, why you can trust it (2 min).** Run `make validate`.
   "Every quote is checked line for line against the code. A verdict
   that can't cite real code can't ship." Then tell the story: **the
   live agent disagreed with my own verdict and was right.**
   `data/live_smoke_run1.json` has the receipts.
5. **For Priya and Ravi, from decision to fix (3 min).** Open PR #9:
   four changes close 36 of 56 findings, with tests. Show **Droid's
   code and security review** on the PR, then its two commits (the
   remediation, then Droid's repair of the Pillow rename the required
   check caught). Optional live moment: comment
   `@droid why is safe_load sufficient here, given the !!merge keys?`
   (post it in the first minutes of the demo so the reply has time to
   arrive).
6. **For Dana, the punchline (1 min).** "This service went from 5.6
   hours to 32 minutes of review. Let's see what that's worth across
   your 40 services."

**Demo-risk plan:** run `make validate` and `make triage` and start
`make serve` before the call. If the network fails, show the screenshots
in `docs-screens/` and the PR page cached in a browser tab. Never debug
live for more than 20 seconds. Say "let me show you the recorded
result" and move on.

---

## 8. Value (0:33-0:38): slide 4, rebuilt with their numbers

Present this as a formula and fill it in live with discovery numbers.
The defaults below are **illustrative**, so say so.

| Input | Default | Source |
|---|---|---|
| Services | 40 | Prior call |
| New findings per service per week | 10 | **Ask Priya** |
| Manual minutes per finding | 6 | MVP assumption; ask Priya |
| Share that needs a human (act now + monitor) | ~20% | MVP: 11 of 56 |
| Review minutes per surfaced finding | 3 | MVP: 32 min for 11 |
| Open backlog | 1,800 | Prior call |

- **Steady state:** 40 × 10 × 6 min = **40 h/week** today, which is a full
  third of a 3-person team. With triage agents: 80 surfaced × 3 min =
  **4 h/week**. That frees **~36 hours a week** of senior security time.
- **Backlog:** 1,800 × 6 min = **180 hours**, about 4.5 weeks of one
  engineer, cleared in a batch run plus a review sprint.
- **Risk (Dana and Marcus):** SLA breaches flagged by the auditor, and
  a board commitment. The real asset is a *cited decision record* for
  every finding.
- **Developer trust (Ravi):** fewer, smaller, tested bump PRs, so
  developers stop ignoring them.

Say: "These are your numbers, not ours. The pilot exists to measure
them for real."

---

## 9. Pilot (0:38-0:46): slide 5

**Scope:** 3 services Priya picks (one high-traffic, one legacy, one
typical), GitHub App on those 3 repos only, 6 weeks.

| Week | Phase | What happens |
|---|---|---|
| 0 | Set up | Vendor security review, GitHub App on 3 repos, API key, agree success criteria in writing |
| 1 | Baseline | Measure current triage time and SLA aging. **Priya hand-triages a blind sample of 50 findings** as ground truth |
| 2-3 | Shadow | Agents triage everything and nothing gets acted on. Compare against the blind sample |
| 4-5 | Assisted | Act-now cards become fix PRs with Droid review. Priya reviews dismissals in batches |
| 6 | Readout | Results to Dana and Marcus, then a go/no-go on rolling out to 40 services |

**Success metrics** (agree on targets in week 0):

| Metric | Target | Owner |
|---|---|---|
| False dismissals on the blind sample (a reachable finding marked dismiss) | **0, a hard gate** | Marcus |
| Agreement with Priya's verdicts | ≥ 90% | Priya |
| Reviewer minutes per finding | < 1 (from ~6) | Priya |
| Critical/High past SLA in pilot repos | -50% | Marcus |
| Citation validity (validator) | 100% | Automatic |
| Fix PRs merged without breaking the build | ≥ 80% | Ravi |
| Senior security hours returned per week | Report the actual number | Dana |

**Why the false-dismiss gate matters:** it turns Marcus's biggest
objection into the pilot's first exit criterion. Say it out loud: "If
it wrongly dismisses one reachable finding in the blind sample, we stop
and figure out why before going further."

**Moving the business forward:** after the pilot, the same pattern
(scan, reason with evidence, fix, review) extends to CodeQL findings,
license findings, and dependency migrations. Ravi gets org-wide Droid
PR review from the same rollout. That is the expansion story, so plant
it and don't sell it.

**Close (ask for something specific):**
> "Here's what I'd propose: Priya picks the three services this week,
> Marcus, we get the vendor security questionnaire to your team by
> Friday, and we hold 30 minutes in two weeks for the week-0 kickoff.
> Dana, would you sponsor the week-6 readout?"

Recap each person's "clear win" from the opening and how the pilot answers it.

---

## 10. Positioning (be fair; never trash competitors)

**Core line:** *"Keep Copilot for the developer at the keyboard. Use
Factory for the work nobody is at the keyboard for."*

| | Strong at | Gap for *this* workflow | How to say it |
|---|---|---|---|
| **GitHub Copilot / Autofix / Dependabot** | Code completion and chat in the editor; Autofix for CodeQL alerts; Dependabot bump PRs | Bumps answer *can we upgrade*, not *does it reach our code*; no cited "not reachable" record; no fan-out triage | "Complementary. Dependabot finds and bumps. Factory decides, explains, and fixes the ones that need code changes, like the PyYAML loader." |
| **Claude Code (internal prototype)** | Excellent model and terminal agent; flexible | You own evals, citation checks, orchestration, CI integration, on-call | "Great choice of model. The question is who maintains the platform around it after Q1." Factory is model-agnostic, so Ravi isn't locked in. |
| **Cursor** | AI-native editor, strong for interactive coding | Editor-centric; this work is headless and scheduled | Same framing as Copilot. |
| **Devin** | Autonomous task-level agent | Ask how it does org-wide, parallel, CI-native work with verifiable output | Focus on fan-out, auditability, and running in their pipeline. |

**Factory points to stress (all demonstrated in the MVP):**
- **Headless and CI-native:** `droid exec` runs one session per finding in parallel; the GitHub Action posts code and security review on PRs.
- **Same agent across interfaces:** CLI, desktop, CI, and `@droid` in PR comments.
- **Model choice:** pick the model per job (`droid exec -m`), so no single-vendor lock-in.
- **Org knowledge as skills:** triage policy, lane rules, and trust boundaries become reusable instructions rather than prompt folklore.

> **Verify before the interview (don't improvise these):** current
> pricing model, compliance certifications (SOC 2 and others),
> data-retention and zero-retention options, self-hosted or VPC
> options, and BYOK details. Get them from Factory docs or the
> interviewers' own materials. If asked and unsure: "Let me confirm
> exactly and send it in writing today." That is a credibility win, not
> a loss.

---

## 11. Objection handling

The pattern for every objection: **Acknowledge, Explore (ask a discovery
question first), Respond, Prove (point at the demo).** The "Explore" step
is how objections become discovery, which is one of the scored criteria.

**1. "We already have Copilot and GHAS. Dependabot and Autofix handle this." (Dana or Ravi)**
- Explore: "How many Dependabot PRs merged last month, versus how many are still open?" / "When Autofix runs, what does it do for a dependency CVE?"
- Respond: Dependabot answers upgradeability. It can't tell you two of the three Criticals are unreachable, or that PyYAML needs a code change and not just a bump. Factory sits on top of the GitHub investment and makes it actionable.
- Prove: the PyYAML card (two-part fix) and the Jinja2 "delete the dead pin" card.

**2. "Ravi's team can build this on Claude Code in two sprints." (Ravi)**
- Explore: "What would you need beyond the prompt: evals, citation checks, parallel runs, CI integration, someone on call?" / "Who owns it after Q1?"
- Respond: the prompt is the easy 10%. The validator, the fan-out, the review loop, and keeping it running are the 90%. Building it is a valid choice if it's strategic for them. Otherwise Ravi's team gets the platform and spends its time on Northgate-specific skills.
- Prove: `scripts/validate.py` and the live-agent disagreement story.

**3. "I don't trust an AI to dismiss vulnerabilities." (Marcus) *The most important one.***
- Explore: "How do you know today's human dismissals are right? Has one ever been wrong?"
- Respond: agree with the instinct. That's why every verdict carries checked citations, confidence labels, and revisit triggers, and why the pilot *starts* in shadow mode against Priya's blind sample with a zero-false-dismissal gate. The agent doesn't replace judgment; it removes the grep.
- Prove: `make validate`, the medium-confidence PDF card, and the live agent catching a bug in my verdict.

**4. "Our code can't leave our environment." (Marcus)**
- Explore: "What's your current policy for Copilot? What did that review require?"
- Respond: anchor on the Copilot precedent they already approved, then give the factual deployment and data-handling options **(verify; see §10)**. Offer to start the vendor questionnaire this week.

**5. "This is a toy app. Our services are 200k-line monorepos." (Priya or Ravi)**
- Explore: "Which service would be the hardest test?" Then put it in the pilot.
- Respond: the fixture has known answers, which a demo needs. The pipeline consumes any Trivy JSON unchanged. The agent works the way Priya does (grep, read, trace), and that scales with parallel sessions, not repo size. The pilot uses their hardest service on purpose.

**6. "Too many AI tools. Come back after the Copilot renewal." (Dana)**
- Explore: "What would you need to see before the renewal to make a confident decision either way?"
- Respond: this isn't a Copilot replacement, so it doesn't compete with the renewal. A 6-week pilot fits *before* Q1 and gives Dana data for the budget conversation. Developers don't get a new tool; the output lands as PRs and Jira/Slack updates.

**7. "Copilot's coding agent will do this soon anyway." (Ravi)**
- Explore: "If it shipped tomorrow, what would it need to do for Marcus to accept its dismissals?"
- Respond: the requirements are the same either way (cited evidence, verification, auditability), and the audit is in 5 months. Factory is model- and tool-agnostic, so the pilot isn't a bet against GitHub.

**8. "What does it cost?" (Dana)**
- Explore: "How are you thinking about it: per seat, or against hours returned?"
- Respond: anchor on value first (~36 security hours a week, the audit risk), then give the real pricing model **(verify; don't invent numbers)**. Pilot pricing goes to the account executive.

**9. "Won't this bury my developers in PRs?" (Priya or Ravi)**
- Explore: "How many PRs a week can a team absorb before ignoring them?"
- Respond: grouping is the point. Four fixes in one PR closed 36 findings in the demo. The pilot can cap PRs per repo per week.

**When you don't know:** "I don't want to guess on that. I'll confirm and send it in writing today." Write it down visibly. Then use it as a next step.

---

## 12. Q&A (0:50-1:00) and close

- Ask them first: "What did you see today that you'd want to dig into further?"
- End on the mutual plan from §9, with names and dates.
- Follow-up email within 24 hours: recap in their words, the business case with their numbers, the pilot plan, open questions with owners.

---

## 13. Prep checklist

- [ ] Send role cards (§2) to the panel 24-48 h ahead
- [ ] Verify the Factory facts flagged in §10 (pricing, certifications, data handling, deployment options)
- [ ] `make validate` and `make triage` pass; `make serve` running; dashboard open in a tab
- [ ] PR #9 open in a tab, with Droid's review and repair commit visible
- [ ] Optional: post the `@droid` question on PR #9 near the start of the demo
- [ ] Screenshots in `docs-screens/` as a fallback
- [ ] A notepad grid: one column per persona for their "clear win" and their numbers
- [ ] Rehearse the opening and the pilot close out loud and time both
