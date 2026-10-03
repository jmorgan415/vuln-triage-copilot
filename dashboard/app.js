// Reach — vulnerability triage copilot dashboard.
// Data contract: data/triage_results.json written by triage/run_triage.py,
// plus optional data/fix_verification.json written by scripts/verify_fixes.py
// and data/pr_history.json written by scripts/pr_history.py.

const state = { data: null, verify: null, history: [], noiseView: false, collapsed: {} };

const FIX_STATUS = {
  verified: { label: "fix verified", cls: "ok" },
  untested: { label: "fix untested", cls: "warn" },
  tests_failed: { label: "fix tests failed", cls: "bad" },
  not_resolved: { label: "fix not resolved", cls: "bad" },
};

const SEV_CLS = {
  CRITICAL: "crit",
  HIGH: "high",
  MEDIUM: "med",
  LOW: "low",
  UNKNOWN: "unk",
};

const LANES = [
  { key: "act_now", title: "Act Now", cls: "lane-act" },
  { key: "monitor", title: "Monitor", cls: "lane-mon" },
  { key: "dismiss", title: "Dismiss (with evidence)", cls: "lane-dis" },
];

function esc(text) {
  return String(text ?? "").replace(/[&<>"]/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;",
  }[c]));
}

function fmtMinutes(min) {
  if (min >= 60) return `${(min / 60).toFixed(1)} h`;
  return `${Math.round(min)} min`;
}

async function boot() {
  const res = await fetch("../data/triage_results.json");
  state.data = await res.json();
  try {
    const vres = await fetch("../data/fix_verification.json");
    if (vres.ok) state.verify = await vres.json();
  } catch (_) {
    state.verify = null;
  }
  try {
    const hres = await fetch("../data/pr_history.json");
    if (hres.ok) state.history = await hres.json();
  } catch (_) {
    state.history = [];
  }
  renderMetrics();
  renderVerify();
  renderHistory();
  renderBoard();
  renderNoise();
  renderMeta();
  wire();
}

function renderMetrics() {
  const { meta } = state.data;
  const total = state.data.findings.length;
  const { summary } = meta;
  const el = document.getElementById("metrics");
  el.innerHTML = `
    <div class="metric hero">
      <div class="label">Scanner findings in</div>
      <div class="value">${total}</div>
    </div>
    <div class="metric act">
      <div class="label">Act now</div>
      <div class="value">${summary.act_now}</div>
    </div>
    <div class="metric mon">
      <div class="label">Monitor</div>
      <div class="value">${summary.monitor}</div>
    </div>
    <div class="metric dis">
      <div class="label">Dismissed with evidence</div>
      <div class="value">${summary.dismiss}</div>
    </div>
    <div class="metric hero">
      <div class="label">Priya's Monday queue</div>
      <div class="value">${fmtMinutes(meta.manual_minutes_baseline)} → ${fmtMinutes(meta.review_minutes_estimate)}</div>
    </div>
  `;
  const note = document.getElementById("untriaged-note");
  if (summary.untriaged > 0) {
    note.hidden = false;
    note.textContent = `${summary.untriaged} finding(s) awaiting live triage — run \`make triage-live\``;
  }
}

function fixFor(f) {
  return state.verify?.findings?.[`${f.id}:${f.package}`] || null;
}

function fixByPackage(pkg) {
  return (state.verify?.fixes || []).find((x) => x.package === pkg) || null;
}

function fixBadge(f) {
  const fx = fixFor(f);
  if (!fx) return "";
  const s = FIX_STATUS[fx.status] || { label: fx.status, cls: "warn" };
  return `<span class="fix-badge ${s.cls}">${esc(s.label)}</span>`;
}

function renderVerify() {
  const v = state.verify;
  const el = document.getElementById("verify-strip");
  if (!v) return;
  const { gate, tests, rescan, meta } = v;
  const verified = v.fixes.filter((x) => x.status === "verified").length;
  el.hidden = false;
  el.className = `verify-strip ${gate.passed ? "ok" : "bad"}`;
  el.innerHTML = `
    <span class="gate">${gate.passed ? "✓ Fix PR verified" : "✗ Fix PR blocked"}</span>
    <span class="vitem">${esc(meta.ref)} @ <code>${esc(meta.commit)}</code></span>
    <span class="vitem">tests <b>${tests.passed}/${tests.ran}</b> on Python ${esc(meta.python)}</span>
    <span class="vitem">${verified}/${v.fixes.length} fixes verified</span>
    <span class="vitem">rescan <b>${rescan.before} → ${rescan.after}</b> findings</span>
    <span class="vitem">${rescan.introduced.length} introduced</span>
    ${gate.reasons.map((r) => `<span class="vreason">${esc(r)}</span>`).join("")}
  `;
}

