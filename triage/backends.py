"""Agent backends for the triage pipeline.

- CachedBackend: replays verdicts authored by Droid during the build
  session (data/golden/verdicts.json). Fast and deterministic — the
  demo-safe path.
- DroidCliBackend: runs a fresh headless Factory session per finding to
  re-derive the verdict from scratch. Slow but fully live.

Both produce the same record shape, so the dashboard never cares which
one ran.
"""
import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = REPO_ROOT / "data" / "golden" / "verdicts.json"
SAMPLE_APP = REPO_ROOT / "sample-app"

VERDICT_FIELDS = (
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


class BackendError(RuntimeError):
    pass


class CachedBackend:
    """Replays Droid-authored golden verdicts, keyed by '<id>:<package>'."""

    name = "cached"

    def __init__(self, golden_path: Path = GOLDEN_PATH):
        if not golden_path.exists():
            raise BackendError(f"no golden verdicts at {golden_path}")
        self.verdicts = json.loads(golden_path.read_text())

    def triage(self, finding: dict) -> dict:
        verdict = self.verdicts.get(f"{finding['id']}:{finding['package']}")
        if verdict is None:
            return {
                "cve": finding["id"],
                "package": finding["package"],
                "verdict": "untriaged",
                "confidence": "none",
                "one_line": "No golden verdict; run `make triage-live` to triage this with a live Droid session.",
                "reasoning": "",
                "vulnerable_path": "",
                "attack_surface": "",
                "evidence": [],
                "recommended_action": "make triage-live",
                "patch_hint": "",
                "effort": "?",
            }
        out = dict(verdict)
        out.setdefault("cve", finding["id"])
        out.setdefault("package", finding["package"])
        return out


DROID_FALLBACK_PATH = Path(
    "/Applications/Factory.app/Contents/Resources/bin/droid"
)


class DroidCliBackend:
    """One headless Factory session per finding, via `droid exec`.

    Finds the CLI on PATH, falling back to the binary bundled with the
    Factory desktop app. Override with REACH_AGENT_CMD (binary + leading
    flags; the prompt file path is appended automatically), e.g.:

        REACH_AGENT_CMD='droid exec --cwd /abs/path/to/sample-app'
    """

    name = "droid"

    def __init__(self, app_dir: Path = SAMPLE_APP, timeout_s: int = 900):
        from .prompt import build_finding_prompt

        self.app_dir = app_dir
        self.timeout_s = timeout_s
        self._build_prompt = build_finding_prompt

    def _resolve_cli(self) -> str:
        override = os.environ.get("REACH_AGENT_CMD")
        if override:
            return shlex.split(override)[0]
        on_path = shutil.which("droid")
        if on_path:
            return on_path
        if DROID_FALLBACK_PATH.exists():
            return str(DROID_FALLBACK_PATH)
        raise BackendError(
            "no Factory CLI found on PATH or at the desktop-app fallback. "
            "Install the Factory CLI, or set REACH_AGENT_CMD. The cached "
            "backend works without a CLI: make triage"
        )

    def triage(self, finding: dict) -> dict:
        # `droid exec` is non-interactive. The prompt goes through a temp
        # file (-f) to sidestep argv quoting issues with multi-line text.
        prompt_path = None
        try:
            import tempfile

            cli = self._resolve_cli()
            override = os.environ.get("REACH_AGENT_CMD")
            lead = shlex.split(override)[1:] if override else []
            fd, prompt_path = tempfile.mkstemp(suffix=".md", prefix="reach-prompt-")
            with os.fdopen(fd, "w") as fh:
                fh.write(self._build_prompt(finding))
            cmd = [cli, "exec", *lead, "-f", prompt_path, "--cwd", str(self.app_dir)]
            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=self.timeout_s
                )
            except subprocess.TimeoutExpired as exc:
                raise BackendError(f"agent timed out on {finding['id']}") from exc
            if proc.returncode != 0:
                raise BackendError(
                    f"agent run failed for {finding['id']}: {proc.stderr[-500:]}"
                )
            return self._parse(proc.stdout, finding)
        finally:
            if prompt_path and Path(prompt_path).exists():
                Path(prompt_path).unlink()

    @staticmethod
    def _parse(stdout: str, finding: dict) -> dict:
        # `droid exec` mixes the model's answer with session logging, so scan
        # for the last JSON object in the output that parses and carries a
        # verdict. raw_decode ignores trailing content after each candidate.
        clean = re.sub(r"\x1b\[[0-9;]*m", "", stdout)
        decoder = json.JSONDecoder()
        candidates = []
        for i, ch in enumerate(clean):
            if ch != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(clean, i)
            except ValueError:
                continue
            if isinstance(obj, dict) and "verdict" in obj:
                candidates.append(obj)
        if not candidates:
            raise BackendError(f"no JSON verdict in agent output for {finding['id']}")
        verdict = candidates[-1]
        verdict.setdefault("cve", finding["id"])
        verdict.setdefault("package", finding["package"])
        verdict.setdefault("verdict", "untriaged")
        return verdict


def get_backend(name: str):
    if name == "cached":
        return CachedBackend()
    if name == "droid":
        return DroidCliBackend()
    raise BackendError(f"unknown backend: {name}")
