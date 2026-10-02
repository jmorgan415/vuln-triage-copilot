"""Prompt construction for the live agent backend.

The cached backend replays verdicts that were produced with this same
prompt in Droid sessions; the droid backend re-runs it from scratch on
every finding.
"""
import json

OUTPUT_SCHEMA = {
    "cve": "str — the vulnerability id",
    "package": "str — affected package name",
    "verdict": "one of: act_now | monitor | dismiss",
    "confidence": "one of: high | medium | low",
    "one_line": "one-sentence summary for the queue card",
    "reasoning": "2-5 sentences of plain-English rationale for the verdict",
    "vulnerable_path": "the exact code path/condition that makes this exploitable, or 'not reachable'",
    "attack_surface": "who can trigger it and how, if reachable",
    "evidence": [
        {
            "file": "path relative to repo root",
            "line_start": 1,
            "line_end": 2,
            "quote": "the exact source lines, verbatim",
        }
    ],
    "recommended_action": "concrete next step for the engineer",
    "patch_hint": "code sketch for the fix, or 'none'",
    "effort": "one of: S | M | L",
}

SYSTEM_FRAME = """You are the triage agent inside Reach, a reachability-first vulnerability triage copilot used by a security engineer at Northgate Financial.

A dependency scanner has produced a finding against the sample-app repository (Python). Decide whether the finding is worth the engineer's attention, based on whether the vulnerable code path is actually reachable from what this application does.

Method:
1. Inspect sample-app for imports and call sites of the affected package.
2. Identify the specific function or condition the CVE requires.
3. Trace whether application inputs can reach it, and whether the vulnerable conditions (attacker-controlled input, proxy configuration, redirects, specific YAML loaders, etc.) actually hold in this codebase.
4. Prefer dismiss with a precise rationale when the vulnerable condition cannot hold. Prefer act_now only with concrete evidence of reachability and impact. Use monitor for reachable-but-lower-impact or mitigated cases.

Be rigorous: cite exact files and line ranges from the repo. Do not pad. Do not speculate about code you cannot find.

Respond with STRICT JSON only (no markdown fences, no prose around it), matching this schema:

{schema}
"""


def build_finding_prompt(finding: dict) -> str:
    """Build the full prompt for one scanner finding."""
    finding_block = json.dumps(
        {
            "vulnerability_id": finding["id"],
            "package": finding["package"],
            "installed_version": finding["installed"],
            "fixed_version": finding.get("fixed") or "unknown",
            "scanner_severity": finding["severity"],
            "title": finding["title"],
            "description": (finding.get("description") or "")[:1500],
        },
        indent=2,
    )
    return (
        SYSTEM_FRAME.format(schema=json.dumps(OUTPUT_SCHEMA, indent=2))
        + "\nFinding to triage:\n"
        + finding_block
    )
