/**
 * static/whatsapp.js — Real WhatsApp Sending tab
 *
 * Connects to backend whatsapp_bridge.py via /api/whatsapp/*.
 * Implements Prospex send-policy: hourly limit, daily limit, quiet hours,
 * human approval queue, STOP opt-out handling.
 */
(function () {
  const TAB = "whatsapp";

  function ensurePanel() {
    if (document.getElementById("tab-whatsapp")) return;
    const panel = document.createElement("section");
    panel.id = "tab-whatsapp";
    panel.setAttribute("role", "tabpanel");
    panel.style.display = "none";
    panel.innerHTML = `
<div style="max-width:960px;margin:0 auto">

  <!-- Status card -->
  <div class="card" id="waStatusCard">
    <h2 style="margin-top:0">💬 WhatsApp Sending (Baileys)</h2>
    <div id="waStatusArea"><em style="color:#9ca3af">Loading…</em></div>
  </div>

  <!-- Setup instructions (shown when bridge offline) -->
  <div id="waSetupCard" class="card" style="margin-top:16px;display:none">
    <h3 style="margin-top:0">🔧 Setup Instructions</h3>
    <div id="waSetupText" style="font-size:14px;white-space:pre-line;font-family:monospace;background:#f8fafc;padding:12px;border-radius:6px;border:1px solid #e2e8f0"></div>
    <div style="margin-top:10px;display:flex;gap:8px">
      <button class="btn-secondary" onclick="window._waScaffold()">📁 Create bridge files</button>
      <button class="btn-secondary" onclick="window._waStartBridge()">▶️ Start bridge</button>
    </div>
  </div>

  <!-- QR code -->
  <div id="waQrCard" class="card" style="margin-top:16px;display:none;text-align:center">
    <h3 style="margin-top:0">📱 Scan QR Code</h3>
    <p style="color:#666">Open WhatsApp → Settings → Linked Devices → Link a Device → scan this code</p>
    <div id="waQrDisplay" style="font-size:11px;font-family:monospace;background:#000;color:#0f0;padding:16px;border-radius:8px;display:inline-block;margin:8px 0"></div>
    <p style="font-size:12px;color:#9ca3af">QR expires in ~30 seconds. Refresh if expired.</p>
    <button class="btn-secondary" onclick="window._waRefreshStatus()">🔄 Refresh</button>
  </div>

  <!-- Compose message -->
  <div class="card" style="margin-top:16px">
    <h3 style="margin-top:0">✍️ Send a Message</h3>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:10px">
      <label><b>Lead (optional)</b>
        <input id="waLeadId" type="text" placeholder="Lead ID or leave blank" style="width:100%;margin-top:4px">
      </label>
      <label><b>Phone number *</b>
        <input id="waPhone" type="text" placeholder="+1 555 000 0000" style="width:100%;margin-top:4px">
      </label>
    </div>
    <label><b>Message *</b>
      <textarea id="waMessage" rows="4" style="width:100%;margin-top:4px" placeholder="Hi [Name], I noticed your business doesn't have a website yet…"></textarea>
    </label>
    <div style="display:flex;gap:8px;margin-top:10px;align-items:center;flex-wrap:wrap">
      <button id="waQueueBtn" class="btn-primary">📋 Queue for approval</button>
      <button id="waAutoSendBtn" class="btn-secondary">⚡ Queue + auto-approve</button>
      <span id="waSendStatus" style="font-size:13px;color:#666"></span>
    </div>
  </div>

  <!-- Approval queue -->
  <div class="card" style="margin-top:16px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h3 style="margin:0">📋 Message Queue</h3>
      <button class="btn-secondary" style="font-size:12px" onclick="window._waLoadQueue()">🔄 Refresh</button>
    </div>
    <div id="waQueue"><em style="color:#9ca3af">No messages in queue.</em></div>
  </div>

  <!-- Config -->
  <div class="card" style="margin-top:16px">
    <h3 style="margin-top:0">⚙️ Send Policy</h3>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:12px">
      <label><b>Hourly limit</b><input id="waCfgHourly" type="number" min="1" max="50" value="10" style="width:100%;margin-top:4px"></label>
      <label><b>Daily limit</b><input id="waCfgDaily" type="number" min="1" max="300" value="80" style="width:100%;margin-top:4px"></label>
      <label><b>Timezone</b><input id="waCfgTz" type="text" value="UTC" style="width:100%;margin-top:4px"></label>
      <label><b>Quiet hours start (0-23)</b><input id="waCfgQS" type="number" min="0" max="23" value="22" style="width:100%;margin-top:4px"></label>
      <label><b>Quiet hours end (0-23)</b><input id="waCfgQE" type="number" min="0" max="23" value="8" style="width:100%;margin-top:4px"></label>
      <label style="display:flex;align-items:center;gap:8px;margin-top:28px">
        <input type="checkbox" id="waCfgEnabled"><b>Enabled</b>
      </label>
    </div>
    <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
      <input type="checkbox" id="waCfgAutoApprove">
      <span><b>Auto-approve</b> (send without manual review — use cautiously)</span>
    </label>
    <button id="waCfgSave" class="btn-secondary">💾 Save policy</button>
    <span id="waCfgStatus" style="font-size:13px;color:#666;margin-left:10px"></span>
  </div>

</div>`;
    document.querySelector("main") && document.querySelector("main").appendChild(panel);
    _initEvents(panel);
    _loadStatus();
    window._waLoadQueue = () => _loadQueue();
    window._waScaffold = () => _scaffold();
    window._waStartBridge = () => _startBridge();
    window._waRefreshStatus = () => _loadStatus();
  }

  async function api(path, body) {
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
    return r.json();
  }

  function _initEvents(panel) {
    panel.querySelector("#waQueueBtn").onclick    = () => _queueMsg(false);
    panel.querySelector("#waAutoSendBtn").onclick = () => _queueMsg(true);
    panel.querySelector("#waCfgSave").onclick     = () => _saveConfig(panel);
  }

  async function _loadStatus() {
    const data = await api("/api/whatsapp/status", {});
    const area = document.getElementById("waStatusArea");
    const setup = document.getElementById("waSetupCard");
    const qrCard = document.getElementById("waQrCard");
    if (!area) return;

    const bridge = data.bridge || {};
    const bstatus = bridge.status || "bridge_offline";
    const policy = data.policy || {};

    const statusColors = { connected: "#16a34a", qr: "#f59e0b", connecting: "#2563eb", disconnected: "#ef4444", bridge_offline: "#9ca3af", logged_out: "#ef4444" };
    const statusLabels = { connected: "✅ Connected", qr: "📱 Scan QR code", connecting: "🔄 Connecting…", disconnected: "❌ Disconnected", bridge_offline: "⚠️ Bridge offline", logged_out: "🚪 Logged out" };

    area.innerHTML = `
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:12px">
  <div style="background:#f8fafc;border-radius:8px;padding:10px;text-align:center">
    <div style="font-size:11px;color:#9ca3af">Bridge</div>
    <div style="font-size:14px;font-weight:700;color:${statusColors[bstatus]||"#374151"}">${statusLabels[bstatus]||bstatus}</div>
  </div>
  <div style="background:#f8fafc;border-radius:8px;padding:10px;text-align:center">
    <div style="font-size:11px;color:#9ca3af">Phone</div>
    <div style="font-size:13px;font-weight:600">${bridge.phone || "–"}</div>
  </div>
  <div style="background:#f8fafc;border-radius:8px;padding:10px;text-align:center">
    <div style="font-size:11px;color:#9ca3af">Sent today</div>
    <div style="font-size:18px;font-weight:700">${data.sent_today || 0} / ${data.daily_limit || 80}</div>
  </div>
  <div style="background:${policy.ok ? "#ecfdf5" : "#fff7ed"};border-radius:8px;padding:10px;text-align:center">
    <div style="font-size:11px;color:#9ca3af">Policy</div>
    <div style="font-size:13px;font-weight:600;color:${policy.ok ? "#16a34a" : "#f59e0b"}">${policy.ok ? "✅ Ready" : "⏸️ " + (policy.reason || "blocked")}</div>
  </div>
</div>`;

    // Show setup card if bridge offline and show instructions
    if (bstatus === "bridge_offline" && data.setup_instructions) {
      setup.style.display = "block";
      document.getElementById("waSetupText").textContent = data.setup_instructions;
    } else {
      setup.style.display = "none";
    }

    // Show QR if status is "qr"
    if (bstatus === "qr") {
      qrCard.style.display = "block";
      _loadQR();
    } else {
      qrCard.style.display = "none";
    }

    // Load config into form
    const cfg = data.config || {};
    _setVal("waCfgHourly", cfg.hourly_limit ?? 10);
    _setVal("waCfgDaily", cfg.daily_limit ?? 80);
    _setVal("waCfgTz", cfg.timezone ?? "UTC");
    _setVal("waCfgQS", cfg.quiet_start ?? 22);
    _setVal("waCfgQE", cfg.quiet_end ?? 8);
    const cb1 = document.getElementById("waCfgEnabled");
    if (cb1) cb1.checked = cfg.enabled ?? false;
    const cb2 = document.getElementById("waCfgAutoApprove");
    if (cb2) cb2.checked = cfg.auto_approve ?? false;

    _loadQueue();
  }

  async function _loadQR() {
    const data = await api("/api/whatsapp/qr", {});
    const disp = document.getElementById("waQrDisplay");
    if (!disp) return;
    if (data.qr) {
      disp.innerHTML = `<img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(data.qr)}" alt="QR Code" style="width:200px;height:200px">`;
    } else {
      disp.textContent = "QR not available yet. Run: cd whatsapp_bridge && node server.js";
    }
  }

  async function _loadQueue() {
    const container = document.getElementById("waQueue");
    if (!container) return;
    const data = await api("/api/whatsapp/queue/list", {});
    const msgs = (data.messages || []).filter(m => m.status !== "sent").slice(0, 20);
    if (!msgs.length) { container.innerHTML = `<em style="color:#9ca3af">No messages in queue.</em>`; return; }
    container.innerHTML = msgs.map(m => `
<div style="border:1px solid #e2e8f0;border-radius:6px;padding:10px;margin-bottom:8px">
  <div style="display:flex;justify-content:space-between;align-items:start">
    <div>
      <b>${_esc(m.phone)}</b>
      <span style="font-size:11px;background:${m.status==="pending"?"#fef9c3":m.status==="approved"?"#dcfce7":"#fee2e2"};padding:2px 6px;border-radius:4px;margin-left:8px">${m.status}</span>
    </div>
    <div style="display:flex;gap:6px">
      ${m.status === "pending" ? `<button class="btn-secondary" style="font-size:11px;color:#16a34a" onclick="window._waApprove('${m.id}')">✅ Approve</button>` : ""}
      <button class="btn-secondary" style="font-size:11px;color:#ef4444" onclick="window._waReject('${m.id}')">❌ Remove</button>
    </div>
  </div>
  <div style="font-size:13px;margin-top:6px;color:#374151">${_esc(m.message.substring(0, 120))}${m.message.length > 120 ? "…" : ""}</div>
  <div style="font-size:11px;color:#9ca3af;margin-top:4px">${m.queued_at}</div>
</div>`).join("");

    window._waApprove = async (id) => { await api("/api/whatsapp/approve", { id }); _loadQueue(); };
    window._waReject  = async (id) => { await api("/api/whatsapp/reject",  { id }); _loadQueue(); };
  }

  async function _queueMsg(autoApprove) {
    const phone   = document.getElementById("waPhone")?.value.trim();
    const message = document.getElementById("waMessage")?.value.trim();
    const leadId  = document.getElementById("waLeadId")?.value.trim();
    if (!phone || !message) { alert("Phone and message are required."); return; }
    const status = document.getElementById("waSendStatus");
    status.textContent = "⏳ Queuing…";
    const data = await api("/api/whatsapp/queue", { lead_id: leadId, phone, message, auto_approve: autoApprove });
    if (data.error) { status.textContent = "❌ " + data.error; return; }
    status.textContent = `✅ Queued (${autoApprove ? "auto-approved" : "pending approval"})`;
    document.getElementById("waMessage").value = "";
    _loadQueue();
    setTimeout(() => { status.textContent = ""; }, 3000);
  }

  async function _saveConfig(panel) {
    const btn = panel.querySelector("#waCfgSave");
    btn.disabled = true;
    await api("/api/whatsapp/config", {
      hourly_limit: parseInt(_getVal("waCfgHourly")) || 10,
      daily_limit:  parseInt(_getVal("waCfgDaily")) || 80,
      timezone:     _getVal("waCfgTz") || "UTC",
      quiet_start:  parseInt(_getVal("waCfgQS")) || 22,
      quiet_end:    parseInt(_getVal("waCfgQE")) || 8,
      enabled:      document.getElementById("waCfgEnabled")?.checked ?? false,
      auto_approve: document.getElementById("waCfgAutoApprove")?.checked ?? false,
    });
    panel.querySelector("#waCfgStatus").textContent = "✅ Saved";
    btn.disabled = false;
    setTimeout(() => { panel.querySelector("#waCfgStatus").textContent = ""; }, 2000);
    _loadStatus();
  }

  async function _scaffold() { await api("/api/whatsapp/scaffold", {}); alert("Bridge files created in whatsapp_bridge/. Run: cd whatsapp_bridge && npm install && node server.js"); }
  async function _startBridge() { await api("/api/whatsapp/start_bridge", {}); setTimeout(_loadStatus, 3000); }

  function _setVal(id, val) { const el = document.getElementById(id); if (el) el.value = val; }
  function _getVal(id) { return document.getElementById(id)?.value || ""; }
  function _esc(s) { return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }

  document.addEventListener("DOMContentLoaded", () => {
    const tabBtn = document.querySelector(`[data-tab="${TAB}"]`);
    if (!tabBtn) return;
    window.LF.bindTab(tabBtn, () => ensurePanel());
  });
})();