function verifyHtml(f) {
  const fx = fixFor(f);
  if (!fx) return "";
  const fix = fixByPackage(fx.package);
  if (!fix) return "";
  const s = FIX_STATUS[fix.status] || { label: fix.status, cls: "warn" };
  const key = `${f.id}:${f.package}`;
  const closed = fix.findings_closed.includes(key);
  const change = fix.to ? `${fix.from} → ${fix.to}` : `${fix.from} → removed`;
  return `
    <h4>Fix verification</h4>
    <div class="kv">
      <span class="k">Status</span><span><span class="fix-badge ${s.cls}">${esc(s.label)}</span></span>
      <span class="k">Change</span><span>${esc(fix.package)} ${esc(change)}</span>
      <span class="k">Tests</span><span>${fix.tests_passed}/${fix.tests_ran} passed (${esc(fix.tests.join(", ") || "none")})</span>
      <span class="k">Rescan</span><span>${closed ? "finding no longer reported" : "finding still reported"}</span>
      <span class="k">Verified on</span><span>${esc(state.verify.meta.ref)} @ ${esc(state.verify.meta.commit)}, Python ${esc(state.verify.meta.python)}</span>
    </div>
  `;
}

function stepResult(s) {
  const ok = s.gate.passed;
  return `${ok ? "✓" : "✗"} tests ${s.tests.passed}/${s.tests.ran} · findings ${s.rescan.before} → ${s.rescan.after} · ${s.rescan.introduced.length} introduced`;
}

function stepHtml(s) {
  const ok = s.gate.passed;
  const fixed = s.app_diff.length > 0;
  return `
    <li class="step ${ok ? "ok" : "bad"}">
      <div class="s-label">${fixed ? "Fix committed" : "Change pushed"} · <code>${esc(s.commit)}</code> · ${esc(s.author)}</div>
      <div class="s-head">${esc(s.headline)}</div>
      ${fixed ? patchHtml(s.app_diff.join("\n")) : ""}
      <div class="s-result">${esc(stepResult(s))}</div>
      ${s.tests.errors.map((e) => `<div class="s-error">${esc(e)}</div>`).join("")}
      <div class="s-gate">${ok ? "Gate passed, merge unblocked" : "Gate failed, merge blocked"}
        ${s.ci?.url ? ` · <a href="${esc(s.ci.url)}" target="_blank" rel="noopener">CI run</a>` : ""}</div>
    </li>
  `;
}

function renderHistory() {
  const el = document.getElementById("history");
  if (!state.history.length) return;
  el.hidden = false;
  el.innerHTML = state.history.map((h) => `
    <div class="pr-history">
      <div class="pr-head">
        <span class="pr-kicker">Fix PR history</span>
        <a href="${esc(h.url)}" target="_blank" rel="noopener">PR #${h.pr}</a>
        <span class="pr-title">${esc(h.title)}</span>
      </div>
      <ol class="steps">${h.steps.map(stepHtml).join('<li class="arrow" aria-hidden="true">→</li>')}</ol>
    </div>
  `).join("");
}

function historyHtml(f) {
  const prs = state.history.filter((h) =>
    h.steps.some((s) => s.fixes.some((x) => x.package === f.package))
  );
  if (!prs.length) return "";
  return prs.map((h) => `
    <h4>PR #${h.pr} history</h4>
    <ul class="drawer-steps">
      ${h.steps.map((s) => `
        <li class="${s.gate.passed ? "ok" : "bad"}">
          <code>${esc(s.commit)}</code> ${esc(s.author)}: ${esc(stepResult(s))}
          ${s.tests.errors.map((e) => `<div class="s-error">${esc(e)}</div>`).join("")}
        </li>`).join("")}
    </ul>
    <p><a href="${esc(h.url)}" target="_blank" rel="noopener">Open PR #${h.pr}</a></p>
  `).join("");
}

function cardHtml(f) {
  const sev = SEV_CLS[f.severity] || "unk";
  return `
    <article class="card ${sev}" data-cve="${esc(f.id)}">
      <div class="row1">
        <span class="cve">${esc(f.id)}</span>
        <span class="sev ${sev}">${esc(f.severity)}</span>
      </div>
      <div class="pkg">${esc(f.package)} ${esc(f.installed)} → ${esc(f.fixed || "?")}</div>
      <div class="oneline">${esc(f.one_line)}</div>
      <div class="conf">confidence: ${esc(f.confidence)} ${fixBadge(f)}</div>
    </article>
  `;
}

function renderBoard() {
  const board = document.getElementById("board");
  board.innerHTML = LANES.map((lane) => {
    const items = state.data.findings.filter((f) => f.verdict === lane.key);
    const collapsed = state.collapsed[lane.key] ? "collapsed" : "";
    return `
      <section class="lane ${lane.cls} ${collapsed}" data-lane="${lane.key}">
        <header>
          <h2>${lane.title}</h2>
          <span class="count">${items.length} findings</span>
        </header>
        <div class="cards">
          ${items.map(cardHtml).join("")}
        </div>
      </section>
    `;
  }).join("");
  board.querySelectorAll(".card").forEach((el) => {
    el.addEventListener("click", () => {
      const f = state.data.findings.find((x) => x.id === el.dataset.cve);
      if (f) openDrawer(f);
    });
  });
  board.querySelectorAll(".lane header").forEach((hdr) => {
    hdr.addEventListener("click", () => {
      const key = hdr.parentElement.dataset.lane;
      state.collapsed[key] = !state.collapsed[key];
      renderBoard();
    });
  });
}

