/* LeadFinder: Hiring posts tab. People already looking for a developer, from sources that allow
   automated reading. Every post links back to its source. You read and reply yourself. */
(function(){
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const api = (p, b) => window.LF.api(p, b || {});
let status = "new", data = null;

const STATUS = [["new","New"],["saved","Saved"],["applied","Applied"],["dismissed","Dismissed"]];

function mount(){
  const sec = document.createElement("section");
  sec.id = "tab-hiring"; sec.hidden = true;
  sec.innerHTML = `
  <div class="panel">
    <h2>Hiring posts</h2>
    <p class="sub" style="margin-top:-4px">People who are already looking for a developer. Checked once a day with Autopilot, or when you press Check now (each source at most every 3 hours). Open the post and reply yourself.</p>
    <div class="grid">
      <div style="grid-column:span 2"><label for="hiKeywords">Match these skills (comma separated)</label><input id="hiKeywords"></div>
      <div><label for="hiExclude">Hide posts that mention</label><input id="hiExclude"></div>
    </div>
    <div class="toolbar" style="margin-top:10px">
      <span class="sub">Sources:</span>
      <span class="seg"><label><input type="checkbox" data-src="hn"> Hacker News</label><label><input type="checkbox" data-src="remotive"> Remotive</label><label><input type="checkbox" data-src="wwr"> We Work Remotely</label></span>
      <span class="sub" style="margin-left:8px">WWR feeds:</span>
      <span id="hiFeeds" class="seg"></span>
    </div>
    <div class="toolbar">
      <span class="seg"><label><input type="checkbox" id="hiOnlyFree"> Only freelance / contract</label><label><input type="checkbox" id="hiAuto"> Check daily with Autopilot</label></span>
      <span class="grow"></span>
      <button class="btn sm" id="hiSave">Save filters</button>
      <button class="btn sm primary" id="hiRefresh">Check now</button>
    </div>
    <div id="hiMsg"></div>
  </div>
  <div class="toolbar" id="hiTabs" role="tablist"></div>
  <div id="hiList"></div>`;
  const wrap = document.querySelector(".wrap");
  const today = document.querySelector("#tab-today");
  wrap.insertBefore(sec, today ? today.nextSibling : wrap.querySelector("section"));
  const nav = document.querySelector("nav");
  const b = document.createElement("button");
  b.setAttribute("role","tab"); b.dataset.tab = "hiring"; b.innerHTML = `Hiring posts <span id="hiCount"></span>`;
  const after = nav.querySelector('[data-tab="today"]');
  nav.insertBefore(b, after ? after.nextSibling : nav.children[0]);
  window.LF.bindTab(b, load);
}

function fillSettings(st){
  $("#hiKeywords").value = st.keywords || "";
  $("#hiExclude").value = st.exclude || "";
  document.querySelectorAll("#tab-hiring [data-src]").forEach(x => x.checked = !!st.sources[x.dataset.src]);
  $("#hiFeeds").innerHTML = data.wwrFeeds.map(f => `<label><input type="checkbox" data-feed="${esc(f)}"${st.wwrFeeds.includes(f) ? " checked" : ""}> ${esc(f)}</label>`).join("");
  $("#hiOnlyFree").checked = !!st.onlyFreelance;
  $("#hiAuto").checked = st.auto !== false;
}
function readSettings(){
  const sources = {};
  document.querySelectorAll("#tab-hiring [data-src]").forEach(x => sources[x.dataset.src] = x.checked);
  return {keywords: $("#hiKeywords").value, exclude: $("#hiExclude").value, sources,
          wwrFeeds: [...document.querySelectorAll("#hiFeeds [data-feed]")].filter(x => x.checked).map(x => x.dataset.feed),
          onlyFreelance: $("#hiOnlyFree").checked, auto: $("#hiAuto").checked};
}

function badge(){
  const n = data ? data.counts.new : 0;
  $("#hiCount").textContent = n ? `(${n})` : "";
}

function render(){
  $("#hiTabs").innerHTML = STATUS.map(([k, label]) =>
    `<button class="btn sm${k === status ? " primary" : ""}" data-st="${k}" role="tab" aria-selected="${k === status}">${label} (${data.counts[k] || 0})</button>`).join("")
    + `<span class="sub grow" style="text-align:right">Last checked: ${Object.entries(data.lastFetch).map(([k,v]) => `${esc(data.sources[k]?.name || k)} ${esc(v)}`).join(", ") || "never"}</span>`;
  const posts = data.posts;
  if (!posts.length){
    $("#hiList").innerHTML = `<div class="panel empty">${status === "new"
      ? "No matching posts yet. Press Check now, or add more skills to the filter."
      : "Nothing here yet."}</div>`;
    return;
  }
  $("#hiList").innerHTML = posts.map(p => `
    <div class="panel" data-id="${esc(p.id)}" style="padding:14px">
      <div class="toolbar" style="margin:0 0 4px;align-items:baseline">
        <span class="score" title="Match score">${p.score}</span>
        <div class="grow">
          <div class="nm">${esc(p.title)}</div>
          <div class="sub">${esc(p.company)}${p.location ? " · " + esc(p.location) : ""}${p.salary ? " · " + esc(p.salary) : ""} · posted ${esc(p.postedAt || p.foundAt)}</div>
        </div>
        ${p.freelance ? '<span class="tag t-no">Freelance / contract</span>' : p.jobType ? `<span class="tag t-yes">${esc(p.jobType)}</span>` : ""}
      </div>
      <div style="margin:4px 0">${p.matched.map(m => `<span class="tag t-weak" style="margin-right:4px">${esc(m)}</span>`).join("")}</div>
      <div class="sub" style="white-space:pre-wrap;max-height:7.5em;overflow:hidden">${esc(p.snippet)}</div>
      <div class="acts" style="margin-top:8px">
        <a class="btn sm primary" href="${esc(p.url)}" target="_blank" rel="noopener">Open on ${esc(p.sourceName)}</a>
        ${p.email ? `<a class="btn sm" href="mailto:${esc(p.email)}">Email ${esc(p.email)}</a>` : ""}
        <button class="btn sm" data-ai="1">Write reply with AI</button>
        <button class="btn sm" data-add="1">Add to My list</button>
        ${status !== "saved" ? '<button class="btn sm" data-set="saved">Save</button>' : ""}
        ${status !== "applied" ? '<button class="btn sm" data-set="applied">Mark replied</button>' : ""}
        ${status !== "dismissed" ? '<button class="btn sm" data-set="dismissed">Dismiss</button>' : '<button class="btn sm" data-set="new">Restore</button>'}
      </div>
      <div data-out></div>
      <div class="note">Source: <a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.sourceName)}</a>${p.thread ? " · " + esc(p.thread) : ""}</div>
    </div>`).join("");
}

async function load(){
  try {
    data = await api("/api/hiring/list", {status});
    fillSettings(data.settings); render(); badge();
  } catch(e){ $("#hiMsg").innerHTML = `<div class="msg err">${esc(e.message)}</div>`; }
}

function replyPrompt(p){
  const S = window.LF.settings();
  let brand = {};
  try { brand = JSON.parse(localStorage.getItem("lf-brand") || "{}"); } catch(e){}
  return `I am ${S.myName || "a developer"}${S.myBusiness ? " from " + S.myBusiness : ""}. ${brand.service ? "Service: " + brand.service + "." : ""} ${brand.proof ? "Experience: " + brand.proof + "." : ""}
Skills that match this post: ${p.matched.join(", ")}.

Here is a job post from ${p.sourceName}:
"""
${p.title}
${p.company ? "Company: " + p.company : ""}
${p.text}
"""

Write a short, specific reply I can send to this person (under 130 words). Open with one line showing I understood their exact need. Then 2-3 lines on how I would approach it, using only the skills listed above. Suggest a quick call or ask one useful question. No generic claims, no invented numbers, no placeholders except [portfolio link]. Also give a one-line subject for an email.`;
}

async function onClick(e){
  const t = e.target.closest("button[data-st],button[data-set],button[data-ai],button[data-add]");
  if (!t) return;
  if (t.dataset.st){ status = t.dataset.st; load(); return; }
  const card = t.closest("[data-id]"); const id = card.dataset.id;
  const p = data.posts.find(x => x.id === id);
  if (t.dataset.set){
    await api("/api/hiring/update", {id, status: t.dataset.set});
    if (t.dataset.set === "applied" && window.LF.log) window.LF.log("emails", 1);
    load(); return;
  }
  if (t.dataset.add){
    const lead = {id: "job:" + id, source: "Hiring post (" + p.sourceName + ")", name: p.company || p.title,
      category: p.title, address: p.location || "Remote", phone: "", email: p.email || "", website: "",
      social: "", rating: null, reviews: 0, mapsUrl: p.url, searchQuery: p.matched.join(", ")};
    window.LF.addLeads([lead]);
    window.LF.updateLead(lead.id, {notes: `${p.sourceName}: ${p.url}`});
    t.textContent = "Added"; t.disabled = true; return;
  }
  if (t.dataset.ai){
    const out = card.querySelector("[data-out]");
    out.innerHTML = '<p class="sub"><span class="spin"></span> Writing…</p>';
    try {
      const full = (await api("/api/hiring/post", {id})).post;
      const r = await api("/api/ai", {ai: {provider: "pool"}, prompt: replyPrompt({...p, text: full.text})});
      out.innerHTML = `<div style="white-space:pre-wrap;background:var(--bg);border-radius:8px;padding:12px;margin-top:10px;font-size:14px">${esc(r.text)}</div>
        <div class="toolbar"><span class="sub grow">by ${esc(r.provider || "AI")}. Read and edit before you send.</span><button class="btn sm" data-copy="1">Copy</button></div>`;
      out.querySelector("[data-copy]").onclick = ev => navigator.clipboard.writeText(r.text).then(() => ev.target.textContent = "Copied");
    } catch(err){ out.innerHTML = `<div class="msg err">${esc(err.message)}</div>`; }
  }
}

function init(){
  mount();
  $("#hiList").addEventListener("click", onClick);
  $("#hiTabs").addEventListener("click", onClick);
  $("#hiSave").onclick = async () => {
    try {
      data = await api("/api/hiring/settings", {settings: readSettings(), status});
      render(); badge();
      $("#hiMsg").innerHTML = '<div class="msg ok">Filters saved.</div>';
    } catch(e){ $("#hiMsg").innerHTML = `<div class="msg err">${esc(e.message)}</div>`; }
  };
  $("#hiRefresh").onclick = async e => {
    const b = e.target; b.disabled = true; b.innerHTML = '<span class="spin"></span> Checking…';
    try {
      await api("/api/hiring/settings", {settings: readSettings(), status});
      const {report} = await api("/api/hiring/refresh", {});
      const names = {hn: "Hacker News", remotive: "Remotive", wwr: "We Work Remotely"};
      const lines = Object.entries(report).map(([k, r]) => `${names[k] || k}: ${
        r.error ? "failed (" + esc(r.error) + ")" : r.skipped ? esc(r.note) : `${r.new} new of ${r.fetched}`}`);
      const bad = Object.values(report).some(r => r.error);
      $("#hiMsg").innerHTML = `<div class="msg ${bad ? "err" : "ok"}">${lines.join("<br>") || "No sources are turned on."}</div>`;
      status = "new"; await load();
    } catch(err){ $("#hiMsg").innerHTML = `<div class="msg err">${esc(err.message)}</div>`; }
    b.disabled = false; b.textContent = "Check now";
  };
  api("/api/hiring/list", {status: "new"}).then(d => { data = d; badge(); }).catch(() => {});
}
init();
})();
