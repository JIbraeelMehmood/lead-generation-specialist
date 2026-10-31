/* LeadFinder: Dorking tab
   Google Custom Search (CSE) query-template engine for discovering business websites.
   Requires a CSE API key + Search Engine ID (set in Settings → Additional API keys).
   Public business discovery only — not a vulnerability scanner.
*/
(function(){
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const api = (p, b) => window.LF.api(p, b);

let _leads = [];
const TEMPLATES = {
  "niche_city":     "{niche} in {city} {country}",
  "contact_page":   "{niche} {city} contact us",
  "hiring":         '"we are hiring" {niche} {city}',
  "needs_website":  '{niche} {city} -site:facebook.com -site:instagram.com',
  "case_studies":   "{niche} case studies {city}",
  "company":        '"{company}" {city} {country}',
};
const DEFAULT_SELECTED = ["niche_city","hiring","needs_website"];

// ---------------------------------------------------------------- mount
function mount(){
  const sec = document.createElement("section");
  sec.id = "tab-dorking"; sec.hidden = true;
  sec.innerHTML = `
  <div class="panel">
    <h2>Google Dorking — Business Discovery</h2>
    <p class="sub" style="margin-top:-4px">Use Google Custom Search query templates to find business websites by niche and city.
    Requires a <b>Google Custom Search API key</b> and <b>Search Engine ID (CX)</b> — set these in <b>Settings → Additional API keys</b>.</p>

    <div class="grid">
      <div>
        <label for="dkNiche">Business niche</label>
        <input id="dkNiche" placeholder="e.g. plumber, dentist, restaurant">
      </div>
      <div>
        <label for="dkCity">City</label>
        <input id="dkCity" placeholder="e.g. Austin">
      </div>
      <div>
        <label for="dkCountry">Country (optional)</label>
        <input id="dkCountry" placeholder="e.g. USA">
      </div>
      <div>
        <label for="dkCompany">Company name (optional)</label>
        <input id="dkCompany" placeholder="Search for a specific company">
      </div>
      <div>
        <label for="dkLimit">Max results per template</label>
        <input id="dkLimit" type="number" value="20" min="5" max="100">
      </div>
    </div>

    <h3>Query templates</h3>
    <p class="sub">Select the templates to run. Each uses one CSE API call per 10 results.</p>
    <div id="dkTemplates" class="seg" style="flex-wrap:wrap;margin-bottom:12px"></div>

    <div class="toolbar">
      <button class="btn primary" id="dkRun">Run discovery</button>
      <button class="btn sm" id="dkAddAll" disabled>Add all to My list</button>
      <button class="btn sm" id="dkExport" disabled>Download CSV</button>
    </div>
    <div id="dkMsg"></div>
    <div id="dkReport"></div>
    <div id="dkResults"></div>
  </div>

  <div class="panel">
    <h2>Custom Query</h2>
    <p class="sub" style="margin-top:-4px">Run any custom Google search query directly against your Custom Search Engine.</p>
    <div class="grid" style="align-items:end">
      <div>
        <label for="dkCustomQuery">Search query</label>
        <input id="dkCustomQuery" placeholder='e.g. plumber London "no website" OR "coming soon"'>
      </div>
      <div>
        <label for="dkCustomLimit">Max results</label>
        <input id="dkCustomLimit" type="number" value="20" min="5" max="100">
      </div>
      <div><button class="btn primary" id="dkCustomRun" style="width:100%">Search</button></div>
    </div>
    <div id="dkCustomMsg"></div>
    <div id="dkCustomResults"></div>
  </div>`;

  document.querySelector(".wrap").appendChild(sec);

  // Build template checkboxes
  const tplEl = document.getElementById("dkTemplates");
  Object.entries(TEMPLATES).forEach(([k, v]) => {
    const lbl = document.createElement("label");
    lbl.className = "seg";
    lbl.style.cssText = "display:inline-flex;gap:6px;align-items:center;margin:2px;padding:6px 10px;border:1px solid var(--line);border-radius:8px;cursor:pointer;font-size:13px";
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.value = k; cb.checked = DEFAULT_SELECTED.includes(k);
    lbl.appendChild(cb);
    lbl.appendChild(document.createTextNode(` ${k.replace(/_/g," ")} — `));
    const code = document.createElement("code");
    code.style.fontSize = "11px"; code.textContent = v;
    lbl.appendChild(code);
    tplEl.appendChild(lbl);
  });

  const nav = document.querySelector("nav");
  const b = document.createElement("button");
  b.setAttribute("role","tab"); b.dataset.tab = "dorking"; b.textContent = "Dorking";
  b.setAttribute("aria-selected","false");
  nav.appendChild(b);
  window.LF.bindTab(b, ()=>{});
}

// ---------------------------------------------------------------- render results table
function renderResults(leads, containerId){
  const el = document.getElementById(containerId);
  if (!leads.length){ el.innerHTML = '<div class="empty">No results found.</div>'; return; }
  el.innerHTML = `<div class="tablewrap" style="margin-top:10px"><table>
    <thead><tr><th>Business / Title</th><th>Website</th><th>Snippet</th><th></th></tr></thead>
    <tbody>${leads.map(l => `<tr>
      <td class="nm">${esc(l.name||"(untitled)")}</td>
      <td><a class="sub" href="${esc(l.website)}" target="_blank" rel="noopener">${esc((l.website||"").slice(0,50))}</a></td>
      <td class="sub" style="max-width:300px">${esc((l.snippet||"").slice(0,120))}</td>
      <td><button class="btn sm primary" data-dork-add="${esc(l.id)}">Add</button></td>
    </tr>`).join("")}</tbody>
  </table></div>`;
  el.querySelectorAll("[data-dork-add]").forEach(btn => {
    btn.onclick = () => {
      const lead = leads.find(l => l.id === btn.dataset.dorkAdd);
      if (lead){ window.LF.addLeads([lead]); btn.textContent = "Added ✓"; btn.disabled = true; }
    };
  });
}

// ---------------------------------------------------------------- run discovery
async function runDiscovery(){
  const btn = document.getElementById("dkRun");
  btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Searching…';
  const msg = document.getElementById("dkMsg");
  try {
    const templates = [...document.querySelectorAll("#dkTemplates input:checked")].map(cb => cb.value);
    if (!templates.length){ throw new Error("Select at least one template."); }
    const r = await api("/api/dorking", {
      niche:   (document.getElementById("dkNiche").value   || "").trim(),
      city:    (document.getElementById("dkCity").value    || "").trim(),
      country: (document.getElementById("dkCountry").value || "").trim(),
      company: (document.getElementById("dkCompany").value || "").trim(),
      templates,
      limit: parseInt(document.getElementById("dkLimit").value) || 20,
    });
    _leads = r.leads || [];
    // Show per-template report
    const report = r.report || {};
    const rows = Object.entries(report).map(([k, v]) =>
      `<tr><td class="sub">${esc(k)}</td><td class="sub" style="font-size:12px">${esc(v.query)}</td><td>${v.found}</td>
       ${v.errors.length ? `<td class="sub" style="color:var(--warn)">${esc(v.errors.join("; ").slice(0,80))}</td>` : '<td>—</td>'}</tr>`
    ).join("");
    document.getElementById("dkReport").innerHTML = `
      <div class="panel" style="margin-top:10px">
        <h3>Run report — ${_leads.length} unique results</h3>
        <div class="tablewrap"><table style="min-width:400px">
          <thead><tr><th>Template</th><th>Query</th><th>Found</th><th>Errors</th></tr></thead>
          <tbody>${rows}</tbody>
        </table></div>
      </div>`;
    renderResults(_leads, "dkResults");
    msg.innerHTML = _leads.length ? `<div class="msg ok">Found ${_leads.length} unique results across ${Object.keys(report).length} template(s).</div>`
      : '<div class="msg err">No results. Check your API key and CX in Settings.</div>';
    document.getElementById("dkAddAll").disabled = !_leads.length;
    document.getElementById("dkExport").disabled = !_leads.length;
  } catch(e){
    msg.innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
  btn.disabled = false; btn.textContent = "Run discovery";
}

// ---------------------------------------------------------------- custom query
async function runCustom(){
  const btn = document.getElementById("dkCustomRun");
  btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Searching…';
  const msg = document.getElementById("dkCustomMsg");
  try {
    const query = (document.getElementById("dkCustomQuery").value || "").trim();
    if (!query){ throw new Error("Enter a search query."); }
    const limit = parseInt(document.getElementById("dkCustomLimit").value) || 20;
    // Use webcrawler CSE endpoint for a single raw query
    const r = await api("/api/webcrawler/crawl", {keyword: query, limit});
    const leads = r.leads || [];
    msg.innerHTML = `<div class="msg ok">Found ${r.urlsFound} URLs, ${leads.length} businesses.</div>`;
    renderResults(leads, "dkCustomResults");
  } catch(e){
    msg.innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
  btn.disabled = false; btn.textContent = "Search";
}

// ---------------------------------------------------------------- init
document.addEventListener("DOMContentLoaded", () => {
  mount();
  document.getElementById("dkRun").onclick = runDiscovery;
  document.getElementById("dkCustomRun").onclick = runCustom;
  document.getElementById("dkAddAll").onclick = () => {
    if (_leads.length){ window.LF.addLeads(_leads); document.getElementById("dkAddAll").textContent = `Added ${_leads.length} ✓`; }
  };
  document.getElementById("dkExport").onclick = () => {
    if (!_leads.length) return;
    const header = ["name","website","snippet","category","source"];
    const q = v => `"${String(v??'').replace(/"/g,'""')}"`;
    const csv = [header, ..._leads.map(l => header.map(k => l[k]))].map(r => r.map(q).join(",")).join("\r\n");
    const a = document.createElement("a"); a.href = "data:text/csv;charset=utf-8,\ufeff" + encodeURIComponent(csv);
    a.download = "dorking-results.csv"; a.click();
  };
});
})();
