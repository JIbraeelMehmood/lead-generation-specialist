/**
 * static/strategy.js — AI Strategy Generation tab
 *
 * Connects to backend strategy.py via /api/strategy/*.
 * Features:
 *   - Magic Auto-Fill: describe your business in plain English
 *   - 30-day plan with weekly milestones
 *   - 90-day scaling path
 *   - ICP definition + lead source recommendations
 *   - Hot/Warm/Cold qualification criteria
 *   - 3-step email sequence templates
 *   - Revenue potential estimates
 *   - Marketing brief generator from your website
 */
(function () {
  const TAB_ID = "strategy";

  function ensurePanel() {
    if (document.getElementById("tab-strategy")) return;
    const panel = document.createElement("section");
    panel.id = "tab-strategy";
    panel.setAttribute("role", "tabpanel");
    panel.style.display = "none";
    panel.innerHTML = `
<div style="max-width:960px;margin:0 auto">

  <div class="card">
    <h2 style="margin-top:0">🎯 AI Strategy Generator</h2>
    <p style="color:#666;margin-top:0">Describe your business in plain English and get a complete
    30-day lead generation plan, 90-day scaling strategy, ICP, lead sources, and revenue potential.</p>

    <!-- Auto-fill from description -->
    <div style="margin-bottom:16px">
      <label><b>✨ Magic Auto-Fill — describe your business in plain English</b>
        <textarea id="stratDesc" rows="2"
          placeholder="e.g. I'm a freelance web developer in Karachi, Pakistan targeting restaurants and salons. I build websites for $300–$800."
          style="width:100%;margin-top:4px"></textarea>
      </label>
      <button id="stratAutoFill" class="btn-secondary" style="margin-top:6px">✨ Auto-fill profile</button>
    </div>

    <hr style="border:none;border-top:1px solid #e2e8f0;margin:16px 0">

    <!-- Structured profile -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
      <label><b>Business type</b>
        <input id="sfBizType" type="text" placeholder="e.g. Web Development Agency"
          style="width:100%;margin-top:4px">
      </label>
      <label><b>Your primary service</b>
        <input id="sfService" type="text" placeholder="e.g. WordPress websites, SEO, logo design"
          style="width:100%;margin-top:4px">
      </label>
      <label><b>Target niche</b>
        <input id="sfNiche" type="text" placeholder="e.g. restaurants, dental clinics, real estate agents"
          style="width:100%;margin-top:4px">
      </label>
      <label><b>Target location</b>
        <input id="sfLocation" type="text" placeholder="e.g. Karachi, Pakistan or United Kingdom"
          style="width:100%;margin-top:4px">
      </label>
      <label><b>Price range</b>
        <input id="sfPrice" type="text" placeholder="e.g. $300–$1,000 per project"
          style="width:100%;margin-top:4px">
      </label>
      <label><b>Outreach language</b>
        <input id="sfLanguage" type="text" value="English"
          style="width:100%;margin-top:4px">
      </label>
    </div>
    <label style="display:block;margin-bottom:12px"><b>Your unique selling point (USP)</b>
      <input id="sfUSP" type="text" placeholder="e.g. 7-day delivery, mobile-first design, bilingual support"
        style="width:100%;margin-top:4px">
    </label>

    <div style="display:flex;gap:8px;align-items:center">
      <button id="stratGenBtn" class="btn-primary">🚀 Generate Strategy</button>
      <span id="stratStatus" style="color:#666;font-size:13px"></span>
    </div>
  </div>

  <!-- Marketing brief section -->
  <div class="card" style="margin-top:16px">
    <h3 style="margin-top:0">📄 Marketing Brief from Your Website</h3>
    <p style="color:#666;margin-top:0;font-size:14px">Enter your own website URL and AI will read it
    and generate a brief explaining who you are, what you offer, and what's proven — used in all outreach.</p>
    <div style="display:flex;gap:8px">
      <input id="briefUrl" type="text" placeholder="https://yourwebsite.com"
        style="flex:1">
      <button id="briefBtn" class="btn-secondary">📄 Generate Brief</button>
    </div>
    <div id="briefResult" style="margin-top:12px"></div>
  </div>

  <!-- Strategy output -->
  <div id="stratResult" style="margin-top:16px"></div>

  <!-- Saved strategies -->
  <div class="card" style="margin-top:16px">
    <h3 style="margin-top:0">📁 Saved Strategies</h3>
    <div id="stratList"><em style="color:#888">No saved strategies yet.</em></div>
  </div>

</div>`;
    document.querySelector("main") && document.querySelector("main").appendChild(panel);
    _initEvents(panel);
    loadStrategyList(panel);
  }

  /* ── API ─────────────────────────────────────────────────────────────── */
  async function apiPost(path, body) {
    const r = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return r.json();
  }

  /* ── Auto-fill ──────────────────────────────────────────────────────── */
  async function autoFill(panel) {
    const desc = panel.querySelector("#stratDesc").value.trim();
    if (!desc) return alert("Describe your business first.");
    const btn = panel.querySelector("#stratAutoFill");
    btn.disabled = true; btn.textContent = "⏳ Filling…";
    try {
      const data = await apiPost("/api/strategy/autofill", { description: desc });
      const p = data.profile || {};
      panel.querySelector("#sfBizType").value = p.business_type || "";
      panel.querySelector("#sfService").value = p.primary_service || "";
      panel.querySelector("#sfNiche").value = p.target_niche || "";
      panel.querySelector("#sfLocation").value = p.target_location || "";
      panel.querySelector("#sfPrice").value = p.price_range || "";
      panel.querySelector("#sfLanguage").value = p.language || "English";
      panel.querySelector("#sfUSP").value = p.usp || "";
    } catch (e) {
      alert("Auto-fill failed: " + e.message);
    } finally {
      btn.disabled = false; btn.textContent = "✨ Auto-fill profile";
    }
  }

  /* ── Generate strategy ──────────────────────────────────────────────── */
  async function generateStrategy(panel) {
    const profile = {
      business_type: panel.querySelector("#sfBizType").value.trim(),
      primary_service: panel.querySelector("#sfService").value.trim(),
      target_niche: panel.querySelector("#sfNiche").value.trim(),
      target_location: panel.querySelector("#sfLocation").value.trim(),
      price_range: panel.querySelector("#sfPrice").value.trim(),
      language: panel.querySelector("#sfLanguage").value.trim() || "English",
      usp: panel.querySelector("#sfUSP").value.trim(),
    };
    if (!profile.target_niche && !profile.business_type) {
      return alert("Please fill in at least your business type and target niche.");
    }
    const btn = panel.querySelector("#stratGenBtn");
    const status = panel.querySelector("#stratStatus");
    btn.disabled = true; btn.textContent = "⏳ Generating…";
    status.textContent = "AI is building your strategy (10–30 seconds)…";
    try {
      const data = await apiPost("/api/strategy/generate", { profile });
      if (data.error) {
        status.textContent = "Error: " + data.error;
      } else {
        renderStrategy(panel, data);
        status.textContent = "Strategy saved ✓";
        loadStrategyList(panel);
      }
    } catch (e) {
      status.textContent = "Error: " + e.message;
    } finally {
      btn.disabled = false; btn.textContent = "🚀 Generate Strategy";
    }
  }

  /* ── Render strategy ────────────────────────────────────────────────── */
  function renderStrategy(panel, s) {
    const container = panel.querySelector("#stratResult");

    const icp = s.icp || {};
    const src = (s.lead_sources || []).map(ls =>
      `<tr><td style="padding:6px 8px"><b>${_esc(ls.source)}</b></td>
       <td style="padding:6px 8px;font-family:monospace;font-size:12px">${_esc(ls.query)}</td>
       <td style="padding:6px 8px"><span style="background:${ls.priority==="high"?"#dcfce7":ls.priority==="medium"?"#fef9c3":"#f1f5f9"};padding:2px 6px;border-radius:4px;font-size:11px">${ls.priority}</span></td>
       <td style="padding:6px 8px;font-size:12px;color:#555">${_esc(ls.reason)}</td></tr>`
    ).join("");

    const qc = s.qualification_criteria || {};
    const d30 = s.day_30_plan || {};
    const weeks = ["week1","week2","week3","week4"].map(wk => {
      const w = d30[wk] || {};
      return `<div style="background:#f8fafc;border-radius:6px;padding:10px;margin-bottom:8px">
        <b>Week ${wk.replace("week","")}: ${_esc(w.focus || "")}</b> — target ${w.target_leads || 0} leads
        <ul style="margin:6px 0 0 20px;font-size:13px">${(w.tasks||[]).map(t=>`<li>${_esc(t)}</li>`).join("")}</ul>
      </div>`;
    }).join("");

    const d90 = s.day_90_plan || {};
    const seq = (s.email_sequence || []).map((step, i) =>
      `<div style="border:1px solid #e2e8f0;border-radius:6px;padding:10px;margin-bottom:8px">
        <div style="display:flex;justify-content:space-between">
          <b>Step ${step.step} — Day ${step.day}</b>
          <em style="font-size:12px;color:#64748b">${_esc(step.purpose||"")}</em>
        </div>
        <div style="margin-top:4px"><b>Subject:</b> ${_esc(step.subject||"")}</div>
        <div style="margin-top:4px;font-size:13px;color:#374151">${_esc(step.hook||"")}</div>
      </div>`
    ).join("");

    const rev = s.revenue_potential || {};
    const qw = (s.quick_wins || []).map(w => `<li>${_esc(w)}</li>`).join("");

    container.innerHTML = `
<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:start">
    <h2 style="margin-top:0">📊 Your Lead Generation Strategy</h2>
    <span style="font-size:12px;color:#94a3b8">${s.generated_at || ""}</span>
  </div>

  <!-- Quick wins -->
  <div style="background:#ecfdf5;border:1px solid #6ee7b7;border-radius:8px;padding:12px;margin-bottom:16px">
    <b>⚡ Quick Wins — Start Today</b>
    <ul style="margin:6px 0 0 20px;font-size:13px">${qw}</ul>
  </div>

  <!-- ICP -->
  <h3>👤 Ideal Customer Profile</h3>
  <p style="font-size:14px">${_esc(icp.description||"")}</p>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
    <div>
      <b style="color:#16a34a">🔥 Hot signals</b>
      <ul style="margin:6px 0 0 20px;font-size:13px">${(icp.hot_signals||[]).map(s=>`<li>${_esc(s)}</li>`).join("")}</ul>
    </div>
    <div>
      <b style="color:#94a3b8">❄️ Cold signals</b>
      <ul style="margin:6px 0 0 20px;font-size:13px">${(icp.cold_signals||[]).map(s=>`<li>${_esc(s)}</li>`).join("")}</ul>
    </div>
  </div>
  <p style="font-size:13px"><b>Company size:</b> ${_esc(icp.company_size||"")} &nbsp;|&nbsp;
  <b>Target titles:</b> ${(icp.target_job_titles||[]).join(", ")}</p>
  <p style="font-size:13px"><b>Pain points:</b> ${(icp.pain_points||[]).join(" · ")}</p>

  <!-- Lead sources -->
  <h3>🔍 Recommended Lead Sources</h3>
  <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:16px">
    <thead><tr style="background:#f1f5f9">
      <th style="padding:6px 8px;text-align:left">Source</th>
      <th style="padding:6px 8px;text-align:left">Query</th>
      <th style="padding:6px 8px;text-align:left">Priority</th>
      <th style="padding:6px 8px;text-align:left">Why</th>
    </tr></thead>
    <tbody>${src}</tbody>
  </table>

  <!-- Qualification -->
  <h3>🏷️ Lead Qualification Criteria</h3>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:16px">
    <div style="background:#fef9c3;border-radius:6px;padding:10px"><b>🔥 Hot</b><p style="font-size:13px;margin:4px 0">${_esc(qc.hot||"")}</p></div>
    <div style="background:#fef3c7;border-radius:6px;padding:10px"><b>🌡️ Warm</b><p style="font-size:13px;margin:4px 0">${_esc(qc.warm||"")}</p></div>
    <div style="background:#f1f5f9;border-radius:6px;padding:10px"><b>❄️ Cold</b><p style="font-size:13px;margin:4px 0">${_esc(qc.cold||"")}</p></div>
  </div>

  <!-- 30-day plan -->
  <h3>📅 30-Day Plan</h3>
  <p style="font-size:14px;font-weight:600;color:#0369a1">${_esc(d30.goal||"")}</p>
  ${weeks}
  <div style="margin-top:8px"><b>KPIs:</b> ${(d30.kpis||[]).join(" · ")}</div>

  <!-- 90-day plan -->
  <h3 style="margin-top:20px">🗓️ 90-Day Scaling Path</h3>
  <p style="font-size:14px;font-weight:600;color:#0369a1">${_esc(d90.goal||"")}</p>
  ${["month2","month3"].map(m => {
    const mo = d90[m] || {};
    return `<div style="background:#f0f9ff;border-radius:6px;padding:10px;margin-bottom:8px">
      <b>${m === "month2" ? "Month 2" : "Month 3"}:</b> ${_esc(mo.focus||"")}
      <div style="font-size:13px;color:#374151;margin-top:4px">${_esc(mo.strategy||"")} → <b>${_esc(mo.target||"")}</b></div>
    </div>`;
  }).join("")}
  <div><b>Scaling moves:</b><ul style="margin:6px 0 0 20px;font-size:13px">${(d90.scaling_moves||[]).map(x=>`<li>${_esc(x)}</li>`).join("")}</ul></div>

  <!-- Email sequence -->
  <h3 style="margin-top:20px">✉️ 3-Step Email Sequence</h3>
  ${seq}
  ${s.whatsapp_template ? `<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:6px;padding:10px;margin-top:8px">
    <b>💬 WhatsApp opener:</b>
    <div style="font-size:13px;margin-top:6px">${_esc(s.whatsapp_template)}</div>
  </div>` : ""}

  <!-- Revenue potential -->
  <h3 style="margin-top:20px">💰 Revenue Potential</h3>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px">
    <div style="background:#f1f5f9;border-radius:6px;padding:10px;text-align:center">
      <div style="font-size:11px;color:#64748b">Conservative</div>
      <div style="font-size:18px;font-weight:700;color:#374151">${_esc(rev.conservative||"–")}</div>
    </div>
    <div style="background:#ecfdf5;border-radius:6px;padding:10px;text-align:center">
      <div style="font-size:11px;color:#64748b">Realistic</div>
      <div style="font-size:18px;font-weight:700;color:#15803d">${_esc(rev.realistic||"–")}</div>
    </div>
    <div style="background:#fef9c3;border-radius:6px;padding:10px;text-align:center">
      <div style="font-size:11px;color:#64748b">Optimistic</div>
      <div style="font-size:18px;font-weight:700;color:#a16207">${_esc(rev.optimistic||"–")}</div>
    </div>
  </div>
  <p style="font-size:12px;color:#94a3b8">${_esc(rev.assumptions||"")}</p>
</div>`;
  }

  /* ── Marketing brief ─────────────────────────────────────────────────── */
  async function generateBrief(panel) {
    const url = panel.querySelector("#briefUrl").value.trim();
    if (!url) return alert("Enter your website URL.");
    const btn = panel.querySelector("#briefBtn");
    btn.disabled = true; btn.textContent = "⏳ Reading…";
    try {
      const data = await apiPost("/api/strategy/brief", { website: url });
      if (data.error) {
        panel.querySelector("#briefResult").innerHTML = `<p style="color:red">${_esc(data.error)}</p>`;
      } else {
        panel.querySelector("#briefResult").innerHTML = `
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px;font-size:14px">
  <h4 style="margin-top:0">${_esc(data.company_name||"")}</h4>
  <p><em>${_esc(data.tagline||"")}</em></p>
  <p><b>Who we are:</b> ${_esc(data.who_we_are||"")}</p>
  <p><b>What we offer:</b> ${(data.what_we_offer||[]).map(x=>_esc(x)).join(" · ")}</p>
  <p><b>Proven results:</b> ${(data.proven_results||[]).map(x=>_esc(x)).join(" · ")}</p>
  <p><b>Target customer:</b> ${_esc(data.target_customer||"")}</p>
  <p><b>Differentiators:</b> ${(data.differentiators||[]).map(x=>_esc(x)).join(" · ")}</p>
  <button class="btn-secondary" onclick="navigator.clipboard.writeText(${JSON.stringify(JSON.stringify(data))}).then(()=>alert('Copied!'))">📋 Copy JSON</button>
</div>`;
      }
    } catch(e) {
      panel.querySelector("#briefResult").innerHTML = `<p style="color:red">${e.message}</p>`;
    } finally {
      btn.disabled = false; btn.textContent = "📄 Generate Brief";
    }
  }

  /* ── Strategy list ───────────────────────────────────────────────────── */
  async function loadStrategyList(panel) {
    const container = panel.querySelector("#stratList");
    try {
      const data = await apiPost("/api/strategy/list", {});
      const strategies = data.strategies || [];
      if (!strategies.length) {
        container.innerHTML = `<em style="color:#888">No saved strategies yet.</em>`;
        return;
      }
      container.innerHTML = strategies.map(s => `
<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f1f5f9">
  <div>
    <b>${_esc(s.business_type||"Strategy")}</b> → ${_esc(s.target_niche||"")}
    <div style="font-size:12px;color:#94a3b8">${s.generated_at||""} &nbsp;|&nbsp; ${_esc(s.goal||"")}</div>
  </div>
  <div style="display:flex;gap:6px">
    <button class="btn-secondary strat-load-btn" data-id="${s.id}" style="font-size:11px">Load</button>
    <button class="btn-secondary strat-del-btn" data-id="${s.id}" style="font-size:11px;color:#ef4444">Delete</button>
  </div>
</div>`).join("");

      container.querySelectorAll(".strat-load-btn").forEach(btn => {
        btn.onclick = async () => {
          const data = await apiPost("/api/strategy/get", { id: btn.dataset.id });
          if (data) renderStrategy(panel, data);
          panel.querySelector("#stratResult").scrollIntoView({ behavior: "smooth" });
        };
      });
      container.querySelectorAll(".strat-del-btn").forEach(btn => {
        btn.onclick = async () => {
          if (!confirm("Delete this strategy?")) return;
          await apiPost("/api/strategy/delete", { id: btn.dataset.id });
          loadStrategyList(panel);
        };
      });
    } catch (e) {
      container.innerHTML = `<em style="color:red">${e.message}</em>`;
    }
  }

  /* ── Helpers ────────────────────────────────────────────────────────── */
  function _esc(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function _initEvents(panel) {
    panel.querySelector("#stratAutoFill").onclick = () => autoFill(panel);
    panel.querySelector("#stratGenBtn").onclick = () => generateStrategy(panel);
    panel.querySelector("#briefBtn").onclick = () => generateBrief(panel);
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
