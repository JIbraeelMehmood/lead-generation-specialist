/**
 * static/campaigns.js — Campaign Optimization & Feedback Loop tab
 *
 * Connects to backend campaign.py via /api/campaign/*.
 * Implements the Free-email-outreach-tool 7-step methodology.
 *
 * Features:
 *   - Campaign creation and management
 *   - Metric recording: sends / opens / replies / meetings / won
 *   - Reply classifier (paste reply → get category)
 *   - Per-campaign stats: reply rate, positive rate, meeting rate
 *   - Variant and segment comparison
 *   - Actionable insights
 *   - Webhook config for Zapier/Make/HubSpot
 */
(function () {
  const TAB_ID = "campaigns";

  function ensurePanel() {
    if (document.getElementById("tab-campaigns")) return;
    const panel = document.createElement("section");
    panel.id = "tab-campaigns";
    panel.setAttribute("role", "tabpanel");
    panel.style.display = "none";
    panel.innerHTML = `
<div style="max-width:960px;margin:0 auto">

  <!-- Summary bar -->
  <div class="card">
    <h2 style="margin-top:0">📊 Campaign Optimization</h2>
    <p style="color:#666;margin-top:0">Track sends, replies, meetings, and revenue across all outreach campaigns.
    Primary metrics: <b>reply rate</b>, <b>positive rate</b>, <b>meeting rate</b>
    (open rate is unreliable due to privacy protections).</p>
    <div id="campSummaryBar" style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:4px"></div>
  </div>

  <!-- Create campaign + list -->
  <div style="display:grid;grid-template-columns:1fr 1.6fr;gap:16px;margin-top:16px">

    <!-- Create -->
    <div class="card">
      <h3 style="margin-top:0">➕ New Campaign</h3>
      <label><b>Campaign name</b>
        <input id="campName" type="text" placeholder="e.g. Karachi Restaurants Nov 2026" style="width:100%;margin-top:4px">
      </label>
      <label style="display:block;margin-top:10px"><b>Description (optional)</b>
        <input id="campDesc" type="text" placeholder="Target niche or angle" style="width:100%;margin-top:4px">
      </label>
      <button id="campCreateBtn" class="btn-primary" style="margin-top:12px;width:100%">Create Campaign</button>
      <span id="campCreateStatus" style="font-size:12px;color:#666;display:block;margin-top:6px"></span>
    </div>

    <!-- Campaigns list -->
    <div class="card">
      <h3 style="margin-top:0">📋 All Campaigns</h3>
      <div id="campList"><em style="color:#888">No campaigns yet.</em></div>
    </div>
  </div>

  <!-- Campaign detail -->
  <div id="campDetail" style="display:none;margin-top:16px"></div>

  <!-- Webhook config -->
  <div class="card" style="margin-top:16px">
    <h3 style="margin-top:0">🔗 CRM Webhooks</h3>
    <p style="color:#666;font-size:14px;margin-top:0">Fire a webhook when a lead reaches a key stage — integrate with Zapier, Make, HubSpot, GoHighLevel, Slack, or any HTTP endpoint.</p>
    <div id="webhooksList"></div>
    <button id="whRefreshBtn" class="btn-secondary" style="margin-top:10px" onclick="window._loadWebhooks()">🔄 Refresh</button>
  </div>

  <!-- Reply classifier -->
  <div class="card" style="margin-top:16px">
    <h3 style="margin-top:0">🏷️ Classify a Reply</h3>
    <p style="color:#666;font-size:14px;margin-top:0">Paste any reply email to classify it and optionally record it against a campaign.</p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:10px">
      <label><b>Subject</b><input id="clSubject" type="text" style="width:100%;margin-top:4px"></label>
      <label><b>Campaign (optional)</b>
        <select id="clCampaign" style="width:100%;margin-top:4px"><option value="">— not tied to campaign —</option></select>
      </label>
    </div>
    <label><b>Reply body</b>
      <textarea id="clBody" rows="4" style="width:100%;margin-top:4px" placeholder="Paste the reply here…"></textarea>
    </label>
    <div style="display:flex;gap:8px;margin-top:10px;align-items:center;flex-wrap:wrap">
      <button id="clClassifyBtn" class="btn-secondary">🏷️ Classify</button>
      <button id="clRecordBtn" class="btn-secondary">📥 Classify + Record</button>
      <div id="clResult" style="font-size:14px;font-weight:600"></div>
    </div>
  </div>

</div>`;
    document.querySelector("main") && document.querySelector("main").appendChild(panel);
    _initEvents(panel);
    _loadAll(panel);
  }

  async function api(path, body) {
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    return r.json();
  }

  function _initEvents(panel) {
    panel.querySelector("#campCreateBtn").onclick = () => _createCampaign(panel);
    panel.querySelector("#clClassifyBtn").onclick = () => _classifyReply(panel, false);
    panel.querySelector("#clRecordBtn").onclick   = () => _classifyReply(panel, true);
  }

  async function _loadAll(panel) {
    _loadSummary(panel);
    _loadCampaignList(panel);
    window._loadWebhooks();
  }

  async function _loadSummary(panel) {
    const data = await api("/api/campaign/all", {});
    const bar = panel.querySelector("#campSummaryBar");
    const t = data.totals || {};
    const r = data.rates || {};
    bar.innerHTML = [
      ["📤 Sends",    t.sends || 0, ""],
      ["💬 Replies",  t.replies || 0, r.reply_rate + "%"],
      ["🎉 Interested", t.interested || 0, r.positive_rate + "%"],
      ["📅 Meetings", t.meetings_booked || 0, r.meeting_rate + "%"],
      ["🏆 Won",      t.won || 0, r.win_rate + "%"],
    ].map(([label, val, rate]) => `
<div style="background:#f8fafc;border-radius:8px;padding:12px;text-align:center">
  <div style="font-size:11px;color:#9ca3af">${label}</div>
  <div style="font-size:22px;font-weight:700;color:#1e293b">${val}</div>
  ${rate ? `<div style="font-size:12px;color:#059669">${rate}</div>` : ""}
</div>`).join("");
  }

  async function _loadCampaignList(panel) {
    const data = await api("/api/campaign/list", {});
    const campaigns = data.campaigns || [];
    const container = panel.querySelector("#campList");
    const clSelect = panel.querySelector("#clCampaign");

    // Populate classifier dropdown
    clSelect.innerHTML = `<option value="">— not tied to campaign —</option>`;
    campaigns.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id; opt.textContent = c.name;
      clSelect.appendChild(opt);
    });

    if (!campaigns.length) { container.innerHTML = `<em style="color:#888">No campaigns yet.</em>`; return; }

    container.innerHTML = campaigns.map(c => {
      const m = c.metrics || {};
      const sends = m.sends || 0;
      const rr = sends ? ((m.replies || 0) / sends * 100).toFixed(1) : "0";
      const pr = sends ? ((m.interested || 0) / sends * 100).toFixed(1) : "0";
      return `
<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f1f5f9;cursor:pointer" onclick="window._loadCampDetail('${c.id}')">
  <div>
    <b>${_esc(c.name)}</b>
    <span style="font-size:11px;background:${c.status === "active" ? "#dcfce7" : "#f1f5f9"};color:${c.status === "active" ? "#15803d" : "#64748b"};padding:2px 6px;border-radius:4px;margin-left:6px">${c.status}</span>
    <div style="font-size:12px;color:#9ca3af">${sends} sends · ${rr}% reply · ${pr}% positive</div>
  </div>
  <span style="color:#9ca3af">›</span>
</div>`;
    }).join("");
  }

  window._loadCampDetail = async function (cid) {
    const data = await api("/api/campaign/get", { id: cid });
    const c = data.campaign || data;
    const detail = document.getElementById("campDetail");
    if (!detail) return;
    detail.style.display = "block";

    const m = c.metrics || {};
    const r = c.rates || {};
    const insights = (c.insights || []).map(i => `<li>${_esc(i)}</li>`).join("");

    detail.innerHTML = `
<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:16px">
    <div>
      <h3 style="margin:0">${_esc(c.name)}</h3>
      <div style="font-size:13px;color:#9ca3af">${_esc(c.description || "")} · created ${c.created_at || ""}</div>
    </div>
    <div style="display:flex;gap:6px">
      <select id="cdStatus" style="font-size:12px" onchange="window._setCampStatus('${c.id}',this.value)">
        <option value="active" ${c.status==="active"?"selected":""}>Active</option>
        <option value="paused" ${c.status==="paused"?"selected":""}>Paused</option>
        <option value="completed" ${c.status==="completed"?"selected":""}>Completed</option>
      </select>
      <button class="btn-secondary" style="font-size:11px;color:#ef4444" onclick="window._deleteCamp('${c.id}')">Delete</button>
    </div>
  </div>

  <!-- Metrics grid -->
  <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-bottom:16px">
    ${[["Sends",m.sends||0,""],["Replies",m.replies||0,r.reply_rate+"%"],
       ["Interested",m.interested||0,r.positive_rate+"%"],["Meetings",m.meetings_booked||0,r.meeting_rate+"%"],
       ["Won",m.won||0,r.win_rate+"%"],["Unsubs",m.unsubscribes||0,r.unsubscribe_rate+"%"]]
      .map(([lbl,val,rt])=>`<div style="background:#f8fafc;border-radius:6px;padding:10px;text-align:center">
        <div style="font-size:11px;color:#9ca3af">${lbl}</div>
        <div style="font-size:18px;font-weight:700">${val}</div>
        ${rt?`<div style="font-size:11px;color:#059669">${rt}</div>`:""}
      </div>`).join("")}
  </div>

  <!-- Insights -->
  ${insights ? `<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:12px;margin-bottom:16px">
    <b>💡 Insights</b><ul style="margin:6px 0 0 20px;font-size:13px">${insights}</ul>
  </div>` : ""}

  <!-- Quick record buttons -->
  <div>
    <b style="font-size:13px">Quick record:</b>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">
      <button class="btn-secondary" style="font-size:12px" onclick="window._quickRecord('${c.id}','send')">+1 Send</button>
      <button class="btn-secondary" style="font-size:12px" onclick="window._quickRecord('${c.id}','open')">+1 Open</button>
      <button class="btn-secondary" style="font-size:12px;color:#16a34a" onclick="window._quickRecord('${c.id}','meeting')">+1 Meeting 📅</button>
      <button class="btn-secondary" style="font-size:12px;color:#2563eb" onclick="window._quickRecord('${c.id}','won')">+1 Won 🏆</button>
    </div>
  </div>
</div>`;
  };

  window._quickRecord = async function (cid, type) {
    await api(`/api/campaign/record/${type}`, { campaign_id: cid });
    window._loadCampDetail(cid);
    _loadSummary(document.getElementById("tab-campaigns"));
  };

  window._setCampStatus = async function (cid, status) {
    await api("/api/campaign/status", { id: cid, status });
    _loadCampaignList(document.getElementById("tab-campaigns"));
  };

  window._deleteCamp = async function (cid) {
    if (!confirm("Delete this campaign?")) return;
    await api("/api/campaign/delete", { id: cid });
    document.getElementById("campDetail").style.display = "none";
    _loadAll(document.getElementById("tab-campaigns"));
  };

  async function _createCampaign(panel) {
    const name = panel.querySelector("#campName").value.trim();
    if (!name) { alert("Enter a campaign name."); return; }
    const btn = panel.querySelector("#campCreateBtn");
    btn.disabled = true;
    const data = await api("/api/campaign/create", { name, description: panel.querySelector("#campDesc").value.trim() });
    panel.querySelector("#campCreateStatus").textContent = `✅ Created: ${name}`;
    panel.querySelector("#campName").value = "";
    panel.querySelector("#campDesc").value = "";
    btn.disabled = false;
    _loadCampaignList(panel);
    _loadSummary(panel);
    setTimeout(() => { panel.querySelector("#campCreateStatus").textContent = ""; }, 3000);
  }

  async function _classifyReply(panel, record) {
    const subject = panel.querySelector("#clSubject").value;
    const body    = panel.querySelector("#clBody").value;
    const cid     = panel.querySelector("#clCampaign").value;
    const result  = panel.querySelector("#clResult");
    result.textContent = "⏳";

    if (record && cid) {
      const data = await api("/api/campaign/record/reply", { campaign_id: cid, lead_id: "", subject, body });
      const colors = { interested:"#16a34a",unsubscribe:"#ef4444",bounce:"#ef4444",referral:"#2563eb",objection:"#f59e0b",ooo:"#6b7280",unknown:"#9ca3af" };
      result.style.color = colors[data.category] || "#374151";
      result.textContent = "🏷️ " + data.category + (record ? " (recorded)" : "");
    } else {
      const data = await api("/api/campaign/classify", { subject, body });
      const colors = { interested:"#16a34a",unsubscribe:"#ef4444",bounce:"#ef4444",referral:"#2563eb",objection:"#f59e0b",ooo:"#6b7280",unknown:"#9ca3af" };
      result.style.color = colors[data.category] || "#374151";
      result.textContent = "🏷️ " + data.category;
    }
  }

  window._loadWebhooks = async function () {
    const container = document.getElementById("webhooksList");
    if (!container) return;
    const data = await api("/api/webhooks/list", {});
    const webhooks = data.webhooks || {};
    container.innerHTML = Object.entries(webhooks).map(([trigger, cfg]) => `
<div style="display:grid;grid-template-columns:140px 1fr auto auto;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:13px">
  <div>
    <b>${_esc(cfg.label || trigger)}</b>
    ${cfg.last_fired ? `<div style="font-size:11px;color:#9ca3af">Last: ${cfg.last_fired}</div>` : ""}
  </div>
  <input type="text" value="${_esc(cfg.url || "")}" placeholder="https://hooks.zapier.com/…"
    id="wh_${trigger}" style="font-size:12px;font-family:monospace">
  <label style="display:flex;align-items:center;gap:4px;font-size:12px">
    <input type="checkbox" ${cfg.enabled ? "checked" : ""} id="whe_${trigger}"> On
  </label>
  <div style="display:flex;gap:4px">
    <button class="btn-secondary" style="font-size:11px" onclick="window._saveWebhook('${trigger}')">Save</button>
    <button class="btn-secondary" style="font-size:11px" onclick="window._testWebhook('${trigger}')">Test</button>
  </div>
</div>`).join("");
  };

  window._saveWebhook = async function (trigger) {
    const url     = document.getElementById(`wh_${trigger}`)?.value.trim() || "";
    const enabled = document.getElementById(`whe_${trigger}`)?.checked ?? true;
    await api("/api/webhooks/configure", { trigger, url, enabled });
    window._loadWebhooks();
  };

  window._testWebhook = async function (trigger) {
    const data = await api("/api/webhooks/test", { trigger });
    alert(data.ok ? `✅ Test delivered to ${data.url}` : `❌ Failed: ${data.error}`);
  };

  function _esc(s) {
    return String(s || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  }

  document.addEventListener("DOMContentLoaded", () => {
    const tabBtn = document.querySelector(`[data-tab="${TAB_ID}"]`);
    if (!tabBtn) return;
    window.LF.bindTab(tabBtn, () => ensurePanel());
  });
})();
