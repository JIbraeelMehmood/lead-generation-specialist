/* LeadFinder: daily assistant (Today tab, autopilot, call mode, AI pool + quota settings, contact enrichment) */
(function(){
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const today = () => new Date().toISOString().slice(0,10);
const addDays = n => { const d = new Date(); d.setDate(d.getDate()+n); return d.toISOString().slice(0,10); };
function store(k, d, v){
  try { if (v !== undefined){ localStorage.setItem(k, JSON.stringify(v)); return v; }
        const x = localStorage.getItem(k); return x ? JSON.parse(x) : d; } catch(e){ return d; }
}
const api = (p, b) => window.LF.api(p, b || {});
let server = {config: null, providers: {}}, inbox = [], goals = store("lf-goals", {calls: 20, emails: 15, newLeads: 20});

/* activity log for goals */
function logAct(kind, n = 1){
  const L = store("lf-log", {}); const d = today();
  L[d] = L[d] || {}; L[d][kind] = (L[d][kind] || 0) + n;
  store("lf-log", null, L);
  if (!$("#tab-today").hidden) renderStats();
}
const act = (kind, d = today()) => ((store("lf-log", {})[d] || {})[kind] || 0);
function streak(){
  const L = store("lf-log", {}); let s = 0;
  for (let i = 0; i < 365; i++){ const d = new Date(); d.setDate(d.getDate() - i); const k = d.toISOString().slice(0,10);
    const x = L[k] || {}; if ((x.calls||0) + (x.emails||0) > 0) s++; else if (i > 0) break; }
  return s;
}

/* ------------------------------------------------------------------ Today tab */
function mountToday(){
  const sec = document.createElement("section");
  sec.id = "tab-today";
  sec.innerHTML = `
  <div class="panel">
    <div class="toolbar" style="margin:0">
      <div class="grow"><h2 style="margin:0" id="tdHello"></h2><div class="sub" id="tdSub"></div></div>
      <button class="btn primary" id="tdCall">Start call session</button>
      <button class="btn" id="tdPlan">Plan my day with AI</button>
    </div>
    <div class="tally" id="tdStats" style="margin:14px 0 0"></div>
    <div id="tdPlanOut"></div>
  </div>

  <div class="panel">
    <div class="toolbar" style="margin-top:0">
      <h3 class="grow" style="margin:0">New leads inbox <span class="sub" id="tdInboxN"></span></h3>
      <button class="btn sm" id="tdEnrichInbox">Find emails</button>
      <button class="btn sm primary" id="tdAcceptAll">Add all to My list</button>
      <button class="btn sm" id="tdDismissAll">Dismiss all</button>
    </div>
    <p class="sub" style="margin-top:0">Autopilot runs your saved searches every day and puts only businesses you haven't seen before here.</p>
    <div class="tablewrap"><table style="min-width:760px">
      <thead><tr><th>Business</th><th>Found by</th><th>Reviews</th><th>Contact</th><th>Website</th><th></th></tr></thead>
      <tbody id="tdInbox"></tbody></table></div>
  </div>

  <div class="panel">
    <h3 style="margin-top:0">Follow-ups due</h3>
    <div id="tdDue"></div>
  </div>

  <div class="panel">
    <div class="toolbar" style="margin-top:0">
      <h3 class="grow" style="margin:0">Autopilot (daily lead search)</h3>
      <label style="display:flex;gap:6px;align-items:center;margin:0;color:var(--ink)"><input type="checkbox" id="apOn" style="width:auto"> On</label>
      <label style="margin:0">Run after</label>
      <select id="apHour" style="width:auto">${Array.from({length:24},(_,h)=>`<option value="${h}">${String(h).padStart(2,"0")}:00</option>`).join("")}</select>
      <button class="btn sm primary" id="apRun">Run now</button>
    </div>
    <p class="sub" style="margin-top:0">Runs once a day while LeadFinder is open (or as soon as you start it after that time). Each saved search uses 1 map search per page.</p>
    <form id="apForm" class="grid">
      <div><label>Business type</label><input name="niche" placeholder="roofing contractor" required></div>
      <div><label>City</label><input name="city" placeholder="Tulsa, Oklahoma, USA" required></div>
      <div><label>Source</label><select name="source"><option value="google">Google Maps</option><option value="serpapi">SerpApi</option><option value="osm">OpenStreetMap</option></select></div>
      <div><label>Keep</label><select name="filter"><option value="no">No website</option><option value="weak">No website + weak website</option><option value="all">All</option></select></div>
      <div><label>Min reviews</label><input name="minReviews" type="number" min="0" value="5"></div>
      <div><label>Pages (20 each)</label><select name="pages"><option>1</option><option>2</option><option>3</option></select></div>
      <div><button class="btn primary" style="width:100%">Save search</button></div>
    </form>
    <div class="tablewrap" style="margin-top:10px"><table style="min-width:640px">
      <thead><tr><th>On</th><th>Search</th><th>Source</th><th>Keep</th><th>Min reviews</th><th>Pages</th><th></th></tr></thead>
      <tbody id="apJobs"></tbody></table></div>
    <div class="sub" id="apStatus" style="margin-top:8px"></div>
    <details style="margin-top:6px"><summary class="sub">Activity log</summary><pre id="apLog" class="sub" style="white-space:pre-wrap"></pre></details>
  </div>

  <div class="panel">
    <h3 style="margin-top:0">Daily goals</h3>
    <div class="grid">
      <div><label>Calls per day</label><input type="number" id="gCalls" min="0"></div>
      <div><label>Emails per day</label><input type="number" id="gEmails" min="0"></div>
      <div><label>New leads per day</label><input type="number" id="gLeads" min="0"></div>
      <div><button class="btn" id="gSave" style="width:100%">Save goals</button></div>
    </div>
  </div>`;
  const wrap = document.querySelector(".wrap");
  wrap.insertBefore(sec, wrap.querySelector("section"));
  const nav = document.querySelector("nav");
  const b = document.createElement("button");
  b.setAttribute("role","tab"); b.dataset.tab = "today"; b.textContent = "Today";
  nav.insertBefore(b, nav.children[0]);
  window.LF.bindTab(b, () => { refreshInbox(); renderStats(); renderDue(); });
}

function bar(done, goal){
  const pct = goal ? Math.min(100, Math.round(100 * done / goal)) : 0;
  return `<div style="height:6px;border-radius:3px;background:var(--chip);margin-top:4px"><div style="height:6px;border-radius:3px;background:var(--go);width:${pct}%"></div></div>`;
}
function dueList(){
  return window.LF.getList().filter(l => l.followUp && l.followUp <= today() && !["Won","Not interested"].includes(l.stage));
}
function renderStats(){
  const h = new Date().getHours();
  const S = window.LF.settings();
  $("#tdHello").textContent = `${h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"}${S.myName ? ", " + S.myName.split(" ")[0] : ""}`;
  $("#tdSub").textContent = new Date().toLocaleDateString(undefined, {weekday:"long", month:"long", day:"numeric"}) + (streak() ? ` · ${streak()}-day outreach streak` : "");
  const drafts = store("lf-outbox", []).filter(o => o.status === "draft").length;
  const approved = store("lf-outbox", []).filter(o => o.status === "approved").length;
  const list = window.LF.getList();
  const newWithPhone = list.filter(l => l.stage === "New" && l.phone).length;
  $("#tdStats").innerHTML = `
    <div><b>${inbox.length}</b><span>new leads in inbox</span></div>
    <div><b>${dueList().length}</b><span>follow-ups due</span></div>
    <div><b>${newWithPhone}</b><span>ready to call</span></div>
    <div><b>${drafts}</b><span>email drafts to review</span>${approved ? `<div class="sub">${approved} approved to send</div>` : ""}</div>
    <div style="min-width:150px"><b>${act("calls")}/${goals.calls}</b><span>calls today</span>${bar(act("calls"), goals.calls)}</div>
    <div style="min-width:150px"><b>${act("emails")}/${goals.emails}</b><span>emails today</span>${bar(act("emails"), goals.emails)}</div>
    <div style="min-width:150px"><b>${act("newLeads")}/${goals.newLeads}</b><span>leads added today</span>${bar(act("newLeads"), goals.newLeads)}</div>`;
}
function renderDue(){
  const due = dueList();
  $("#tdDue").innerHTML = due.length ? `<div class="tablewrap"><table style="min-width:600px"><thead><tr><th>Business</th><th>Stage</th><th>Due</th><th>Last note</th><th></th></tr></thead><tbody>
    ${due.map(l => `<tr><td class="nm">${esc(l.name)}<div class="sub">${esc(l.phone||"")}</div></td><td>${esc(l.stage)}</td><td>${esc(l.followUp)}</td>
      <td class="sub">${esc((l.notes||"").split("\n").pop())}</td>
      <td><button class="btn sm primary" data-callone="${esc(l.id)}">Call</button></td></tr>`).join("")}
    </tbody></table></div>` : '<p class="sub">Nothing due. Nice work.</p>';
}
function contactMini(l){
  return `${l.phone ? `<a href="tel:${esc(l.phone.replace(/\s/g,""))}">${esc(l.phone)}</a>` : '<span class="sub">no phone</span>'}
    ${l.email ? `<div class="sub">${esc(l.email)}</div>` : ""}${l.contactPage ? `<div><a class="sub" target="_blank" rel="noopener" href="${esc(l.contactPage)}">contact form</a></div>` : ""}`;
}
async function refreshInbox(){
  try {
    const fresh = (await api("/api/assistant/inbox")).inbox;
    const old = new Map(inbox.map(l => [l.id, l]));
    inbox = fresh.map(l => old.has(l.id) ? Object.assign(l, old.get(l.id)) : l);  // keep contacts found in this session
  } catch(e){ inbox = []; }
  renderInbox();
}
function renderInbox(){
  $("#tdInboxN").textContent = inbox.length ? `(${inbox.length})` : "";
  $("#tdInbox").innerHTML = inbox.length ? inbox.map(l => `<tr data-iid="${esc(l.id)}">
    <td><div class="nm">${esc(l.name)}</div><div class="sub">${esc(l.address)}</div></td>
    <td class="sub">${esc(l.job)}<br>${esc(l.foundAt)}</td>
    <td>${l.rating ? l.rating + "★ " : ""}<span class="sub">${l.reviews || 0}</span></td>
    <td>${contactMini(l)}</td>
    <td>${l.website ? `<a class="sub" target="_blank" rel="noopener" href="${esc(l.website)}">${esc(l.website.replace(/^https?:\/\/(www\.)?/,"").slice(0,30))}</a>${l.audit ? `<div class="sub">${l.audit.issues.length} issues</div>` : ""}` : '<span class="tag t-no">No website</span>'}</td>
    <td><div class="acts"><button class="btn sm primary" data-in="accept">Add</button><button class="btn sm" data-in="analyze">Analyze</button><button class="btn sm" data-in="dismiss">Dismiss</button></div></td>
  </tr>`).join("") : '<tr><td colspan="6" class="empty">Inbox empty. Save a search in Autopilot below and press Run now.</td></tr>';
  renderStats();
}
async function resolveInbox(ids, accept){
  const leads = inbox.filter(l => ids.includes(l.id));
  if (accept) window.LF.addLeads(leads);
  await api("/api/assistant/resolve", {ids});
  refreshInbox();
}

/* autopilot config */
function jobsTable(){
  const jobs = server.config.jobs;
  $("#apJobs").innerHTML = jobs.length ? jobs.map(j => `<tr data-jid="${esc(j.id)}">
    <td><input type="checkbox" data-jon ${j.enabled !== false ? "checked" : ""} style="width:auto" aria-label="Enabled"></td>
    <td class="nm">${esc(j.niche)} <span class="sub">in ${esc(j.city)}</span></td><td>${esc(j.source)}</td>
    <td>${{no:"No website",weak:"No/weak website",all:"All"}[j.filter]}</td><td>${j.minReviews||0}</td><td>${j.pages||1}</td>
    <td><div class="acts"><button class="btn sm" data-jrun>Run</button><button class="btn sm" data-jdel>Delete</button></div></td></tr>`).join("")
    : '<tr><td colspan="7" class="empty">No saved searches yet.</td></tr>';
  $("#apOn").checked = !!server.config.autopilot;
  $("#apHour").value = server.config.runHour;
}
async function saveConfig(patch){
  const r = await api("/api/assistant/config", {save: patch});
  server.config = r.config; server.providers = r.providers;
  return r;
}
let pollT = null;
async function pollStatus(){
  try {
    const s = await api("/api/assistant/status");
    $("#apStatus").textContent = s.running ? `Running… ${s.progress}` : `Last run: ${s.lastRun || "never"} · Map searches this month: Google ${s.usage.google||0}/${s.caps.google||"∞"}, SerpApi ${s.usage.serpapi||0}/${s.caps.serpapi||"∞"}`;
    $("#apLog").textContent = s.log.join("\n");
    $("#apRun").disabled = s.running;
    if (s.inboxCount !== inbox.length) refreshInbox();
    renderQuota(s);
    renderPoolStatus(s.ai);
    clearTimeout(pollT); pollT = setTimeout(pollStatus, s.running ? 3000 : 30000);
  } catch(e){ clearTimeout(pollT); pollT = setTimeout(pollStatus, 30000); }
}

/* ------------------------------------------------------------------ Call mode */
let callQ = [], callI = 0, dlg;
function callQueue(){
  const list = window.LF.getList();
  const PR = {Hot:3, Warm:2, Low:1};
  const due = dueList().filter(l => l.phone);
  const fresh = list.filter(l => l.stage === "New" && l.phone && !due.includes(l))
    .sort((a,b) => (PR[b.priority]||0) - (PR[a.priority]||0) || (b.reviews||0) - (a.reviews||0));
  return [...due, ...fresh];
}
function openCall(queue){
  callQ = queue; callI = 0;
  if (!callQ.length){ alert("No leads with phone numbers to call. Add leads to My list first."); return; }
  if (!dlg){
    dlg = document.createElement("dialog"); dlg.id = "callDlg";
    dlg.style.cssText = "border:1px solid var(--line);border-radius:14px;padding:0;max-width:760px;width:calc(100% - 24px);background:var(--panel);color:var(--ink)";
    document.body.appendChild(dlg);
  }
  dlg.showModal(); renderCall();
}
function defaultScript(l){
  const S = window.LF.settings();
  const city = window.LFOutreach ? window.LFOutreach.cityOf(l.address) : "";
  let gap = !l.website ? "I noticed you don't have a website" : "I had a look at your website and saw a few quick wins";
  if (l.analysis && window.LFReport){
    const ins = window.LFReport.insights(l, l.analysis);
    if (ins.top && !ins.mine.website) gap = `I noticed you don't have a website, while ${ins.top.name} nearby does`;
  }
  if (l.identity && window.LFOutreach){
    const extra = window.LFOutreach.missingPhrases(l.identity, 3).filter(x => x !== "no website");
    if (extra.length) gap += `, and there's also ${extra.slice(0,2).join(" and ")}`;
  }
  const hello = l.ownerName ? `Hi, is that ${l.contactName || l.ownerName}?` : `Hi, is this the owner of ${l.name}?`;
  return `${hello} My name is ${S.myName || "[your name]"}${S.myBusiness ? " from " + S.myBusiness : ""}, I'll be quick.

I was searching for ${(l.searchQuery || l.category || "businesses").toLowerCase()} in ${city || "your area"} and your ${l.reviews ? l.reviews + " reviews" : "listing"} stood out. ${gap}.

Quick question: how do most new customers find you right now?

[Listen] I build simple websites for local businesses that help people who search online call you instead of a competitor. I've made a free sample homepage for you. Can I send it to you on WhatsApp or email?

If "no time": Totally understand. It's a 2-minute look, can I just text you the link?
If "too expensive": The sample is free, and packages start small. Worth seeing first?
If "enough customers": Great to hear! A site mostly helps you pick better-paying jobs. Can I send it anyway?`;
}
function renderCall(){
  const l = callQ[callI];
  if (!l){ dlg.innerHTML = `<div style="padding:22px"><h2>Session done</h2><p>${act("calls")} calls today. Great work!</p><button class="btn primary" onclick="this.closest('dialog').close()">Close</button></div>`; renderStats(); return; }
  const tel = (l.phone||"").replace(/\s/g,"");
  const d = String(l.phone||"").replace(/\D/g,"");
  const ins = l.analysis && window.LFReport ? window.LFReport.insights(l, l.analysis) : null;
  dlg.innerHTML = `<div style="padding:18px 20px 20px">
    <div class="toolbar" style="margin:0"><span class="sub grow">Call ${callI+1} of ${callQ.length}${l.followUp && l.followUp <= today() ? " · follow-up due" : ""}</span>
      <button class="btn sm" data-c="close">Close</button></div>
    <h2 style="margin:4px 0 0">${esc(l.name)} ${l.priority ? `<span class="tag ${l.priority==="Hot"?"t-no":"t-weak"}">${esc(l.priority)}</span>` : ""}</h2>
    <div class="sub">${esc(l.category||"")} · ${esc(l.address||"")} · ${l.rating ? l.rating + "★ " : ""}${l.reviews||0} reviews · ${l.website ? "has website" : "no website"}</div>
    <div class="toolbar"><a class="btn primary" href="tel:${esc(tel)}" style="font-size:18px">📞 ${esc(l.phone)}</a>
      <a class="btn" target="_blank" rel="noopener" href="https://wa.me/${d}">WhatsApp</a>
      <a class="btn sm" target="_blank" rel="noopener" href="https://www.google.com/search?q=${encodeURIComponent(l.name + " " + (l.address||""))}">Google</a>
      ${l.mapsUrl ? `<a class="btn sm" target="_blank" rel="noopener" href="${esc(l.mapsUrl)}">Map</a>` : ""}</div>
    ${ins && ins.gaps.length ? `<div class="sub"><b>Talking points:</b> ${esc(ins.gaps.slice(0,2).map(g => g.text).join(" "))}</div>` : ""}
    ${l.notes ? `<div class="sub" style="margin-top:4px"><b>Notes:</b> ${esc(l.notes).replace(/\n/g,"<br>")}</div>` : ""}
    <label style="margin-top:10px">Script ${l.aiNotes && l.aiNotes.call ? "(AI)" : ""}</label>
    <textarea id="cScript" rows="11" style="font-size:14px">${esc((l.aiNotes && l.aiNotes.call) || defaultScript(l))}</textarea>
    <div class="toolbar"><button class="btn sm" data-c="ai">Write script with AI</button><span class="sub" id="cMsg"></span></div>
    <label>Call notes</label><textarea id="cNote" rows="2" placeholder="Owner name, what they said, best time…"></textarea>
    <label style="margin-top:8px">Outcome</label>
    <div class="acts" style="gap:6px">
      <button class="btn" data-o="noanswer">No answer (retry in 2 days)</button>
      <button class="btn" data-o="callback">Call back…</button>
      <button class="btn primary" data-o="interested">Interested (send sample)</button>
      <button class="btn" data-o="proposal">Wants a quote</button>
      <button class="btn" data-o="won">Won 🎉</button>
      <button class="btn" data-o="no">Not interested</button>
      <button class="btn" data-o="bad">Wrong number</button>
      <button class="btn sm" data-o="skip">Skip</button>
    </div>
    <div class="toolbar"><label style="margin:0">Call back on</label><input type="date" id="cDate" value="${addDays(1)}" style="width:auto"></div>
  </div>`;
  dlg.onclick = async e => {
    if (e.target === dlg) return;
    const c = e.target.dataset.c, o = e.target.dataset.o;
    if (c === "close"){ dlg.close(); renderStats(); renderDue(); return; }
    if (c === "ai"){
      $("#cMsg").innerHTML = '<span class="spin"></span> Writing…';
      try {
        const S = window.LF.settings();
        const r = await api("/api/ai", {ai: S.ai || {provider:"pool"}, prompt:
          `Write a friendly cold-call script (under 170 words) for ${S.myName || "[your name]"}, a web designer, calling ${l.name} (${l.category}) at ${l.address}. Facts: ${l.reviews||0} reviews, rating ${l.rating||"n/a"}, website: ${l.website||"none"}. ${ins ? "Gaps: " + ins.gaps.map(g=>g.text).join(" ") : ""} Include an opener, one question, a free sample website offer, and 3 short objection answers. Only use these facts.`});
        l.aiNotes = {...(l.aiNotes||{}), call: r.text}; window.LF.updateLead(l.id, {aiNotes: l.aiNotes});
        $("#cScript").value = r.text; $("#cMsg").textContent = r.provider ? "by " + r.provider : "";
      } catch(err){ $("#cMsg").textContent = err.message; }
      return;
    }
    if (!o) return;
    const note = $("#cNote").value.trim();
    const stamp = `${today()} call: `;
    const map = {
      noanswer: {stage: l.stage === "New" ? "No answer" : l.stage, followUp: addDays(2), text: "no answer"},
      callback: {stage: "Follow up", followUp: $("#cDate").value || addDays(1), text: "asked to call back " + ($("#cDate").value||"")},
      interested: {stage: "Interested", followUp: addDays(2), text: "interested, send sample"},
      proposal: {stage: "Proposal sent", followUp: addDays(3), text: "wants a quote"},
      won: {stage: "Won", followUp: "", text: "WON"},
      no: {stage: "Not interested", followUp: "", text: "not interested"},
      bad: {stage: "Not interested", followUp: "", text: "wrong number"},
    };
    if (o !== "skip"){
      const m = map[o];
      window.LF.updateLead(l.id, {stage: m.stage, followUp: m.followUp,
        notes: `${l.notes ? l.notes + "\n" : ""}${stamp}${m.text}${note ? " – " + note : ""}`});
      logAct("calls");
    }
    callI++; renderCall();
  };
}

/* ------------------------------------------------------------------ Settings: AI pool, quota, keys */
const ORDER = ["gemini","groq","openrouter","mistral","github","nvidia","cerebras","ollama","anthropic","custom"];
function mountSettings(){
  const panel = document.createElement("div");
  panel.className = "panel guide"; panel.style.maxWidth = "none";
  panel.innerHTML = `
    <h2>Free AI pool</h2>
    <p class="sub" style="margin-top:-4px">Add free keys from several providers. LeadFinder uses them top to bottom and automatically moves to the next one when a provider hits its per-minute or daily limit, so you don't pay and don't get stuck. Free limits change often; check each provider's page.</p>
    <div class="tablewrap"><table style="min-width:900px">
      <thead><tr><th>Use</th><th>Provider</th><th>API key</th><th>Model</th><th>Today</th><th></th></tr></thead>
      <tbody id="poolRows"></tbody></table></div>
    <p class="note">Tip: Gemini + Groq + OpenRouter together cover most daily use for free. Free tiers may use your prompts to improve their models; don't paste private customer data. Anthropic's Claude API is paid (prepaid credits) and is separate from a claude.ai subscription.</p>
    <button class="btn primary" id="poolSave">Save AI pool</button> <span class="sub" id="poolMsg"></span>

    <h2 style="margin-top:22px">Free quota guard</h2>
    <p class="sub" style="margin-top:-4px">Stops map searches before you pass your free monthly allowance. Google's free allowance for searches with phone, website and rating is about 1,000 per month (check your Google Cloud billing page).</p>
    <div class="grid">
      <div><label for="capG">Google map searches / month</label><input id="capG" type="number" min="0"></div>
      <div><label for="capS">SerpApi searches / month</label><input id="capS" type="number" min="0"></div>
      <div><label for="hunterKey">Hunter.io key (optional)</label><input id="hunterKey" type="password" autocomplete="off"></div>
      <div><label for="cseKey">Google Custom Search API key</label><input id="cseKey" type="password" autocomplete="off"></div>
      <div><label for="cseId">Custom Search Engine ID (cx)</label><input id="cseId" autocomplete="off" placeholder="017…"></div>
      <div><label for="chKey">Companies House key (UK)</label><input id="chKey" type="password" autocomplete="off"></div>
      <div><label for="psKey">PageSpeed API key (optional)</label><input id="psKey" type="password" autocomplete="off"></div>
      <div><button class="btn" id="capSave" style="width:100%">Save</button></div>
    </div>
    <div id="quotaView" style="margin-top:10px"></div>`;
  $("#tab-settings").appendChild(panel);
  const sel = $("#aiProvider");
  if (sel && !sel.querySelector('option[value="pool"]')){
    sel.insertAdjacentHTML("afterbegin", '<option value="pool">Free AI pool (recommended)</option>');
    const S = window.LF.settings();
    if (!S.ai || !S.ai.provider || S.ai.provider === "pool") sel.value = "pool";
  }
}
function poolRows(){
  const pool = server.config.pool || [];
  const rows = [...pool.map(p => p.provider), ...ORDER.filter(p => !pool.some(x => x.provider === p))];
  $("#poolRows").innerHTML = rows.map((pid, i) => {
    const P = server.providers[pid] || {}; const c = pool.find(x => x.provider === pid) || {};
    return `<tr data-pid="${pid}">
      <td><input type="checkbox" data-k="enabled" style="width:auto" ${c.enabled ? "checked" : ""} aria-label="Use ${esc(P.label)}"></td>
      <td><div class="nm">${esc(P.label)}</div>${P.free === true ? '<span class="tag t-no">free tier</span>' : P.free === false ? '<span class="tag t-weak">paid</span>' : ''}
        ${P.signup ? `<a class="sub" target="_blank" rel="noopener" href="${esc(P.signup)}">get key</a>` : ""}</td>
      <td>${P.nokey ? '<span class="sub">no key needed</span>' : `<input data-k="key" type="password" autocomplete="off" value="${esc(c.key||"")}" placeholder="paste key">`}
        ${pid === "custom" || pid === "ollama" ? `<input data-k="base" placeholder="${esc(P.base || "https://…/v1")}" value="${esc(c.base||"")}" style="margin-top:4px">` : ""}</td>
      <td><input data-k="model" list="ml-${pid}" value="${esc(c.model || P.model || "")}" placeholder="choose with List models"><datalist id="ml-${pid}"></datalist></td>
      <td class="sub" data-stat></td>
      <td><div class="acts"><button class="btn sm" data-p="models">List models</button><button class="btn sm" data-p="test">Test</button>
        <button class="btn sm" data-p="up" ${i===0?"disabled":""} aria-label="Move up">↑</button><button class="btn sm" data-p="down" aria-label="Move down">↓</button></div></td></tr>`;
  }).join("");
}
function readPool(){
  return [...document.querySelectorAll("#poolRows tr")].map(tr => {
    const o = {provider: tr.dataset.pid};
    tr.querySelectorAll("[data-k]").forEach(i => o[i.dataset.k] = i.type === "checkbox" ? i.checked : i.value.trim());
    return o;
  }).filter(o => o.enabled || o.key || o.base);
}
function renderPoolStatus(ai){
  (ai || []).forEach(s => {
    const td = document.querySelector(`#poolRows tr[data-pid="${s.provider}"] [data-stat]`);
    if (td) td.innerHTML = `${s.usedToday} used${s.coolingFor ? `<br><span style="color:var(--warn)">${esc(s.reason)} · ${Math.ceil(s.coolingFor/60)} min</span>` : ""}`;
  });
}
function renderQuota(s){
  const q = $("#quotaView"); if (!q) return;
  const row = (name, used, cap) => `<div style="margin:6px 0"><b>${name}</b> <span class="sub">${used}/${cap || "no cap"} this month</span>${cap ? bar(used, cap) : ""}</div>`;
  q.innerHTML = row("Google Maps", s.usage.google||0, s.caps.google) + row("SerpApi", s.usage.serpapi||0, s.caps.serpapi);
}

/* ------------------------------------------------------------------ contact enrichment */
async function enrichLeads(leads, btn){
  const targets = leads.filter(l => l.website && !/facebook|instagram|linktr|business\.site/i.test(l.website) && !l.enriched);
  if (!targets.length){ alert("No businesses with a website to check here."); return; }
  const label = btn.textContent; btn.disabled = true; let done = 0;
  const q = [...targets];
  const worker = async () => { while (q.length){ const l = q.shift();
    try {
      const r = await api("/api/contacts/enrich", {website: l.website});
      const best = r.emails.find(e => !e.free) || r.emails[0];
      Object.assign(l, {enriched: true, contactPage: r.contactPage || l.contactPage || "",
        emailsFound: [...new Set([...(l.emailsFound||[]), ...r.emails.map(e => e.email)])],
        guessedEmails: r.guessed, emailStatus: best ? best.status : (r.guessed.length ? "guessed" : "none")});
      if (!l.email && best) l.email = best.email;
      window.LF.saveLead(l);
    } catch(e){}
    done++; btn.textContent = `${done}/${targets.length}…`; } };
  await Promise.all([worker(), worker(), worker(), worker()]);
  btn.disabled = false; btn.textContent = label;
  window.LF.refresh();
}
async function verifyListEmails(btn){
  const list = window.LF.getList().filter(l => l.email && !l.emailVerified);
  if (!list.length){ alert("No unverified emails in My list."); return; }
  btn.disabled = true;
  for (let i = 0; i < list.length; i += 25){
    const chunk = list.slice(i, i + 25);
    const r = await api("/api/contacts/verify", {emails: chunk.map(l => l.email)});
    r.results.forEach((v, k) => window.LF.updateLead(chunk[k].id, {emailVerified: v.status, emailStatus: v.status}));
    btn.textContent = `${Math.min(i+25, list.length)}/${list.length}…`;
  }
  btn.disabled = false; btn.textContent = "Verify emails"; window.LF.refresh();
}

/* ------------------------------------------------------------------ init */
async function init(){
  mountToday(); mountSettings();
  window.LF.log = logAct;
  // extra buttons
  $("#bulkEmail").insertAdjacentHTML("beforebegin", '<button class="btn sm" id="enrichBtn">Find & verify contacts</button>');
  $("#enrichBtn").onclick = e => enrichLeads(window.LF.getShown(), e.target);
  $("#exportList").insertAdjacentHTML("beforebegin", '<button class="btn sm" id="listEnrich">Find contacts</button><button class="btn sm" id="listVerify">Verify emails</button><button class="btn sm primary" id="listCall">Call session</button>');
  $("#listEnrich").onclick = e => enrichLeads(window.LF.getList(), e.target);
  $("#listVerify").onclick = e => verifyListEmails(e.target);
  $("#listCall").onclick = () => openCall(callQueue());
  $("#tdCall").onclick = () => openCall(callQueue());
  $("#tdDue").onclick = e => { const id = e.target.dataset.callone; if (id) openCall([window.LF.getList().find(l => l.id === id)]); };
  $("#tdEnrichInbox").onclick = async e => { await enrichLeads(inbox, e.target); renderInbox(); };
  $("#tdInbox").onclick = async e => {
    const b = e.target.closest("[data-in]"); if (!b) return;
    const id = b.closest("tr").dataset.iid, l = inbox.find(x => x.id === id);
    if (b.dataset.in === "analyze"){ window.LFReport.open(l, x => {}); return; }
    resolveInbox([id], b.dataset.in === "accept");
  };
  $("#tdAcceptAll").onclick = () => inbox.length && resolveInbox(inbox.map(l => l.id), true);
  $("#tdDismissAll").onclick = () => inbox.length && confirm("Dismiss all new leads?") && resolveInbox(inbox.map(l => l.id), false);
  $("#tdPlan").onclick = async () => {
    const out = $("#tdPlanOut"); out.innerHTML = '<p class="sub"><span class="spin"></span> Planning…</p>';
    const list = window.LF.getList();
    const hot = list.filter(l => l.priority === "Hot" && !["Won","Not interested"].includes(l.stage)).slice(0, 8);
    const due = dueList().slice(0, 10);
    const summary = `Today: ${new Date().toDateString()}. Goals: ${goals.calls} calls, ${goals.emails} emails, ${goals.newLeads} new leads.
Done so far today: ${act("calls")} calls, ${act("emails")} emails.
Inbox: ${inbox.length} new leads. Pipeline: ${["New","Contacted","No answer","Interested","Follow up","Proposal sent","Won"].map(s => `${s} ${list.filter(l=>l.stage===s).length}`).join(", ")}.
Follow-ups due: ${due.map(l => `${l.name} (${l.stage}; ${(l.notes||"").split("\n").pop()})`).join("; ") || "none"}.
Hot leads: ${hot.map(l => `${l.name} (${l.category}, ${l.reviews||0} reviews, stage ${l.stage})`).join("; ") || "none"}.
Email drafts waiting: ${store("lf-outbox", []).filter(o => o.status === "draft").length}.`;
    try {
      const r = await api("/api/ai", {ai: {provider: "pool"}, prompt: summary + "\n\nAs my sales assistant, write today's plan: 1) a prioritized to-do list with times (morning / midday / afternoon), naming the specific businesses to call first and why, 2) one tip to improve results today. Keep it under 200 words. Only use the data above."});
      out.innerHTML = `<div class="aiout" style="white-space:pre-wrap;background:var(--bg);border-radius:8px;padding:12px;margin-top:12px">${esc(r.text)}</div><div class="sub">by ${esc(r.provider||"AI")}</div>`;
    } catch(err){ out.innerHTML = `<div class="msg err">${esc(err.message)}</div>`; }
  };
  $("#gCalls").value = goals.calls; $("#gEmails").value = goals.emails; $("#gLeads").value = goals.newLeads;
  $("#gSave").onclick = () => { goals = {calls:+$("#gCalls").value||0, emails:+$("#gEmails").value||0, newLeads:+$("#gLeads").value||0}; store("lf-goals", null, goals); renderStats(); };

  // server config
  try {
    const r = await api("/api/assistant/config");
    server.config = r.config; server.providers = r.providers;
  } catch(e){ server.config = {jobs:[], pool:[], caps:{}, keys:{}}; }
  // push browser-saved map keys to the server so autopilot can use them
  const S = window.LF.settings();
  if ((S.apiKey && S.apiKey !== server.config.keys.google) || (S.serpKey && S.serpKey !== server.config.keys.serp))
    saveConfig({keys: {google: S.apiKey || null, serp: S.serpKey || null}}).catch(()=>{});
  $("#saveSettings").addEventListener("click", () => {
    const s2 = window.LF.settings();
    saveConfig({keys: {google: s2.apiKey || "", serp: s2.serpKey || ""}}).catch(()=>{});
  });
  jobsTable(); poolRows();
  $("#capG").value = server.config.caps.google; $("#capS").value = server.config.caps.serpapi;
  $("#hunterKey").value = server.config.keys.hunter || "";
  if ($("#cseKey"))  $("#cseKey").value  = server.config.keys.cse  || "";
  if ($("#cseId"))   $("#cseId").value   = server.config.keys.cseId || "";
  if ($("#chKey"))   $("#chKey").value   = server.config.keys.ch    || "";
  if ($("#psKey"))   $("#psKey").value   = server.config.keys.pagespeed || "";
  $("#capSave").onclick = async () => {
    await saveConfig({caps: {google: +$("#capG").value||0, serpapi: +$("#capS").value||0},
      keys: {
        hunter: $("#hunterKey").value.trim(),
        cse: $("#cseKey") ? $("#cseKey").value.trim() : undefined,
        cseId: $("#cseId") ? $("#cseId").value.trim() : undefined,
        ch: $("#chKey") ? $("#chKey").value.trim() : undefined,
        pagespeed: $("#psKey") ? $("#psKey").value.trim() : undefined,
      }});
    pollStatus();
  };
  $("#poolSave").onclick = async () => { await saveConfig({pool: readPool()}); poolRows(); $("#poolMsg").textContent = "Saved."; pollStatus(); };
  $("#poolRows").onclick = async e => {
    const b = e.target.closest("[data-p]"); if (!b) return;
    const tr = b.closest("tr"); const p = b.dataset.p;
    const cfg = {provider: tr.dataset.pid}; tr.querySelectorAll("[data-k]").forEach(i => cfg[i.dataset.k] = i.type === "checkbox" ? i.checked : i.value.trim());
    if (p === "up" && tr.previousElementSibling){ tr.parentNode.insertBefore(tr, tr.previousElementSibling); return; }
    if (p === "down" && tr.nextElementSibling){ tr.parentNode.insertBefore(tr.nextElementSibling, tr); return; }
    const label = b.textContent; b.disabled = true; b.innerHTML = '<span class="spin"></span>';
    try {
      if (p === "models"){
        const r = await api("/api/pool/models", {cfg});
        tr.querySelector("datalist").innerHTML = r.models.map(m => `<option value="${esc(m)}">`).join("");
        tr.querySelector('[data-k="model"]').focus();
        $("#poolMsg").textContent = `${r.models.length} models found. Click the Model box to pick one.`;
      } else {
        const r = await api("/api/pool/test", {cfg});
        $("#poolMsg").textContent = `${server.providers[cfg.provider].label}: works (${r.model}, ${r.seconds}s). Tick "Use" and save.`;
        tr.querySelector('[data-k="enabled"]').checked = true;
      }
    } catch(err){ $("#poolMsg").textContent = err.message.slice(0, 220); }
    b.disabled = false; b.textContent = label;
  };
  $("#apForm").onsubmit = async e => {
    e.preventDefault();
    const f = new FormData(e.target);
    const j = Object.fromEntries(f.entries());
    j.id = Date.now().toString(36); j.enabled = true; j.pages = +j.pages; j.minReviews = +j.minReviews;
    await saveConfig({jobs: [...server.config.jobs, j]}); e.target.reset(); jobsTable();
  };
  $("#apJobs").onclick = async e => {
    const tr = e.target.closest("tr[data-jid]"); if (!tr) return;
    const id = tr.dataset.jid;
    if (e.target.hasAttribute("data-jdel")){ await saveConfig({jobs: server.config.jobs.filter(j => j.id !== id)}); jobsTable(); }
    if (e.target.hasAttribute("data-jrun")){ await api("/api/assistant/run", {only: [id]}); pollStatus(); }
  };
  $("#apJobs").onchange = async e => {
    if (!e.target.hasAttribute("data-jon")) return;
    const id = e.target.closest("tr").dataset.jid;
    await saveConfig({jobs: server.config.jobs.map(j => j.id === id ? {...j, enabled: e.target.checked} : j)});
  };
  $("#apOn").onchange = () => saveConfig({autopilot: $("#apOn").checked});
  $("#apHour").onchange = () => saveConfig({runHour: +$("#apHour").value});
  $("#apRun").onclick = async () => {
    if (!server.config.jobs.length){ alert("Save at least one search first."); return; }
    await api("/api/assistant/run", {}); pollStatus();
  };
  window.LF.showTab("today");
  refreshInbox(); renderDue(); pollStatus();
}
window.LFAssistant = {openCall, logAct};
if (window.LF) init(); else document.addEventListener("lf-ready", init);
})();