function renderNoise() {
  const el = document.getElementById("noise-list");
  const sevOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, UNKNOWN: 4 };
  const items = [...state.data.findings].sort(
    (a, b) => (sevOrder[a.severity] ?? 9) - (sevOrder[b.severity] ?? 9)
  );
  el.innerHTML = items.map((f) => {
    const sev = SEV_CLS[f.severity] || "unk";
    return `
      <div class="noise-row" data-cve="${esc(f.id)}">
        <span class="sev nsev ${sev}">${esc(f.severity)}</span>
        <span class="cve">${esc(f.id)}</span>
        <span class="npkg">${esc(f.package)} ${esc(f.installed)}</span>
        <span class="ntitle">${esc(f.title || "")}</span>
      </div>
    `;
  }).join("");
  el.querySelectorAll(".noise-row").forEach((row) => {
    row.addEventListener("click", () => {
      const f = state.data.findings.find((x) => x.id === row.dataset.cve);
      if (f) openDrawer(f);
    });
  });
}

function evidenceHtml(ev) {
  return (ev || []).map((e) => `
    <div class="evidence">
      <div class="file">${esc(e.file)}:${e.line_start}-${e.line_end}</div>
      <pre>${esc(e.quote)}</pre>
    </div>
  `).join("");
}

function patchHtml(hint) {
  if (!hint || hint === "none") return "<p>—</p>";
  const lines = String(hint).split("\n").map((line) => {
    const cls = line.startsWith("+") ? "plus" : line.startsWith("-") ? "minus" : "";
    return `<span class="${cls}">${esc(line)}</span>`;
  });
  return `<div class="patch"><code>${lines.join("\n")}</code></div>`;
}

function openDrawer(f) {
  const drawer = document.getElementById("drawer");
  const overlay = document.getElementById("overlay");
  document.getElementById("drawer-body").innerHTML = `
    <span class="verdict-banner ${esc(f.verdict)}">${esc(f.verdict.replace("_", " "))}</span>
    <h3>${esc(f.id)}</h3>
    <div class="subhead">
      ${esc(f.package)} ${esc(f.installed)} → fixed in ${esc(f.fixed || "?")}
      · scanner severity ${esc(f.severity)} · confidence ${esc(f.confidence)}
    </div>
    <h4>Summary</h4>
    <p>${esc(f.one_line)}</p>
    <h4>Why</h4>
    <p>${esc(f.reasoning)}</p>
    <div class="kv">
      <span class="k">Vulnerable path</span><span>${esc(f.vulnerable_path)}</span>
      <span class="k">Attack surface</span><span>${esc(f.attack_surface)}</span>
      <span class="k">Effort</span><span>${esc(f.effort)}</span>
      <span class="k">Triaged by</span><span>${esc(f.triaged_by)} backend</span>
    </div>
    <h4>Evidence from the codebase</h4>
    ${evidenceHtml(f.evidence)}
    <h4>Recommended action</h4>
    <p>${esc(f.recommended_action)}</p>
    <h4>Patch hint</h4>
    ${patchHtml(f.patch_hint)}
    ${verifyHtml(f)}
    ${historyHtml(f)}
    <h4>Advisory</h4>
    <p><a href="${esc(f.primary_url)}" target="_blank" rel="noopener">${esc(f.primary_url || f.id)}</a></p>
  `;
  drawer.hidden = false;
  overlay.hidden = false;
}

function closeDrawer() {
  document.getElementById("drawer").hidden = true;
  document.getElementById("overlay").hidden = true;
}

function renderMeta() {
  const { meta } = state.data;
  document.getElementById("meta-strip").textContent =
    `backend: ${meta.backend} · scanner: ${meta.scanner} · generated: ${meta.generated_at} · ` +
    `manual baseline assumes ${meta.assumptions.manual_minutes_per_finding} min/finding (${meta.assumptions.note}) · ` +
    `golden verdicts: data/golden/verdicts.json (authored by Droid sessions)`;
}

function toggleNoise() {
  state.noiseView = !state.noiseView;
  document.getElementById("noise").hidden = !state.noiseView;
  document.getElementById("board").hidden = state.noiseView;
  document.getElementById("toggle-noise").textContent = state.noiseView
    ? "Back to the triaged board"
    : "Show the raw scanner queue";
}

function wire() {
  document.getElementById("toggle-noise").addEventListener("click", toggleNoise);
  document.getElementById("drawer-close").addEventListener("click", closeDrawer);
  document.getElementById("overlay").addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeDrawer();
  });
}

boot();
