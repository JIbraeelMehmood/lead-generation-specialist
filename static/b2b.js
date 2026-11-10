/**
 * static/b2b.js — B2B International Buyer Hunt tab
 *
 * Connects to backend b2b.py via /api/b2b/hunt and /api/b2b/email.
 * Displays dual-layer scored buyer leads with intent bands, contact info,
 * WhatsApp links, and bilingual email generation.
 */
(function () {
  /* ── Tab registration ──────────────────────────────────────────────── */
  const TAB_ID = "b2b";

  function ensurePanel() {
    if (document.getElementById("tab-b2b")) return;
    const panel = document.createElement("section");
    panel.id = "tab-b2b";
    panel.setAttribute("role", "tabpanel");
    panel.style.display = "none";
    panel.innerHTML = `
<div class="card" style="max-width:960px;margin:0 auto;">
  <h2 style="margin-top:0">🌍 B2B International Buyer Hunt</h2>
  <p style="color:#666;margin-top:0">Find genuine B2B buyers for your product across global markets.
  Uses dual-layer scoring: rule engine (11 filters) + AI deep analysis.</p>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
    <div>
      <label><b>Product / Keyword *</b>
        <input id="b2bKeyword" type="text" placeholder="e.g. scrap metal, solar panels, coffee beans"
          style="width:100%;margin-top:4px">
      </label>
    </div>
    <div>
      <label><b>Min. Intent Score (1–12)</b>
        <input id="b2bMinScore" type="number" value="5" min="1" max="12"
          style="width:100%;margin-top:4px">
      </label>
    </div>
  </div>

  <label><b>Target Markets (one per line) *</b>
    <textarea id="b2bMarkets" rows="3"
      placeholder="Mexico&#10;Peru&#10;Chile&#10;India&#10;Germany"
      style="width:100%;margin-top:4px;font-family:monospace"></textarea>
  </label>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0">
    <div>
      <label><b>Max results per market</b>
        <input id="b2bMax" type="number" value="20" min="5" max="50"
          style="width:100%;margin-top:4px">
      </label>
    </div>
    <div>
      <label><b>Your product name (for email)</b>
        <input id="b2bProduct" type="text" placeholder="optional — used for outreach email"
          style="width:100%;margin-top:4px">
      </label>
    </div>
  </div>

  <div style="display:flex;gap:8px;align-items:center;margin-bottom:16px">
    <button id="b2bHuntBtn" class="btn-primary">🔍 Hunt for Buyers</button>
    <button id="b2bClearBtn" class="btn-secondary">Clear</button>
    <span id="b2bStatus" style="color:#666;font-size:13px"></span>
  </div>

  <!-- Live SSE progress -->
  <div id="b2bProgress" style="display:none;margin-bottom:12px">
    <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:6px;padding:10px">
      <b>🔄 Searching…</b> <span id="b2bProgressMsg"></span>
      <div id="b2bProgressBar" style="height:4px;background:#0ea5e9;width:0%;margin-top:6px;border-radius:2px;transition:width 0.3s"></div>
    </div>
  </div>

  <!-- Results -->
  <div id="b2bResults"></div>
</div>`;
    document.querySelector("main") && document.querySelector("main").appendChild(panel);
    _initB2BEvents(panel);
  }

  /* ── API calls ──────────────────────────────────────────────────────── */
  async function apiPost(path, body) {
    const r = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return r.json();
  }

  /* ── SSE listener for live progress ────────────────────────────────── */
  let _sse = null;
  function startSSE(keyword) {
    if (_sse) { _sse.close(); _sse = null; }
    _sse = new EventSource("/api/events/stream");
    _sse.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data);
        if (ev.type === "b2b_lead_found") {
          const msg = document.getElementById("b2bProgressMsg");
          if (msg) msg.textContent = `Found: ${ev.data.name || "lead"} (score ${ev.data.score}/12) in ${ev.data.market || ""}`;
        }
        if (ev.type === "task_done" || ev.type === "b2b_hunt_done") {
          if (_sse) { _sse.close(); _sse = null; }
        }
      } catch (_) {}
    };
  }

  /* ── Hunt ───────────────────────────────────────────────────────────── */
  async function runHunt(panel) {
    const keyword = panel.querySelector("#b2bKeyword").value.trim();
    const marketsRaw = panel.querySelector("#b2bMarkets").value.trim();
    if (!keyword || !marketsRaw) {
      alert("Please enter a product keyword and at least one market.");
      return;
    }
    const markets = marketsRaw.split("\n").map(m => m.trim()).filter(Boolean);
    const minScore = parseInt(panel.querySelector("#b2bMinScore").value) || 5;
    const maxPerKeyword = parseInt(panel.querySelector("#b2bMax").value) || 20;

    const btn = panel.querySelector("#b2bHuntBtn");
    const status = panel.querySelector("#b2bStatus");
    const progress = panel.querySelector("#b2bProgress");
    const bar = panel.querySelector("#b2bProgressBar");

    btn.disabled = true;
    btn.textContent = "⏳ Hunting…";
    status.textContent = `Searching ${markets.length} market(s)…`;
    progress.style.display = "block";
    bar.style.width = "10%";

    startSSE(keyword);

    try {
      const data = await apiPost("/api/b2b/hunt", { keyword, markets, min_score: minScore, max_per_keyword: maxPerKeyword });
      bar.style.width = "100%";
      setTimeout(() => { progress.style.display = "none"; }, 1000);
      renderResults(panel, data.leads || [], keyword);
      status.textContent = `Found ${data.count || 0} buyers.`;
    } catch (err) {
      status.textContent = "Error: " + err.message;
      progress.style.display = "none";
    } finally {
      btn.disabled = false;
      btn.textContent = "🔍 Hunt for Buyers";
      if (_sse) { _sse.close(); _sse = null; }
    }
  }

  /* ── Render results ─────────────────────────────────────────────────── */
  function renderResults(panel, leads, keyword) {
    const container = panel.querySelector("#b2bResults");
    if (!leads.length) {
      container.innerHTML = `<p style="color:#888">No buyers found above the minimum score. Try lowering the Min. Intent Score or adding more markets.</p>`;
      return;
    }

    const bandColors = { extreme: "#fee2e2", high: "#fef3c7", medium: "#ecfdf5", low: "#f9fafb" };

    container.innerHTML = `
<div style="margin-bottom:8px">
  <b>${leads.length} buyer leads</b> found for "<em>${keyword}</em>"
  <button id="b2bAddAllBtn" class="btn-secondary" style="margin-left:12px;font-size:12px">➕ Add all to My List</button>
  <button id="b2bExportBtn" class="btn-secondary" style="margin-left:6px;font-size:12px">📥 Export CSV</button>
</div>
<table style="width:100%;border-collapse:collapse;font-size:13px">
  <thead>
    <tr style="background:#f1f5f9;text-align:left">
      <th style="padding:8px 6px">Score</th>
      <th style="padding:8px 6px">Company</th>
      <th style="padding:8px 6px">Market</th>
      <th style="padding:8px 6px">Contacts</th>
      <th style="padding:8px 6px">Tags</th>
      <th style="padding:8px 6px">Actions</th>
    </tr>
  </thead>
  <tbody id="b2bTbody">
  </tbody>
</table>`;

    const tbody = container.querySelector("#b2bTbody");
    leads.forEach((lead) => {
      const tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid #e2e8f0";
      tr.style.background = bandColors[lead.intent_band?.toLowerCase().includes("extreme") ? "extreme"
        : lead.intent_band?.includes("High") ? "high"
        : lead.intent_band?.includes("Medium") ? "medium" : "low"] || "#fff";

      const contacts = [
        lead.email ? `<a href="mailto:${lead.email}">${lead.email}</a>` : "",
        lead.phone ? `📞 ${lead.phone}` : "",
        lead.whatsapp_link ? `<a href="${lead.whatsapp_link}" target="_blank">💬 WhatsApp</a>` : "",
      ].filter(Boolean).join("<br>");

      tr.innerHTML = `
<td style="padding:8px 6px;font-weight:700;font-size:16px">${lead.score}/12</td>
<td style="padding:8px 6px">
  <a href="${lead.website}" target="_blank" style="font-weight:600">${_esc(lead.name)}</a>
  <div style="font-size:11px;color:#64748b;margin-top:2px">${_esc(lead.ai_reasoning || "")}</div>
</td>
<td style="padding:8px 6px">${_esc(lead.address || "")}</td>
<td style="padding:8px 6px">${contacts || "<span style='color:#999'>–</span>"}</td>
<td style="padding:8px 6px;font-size:12px">${(lead.tags || []).join(" ")}</td>
<td style="padding:8px 6px">
  <button class="btn-secondary b2b-add-btn" data-id="${lead.id}" style="font-size:11px;margin-bottom:4px">➕ Add</button>
  ${lead.email ? `<button class="btn-secondary b2b-email-btn" data-id="${lead.id}" style="font-size:11px">✉️ Draft email</button>` : ""}
</td>`;
      tbody.appendChild(tr);
    });

    // Store leads for buttons
    container._leads = leads;

    // Add all to My List
    container.querySelector("#b2bAddAllBtn").onclick = () => {
      window.LF && window.LF.addLeads && window.LF.addLeads(leads);
      alert(`Added ${leads.length} buyers to My List.`);
    };

    // Export CSV
    container.querySelector("#b2bExportBtn").onclick = () => exportCSV(leads, keyword);

    // Individual add buttons
    container.querySelectorAll(".b2b-add-btn").forEach(btn => {
      btn.onclick = () => {
        const lead = leads.find(l => l.id === btn.dataset.id);
        if (lead) {
          window.LF && window.LF.addLeads && window.LF.addLeads([lead]);
          btn.textContent = "✅ Added";
          btn.disabled = true;
        }
      };
    });

    // Email draft buttons
    container.querySelectorAll(".b2b-email-btn").forEach(btn => {
      btn.onclick = () => {
        const lead = leads.find(l => l.id === btn.dataset.id);
        if (!lead) return;
        const product = panel.querySelector("#b2bProduct").value.trim() || keyword;
        btn.disabled = true;
        btn.textContent = "⏳";
        apiPost("/api/b2b/email", { lead, product }).then(res => {
          btn.disabled = false;
          btn.textContent = "✉️ Draft email";
          if (res.subject) {
            showEmailModal(lead, res);
          } else {
            alert("Could not generate email: " + (res.error || "Unknown error"));
          }
        }).catch(() => { btn.disabled = false; btn.textContent = "✉️ Draft email"; });
      };
    });
  }

  /* ── Email modal ────────────────────────────────────────────────────── */
  function showEmailModal(lead, emailData) {
    let modal = document.getElementById("b2bEmailModal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "b2bEmailModal";
      modal.style.cssText = "position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center";
      document.body.appendChild(modal);
    }
    modal.innerHTML = `
<div style="background:#fff;border-radius:10px;padding:24px;width:600px;max-width:95vw;max-height:80vh;overflow-y:auto">
  <h3 style="margin-top:0">✉️ Draft email for ${_esc(lead.name)}</h3>
  <div style="margin-bottom:8px"><b>Language:</b> ${emailData.language || "English"}</div>
  <label><b>Subject</b>
    <input id="b2bEmailSubject" type="text" value="${_esc(emailData.subject || "")}"
      style="width:100%;margin-top:4px;margin-bottom:12px">
  </label>
  <label><b>Body</b>
    <textarea id="b2bEmailBody" rows="10" style="width:100%;font-family:monospace;font-size:13px">${_esc(emailData.body || "")}</textarea>
  </label>
  <div style="display:flex;gap:8px;margin-top:16px">
    <button id="b2bEmailCopy" class="btn-primary">📋 Copy to clipboard</button>
    <button id="b2bEmailClose" class="btn-secondary">Close</button>
  </div>
</div>`;
    modal.style.display = "flex";
    modal.querySelector("#b2bEmailClose").onclick = () => { modal.style.display = "none"; };
    modal.querySelector("#b2bEmailCopy").onclick = () => {
      const subject = modal.querySelector("#b2bEmailSubject").value;
      const body = modal.querySelector("#b2bEmailBody").value;
      navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`)
        .then(() => alert("Copied to clipboard!"));
    };
  }

  /* ── CSV export ─────────────────────────────────────────────────────── */
  function exportCSV(leads, keyword) {
    const headers = ["name", "website", "email", "phone", "whatsapp_link", "address",
      "score", "intent_band", "tags", "ai_reasoning"];
    const rows = [headers.join(",")];
    leads.forEach(l => {
      rows.push(headers.map(h => {
        let v = l[h];
        if (Array.isArray(v)) v = v.join("; ");
        v = String(v ?? "").replace(/"/g, '""');
        return `"${v}"`;
      }).join(","));
    });
    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `b2b-buyers-${keyword.replace(/\s+/g, "-")}-${Date.now()}.csv`;
    a.click();
  }

  /* ── Helpers ────────────────────────────────────────────────────────── */
  function _esc(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function _initB2BEvents(panel) {
    panel.querySelector("#b2bHuntBtn").onclick = () => runHunt(panel);
    panel.querySelector("#b2bClearBtn").onclick = () => {
      panel.querySelector("#b2bKeyword").value = "";
      panel.querySelector("#b2bMarkets").value = "";
      panel.querySelector("#b2bResults").innerHTML = "";
      panel.querySelector("#b2bStatus").textContent = "";
    };
  }

  /* ── Register tab ───────────────────────────────────────────────────── */
  document.addEventListener("DOMContentLoaded", () => {
    const tabBtn = document.querySelector(`[data-tab="${TAB_ID}"]`);
    if (!tabBtn) return;
    window.LF.bindTab(tabBtn, () => {
      ensurePanel();
    });
  });
})();
