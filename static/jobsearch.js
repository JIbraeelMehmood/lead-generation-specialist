/* LeadFinder: Job search tab. Find companies actively hiring developers on BeBee,
   Google search and JobLeads. Every result links back to its source. You read it and reply yourself. */
(function(){
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const api = (p, b) => window.LF.api(p, b || {});
let results = [], data = {sources: {}, bebeeFilters: {}};

const SRC = {bebee: "BeBee", google: "Google search", jobleads: "JobLeads"};

function mount(){
  const sec = document.createElement("section");
  sec.id = "tab-jobsearch"; sec.hidden = true;
  sec.innerHTML = `
  <div class="panel">
    <h2>Job search</h2>
    <p class="sub" style="margin-top:-4px">Find companies already hiring developers. BeBee is free and needs no key. Google search and JobLeads go through SerpApi (add your SerpApi key in Settings) - JobLeads is Cloudflare-protected, so its posts are surfaced through Google with a site:jobleads.com search.</p>
    <div class="grid">
      <div style="grid-column:span 2"><label for="jsQuery">Job search query</label><input id="jsQuery" placeholder="e.g. PHP Laravel backend developer software engineer"></div>
      <div><label for="jsLoc">Location (optional)</label><input id="jsLoc" placeholder="e.g. Lahore"></div>
      <div><label for="jsCountry">BeBee country code</label><input id="jsCountry" placeholder="pk" value="pk" style="max-width:120px"></div>
    </div>
    <div class="toolbar" style="margin-top:10px;align-items:center">
      <span class="sub">Sources:</span>
      <span class="seg">
        <label><input type="checkbox" id="jsBebee" checked> BeBee (free)</label>
        <label><input type="checkbox" id="jsGoogle"> Google search</label>
        <label><input type="checkbox" id="jsJobleads"> JobLeads</label>
      </span>
    </div>
    <details style="margin-top:8px"><summary class="sub" style="cursor:pointer">BeBee filters</summary>
      <div class="grid" style="margin-top:8px">
        <div><label for="jsContract">Contract type</label><select id="jsContract"><option value="">Any</option></select></div>
        <div><label for="jsPosted">Posted within</label><select id="jsPosted"><option value="">Anytime</option></select></div>
        <div><label for="jsRemote">Remote</label><select id="jsRemote"><option value="">Any</option></select></div>
        <div><label for="jsJobType">Job type</label><select id="jsJobType"><option value="">Any</option></select></div>
      </div>
    </details>
    <div class="toolbar" style="margin-top:10px">
      <span class="grow"></span>
      <button class="btn sm primary" id="jsSearch">Search jobs</button>
    </div>
    <div id="jsMsg"></div>
  </div>
  <div id="jsReport"></div>
  <div id="jsList"></div>`;
  const wrap = document.querySelector(".wrap");
  const hiring = document.querySelector("#tab-hiring");
  wrap.insertBefore(sec, hiring ? hiring.nextSibling : wrap.querySelector("section"));
  const nav = document.querySelector("nav");
  const b = document.createElement("button");
  b.setAttribute("role","tab"); b.dataset.tab = "jobsearch"; b.innerHTML = "Job search";
  const after = nav.querySelector('[data-tab="hiring"]') || nav.querySelector('[data-tab="today"]') || nav.querySelector('[data-tab="list"]');
  nav.insertBefore(b, after ? after.nextSibling : nav.children[0]);
  window.LF.bindTab(b, () => {});
}

function fillFilters(){
  const f = data.bebeeFilters || {};
  const opt = (vals) => vals.map(v => `<option value="${esc(v)}">${v ? esc(v).replace("_", " ") : "Any"}</option>`).join("");
  $("#jsContract").innerHTML = opt(f.contractType || ["","full_time","part_time","contract"]);
  $("#jsPosted").innerHTML = opt(f.postedWithin || ["","24h","3d","7d","14d","30d"]);
  $("#jsRemote").innerHTML = opt(f.remote || ["","full_remote","hybrid","on_site"]);
  $("#jsJobType").innerHTML = opt(f.jobType || ["","company","recruiter","headhunter"]);
  $("#jsPosted").value = "14d";
}

function read(){
  const filters = {contractType: $("#jsContract").value, postedWithin: $("#jsPosted").value,
                    remote: $("#jsRemote").value, jobType: $("#jsJobType").value};
  const sources = [];
  if ($("#jsBebee").checked) sources.push("bebee");
  if ($("#jsGoogle").checked) sources.push("google");
  if ($("#jsJobleads").checked) sources.push("jobleads");
  return {query: $("#jsQuery").value.trim(), location: $("#jsLoc").value.trim(),
          country: $("#jsCountry").value.trim() || "pk", sources: sources.length ? sources : ["bebee"], filters};
}

function renderReport(report){
  if (!report || !Object.keys(report).length){ $("#jsReport").innerHTML = ""; return; }
  $("#jsReport").innerHTML = `<div class="panel" style="padding:10px 14px"><div class="sub"><b>Per source:</b> ${
    Object.entries(report).map(([k, r]) => {
      const name = data.sources[k]?.name || SRC[k] || k;
      return `${esc(name)}: ${r.error ? '<span style="color:var(--stop)">' + esc(r.error) + "</span>" : r.fetched + " found"}`;
    }).join(" &nbsp;·&nbsp; ")}</div></div>`;
}

function render(){
  if (!results.length){
    $("#jsList").innerHTML = `<div class="panel empty">No job leads yet. Type a query and press Search jobs.</div>`;
    return;
  }
  $("#jsList").innerHTML = results.map(p => `
    <div class="panel" data-id="${esc(p.id)}" style="padding:14px">
      <div class="toolbar" style="margin:0 0 4px;align-items:baseline">
        <div class="grow">
          <div class="nm">${esc(p.title)}</div>
          <div class="sub">${esc(p.company || "—")}${p.location ? " · " + esc(p.location) : ""}${p.jobType ? " · " + esc(p.jobType) : ""}${p.postedAt ? " · " + esc(p.postedAt) : ""}</div>
        </div>
        <span class="tag t-yes">${esc(p.sourceName)}</span>
      </div>
      <div class="sub" style="white-space:pre-wrap;max-height:7.5em;overflow:hidden;margin:4px 0">${esc(p.snippet)}</div>
      <div class="acts" style="margin-top:8px">
        <a class="btn sm primary" href="${esc(p.url)}" target="_blank" rel="noopener">Open on ${esc(p.sourceName)}</a>
        <button class="btn sm" data-fit="1">Fit</button>
        <button class="btn sm" data-tailor="1">Tailor resume</button>
        <button class="btn sm" data-save="1">Save application</button>
        <button class="btn sm" data-ai="1">Write reply with AI</button>
        <button class="btn sm" data-add="1">Add to My list</button>
      </div>
      <div data-out></div>
      <div data-career></div>
    </div>`).join("");
}

function replyPrompt(p){
  const S = window.LF.settings();
  return `I am ${S.myName || "a developer"}${S.myBusiness ? " from " + S.myBusiness : ""}.
Write a short, specific application reply (under 130 words) for this job post. Open with one line showing I understood the exact need, then 2-3 lines on how I'd approach it. Ask for a quick call or ask one useful question. No generic claims, no invented numbers, no placeholders except [portfolio link]. Also give a one-line email subject.

${p.sourceName}:
${p.title}
${p.company ? "Company: " + p.company : ""}
${p.location ? "Location: " + p.location : ""}
${p.snippet}`;
}

async function onClick(e){
  const t = e.target.closest("button[data-ai],button[data-add],button[data-fit],button[data-tailor],button[data-save]");
  if (!t) return;
  const card = t.closest("[data-id]"); const id = card.dataset.id;
  const p = results.find(x => x.id === id);
  if (!p) return;
  const out = card.querySelector("[data-career]");
  const careerJob = () => ({id: "src:" + id, company: p.company || "", title: p.title || "",
    url: p.url || "", location: p.location || "", jobType: p.jobType || "", source: p.sourceName || "",
    query: p.query || "", posting: p.snippet || ""});
  if (t.dataset.fit){
    out.innerHTML = '<p class="sub"><span class="spin"></span> Scoring fit…</p>';
    try { const r = await api("/api/career/fit", {job: careerJob()});
      out.innerHTML = `<div class="msg ${r.fit==="Skip"||r.fit==="Low"?"err":"ok"}"><b>${esc(r.fit)}</b> — ${esc(r.reasons||"")}${r.dealbreakers&&r.dealbreakers.length?` · Dealbreakers: ${esc(r.dealbreakers.join(", "))}`:""}</div>`; }
    catch(err){ out.innerHTML = `<div class="msg err">${esc(err.message)}</div>`; }
    return;
  }
  if (t.dataset.save){
    try { const r = await api("/api/career/job/save", {job: careerJob()});
      t.textContent = "Saved in Career"; t.disabled = true; out.innerHTML = `<div class="msg ok">Saved to Career → Job applications (id ${esc(r.id)}). Open the Career tab to tailor a resume and write a cover letter.</div>`; }
    catch(err){ out.innerHTML = `<div class="msg err">${esc(err.message)}</div>`; }
    return;
  }
  if (t.dataset.tailor){
    out.innerHTML = '<p class="sub"><span class="spin"></span> Saving & tailoring resume… (20-60s)</p>';
    try { const s = await api("/api/career/job/save", {job: careerJob()});
      const r = await api("/api/career/tailor", {jobId: s.id});
      out.innerHTML = `<div class="msg ok">Tailored resume saved to Career (id ${esc(r.jobId)}). by ${esc(r.provider||"AI")}.</div>
        <div style="white-space:pre-wrap;background:var(--bg);border-radius:8px;padding:12px;margin-top:8px;max-height:22em;overflow:auto;font-size:13px">${esc(r.resume)}</div>
        <div class="toolbar"><span class="sub grow">Review and edit in the Career tab.</span><button class="btn sm" data-copyresume="1">Copy</button></div>`;
      out.querySelector("[data-copyresume]").onclick = ev => navigator.clipboard.writeText(r.resume).then(()=>ev.target.textContent="Copied");
      t.textContent = "Tailored"; }
    catch(err){ out.innerHTML = `<div class="msg err">${esc(err.message)}</div>`; }
    return;
  }
  if (t.dataset.add){
    const lead = {id: "job:" + id, source: "Job search (" + p.sourceName + ")", name: p.company || p.title,
      category: p.title, address: p.location || "Remote", phone: "", email: "", website: "",
      social: "", rating: null, reviews: 0, mapsUrl: p.url, searchQuery: p.query};
    window.LF.addLeads([lead]);
    window.LF.updateLead(lead.id, {notes: p.sourceName + ": " + p.url});
    t.textContent = "Added"; t.disabled = true; return;
  }
  if (t.dataset.ai){
    const out = card.querySelector("[data-out]");
    out.innerHTML = '<p class="sub"><span class="spin"></span> Writing…</p>';
    try {
      const r = await api("/api/ai", {ai: {provider: "pool"}, prompt: replyPrompt(p)});
      out.innerHTML = `<div style="white-space:pre-wrap;background:var(--bg);border-radius:8px;padding:12px;margin-top:10px;font-size:14px">${esc(r.text)}</div>
        <div class="toolbar"><span class="sub grow">by ${esc(r.provider || "AI")}. Read and edit before you send.</span><button class="btn sm" data-copy="1">Copy</button></div>`;
      out.querySelector("[data-copy]").onclick = ev => navigator.clipboard.writeText(r.text).then(() => ev.target.textContent = "Copied");
    } catch(err){ out.innerHTML = `<div class="msg err">${esc(err.message)}</div>`; }
  }
}

function init(){
  mount();
  $("#jsList").addEventListener("click", onClick);
  $("#jsSearch").onclick = async e => {
    const b = e.target; const q = read();
    if (!q.query){ $("#jsMsg").innerHTML = '<div class="msg err">Enter a job search query.</div>'; return; }
    b.disabled = true; b.innerHTML = '<span class="spin"></span> Searching…';
    $("#jsMsg").innerHTML = ""; $("#jsReport").innerHTML = "";
    $("#jsList").innerHTML = '<div class="panel empty"><span class="spin"></span> Searching job sites…</div>';
    try {
      const j = await api("/api/jobsearch", {serpKey: window.LF.settings().serpKey, ...q});
      results = j.results; renderReport(j.report); render();
      if (!results.length) $("#jsMsg").innerHTML = '<div class="msg">No results. Try a broader query or turn on more sources.</div>';
    } catch(err){ $("#jsMsg").innerHTML = `<div class="msg err">${esc(err.message)}</div>`; $("#jsList").innerHTML = ""; }
    b.disabled = false; b.textContent = "Search jobs";
  };
  api("/api/jobsearch/sources", {}).then(d => { data = d; fillFilters(); }).catch(() => fillFilters());
}
init();
})();
