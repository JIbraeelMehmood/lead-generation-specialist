/**
 * static/linkedin.js — LinkedIn automation config tab for LeadFinder.
 *
 * Provides setup guide and integration status for the LinkedIn companion
 * extension (linkedin-autopilot). The extension runs as a Chrome extension
 * that automates connection growth on LinkedIn. This tab lets users:
 * - See setup instructions
 * - Configure connection limits and delays
 * - View connection stats
 * - Export LinkedIn connections as leads
 */
(function () {
  'use strict';
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const store = (k, d, v) => { try { if (v !== undefined){ localStorage.setItem(k, JSON.stringify(v)); return v; } const x = localStorage.getItem(k); return x ? JSON.parse(x) : d; } catch(e){ return d; } };

  function mount() {
    const sec = document.createElement('section');
    sec.id = 'tab-linkedin';
    sec.hidden = true;
    sec.innerHTML = `
      <div class="card">
        <div class="card-title"><span class="icon">🔗</span> LinkedIn Automation</div>
        <p class="sub" style="margin-top:-4px;margin-bottom:16px">
          Grow your LinkedIn network automatically with the LeadFinder companion extension.
          Send connection requests with randomized delays, weekly limit protection, and anti-ban safety.
        </p>

        <!-- Status banner -->
        <div id="liStatus" style="margin-bottom:16px"></div>

        <!-- Setup guide -->
        <div class="card" style="margin-bottom:16px;background:var(--surface-2)">
          <div class="card-title" style="font-size:14px"><span class="icon" style="font-size:13px">📦</span> Setup Guide</div>
          <ol style="color:var(--ink-2);font-size:13.5px;line-height:2;padding-left:20px">
            <li>Open <code>chrome://extensions</code> in your browser</li>
            <li>Enable <b>Developer mode</b> (top right toggle)</li>
            <li>Click <b>Load unpacked</b> and select the <code>linkedin-autopilot/</code> folder from this project</li>
            <li>Open LinkedIn and navigate to <a href="https://www.linkedin.com/mynetwork/grow/" target="_blank">/mynetwork/grow/</a></li>
            <li>Click the extension icon and press <b>Start</b></li>
            <li>The extension will send connection requests with 8–16 second random delays</li>
          </ol>
          <div class="msg warn" style="margin-top:8px">
            <div>⚠️ LinkedIn limits: ~100 connections/week. The extension auto-pauses for 24h when the weekly limit is hit. Use responsibly.</div>
          </div>
        </div>

        <!-- Configuration -->
        <div class="card" style="margin-bottom:16px">
          <div class="card-title" style="font-size:14px"><span class="icon" style="font-size:13px">⚙️</span> Settings</div>
          <div class="grid-3">
            <div class="form-group">
              <label>Daily connection limit</label>
              <input id="liDailyLimit" type="number" value="20" min="1" max="100">
            </div>
            <div class="form-group">
              <label>Min delay (seconds)</label>
              <input id="liMinDelay" type="number" value="8" min="3" max="30">
            </div>
            <div class="form-group">
              <label>Max delay (seconds)</label>
              <input id="liMaxDelay" type="number" value="16" min="5" max="60">
            </div>
          </div>
          <div class="grid-2">
            <div class="form-group">
              <label>Connection note (optional)</label>
              <textarea id="liNote" placeholder="Hi, I'd like to connect…" style="min-height:60px"></textarea>
            </div>
            <div class="form-group">
              <label>Filter — only connect with</label>
              <select id="liFilter">
                <option value="">Anyone</option>
                <option value="founder">Founders / CEOs</option>
                <option value="owner">Business owners</option>
                <option value="marketing">Marketing managers</option>
                <option value="design">Designers</option>
              </select>
            </div>
          </div>
          <button class="btn sm primary" id="liSaveSettings">💾 Save Settings</button>
          <div id="liSettingsMsg"></div>
        </div>

        <!-- Stats -->
        <div class="card">
          <div class="card-title" style="font-size:14px"><span class="icon" style="font-size:13px">📊</span> Connection Stats</div>
          <div class="tally" id="liStats">
            <div><b id="liTotal">0</b><span>total connections</span></div>
            <div><b id="liToday">0</b><span>sent today</span></div>
            <div><b id="liWeek">0</b><span>this week</span></div>
            <div><b id="liAccepted">0</b><span>accepted</span></div>
          </div>
          <div class="toolbar" style="margin-top:12px">
            <div class="grow"></div>
            <button class="btn sm" id="liExportConnections">📥 Export as leads CSV</button>
            <button class="btn sm primary" id="liRefreshStats">🔄 Refresh</button>
          </div>
        </div>
      </div>
    `;

    const main = document.querySelector('.main-content') || document.querySelector('.wrap');
    if (main) main.appendChild(sec);

    // Load saved settings
    const cfg = store('lf-linkedin-cfg', { dailyLimit: 20, minDelay: 8, maxDelay: 16, note: '', filter: '' });
    $('#liDailyLimit').value = cfg.dailyLimit;
    $('#liMinDelay').value = cfg.minDelay;
    $('#liMaxDelay').value = cfg.maxDelay;
    $('#liNote').value = cfg.note;
    $('#liFilter').value = cfg.filter;

    // Save settings
    $('#liSaveSettings')?.addEventListener('click', () => {
      const newCfg = {
        dailyLimit: +$('#liDailyLimit').value,
        minDelay: +$('#liMinDelay').value,
        maxDelay: +$('#liMaxDelay').value,
        note: $('#liNote').value,
        filter: $('#liFilter').value,
      };
      store('lf-linkedin-cfg', null, newCfg);
      $('#liSettingsMsg').innerHTML = '<div class="msg ok">Settings saved.</div>';
      setTimeout(() => { const el = $('#liSettingsMsg'); if (el) el.innerHTML = ''; }, 3000);
      if (window.LF?.toast) window.LF.toast('LinkedIn settings saved', 'success');
    });

    // Refresh stats (reads from localStorage — the extension writes here)
    function refreshStats() {
      const stats = store('lf-linkedin-stats', { total: 0, today: 0, week: 0, accepted: 0, connections: [] });
      $('#liTotal').textContent = stats.total;
      $('#liToday').textContent = stats.today;
      $('#liWeek').textContent = stats.week;
      $('#liAccepted').textContent = stats.accepted;
    }

    $('#liRefreshStats')?.addEventListener('click', refreshStats);
    refreshStats();

    // Export connections as CSV leads
    $('#liExportConnections')?.addEventListener('click', () => {
      const stats = store('lf-linkedin-stats', { connections: [] });
      const cols = ['name', 'headline', 'profileUrl', 'connectedDate'];
      const header = cols.map(c => c.charAt(0).toUpperCase() + c.slice(1)).join(',');
      const rows = (stats.connections || []).map(c => cols.map(k => `"${String(c[k] || '').replace(/"/g, '""')}"`).join(','));
      const csv = [header, ...rows].join('\r\n');
      const blob = new Blob(['\ufeff' + csv], { type: 'text/csv' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'linkedin-connections.csv';
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
      if (window.LF?.toast) window.LF.toast('Exported LinkedIn connections', 'success');
    });

    // Check extension status
    const status = store('lf-linkedin-stats', null) ? 'active' : 'inactive';
    const statusEl = $('#liStatus');
    if (statusEl) {
      statusEl.innerHTML = status === 'active'
        ? '<div class="msg ok">Extension detected — LinkedIn automation is configured.</div>'
        : '<div class="msg info">Extension not yet detected. Follow the setup guide above to install it.</div>';
    }
  }

  // Create nav button
  function createNavButton() {
    const nav = document.querySelector('nav.sidebar');
    if (!nav) return;
    // Find the Outreach group
    const groups = nav.querySelectorAll('.nav-group');
    let outreachGroup = null;
    groups.forEach(g => {
      if (g.querySelector('.nav-group-label')?.textContent === 'Outreach') outreachGroup = g;
    });
    const b = document.createElement('button');
    b.className = 'nav-item';
    b.setAttribute('role', 'tab');
    b.dataset.tab = 'linkedin';
    b.innerHTML = '<span class="nav-icon">💼</span> LinkedIn';
    if (outreachGroup) outreachGroup.appendChild(b);
    else nav.appendChild(b);
    if (window.LF?.bindTab) window.LF.bindTab(b, null);
  }

  // Add tab metadata
  if (window.LF) {
    // Wait for LF to be ready
    setTimeout(() => {
      mount();
      createNavButton();
    }, 200);
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      setTimeout(() => { mount(); createNavButton(); }, 200);
    });
  }
})();
