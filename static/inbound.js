/**
 * static/inbound.js — Inbound Lead Capture & Onboarding tab
 *
 * Connects to backend inbound.py via /api/inbound/*.
 * Features:
 *   - Embeddable capture form (Name, Email, Profession, Goal)
 *   - Webhook URL display for external integrations (Typeform, Tally, etc.)
 *   - AI welcome email preview before saving config
 *   - Reply classifier — paste a reply, see its category
 *   - Config panel: SMTP, tone, your name/company
 *   - Recent inbound leads list
 */
(function () {
  const TAB_ID = "inbound";

  function ensurePanel() {
    if (document.getElementById("tab-inbound")) return;
    const panel = document.createElement("section");
    panel.id = "tab-inbound";
    panel.setAttribute("role", "tabpanel");
    panel.style.display = "none";
    panel.innerHTML = `
<div style="max-width:960px;margin:0 auto">

  <!-- Header -->
  <div class="card">
    <h2 style="margin-top:0">📥 Inbound Lead Capture & Onboarding</h2>
    <p style="color:#666;margin-top:0">When someone fills a form, responds to your outreach, or submits via a webhook,
    LeadFinder automatically logs them as a lead and sends a personalized AI welcome email.</p>

    <!-- Webhook URL -->
    <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:12px;margin-bottom:16px">
      <b>🔗 Webhook URL</b> — Point any external form here to auto-capture leads:
      <div style="display:flex;gap:8px;margin-top:8px">
        <code style="flex:1;background:#fff;padding:8px 12px;border-radius:6px;border:1px solid #e2e8f0;font-size:13px">
          http://localhost:8765/api/inbound/webhook
        </code>
        <button class="btn-secondary" onclick="navigator.clipboard.writeText('http://localhost:8765/api/inbound/webhook').then(()=>alert('Copied!'))">📋 Copy</button>
      </div>
      <div style="font-size:12px;color:#64748b;margin-top:6px">
        Works with: Typeform, Tally, Webflow Forms, GoHighLevel, Zapier, Make, n8n — any tool that can POST JSON.
      </div>
    </div>

    <!-- Manual capture form -->
    <h3 style="margin-bottom:12px">✍️ Manual Capture</h3>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
      <label><b>Name *</b><input id="ibName" type="text" placeholder="Jane Smith" style="width:100%;margin-top:4px"></label>
      <label><b>Email *</b><input id="ibEmail" type="email" placeholder="jane@example.com" style="width:100%;margin-top:4px"></label>
      <label><b>Profession / Role</b><input id="ibProfession" type="text" placeholder="Marketing Manager" style="width:100%;margin-top:4px"></label>
      <label><b>Company</b><input id="ibCompany" type="text" placeholder="Acme Corp" style="width:100%;margin-top:4px"></label>
    </div>
    <label style="display:block;margin-bottom:12px"><b>Goal / Message</b>
      <textarea id="ibGoal" rows="2" placeholder="What are they looking for or what did they say?" style="width:100%;margin-top:4px"></textarea>
    </label>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <button id="ibCaptureBtn" class="btn-primary">📥 Capture Lead</button>
      <button id="ibPreviewBtn" class="btn-secondary">👁️ Preview Welcome Email</button>
      <span id="ibStatus" style="font-size:13px;color:#666"></span>
    </div>
    <div id="ibEmailPreview" style="display:none;margin-top:16px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px;font-size:13px"></div>
  </div>

  <!-- Reply Classifier -->
  <div class="card" style="margin-top:16px">
    <h3 style="margin-top:0">🏷️ Reply Classifier</h3>
    <p style="color:#666;font-size:14px;margin-top:0">Paste a reply email to classify it: interested / referral / objection / unsubscribe / ooo / bounce</p>
    <label><b>Subject</b><input id="rcSubject" type="text" placeholder="RE: Quick question about your website" style="width:100%;margin-top:4px;margin-bottom:8px"></label>
    <label><b>Body</b>
      <textarea id="rcBody" rows="4" placeholder="Paste the reply email body here…" style="width:100%;margin-top:4px"></textarea>
    </label>
    <div style="display:flex;gap:8px;margin-top:10px;align-items:center">
      <button id="rcClassifyBtn" class="btn-secondary">🏷️ Classify</button>
      <div id="rcResult" style="font-size:14px;font-weight:600"></div>
    </div>
  </div>

  <!-- Config -->
  <div class="card" style="margin-top:16px">
    <h3 style="margin-top:0">⚙️ Welcome Email Config</h3>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
      <label><b>Your name</b><input id="cfName" type="text" placeholder="Your Name" style="width:100%;margin-top:4px"></label>
      <label><b>Your company</b><input id="cfCompany" type="text" placeholder="Your Company Name" style="width:100%;margin-top:4px"></label>
    </div>
    <label style="display:block;margin-bottom:12px"><b>Your service/product</b>
      <input id="cfService" type="text" placeholder="e.g. WordPress websites for restaurants" style="width:100%;margin-top:4px">
    </label>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
      <label><b>Subject line</b><input id="cfSubject" type="text" placeholder="Welcome! We received your message" style="width:100%;margin-top:4px"></label>
      <label><b>Tone</b>
        <select id="cfTone" style="width:100%;margin-top:4px">
          <option value="professional">Professional</option>
          <option value="friendly">Friendly</option>
          <option value="energetic">Energetic</option>
        </select>
      </label>
    </div>
    <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
      <input type="checkbox" id="cfAutoReply" checked>
      <span><b>Auto-send welcome email</b> (requires SMTP config in Settings)</span>
    </label>
    <button id="cfSaveBtn" class="btn-secondary">💾 Save Config</button>
    <span id="cfStatus" style="font-size:13px;color:#666;margin-left:10px"></span>
  </div>

  <!-- Recent inbound leads -->
  <div class="card" style="margin-top:16px">
    <h3 style="margin-top:0">📋 Recent Inbound Leads</h3>
    <div id="ibLeadsList"><em style="color:#888">No inbound leads yet.</em></div>
  </div>

</div>`;
    document.querySelector("main") && document.querySelector("main").appendChild(panel);
    _initEvents(panel);
    _loadConfig(panel);
    _loadLeads(panel);
  }

  async function api(path, body) {
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    return r.json();
  }

  function _initEvents(panel) {
    panel.querySelector("#ibCaptureBtn").onclick = () => _capture(panel, false);
    panel.querySelector("#ibPreviewBtn").onclick = () => _capture(panel, true);
    panel.querySelector("#rcClassifyBtn").onclick = () => _classify(panel);
    panel.querySelector("#cfSaveBtn").onclick = () => _saveConfig(panel);
  }

  async function _capture(panel, previewOnly) {
    const fields = {
      name:       panel.querySelector("#ibName").value.trim(),
      email:      panel.querySelector("#ibEmail").value.trim(),
      profession: panel.querySelector("#ibProfession").value.trim(),
      company:    panel.querySelector("#ibCompany").value.trim(),
      goal:       panel.querySelector("#ibGoal").value.trim(),
    };
    if (!fields.name && !fields.email) { alert("Enter at least a name or email."); return; }

    const btn = previewOnly ? panel.querySelector("#ibPreviewBtn") : panel.querySelector("#ibCaptureBtn");
    const status = panel.querySelector("#ibStatus");
    btn.disabled = true;
    status.textContent = previewOnly ? "Generating preview…" : "Capturing…";

    try {
      if (previewOnly) {
        const data = await api("/api/inbound/preview", { fields });
        const prev = panel.querySelector("#ibEmailPreview");
        prev.style.display = "block";
        prev.innerHTML = `<b>Subject:</b> ${_esc(data.subject)}<hr style="border:none;border-top:1px solid #e2e8f0;margin:8px 0"><pre style="white-space:pre-wrap;font-family:inherit;margin:0">${_esc(data.body)}</pre>`;
        status.textContent = "";
      } else {
        const data = await api("/api/inbound/capture", { ...fields, _source: "inbound:manual" });
        status.textContent = `✅ Lead captured${data.email_sent ? " + welcome email sent" : ""}`;
        _loadLeads(panel);
      }
    } catch (e) {
      status.textContent = "Error: " + e.message;
    } finally {
      btn.disabled = false;
    }
  }

  async function _classify(panel) {
    const subject = panel.querySelector("#rcSubject").value;
    const body    = panel.querySelector("#rcBody").value;
    const result  = panel.querySelector("#rcResult");
    result.textContent = "⏳ Classifying…";
    const data = await api("/api/inbound/classify", { text: subject + " " + body });
    const colors = { interested: "#16a34a", unsubscribe: "#ef4444", bounce: "#ef4444",
                     referral: "#2563eb", objection: "#f59e0b", ooo: "#6b7280", unknown: "#9ca3af" };
    const labels = { interested: "🎉 Interested", unsubscribe: "🛑 Unsubscribe",
                     bounce: "💔 Bounce", referral: "🔀 Referral",
                     objection: "🤔 Objection", ooo: "🏖️ Out of Office", unknown: "❓ Unknown" };
    result.style.color = colors[data.category] || "#374151";
    result.textContent = labels[data.category] || data.category;
  }

  async function _loadConfig(panel) {
    const data = await api("/api/inbound/config", {});
    const cfg = data.config || {};
    panel.querySelector("#cfName").value        = cfg.your_name || "";
    panel.querySelector("#cfCompany").value     = cfg.your_company || "";
    panel.querySelector("#cfService").value     = cfg.your_service || "";
    panel.querySelector("#cfSubject").value     = cfg.welcome_subject || "";
    panel.querySelector("#cfTone").value        = cfg.tone || "professional";
    panel.querySelector("#cfAutoReply").checked = cfg.auto_reply !== false;
  }

  async function _saveConfig(panel) {
    const btn = panel.querySelector("#cfSaveBtn");
    btn.disabled = true;
    await api("/api/inbound/config", {
      your_name:       panel.querySelector("#cfName").value.trim(),
      your_company:    panel.querySelector("#cfCompany").value.trim(),
      your_service:    panel.querySelector("#cfService").value.trim(),
      welcome_subject: panel.querySelector("#cfSubject").value.trim(),
      tone:            panel.querySelector("#cfTone").value,
      auto_reply:      panel.querySelector("#cfAutoReply").checked,
    });
    panel.querySelector("#cfStatus").textContent = "✅ Saved";
    btn.disabled = false;
    setTimeout(() => { panel.querySelector("#cfStatus").textContent = ""; }, 2000);
  }

  async function _loadLeads(panel) {
    const container = panel.querySelector("#ibLeadsList");
    const data = await api("/api/db/leads", { limit: 20 });
    const leads = (data.leads || []).filter(l => (l.source || "").startsWith("inbound"));
    if (!leads.length) { container.innerHTML = `<em style="color:#888">No inbound leads yet.</em>`; return; }
    container.innerHTML = leads.map(l => `
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:13px">
  <div>
    <b>${_esc(l.name)}</b> ${l.email ? `· <a href="mailto:${_esc(l.email)}">${_esc(l.email)}</a>` : ""}
    <div style="font-size:11px;color:#9ca3af">${_esc(l.notes || "")} · ${l.added_at || ""}</div>
  </div>
  <span style="color:#9ca3af;font-size:11px">${_esc(l.stage || "New")}</span>
</div>`).join("");
  }

  function _esc(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  document.addEventListener("DOMContentLoaded", () => {
    const tabBtn = document.querySelector(`[data-tab="${TAB_ID}"]`);
    if (!tabBtn) return;
    window.LF.bindTab(tabBtn, () => ensurePanel());
  });
})();
