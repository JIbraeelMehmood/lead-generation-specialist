/* LeadFinder: Dashboard tab — pipeline funnel, activity chart, source stats, top opps */
(function(){
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const api = (p, b) => window.LF.api(p, b);

// ---------------------------------------------------------------- mount
function mount(){
  const sec = document.createElement("section");
  sec.id = "tab-dashboard"; sec.hidden = true;
  sec.innerHTML = `
  <div class="panel" id="db-funnel-panel">
    <div class="toolbar" style="margin:0">
      <h2 class="grow" style="margin:0">Pipeline</h2>
      <button class="btn sm" id="dbRefresh">Refresh</button>
      <button class="btn sm primary" id="dbAISummary">AI Weekly Summary</button>
    </div>
    <div id="dbFunnel" class="tally" style="margin-top:12px;flex-wrap:nowrap;overflow-x:auto;gap:0"></div>
  </div>

  <div style="display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(340px,1fr))">
    <div class="panel">
      <h3 style="margin-top:0">Activity (last 7 days)</h3>
      <div id="dbActivity"></div>
      <div class="sub" id="dbStreak" style="margin-top:8px"></div>
    </div>
    <div class="panel">
      <h3 style="margin-top:0">Source performance</h3>
      <div id="dbSources"></div>
    </div>
    <div class="panel">
      <h3 style="margin-top:0">Email campaign</h3>
      <div id="dbEmail"></div>
    </div>
    <div class="panel">
      <h3 style="margin-top:0">API usage this month</h3>
      <div id="dbUsage"></div>
    </div>
  </div>

  <div class="panel">
    <h3 style="margin-top:0">Top 10 opportunities</h3>
    <div class="tablewrap"><table>
      <thead><tr><th>Score</th><th>Business</th><th>Stage</th><th>Phone</th><th>Email</th><th>Reviews</th></tr></thead>
      <tbody id="dbOpps"></tbody>
    </table></div>
  </div>

  <div class="panel" id="dbAIOut" hidden>
    <h3 style="margin-top:0">Weekly AI summary</h3>
    <div id="dbAIText" style="white-space:pre-wrap;line-height:1.6"></div>
  </div>`;
  document.querySelector(".wrap").appendChild(sec);
  const nav = document.querySelector("nav");
  const b = document.createElement("button");
  b.setAttribute("role","tab"); b.dataset.tab = "dashboard"; b.textContent = "Dashboard";
  b.setAttribute("aria-selected","false");
  nav.appendChild(b);
  window.LF.bindTab(b, load);
}

// ---------------------------------------------------------------- bar chart (pure CSS)
function barChart(data /* [{label, value, max, color}] */){
  const peak = Math.max(1, ...data.map(d => d.value));
  return `<div style="display:flex;align-items:flex-end;gap:10px;height:80px;padding:0 4px">
    ${data.map(d => {
      const h = Math.round(70 * d.value / peak);
      const col = d.color || "var(--go)";
      return `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px">
        <span class="sub" style="font-size:11px">${d.value}</span>
        <div style="width:100%;background:${col};height:${h}px;border-radius:3px 3px 0 0;min-height:${d.value?2:0}px"></div>
        <span class="sub" style="font-size:10px;white-space:nowrap;overflow:hidden;max-width:40px">${esc(d.label.slice(-4))}</span>
      </div>`;
    }).join("")}
  </div>`;
}

function funnelBar(stages){
  const FLOW = ["New","Contacted","Interested","Proposal sent","Won"];
  const counts = {};
  stages.forEach(s => counts[s.stage] = s.count);
  const max = Math.max(1, ...Object.values(counts));
  const colors = {"New":"var(--chip)","Contacted":"var(--go-soft)","Interested":"var(--warn-soft)","Proposal sent":"var(--go)","Won":"#0B7A55"};
  return `<div style="display:flex;gap:0;align-items:stretch;width:100%">
    ${FLOW.map((st, i) => {
      const n = counts[st] || 0;
      const w = Math.max(8, Math.round(100 * n / max));
      const arrow = i < FLOW.length - 1 ? `<div style="width:0;height:0;border-top:24px solid transparent;border-bottom:24px solid transparent;border-left:12px solid ${colors[st]};flex-shrink:0"></div>` : "";
      return `<div style="flex:${w};background:${colors[st]};padding:8px 10px;display:flex;flex-direction:column;justify-content:center;min-width:60px;position:relative">
        <b style="font-family:var(--display);font-size:20px">${n}</b>
        <span class="sub" style="font-size:11px">${esc(st)}</span>
      </div>${arrow}`;
    }).join("")}
    <div style="flex:${Math.max(8, Math.round(100*(counts["Not interested"]||0)/max))};background:var(--stop-soft);padding:8px 10px;min-width:60px">
      <b style="font-family:var(--display);font-size:20px">${counts["Not interested"]||0}</b>
      <span class="sub" style="display:block;font-size:11px">Not interested</span>
    </div>
  </div>`;
}

// ---------------------------------------------------------------- render
function renderDashboard(data){
  // Funnel
  $("#dbFunnel").innerHTML = funnelBar(data.funnel.stages) +
    `<div class="sub" style="margin-top:8px">
      ${data.funnel.total} total · ${data.funnel.won} won · ${data.funnel.contacted} contacted · ${data.funnel.conversionRate}% conversion
    </div>`;

  // Activity chart
  const am = data.activityMetrics;
  const days7 = Object.entries(am.last7Days).sort(([a],[b]) => a > b ? 1 : -1);
  const callData = days7.map(([d, v]) => ({label: d.slice(5), value: v.calls||0, color:"var(--go)"}));
  const emailData = days7.map(([d, v]) => ({label: d.slice(5), value: v.emails||0, color:"var(--warn)"}));
  $("#dbActivity").innerHTML =
    `<div class="sub" style="margin-bottom:4px">Calls <span style="color:var(--go)">■</span> · Emails <span style="color:var(--warn)">■</span></div>` +
    `<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">` +
    barChart(callData) + barChart(emailData) + `</div>` +
    `<div class="tally" style="margin-top:8px">
      <div><b>${am.today.calls||0}</b><span>calls today</span></div>
      <div><b>${am.today.emails||0}</b><span>emails today</span></div>
      <div><b>${am.today.newLeads||0}</b><span>leads added today</span></div>
    </div>`;
  $("#dbStreak").textContent = am.streak ? `🔥 ${am.streak}-day outreach streak` : "Start your streak: contact at least one lead today.";

  // Source performance
  $("#dbSources").innerHTML = data.sourcePerformance.length
    ? `<table style="width:100%;border-collapse:collapse"><thead><tr>
        <th class="sub" style="text-align:left;padding:3px 6px">Source</th>
        <th class="sub" style="text-align:right;padding:3px 6px">Leads</th>
        <th class="sub" style="text-align:right;padding:3px 6px">With Email</th>
        <th class="sub" style="text-align:right;padding:3px 6px">Won</th>
        <th class="sub" style="text-align:right;padding:3px 6px">Conv%</th>
      </tr></thead><tbody>
        ${data.sourcePerformance.map(s => `<tr>
          <td style="padding:3px 6px;font-size:13px">${esc(s.source)}</td>
          <td style="text-align:right;padding:3px 6px">${s.total}</td>
          <td style="text-align:right;padding:3px 6px">${s.hasEmail}</td>
          <td style="text-align:right;padding:3px 6px">${s.won}</td>
          <td style="text-align:right;padding:3px 6px">${s.convRate}%</td>
        </tr>`).join("")}
      </tbody></table>`
    : '<p class="sub">No leads yet. Search for businesses to populate this.</p>';

  // Email stats
  const em = data.emailStats;
  $("#dbEmail").innerHTML = `
    <div class="tally" style="margin:0">
      <div><b>${em.counts.draft||0}</b><span>drafts</span></div>
      <div><b>${em.counts.approved||0}</b><span>approved</span></div>
      <div><b>${em.counts.sent||0}</b><span>sent</span></div>
      <div><b>${em.sentToday||0}</b><span>sent today</span></div>
    </div>
    ${em.failRate > 10 ? `<div class="msg err" style="margin-top:8px;font-size:13px">⚠ ${em.failRate}% send failure rate — check your SMTP settings.</div>` : ""}
    ${em.byGroup.length ? `<div class="sub" style="margin-top:8px">By template group:</div>
      ${em.byGroup.slice(0,5).map(g => `<div class="sub" style="margin:2px 0">${esc(g.group)}: ${g.sent} sent, ${g.draft} draft</div>`).join("")}` : ""}`;

  // API usage
  const u = data.usage;
  const bar = (used, cap) => cap ? `<div style="height:5px;border-radius:2px;background:var(--chip);margin-top:3px"><div style="height:5px;border-radius:2px;background:var(--go);width:${Math.min(100, Math.round(100*used/cap))}%"></div></div>` : "";
  $("#dbUsage").innerHTML = `
    <div style="margin:4px 0"><b>Google Maps</b> <span class="sub">${u.google||0} searches this month</span>${bar(u.google, 900)}</div>
    <div style="margin:4px 0"><b>SerpApi</b> <span class="sub">${u.serpapi||0} searches this month</span>${bar(u.serpapi, 90)}</div>
    <div class="sub" style="margin-top:6px">Inbox: ${data.inboxCount} new leads · Last autopilot: ${data.lastRun || "never"}</div>`;

  // Top opportunities
  const opps = data.topOpportunities;
  $("#dbOpps").innerHTML = opps.length ? opps.map(l => {
    const scoreColor = l.score >= 70 ? "var(--go)" : l.score >= 50 ? "var(--warn)" : "var(--muted)";
    return `<tr>
      <td><span style="font-family:var(--display);font-weight:700;font-size:18px;color:${scoreColor}">${l.score}</span></td>
      <td><div class="nm">${esc(l.name)}</div><div class="sub">${esc(l.category||"")} · ${esc(l.address||"")}</div></td>
      <td><span class="tag ${l.priority==="Hot"?"t-no":l.priority==="Warm"?"t-weak":"t-yes"}">${esc(l.stage||"New")}</span></td>
      <td>${l.phone ? `<a href="tel:${esc(l.phone.replace(/\s/g,""))}">${esc(l.phone)}</a>` : '<span class="sub">—</span>'}</td>
      <td>${l.email ? `<a href="mailto:${esc(l.email)}">${esc(l.email)}</a>` : '<span class="sub">—</span>'}</td>
      <td>${l.rating ? `${l.rating}★` : "—"} <span class="sub">${l.reviews||0}</span></td>
    </tr>`;
  }).join("") : '<tr><td colspan="6" class="empty">No leads yet.</td></tr>';
}

// ---------------------------------------------------------------- load
async function load(){
  const list = window.LF.getList();
  const outbox = (() => { try { return JSON.parse(localStorage.getItem("lf-outbox") || "[]"); } catch(e){ return []; } })();
  const actLog = (() => { try { return JSON.parse(localStorage.getItem("lf-log") || "{}"); } catch(e){ return {}; } })();
  try {
    const data = await api("/api/dashboard", {leads: list, outbox, activityLog: actLog});
    renderDashboard(data);
  } catch(e){
    console.error("Dashboard load failed:", e.message);
  }
}

// ---------------------------------------------------------------- AI summary
async function aiSummary(){
  const btn = $("#dbAISummary"); btn.disabled = true; btn.innerHTML = '<span class="spin"></span>';
  try {
    const list = window.LF.getList();
    const r = await api("/api/dashboard/ai-summary", {leads: list});
    $("#dbAIText").textContent = r.summary || "(No summary generated — check your AI pool settings.)";
    $("#dbAIOut").hidden = false;
  } catch(e){
    alert("AI summary failed: " + e.message);
  }
  btn.disabled = false; btn.textContent = "AI Weekly Summary";
}

function init(){
  mount();
  $("#dbRefresh").onclick = load;
  $("#dbAISummary").onclick = aiSummary;
}

window.LFDashboard = {load};
document.addEventListener("DOMContentLoaded", init);
})();
