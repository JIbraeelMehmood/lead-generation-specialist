/* LeadFinder: Opportunities tab
   Standalone view of the scored opportunity engine.
   Analyzes all leads in My list and shows them ranked by blueprint score,
   with per-lead opportunity cards.
*/
(function(){
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const api = (p, b) => window.LF.api(p, b);

let _results = [];

// ---------------------------------------------------------------- HTML shell
function mount(){
  const sec = document.createElement("section");
  sec.id = "tab-opportunities"; sec.hidden = true;
  sec.innerHTML = `
  <div class="panel">
    <h2>Opportunities</h2>
    <p class="sub" style="margin-top:-4px">Score every lead in My list using the 5-component opportunity engine
    (opportunity · fit · commercial · contactability · confidence) to find your best-value prospects.</p>
    <div class="toolbar">
      <select id="oppFilter" style="max-width:200px">
        <option value="all">All bands</option>
        <option value="Review first">Review first (80+)</option>
        <option value="Normal review">Normal review (65+)</option>
        <option value="Nurture / research">Nurture / research (50+)</option>
        <option value="Skip">Skip (&lt;50)</option>
      </select>
      <div class="grow"></div>
      <button class="btn sm primary" id="oppAnalyze">Analyze My list</button>
      <button class="btn sm" id="oppExport">Download CSV</button>
    </div>
    <div id="oppMsg"></div>
    <div id="oppProgress" hidden style="margin:8px 0"></div>
  </div>
  <div id="oppSummary" class="tally" style="margin-bottom:12px"></div>
  <div id="oppList"></div>`;

  document.querySelector(".wrap").appendChild(sec);

  const nav = document.querySelector("nav");
  const b = document.createElement("button");
  b.setAttribute("role","tab"); b.dataset.tab = "opportunities"; b.textContent = "Opportunities";
  b.setAttribute("aria-selected","false");
  nav.appendChild(b);
  window.LF.bindTab(b, renderCached);
}

// ---------------------------------------------------------------- band colors
const BAND_CLASS = {
  "Review first": "t-no",
  "Normal review": "t-weak",
  "Nurture / research": "t-yes",
  "Skip": "t-yes",
};

// ---------------------------------------------------------------- render
function renderSummary(data){
  const counts = {};
  data.forEach(r => { const b = (r.score || {}).band || "?"; counts[b] = (counts[b]||0)+1; });
  const order = ["Review first","Normal review","Nurture / research","Skip"];
  const tally = document.getElementById("oppSummary");
  tally.innerHTML = `<div><b>${data.length}</b><span>analyzed</span></div>` +
    order.map(b => `<div><b>${counts[b]||0}</b><span>${esc(b)}</span></div>`).join("");
}

function scoreBar(sub){
  const total = sub.total || 0;
  const pct = Math.round(total);
  const cols = [
    ["opportunity", sub.opportunity, 30, "var(--go)"],
    ["fit",         sub.fit,         20, "#6AB0D8"],
    ["commercial",  sub.commercial,  20, "#F0B35A"],
    ["contactability", sub.contactability, 15, "#B08AF0"],
    ["confidence",  sub.confidence,  15, "#7DC9A3"],
  ];
  const segs = cols.map(([k, v, max, col]) =>
    `<div title="${k}: ${v}/${max}" style="flex:${v};background:${col};height:8px"></div>`
  ).join("");
  return `<div style="display:flex;border-radius:4px;overflow:hidden;margin:4px 0">${segs}</div>
    <div class="sub" style="font-size:12px">Total: <b>${pct}</b>/100
      · ${cols.map(([k,v,max]) => `${k} ${v}/${max}`).join(" · ")}
    </div>`;
}

function oppCard(r){
  const sub = r.score || {};
  const band = sub.band || "?";
  const opps = r.opportunities || [];
  const pkg  = r.recommendedPackage || {};
  const high = opps.filter(o => o.confidence === "high").length;
  const oppRows = opps.slice(0,6).map(o => `<tr>
    <td class="sub">${esc(o.category.replace(/_/g," "))}</td>
    <td>${esc(o.observation)}</td>
    <td><span class="tag ${o.confidence==="high"?"t-no":o.confidence==="medium"?"t-weak":"t-yes"}">${esc(o.confidence)}</span></td>
    <td class="sub">${esc(o.suggested_fix)}</td>
  </tr>`).join("");

  return `<div class="panel" style="margin-bottom:12px">
    <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:8px">
      <div>
        <div class="nm">${esc(r.lead.name)}</div>
        <div class="sub">${esc(r.lead.category||"")} · ${esc(r.lead.website||"no website")}</div>
      </div>
      <div style="text-align:right">
        <span class="tag ${BAND_CLASS[band]||"t-yes"}" style="font-size:14px;padding:4px 12px">${esc(band)}</span>
        <div class="sub" style="margin-top:4px">Score: ${sub.total||0}/100</div>
        ${pkg.name ? `<div class="sub">Recommended: ${esc(pkg.name)} ${esc(pkg.price||"")}</div>` : ""}
      </div>
    </div>
    ${scoreBar(sub)}
    ${opps.length ? `<details style="margin-top:8px"><summary class="sub">${high} high · ${opps.length} total opportunities</summary>
      <div class="tablewrap" style="margin-top:6px"><table style="min-width:400px">
        <thead><tr><th>Category</th><th>Finding</th><th>Confidence</th><th>Suggested fix</th></tr></thead>
        <tbody>${oppRows}</tbody>
      </table></div>
    </details>` : '<div class="sub" style="margin-top:6px">No specific opportunities found.</div>'}
    <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">
      <button class="btn sm primary" data-opp-add="${esc(r._leadId)}">Add to My list</button>
    </div>
  </div>`;
}

function renderList(){
  const filter = (document.getElementById("oppFilter")||{}).value || "all";
  const rows = filter === "all" ? _results
    : _results.filter(r => (r.score||{}).band === filter);
  const sorted = [...rows].sort((a,b) => ((b.score||{}).total||0) - ((a.score||{}).total||0));
  const el = document.getElementById("oppList");
  if (!el) return;
  if (!sorted.length){
    el.innerHTML = `<div class="empty panel">No leads yet. Click "Analyze My list" to score your leads.</div>`;
    return;
  }
  el.innerHTML = sorted.map(r => oppCard(r)).join("");
  // bind add buttons
  el.querySelectorAll("[data-opp-add]").forEach(btn => {
    btn.onclick = () => {
      const id = btn.dataset.oppAdd;
      const lead = window.LF.getList().find(l => l.id === id);
      if (lead){ window.LF.addToList && window.LF.addToList(lead); btn.textContent = "In list ✓"; btn.disabled = true; }
    };
  });
}

function renderCached(){
  if (_results.length){ renderSummary(_results); renderList(); }
}

// ---------------------------------------------------------------- analyze
document.addEventListener("DOMContentLoaded", () => {
  const oppF = document.getElementById("oppFilter");
  if (oppF) oppF.onchange = renderList;
  const oppExport = document.getElementById("oppExport");
  if (oppExport) oppExport.onclick = exportCsv;
  document.getElementById("oppAnalyze").onclick = analyze;
});

async function analyze(){
  const leads = window.LF.getList();
  if (!leads.length){ document.getElementById("oppMsg").innerHTML = '<div class="msg err">Your list is empty — add some leads first.</div>'; return; }
  const btn = document.getElementById("oppAnalyze");
  btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Analyzing…';
  const prog = document.getElementById("oppProgress");
  prog.hidden = false;
  _results = [];
  let done = 0;
  const queue = [...leads];
  const worker = async () => {
    while (queue.length){
      const lead = queue.shift();
      try {
        const r = await api("/api/opportunities", {lead});
        r._leadId = lead.id;
        _results.push(r);
      } catch(e){ _results.push({lead:{name:lead.name,website:lead.website,category:lead.category,source:lead.source}, opportunities:[], score:{total:0,band:"Skip",opportunity:0,fit:0,commercial:0,contactability:0,confidence:0}, _leadId:lead.id}); }
      done++;
      prog.textContent = `Analyzed ${done}/${leads.length}…`;
      if (done % 3 === 0){ renderSummary(_results); renderList(); }
    }
  };
  await Promise.all([worker(), worker(), worker()]);
  prog.hidden = true;
  renderSummary(_results); renderList();
  btn.disabled = false; btn.textContent = "Analyze My list";
}

// ---------------------------------------------------------------- CSV export
function exportCsv(){
  if (!_results.length){ alert("Analyze first."); return; }
  const header = ["Name","Website","Category","Score","Band","Opportunity","Fit","Commercial","Contactability","Confidence","Opportunities","Package"];
  const rows = _results.map(r => {
    const s = r.score||{}; const l = r.lead||{};
    return [l.name, l.website, l.category, s.total, s.band, s.opportunity, s.fit, s.commercial, s.contactability, s.confidence,
            (r.opportunities||[]).length, (r.recommendedPackage||{}).name];
  });
  const q = v => `"${String(v??'').replace(/"/g,'""')}"`;
  const csv = [header, ...rows].map(r => r.map(q).join(",")).join("\r\n");
  const a = document.createElement("a"); a.href = "data:text/csv;charset=utf-8,\ufeff" + encodeURIComponent(csv);
  a.download = "opportunities.csv"; a.click();
}

// ---------------------------------------------------------------- init
document.addEventListener("DOMContentLoaded", mount);
})();
