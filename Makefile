# Reach — vulnerability triage copilot demo harness
# Persona: security engineer at Northgate Financial

.PHONY: scan triage triage-live serve validate verify history demo

# Produce raw scanner output from the sample app's pinned deps.
scan:
	trivy fs --scanners vuln --format json -o data/raw_scan.json sample-app

# Replay the Droid-authored golden verdicts (fast, deterministic).
triage:
	python3 triage/run_triage.py --backend cached

# Re-derive verdicts from scratch with live Droid sessions (slow: N findings).
triage-live:
	python3 triage/run_triage.py --backend droid --max-workers 3

# Serve the dashboard at http://localhost:8765
serve:
	python3 -m http.server 8765

# Self-check: evidence citations point at real code.
validate:
	python3 scripts/validate.py

# Prove the fix branch is safe: clean pinned install, per-fix tests,
# Trivy rescan. Writes data/fix_verification.json for the dashboard.
verify:
	python3 scripts/verify_fixes.py

# Re-verify each commit of a fix PR (red bump -> Droid repair) for the
# dashboard's "Fix PR history" panel. Usage: make history PR=9
history:
	python3 scripts/pr_history.py --pr $(PR)

demo: triage
	@echo "Run 'make serve' in another terminal, then open http://localhost:8765/dashboard/"
