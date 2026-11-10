/**
 * static/voice.js — AI Voice Call Agent tab
 * Connects to voice_agent.py via /api/voice/*.
 */
(function () {
  const TAB = "voice";

  function ensurePanel() {
    if (document.getElementById("tab-voice")) return;
    const p = document.createElement("section");
    p.id = "tab-voice"; p.setAttribute("role","tabpanel"); p.style.display = "none";
    p.innerHTML = `
<div style="max-width:960px;margin:0 auto">
  <div class="card">
    <h2 style="margin-top:0">📞 AI Voice Call Agent</h2>
    <p style="color:#666;margin-top:0">Uses n8n + Vapi + Twilio to call your leads, hold a real AI conversation, extract their email from speech, and log the transcript. Local businesses ignore emails — they answer the phone.</p>
    <div id="voiceStatusArea"><em style="color:#9ca3af">Loading…</em></div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px">

    <!-- Call a lead -->
    <div class="card">
      <h3 style="margin-top:0">📞 Call a Lead</h3>
      <label><b>Lead ID</b><input id="vcLeadId" type="text" placeholder="Lead ID from My List" style="width:100%;margin-top:4px;margin-bottom:10px"></label>
      <label><b>Phone number</b><input id="vcPhone" type="text" placeholder="+1 555 000 0000" style="width:100%;margin-top:4px;margin-bottom:10px"></label>
      <label><b>Lead name</b><input id="vcName" type="text" placeholder="Business name" style="width:100%;margin-top:4px;margin-bottom:10px"></label>
      <button id="vcCallBtn" class="btn-primary" style="width:100%">📞 Start Call</button>
      <div id="vcCallStatus" style="font-size:13px;color:#666;margin-top:8px"></div>
    </div>

    <!-- Config -->
    <div class="card">
      <h3 style="margin-top:0">⚙️ Configuration</h3>
      <label><b>Mode</b>
        <select id="vcMode" style="width:100%;margin-top:4px;margin-bottom:10px">
          <option value="n8n">n8n workflow (recommended)</option>
          <option value="vapi_direct">Vapi direct API</option>
        </select>
      </label>
      <label><b>n8n webhook URL</b><input id="vcN8n" type="text" placeholder="https://your-n8n.cloud/webhook/…" style="width:100%;margin-top:4px;margin-bottom:10px"></label>
      <label><b>Vapi API key (direct mode)</b><input id="vcVapi" type="text" placeholder="vapi_…" style="width:100%;margin-top:4px;margin-bottom:10px"></label>
      <label><b>Vapi Phone Number ID</b><input id="vcPhoneId" type="text" placeholder="phone-id from Vapi dashboard" style="width:100%;margin-top:4px;margin-bottom:10px"></label>
      <label><b>Your name / company</b><input id="vcYourName" type="text" placeholder="Alex from WebCo" style="width:100%;margin-top:4px;margin-bottom:10px"></label>
      <label style="display:flex;align-items:center;gap:8px;margin-bottom:10px"><input type="checkbox" id="vcEnabled"><b>Enable voice calling</b></label>
      <button id="vcSaveCfg" class="btn-secondary">💾 Save</button>
      <span id="vcCfgStatus" style="font-size:12px;color:#666;margin-left:8px"></span>
    </div>
  </div>

  <!-- Call log -->
  <div class="card" style="margin-top:16px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h3 style="margin:0">📋 Call Log</h3>
      <button class="btn-secondary" style="font-size:12px" onclick="window._vcLoadLog()">🔄 Refresh</button>
    </div>
    <div id="vcCallLog"><em style="color:#9ca3af">No calls yet.</em></div>
  </div>
</div>`;
    document.querySelector("main") && document.querySelector("main").appendChild(p);
    _init(p);
    _loadStatus(p);
    window._vcLoadLog = () => _loadLog();
  }

  async function api(path, body) {
    const r = await fetch(path, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body||{}) });
    return r.json();
  }

  function _init(p) {
    p.querySelector("#vcCallBtn").onclick = () => _placeCall(p);
    p.querySelector("#vcSaveCfg").onclick = () => _saveConfig(p);
  }

  async function _loadStatus(p) {
    const data = await api("/api/voice/status", {});
    const area = p.querySelector("#voiceStatusArea");
    area.innerHTML = `
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px">
  <div style="background:#f8fafc;border-radius:8px;padding:10px;text-align:center">
    <div style="font-size:11px;color:#9ca3af">Status</div>
    <div style="font-weight:700;color:${data.enabled?"#16a34a":"#f59e0b"}">${data.enabled?"✅ Enabled":"⚠️ Disabled"}</div>
  </div>
  <div style="background:#f8fafc;border-radius:8px;padding:10px;text-align:center">
    <div style="font-size:11px;color:#9ca3af">Mode</div>
    <div style="font-weight:600">${data.mode||"n8n"}</div>
  </div>
  <div style="background:#f8fafc;border-radius:8px;padding:10px;text-align:center">
    <div style="font-size:11px;color:#9ca3af">n8n</div>
    <div style="font-weight:600;color:${data.n8n_configured?"#16a34a":"#f59e0b"}">${data.n8n_configured?"✅":"⚠️ Not set"}</div>
  </div>
  <div style="background:#f8fafc;border-radius:8px;padding:10px;text-align:center">
    <div style="font-size:11px;color:#9ca3af">Calls today</div>
    <div style="font-size:18px;font-weight:700">${data.calls_today||0}</div>
  </div>
</div>`;

    const cfg = data.config || {};
    _setVal("vcMode", cfg.mode||"n8n");
    _setVal("vcN8n", cfg.n8n_webhook||"");
    _setVal("vcVapi", cfg.vapi_api_key||"");
    _setVal("vcPhoneId", cfg.vapi_phone_id||"");
    _setVal("vcYourName", (cfg.your_name||"") + (cfg.your_company ? " from "+cfg.your_company : ""));
    const cb = p.querySelector("#vcEnabled"); if (cb) cb.checked = cfg.enabled||false;
    _loadLog();
  }

  async function _placeCall(p) {
    const leadId = _getVal("vcLeadId");
    const phone  = _getVal("vcPhone");
    const name   = _getVal("vcName");
    if (!phone && !leadId) { alert("Enter a phone number or lead ID."); return; }
    const btn = p.querySelector("#vcCallBtn");
    btn.disabled = true; btn.textContent = "⏳ Calling…";
    const data = await api("/api/voice/call", { lead_id: leadId, lead: { phone, name } });
    p.querySelector("#vcCallStatus").textContent = data.ok ? `✅ Call started (${data.call_id})` : "❌ " + (data.error||"Failed");
    btn.disabled = false; btn.textContent = "📞 Start Call";
    setTimeout(() => _loadLog(), 3000);
  }

  async function _saveConfig(p) {
    const name_co = _getVal("vcYourName").split(" from ");
    await api("/api/voice/config", {
      mode:              _getVal("vcMode"),
      n8n_webhook:       _getVal("vcN8n"),
      vapi_api_key:      _getVal("vcVapi"),
      vapi_phone_id:     _getVal("vcPhoneId"),
      your_name:         name_co[0]||"",
      your_company:      name_co[1]||"",
      enabled:           p.querySelector("#vcEnabled")?.checked||false,
    });
    p.querySelector("#vcCfgStatus").textContent = "✅ Saved";
    setTimeout(() => { p.querySelector("#vcCfgStatus").textContent = ""; }, 2000);
  }

  async function _loadLog() {
    const c = document.getElementById("vcCallLog"); if (!c) return;
    const data = await api("/api/voice/calls", { limit: 20 });
    const calls = data.calls||[];
    if (!calls.length) { c.innerHTML = `<em style="color:#9ca3af">No calls yet.</em>`; return; }
    const oc = { answered_interested:"#16a34a", answered_not_interested:"#f59e0b", no_answer:"#9ca3af", error:"#ef4444" };
    c.innerHTML = calls.map(cl => `
<div style="border:1px solid #e2e8f0;border-radius:6px;padding:10px;margin-bottom:8px;font-size:13px">
  <div style="display:flex;justify-content:space-between">
    <b>${_esc(cl.lead_name||cl.phone)}</b>
    <span style="color:${oc[cl.outcome]||"#6b7280"};font-size:12px">${cl.outcome||cl.status}</span>
  </div>
  ${cl.email_extracted ? `<div style="color:#059669;margin-top:4px">📧 ${_esc(cl.email_extracted)}</div>` : ""}
  ${cl.summary ? `<div style="color:#374151;margin-top:4px">${_esc(cl.summary.substring(0,120))}</div>` : ""}
  <div style="color:#9ca3af;font-size:11px;margin-top:4px">${cl.queued_at||""}</div>
</div>`).join("");
  }

  function _setVal(id, v) { const e = document.getElementById(id); if (e) e.value = v; }
  function _getVal(id) { return document.getElementById(id)?.value||""; }
  function _esc(s) { return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

  document.addEventListener("DOMContentLoaded", () => {
    const btn = document.querySelector(`[data-tab="${TAB}"]`);
    if (!btn) return;
    window.LF.bindTab(btn, () => ensurePanel());
  });
})();
