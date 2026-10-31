/* LeadFinder: Pipeline / Suppression tab
   - View and manage the do-not-contact suppression list
   - Blueprint config (daily targets, project value, approval rules)
*/
(function(){
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const api = (p, b) => window.LF.api(p, b);

// ---------------------------------------------------------------- mount
function mount(){
  const sec = document.createElement("section");
  sec.id = "tab-pipeline"; sec.hidden = true;
  sec.innerHTML = `
  <!-- SUPPRESSION LIST -->
  <div class="panel">
    <h2>Suppression List (Do-Not-Contact)</h2>
    <p class="sub" style="margin-top:-4px">Domains on this list are automatically skipped in autopilot runs and flagged during outreach. Add any client, competitor, or anyone who has asked not to be contacted.</p>
    <div class="grid" style="align-items:end;max-width:540px">
      <div>
        <label for="suppDomain">Domain to suppress</label>
        <input id="suppDomain" placeholder="example.com">
      </div>
      <div><button class="btn primary" id="suppAdd">Add to suppression list</button></div>
    </div>
    <div id="suppMsg"></div>
    <div id="suppList" style="margin-top:12px"></div>
  </div>

  <!-- BLUEPRINT CONFIG -->
  <div class="panel">
    <h2>Blueprint Configuration</h2>
    <p class="sub" style="margin-top:-4px">These settings govern how the autopilot and opportunity engine operate. Adjust them to match your workflow and project budget.</p>
    <div class="grid">
      <div>
        <label for="bpDaily">Daily candidate target</label>
        <input id="bpDaily" type="number" value="75" min="1">
      </div>
      <div>
        <label for="bpMin">Min project value (USD)</label>
        <input id="bpMin" type="number" value="300" min="0">
      </div>
      <div>
        <label for="bpMax">Max project value (USD)</label>
        <input id="bpMax" type="number" value="1000" min="0">
      </div>
    </div>
    <div style="margin-top:10px">
      <label class="seg" style="display:inline-flex;gap:8px;align-items:center;margin-bottom:8px">
        <input type="checkbox" id="bpApproval" checked>
        Require human approval before outreach
      </label><br>
      <label class="seg" style="display:inline-flex;gap:8px;align-items:center;margin-bottom:8px">
        <input type="checkbox" id="bpEvidence" checked>
        Require evidence URL for confirmed opportunities
      </label><br>
      <label class="seg" style="display:inline-flex;gap:8px;align-items:center">
        <input type="checkbox" id="bpOptOut" checked>
        Always respect opt-outs
      </label>
    </div>
    <button class="btn primary" id="bpSave" style="margin-top:12px">Save blueprint config</button>
    <div id="bpMsg"></div>
  </div>

  <!-- DEDUP CHECK -->
  <div class="panel">
    <h2>Deduplication Check</h2>
    <p class="sub" style="margin-top:-4px">Check whether a website domain is already on your suppression list, or check an entire list at once to filter suppressed leads.</p>
    <div class="grid" style="align-items:end;max-width:540px">
      <div>
        <label for="dedupUrl">URL or domain</label>
        <input id="dedupUrl" placeholder="https://example.com or example.com">
      </div>
      <div><button class="btn" id="dedupCheck">Check domain</button></div>
    </div>
    <div id="dedupMsg"></div>
    <hr style="border:0;border-top:1px solid var(--line);margin:16px 0">
    <p class="sub">Filter your current My list to remove suppressed domains:</p>
    <button class="btn" id="dedupFilterList">Filter My list</button>
    <div id="dedupListMsg"></div>
  </div>`;

  document.querySelector(".wrap").appendChild(sec);

  const nav = document.querySelector("nav");
  const b = document.createElement("button");
  b.setAttribute("role","tab"); b.dataset.tab = "pipeline"; b.textContent = "Pipeline";
  b.setAttribute("aria-selected","false");
  nav.appendChild(b);
  window.LF.bindTab(b, loadAll);
}

// ---------------------------------------------------------------- suppression
async function loadSuppressionList(){
  try {
    const r = await api("/api/suppression", {});
    const domains = r.domains || [];
    const el = document.getElementById("suppList");
    if (!domains.length){
      el.innerHTML = '<p class="sub">Suppression list is empty.</p>'; return;
    }
    el.innerHTML = `<div class="tablewrap"><table style="min-width:300px">
      <thead><tr><th>Domain</th><th></th></tr></thead>
      <tbody>${domains.map(d => `<tr>
        <td class="sub">${esc(d)}</td>
        <td><button class="btn sm" data-supp-remove="${esc(d)}">Remove</button></td>
      </tr>`).join("")}</tbody>
    </table></div>`;
    el.querySelectorAll("[data-supp-remove]").forEach(btn => {
      btn.onclick = async () => {
        await api("/api/suppression", {remove: btn.dataset.suppRemove});
        loadSuppressionList();
      };
    });
  } catch(e){
    document.getElementById("suppList").innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
}

async function addSuppression(){
  const domain = (document.getElementById("suppDomain").value || "").trim();
  if (!domain){ document.getElementById("suppMsg").innerHTML = '<div class="msg err">Enter a domain first.</div>'; return; }
  try {
    await api("/api/suppression", {add: domain});
    document.getElementById("suppMsg").innerHTML = `<div class="msg ok">${esc(domain)} added to suppression list.</div>`;
    document.getElementById("suppDomain").value = "";
    loadSuppressionList();
  } catch(e){
    document.getElementById("suppMsg").innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
}

// ---------------------------------------------------------------- blueprint config
async function loadBpConfig(){
  try {
    const r = await api("/api/bp-config", {});
    const c = r.config || {};
    const el = v => document.getElementById(v);
    if (c.daily_candidate_target !== undefined) el("bpDaily").value = c.daily_candidate_target;
    if (c.project_value_min_usd !== undefined) el("bpMin").value = c.project_value_min_usd;
    if (c.project_value_max_usd !== undefined) el("bpMax").value = c.project_value_max_usd;
    if (c.require_human_approval_before_outreach !== undefined) el("bpApproval").checked = c.require_human_approval_before_outreach;
    if (c.require_evidence_for_confirmed_opportunity !== undefined) el("bpEvidence").checked = c.require_evidence_for_confirmed_opportunity;
    if (c.respect_opt_outs !== undefined) el("bpOptOut").checked = c.respect_opt_outs;
  } catch(e){}
}

async function saveBpConfig(){
  const el = v => document.getElementById(v);
  const save = {
    daily_candidate_target: parseInt(el("bpDaily").value) || 75,
    project_value_min_usd: parseInt(el("bpMin").value) || 300,
    project_value_max_usd: parseInt(el("bpMax").value) || 1000,
    require_human_approval_before_outreach: el("bpApproval").checked,
    require_evidence_for_confirmed_opportunity: el("bpEvidence").checked,
    respect_opt_outs: el("bpOptOut").checked,
  };
  try {
    await api("/api/bp-config", {save});
    el("bpMsg").innerHTML = '<div class="msg ok">Blueprint config saved.</div>';
  } catch(e){
    el("bpMsg").innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
}

// ---------------------------------------------------------------- dedup
async function dedupCheck(){
  const url = (document.getElementById("dedupUrl").value || "").trim();
  const msg = document.getElementById("dedupMsg");
  if (!url){ msg.innerHTML = '<div class="msg err">Enter a URL or domain.</div>'; return; }
  try {
    const r = await api("/api/dedup/check", {url});
    msg.innerHTML = r.suppressed
      ? `<div class="msg err">⛔ <b>${esc(r.domain)}</b> is on the suppression list.</div>`
      : `<div class="msg ok">✓ <b>${esc(r.domain)}</b> is NOT suppressed.</div>`;
  } catch(e){
    msg.innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
}

async function dedupFilterList(){
  const leads = window.LF.getList();
  if (!leads.length){ document.getElementById("dedupListMsg").innerHTML = '<div class="msg err">My list is empty.</div>'; return; }
  try {
    const r = await api("/api/dedup/filter", {leads});
    const msg = document.getElementById("dedupListMsg");
    if (!r.droppedCount){
      msg.innerHTML = `<div class="msg ok">All ${leads.length} leads are clean — none are suppressed.</div>`;
    } else {
      const names = r.dropped.map(l => esc(l.name || l.website || "unknown")).join(", ");
      msg.innerHTML = `<div class="msg err">⚠ ${r.droppedCount} suppressed leads found: ${names}.
        <button class="btn sm" style="margin-left:10px" id="dedupRemove">Remove them from My list</button></div>`;
      document.getElementById("dedupRemove").onclick = () => {
        const suppIds = new Set(r.dropped.map(l => l.id));
        const all = window.LF.getList().filter(l => !suppIds.has(l.id));
        // rebuild list via internal state (getList returns the live array)
        const live = window.LF.getList();
        suppIds.forEach(id => { const i = live.findIndex(l => l.id === id); if (i >= 0) live.splice(i, 1); });
        window.LF.refresh && window.LF.refresh();
        msg.innerHTML = `<div class="msg ok">Removed ${r.droppedCount} suppressed leads from My list.</div>`;
      };
    }
  } catch(e){
    document.getElementById("dedupListMsg").innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
}

// ---------------------------------------------------------------- load all on tab open
async function loadAll(){
  await Promise.all([loadSuppressionList(), loadBpConfig()]);
}

// ---------------------------------------------------------------- init
document.addEventListener("DOMContentLoaded", () => {
  mount();
  document.getElementById("suppAdd").onclick = addSuppression;
  document.getElementById("bpSave").onclick = saveBpConfig;
  document.getElementById("dedupCheck").onclick = dedupCheck;
  document.getElementById("dedupFilterList").onclick = dedupFilterList;
});
})();
