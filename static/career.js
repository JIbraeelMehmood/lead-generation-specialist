/* LeadFinder: Career tab. Merges the portable Proficiently skills into LeadFinder -
   profile + preferences, fit scoring, resume tailoring, cover letters, and
   application tracking. Generation uses LeadFinder's free AI pool (Settings). */
(function(){
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const api = (p, b) => window.LF.api(p, b || {});
let profile = {resume:"", preferences:{}, workHistory:""}, jobs = [], active = null, tab = "resume";

const STATUS = [["saved","Saved"],["applied","Applied"],["interview","Interview"],["offer","Offer"],["rejected","Rejected"]];
const FIT_COLOR = {High:"t-no", Medium:"t-weak", Low:"t-yes", Skip:"t-yes"};

function mount(){
  const sec = document.createElement("section");
  sec.id = "tab-career"; sec.hidden = true;
  sec.innerHTML = `
  <div class="panel">
    <h2>Career profile</h2>
    <p class="sub" style="margin-top:-4px">Your resume, job preferences and work history. Preferences drive fit scoring; the resume and profile feed resume tailoring and cover letters. This data stays on your computer.</p>
    <div class="grid">
      <div style="grid-column:span 2"><label for="crResume">Your resume (paste full text)</label><textarea id="crResume" rows="8" placeholder="Paste your current resume here"></textarea></div>
      <div style="grid-column:span 2"><label for="crProfile">Work history profile (optional but better tailoring)</label><textarea id="crProfile" rows="6" placeholder="Notes on each role: company context, accomplishments with numbers, why you left. The richer this is, the better your tailored resumes."></textarea></div>
    </div>
    <div class="grid" style="margin-top:6px">
      <div style="grid-column:span 2"><label for="crRoles">Target roles (comma separated)</label><input id="crRoles" placeholder="e.g. PHP Laravel developer, backend engineer"></div>
      <div><label for="crLoc">Location</label><input id="crLoc" placeholder="Remote / Lahore"></div>
      <div><label for="crSalary">Salary minimum</label><input id="crSalary" placeholder="e.g. $40k"></div>
      <div><label for="crMust">Must-haves</label><input id="crMust" placeholder="e.g. Laravel, full-time"></div>
      <div><label for="crNice">Nice-to-haves</label><input id="crNice" placeholder="e.g. startup, remote"></div>
      <div><label for="crDeal">Dealbreakers (auto-Skip)</label><input id="crDeal" placeholder="e.g. agency, crypto, clearance"></div>
      <div><label for="crInt">Companies of interest</label><input id="crInt"></div>
      <div><label for="crAvoid">Companies to avoid</label><input id="crAvoid"></div>
    </div>
    <div class="toolbar" style="margin-top:10px"><span class="grow"></span><button class="btn sm primary" id="crSave">Save profile</button></div>
    <div id="crMsg"></div>
  </div>

  <div class="panel">
    <div class="toolbar"><h2 style="margin:0">Job applications</h2><span class="grow"></span><button class="btn sm" id="crRefresh">Refresh</button></div>
    <p class="sub">Saved from Job search. Tailor a resume and write a cover letter for each, then track status.</p>
    <div id="crJobs"></div>
  </div>

  <div id="crDetail" hidden></div>`;
  const wrap = document.querySelector(".wrap");
  const js = document.querySelector("#tab-jobsearch");
  wrap.insertBefore(sec, js ? js.nextSibling : wrap.querySelector("section"));
  const nav = document.querySelector("nav");
  const b = document.createElement("button");
  b.setAttribute("role","tab"); b.dataset.tab = "career"; b.textContent = "Career";
  const after = nav.querySelector('[data-tab="jobsearch"]') || nav.querySelector('[data-tab="hiring"]');
  nav.insertBefore(b, after ? after.nextSibling : nav.children[0]);
  window.LF.bindTab(b, () => { loadProfile(); loadJobs(); });
}

function readProfile(){
  const val = id => ( $("#"+id).value || "" ).trim();
  const list = id => { const v = val(id); return v ? v.split(",").map(s=>s.trim()).filter(Boolean) : []; };
  return {resume: val("crResume"), workHistory: val("crProfile"),
    preferences: {targetRoles: list("crRoles"), location: val("crLoc"), salary: val("crSalary"),
      mustHaves: list("crMust"), niceToHaves: list("crNice"), dealbreakers: list("crDeal"),
      companiesInterest: list("crInt"), companiesAvoid: list("crAvoid")}};
}

function fillProfile(p){
  $("#crResume").value = p.resume || "";
  $("#crProfile").value = p.workHistory || "";
  const pr = p.preferences || {};
  const join = v => Array.isArray(v) ? v.join(", ") : (v||"");
  $("#crRoles").value = join(pr.targetRoles); $("#crLoc").value = pr.location||"";
  $("#crSalary").value = pr.salary||""; $("#crMust").value = join(pr.mustHaves);
  $("#crNice").value = join(pr.niceToHaves); $("#crDeal").value = join(pr.dealbreakers);
  $("#crInt").value = join(pr.companiesInterest); $("#crAvoid").value = join(pr.companiesAvoid);
}

async function loadProfile(){
  try { const j = await api("/api/career/profile", {}); profile = j.profile; fillProfile(profile); }
  catch(e){ $("#crMsg").innerHTML = `<div class="msg err">${esc(e.message)}</div>`; }
}

function fitTag(f){ return f ? `<span class="tag ${FIT_COLOR[f]||"t-yes"}">${esc(f)}</span>` : ""; }

function renderJobs(){
  if (!jobs.length){ $("#crJobs").innerHTML = `<div class="empty">No saved applications yet. Use "Tailor resume" or "Save application" on the Job search tab.</div>`; return; }
  $("#crJobs").innerHTML = jobs.map(j => `
    <div class="panel" data-id="${esc(j.id)}" style="padding:12px 14px">
      <div class="toolbar" style="margin:0;align-items:baseline">
        <div class="grow"><div class="nm">${esc(j.title||"Untitled role")}</div>
          <div class="sub">${esc(j.company||"—")}${j.location?" · "+esc(j.location):""}${j.source?" · "+esc(j.source):""}</div></div>
        <span class="tag t-yes">${esc((STATUS.find(s=>s[0]===j.status)||["saved","Saved"])[1])}</span>
      </div>
      <div class="acts" style="margin-top:8px">
        <button class="btn sm primary" data-open="1">Open</button>
        <button class="btn sm" data-fit="1">Fit score</button>
        <button class="btn sm" data-tailor="1">Tailor resume</button>
        <button class="btn sm" data-cl="1">Cover letter</button>
        <select class="btn sm" data-status style="width:auto">
          ${STATUS.map(s=>`<option value="${s[0]}"${s[0]===j.status?" selected":""}>${s[1]}</option>`).join("")}
        </select>
        <button class="btn sm" data-del="1">Delete</button>
      </div>
    </div>`).join("");
}

async function loadJobs(){
  try { const j = await api("/api/career/jobs", {}); jobs = j.jobs; renderJobs(); }
  catch(e){ $("#crJobs").innerHTML = `<div class="msg err">${esc(e.message)}</div>`; }
}

function renderDetail(j){
  active = j;
  if (!["posting","resume","coverLetter"].includes(tab)) tab = "resume";
  const pane = (id, val) => `<div data-pane="${id}" ${id!==tab?'hidden':''}>
    <textarea data-field="${id}" rows="20" style="font-family:monospace;font-size:13px">${esc(val||"")}</textarea>
    <div class="toolbar"><span class="sub grow"></span><button class="btn sm" data-savetext="${id}">Save text</button>
      <button class="btn sm" data-copy="${id}">Copy</button> ${id!=="posting"?`<button class="btn sm" data-dl="${id}">Download</button>`:""}</div></div>`;
  $("#crDetail").hidden = false;
  $("#crDetail").innerHTML = `
  <div class="panel" data-id="${esc(j.id)}">
    <div class="toolbar"><h2 style="margin:0">${esc(j.title||"Job")} ${j.company?`<span class="sub">· ${esc(j.company)}</span>`:""}</h2>
      <span class="grow"></span>${j.url?`<a class="btn sm" href="${esc(j.url)}" target="_blank" rel="noopener">Open posting</a>`:""}
      <button class="btn sm" data-close="1">Close</button></div>
    <div class="acts" style="margin-bottom:10px">
      ${["posting","resume","coverLetter"].map(f=>`<button class="btn sm ${f===tab?"primary":""}" data-tab="${f}">${f==="coverLetter"?"Cover letter":f[0].toUpperCase()+f.slice(1)}</button>`).join("")}
      <button class="btn sm primary" data-tailor="1">Tailor resume</button>
      <button class="btn sm primary" data-cl="1">Write cover letter</button>
      <button class="btn sm" data-fit="1">Fit score</button>
    </div>
    ${["posting","resume","coverLetter"].map(f=>pane(f, j[f])).join("")}
    <div id="crDetailMsg"></div>
  </div>`;
  $("#crDetail").scrollIntoView({behavior:"smooth"});
}

function msg(html){ const m = $("#crDetailMsg"); if (m) m.innerHTML = html; else $("#crMsg").innerHTML = html; }
function spin(t){ msg(`<p class="sub"><span class="spin"></span> ${esc(t)}</p>`); }

async function setFit(id, card){
  spin("Scoring fit…");
  try { const r = await api("/api/career/fit", {job: active || jobs.find(x=>x.id===id) || {}});
    const j = jobs.find(x=>x.id===id); if (j) j.fit = r.fit;
    msg(`<div class="msg ${r.fit==="High"||r.fit==="Medium"?"ok":"err"}"><b>${esc(r.fit)}</b> — ${esc(r.reasons||"")}${r.dealbreakers&&r.dealbreakers.length?` · Dealbreakers: ${esc(r.dealbreakers.join(", "))}`:""}</div>`);
    renderJobs();
  } catch(e){ msg(`<div class="msg err">${esc(e.message)}</div>`); }
}

async function doTailor(id){
  spin("Tailoring resume… (this can take 20-60s)");
  try { const r = await api("/api/career/tailor", {jobId: id});
    const j = await api("/api/career/job", {id}); tab = "resume"; renderDetail(j.job); loadJobs();
    msg(`<div class="msg ok">Tailored resume saved. by ${esc(r.provider||"AI")} - review and edit before sending.</div>`);
  } catch(e){ msg(`<div class="msg err">${esc(e.message)}</div>`); }
}

async function doCover(id){
  spin("Writing cover letter…");
  try { const r = await api("/api/career/cover-letter", {jobId: id});
    const j = await api("/api/career/job", {id}); tab = "coverLetter"; renderDetail(j.job); loadJobs();
    msg(`<div class="msg ok">Cover letter saved. by ${esc(r.provider||"AI")} - review and edit before sending.</div>`);
  } catch(e){ msg(`<div class="msg err">${esc(e.message)}</div>`); }
}

function dl(field, j){
  const name = (j.company||j.title||"document").replace(/[^a-z0-9]+/gi,"-") + "-" + field + ".md";
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([j[field]||""], {type:"text/markdown"})); a.download = name; a.click();
}

async function onClick(e){
  const t = e.target.closest("button,[data-status]");
  if (!t) return;
  const card = t.closest("[data-id]"); const id = card?.dataset.id;
  if (!id) return;
  if (t.dataset.open){ try { const j = await api("/api/career/job",{id}); tab="resume"; renderDetail(j.job); } catch(err){ msg(`<div class="msg err">${esc(err.message)}</div>`); } return; }
  if (t.dataset.close){ $("#crDetail").hidden = true; return; }
  if (t.dataset.tab){ tab = t.dataset.tab; if (active) renderDetail(active); return; }
  if (t.dataset.savetext){ const f=t.dataset.savetext; const txt=$(`[data-pane="${f}"] textarea`).value;
    try { await api("/api/career/job/text",{id, field:f, text:txt}); if (active) active[f]=txt; msg(`<div class="msg ok">${esc(f)} saved.</div>`); loadJobs(); }
    catch(err){ msg(`<div class="msg err">${esc(err.message)}</div>`); } return; }
  if (t.dataset.copy){ const f=t.dataset.copy; navigator.clipboard.writeText(active?.[f]||""); t.textContent="Copied"; setTimeout(()=>t.textContent="Copy",1200); return; }
  if (t.dataset.dl){ dl(t.dataset.dl, active||{}); return; }
  if (t.dataset.del){ if(confirm("Delete this application?")){ await api("/api/career/delete",{id}); $("#crDetail").hidden=true; active=null; loadJobs(); } return; }
  if (t.dataset.status){ await api("/api/career/job/status",{id, status:t.value}); loadJobs(); return; }
  if (t.dataset.fit){ setFit(id, card); return; }
  if (t.dataset.tailor){ doTailor(id); return; }
  if (t.dataset.cl){ doCover(id); return; }
}

function init(){
  mount();
  $("#crSave").onclick = async () => {
    try { const j = await api("/api/career/profile", {save: readProfile()}); profile=j.profile; fillProfile(profile);
      $("#crMsg").innerHTML = '<div class="msg ok">Profile saved.</div>'; }
    catch(e){ $("#crMsg").innerHTML = `<div class="msg err">${esc(e.message)}</div>`; }
  };
  $("#crRefresh").onclick = loadJobs;
  $("#crJobs").addEventListener("click", onClick);
  $("#crDetail").addEventListener("click", onClick);
  loadProfile();
}
init();
})();
