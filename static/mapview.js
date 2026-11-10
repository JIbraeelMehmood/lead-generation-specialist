/**
 * static/mapview.js — Interactive Map Discovery UI
 *
 * Ported from Google-Maps-Lead-Generation (Mapleads) page.js.
 * Uses the Google Maps JavaScript API (no React/Next.js needed).
 *
 * Features (mirrors Mapleads exactly):
 *   - Full-screen map with click-to-drop-pin
 *   - Radius circle drawn at selected km radius
 *   - Slide-in search panel (keyword, radius, filters)
 *   - Results bottom sheet (expandable, sortable)
 *   - Per-lead "Deep scan" button → calls /api/enrich/full
 *   - Add to My List → calls db.upsert_lead via /api/db/upsert
 *   - CSV export
 *   - Location search box (autocomplete)
 *
 * Requires: Google Maps API key set in Settings (google key).
 * The <script> tag that loads the Google Maps JS API is injected dynamically
 * when the tab is first shown, using the key from /api/health.
 */
(function () {
  const TAB_ID = "mapview";

  let _map = null;
  let _marker = null;
  let _circle = null;
  let _point = null;       // { lat, lng }
  let _leads = [];
  let _panelExpanded = true;
  let _apiLoaded = false;

  /* ── Tab registration ──────────────────────────────────────────────── */

  function ensurePanel() {
    if (document.getElementById("tab-mapview")) return;
    const panel = document.createElement("section");
    panel.id = "tab-mapview";
    panel.setAttribute("role", "tabpanel");
    panel.style.display = "none";
    panel.innerHTML = `
<div style="position:relative;height:calc(100vh - 60px);min-height:500px;overflow:hidden">

  <!-- Map canvas -->
  <div id="mapCanvas" style="position:absolute;inset:0;background:#e5e7eb">
    <div id="mapLoading" style="display:flex;align-items:center;justify-content:center;height:100%;flex-direction:column;gap:12px">
      <div style="font-size:48px">🗺️</div>
      <div id="mapLoadMsg" style="font-size:14px;color:#6b7280">Loading map…</div>
    </div>
  </div>

  <!-- Top bar -->
  <div style="position:absolute;top:12px;left:12px;right:12px;z-index:20;display:flex;gap:8px;align-items:center;flex-wrap:wrap;pointer-events:none">
    <div id="mapTopInfo" style="background:rgba(255,255,255,0.97);padding:8px 14px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.15);font-size:13px;pointer-events:auto">
      <b>🗺️ Map Discovery</b>
      <span style="color:#6b7280;margin-left:8px" id="mapHint">Click anywhere on the map to drop a search pin</span>
    </div>
    <input id="mapSearchBox" type="text" placeholder="🔍 Search address or city…"
      style="flex:1;min-width:200px;padding:8px 12px;border-radius:8px;border:1px solid #d1d5db;font-size:13px;box-shadow:0 2px 8px rgba(0,0,0,0.1);pointer-events:auto"
      title="Type an address and press Enter to jump to it">
    <button id="mapEditBtn" class="btn-primary" style="pointer-events:auto;white-space:nowrap" onclick="window._mapOpenPanel()">
      ⚙️ Search settings
    </button>
  </div>

  <!-- Slide-in search panel -->
  <div id="mapPanel" style="position:absolute;top:0;right:0;bottom:0;width:320px;background:#fff;box-shadow:-4px 0 20px rgba(0,0,0,0.15);z-index:30;transform:translateX(100%);transition:transform 0.25s ease;overflow-y:auto;padding:20px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h3 style="margin:0">Search Settings</h3>
      <button onclick="window._mapClosePanel()" style="background:none;border:none;font-size:20px;cursor:pointer;color:#6b7280">✕</button>
    </div>

    <label style="display:block;margin-bottom:10px"><b>Keyword *</b>
      <input id="mpKeyword" type="text" placeholder="e.g. restaurant, dentist, plumber"
        style="width:100%;margin-top:4px">
    </label>

    <label style="display:block;margin-bottom:10px"><b>Radius: <span id="mpRadiusLabel">10</span> km</b>
      <input id="mpRadius" type="range" min="1" max="50" value="10"
        style="width:100%;margin-top:4px"
        oninput="document.getElementById('mpRadiusLabel').textContent=this.value">
    </label>

    <label style="display:block;margin-bottom:10px"><b>Max results</b>
      <select id="mpMax" style="width:100%;margin-top:4px">
        <option value="20">20</option>
        <option value="40">40</option>
        <option value="60" selected>60</option>
      </select>
    </label>

    <label style="display:block;margin-bottom:10px"><b>Source</b>
      <select id="mpSource" style="width:100%;margin-top:4px">
        <option value="google">Google Places API</option>
        <option value="serpapi">SerpApi</option>
        <option value="osm">OpenStreetMap (free)</option>
      </select>
    </label>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px">
      <label style="display:flex;align-items:center;gap:6px;font-size:13px">
        <input type="checkbox" id="mpHasWebsite"> Has website
      </label>
      <label style="display:flex;align-items:center;gap:6px;font-size:13px">
        <input type="checkbox" id="mpNoWebsite"> No website
      </label>
      <label style="display:flex;align-items:center;gap:6px;font-size:13px">
        <input type="checkbox" id="mpHasPhone"> Has phone
      </label>
      <label style="display:flex;align-items:center;gap:6px;font-size:13px">
        <input type="checkbox" id="mpOpenNow"> Open now
      </label>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px">
      <label style="display:block"><b>Min rating</b>
        <input id="mpMinRating" type="number" min="0" max="5" step="0.5" value="0"
          style="width:100%;margin-top:4px">
      </label>
      <label style="display:block"><b>Min reviews</b>
        <input id="mpMinReviews" type="number" min="0" value="0"
          style="width:100%;margin-top:4px">
      </label>
    </div>

    <div id="mapPanelStatus" style="font-size:12px;color:#6b7280;margin-bottom:10px"></div>
    <button id="mpSearchBtn" class="btn-primary" style="width:100%" onclick="window._mapRunSearch()">
      🔍 Search this area
    </button>
    <div id="mpSearchErr" style="color:#ef4444;font-size:12px;margin-top:8px"></div>
  </div>

  <!-- Results bottom sheet -->
  <div id="mapSheet" style="position:absolute;inset-x:0;bottom:0;z-index:25;background:#fff;border-radius:12px 12px 0 0;box-shadow:0 -4px 20px rgba(0,0,0,0.15);display:none;flex-direction:column;max-height:55%">
    <!-- Sheet handle -->
    <div id="mapSheetHandle" style="display:flex;align-items:center;justify-content:space-between;padding:0 20px;height:52px;border-bottom:1px solid #f1f5f9;cursor:pointer;flex-shrink:0"
      onclick="window._mapToggleSheet()">
      <span style="font-size:14px;font-weight:600" id="mapSheetTitle">0 leads found</span>
      <div style="display:flex;gap:8px;align-items:center">
        <button class="btn-secondary" style="font-size:12px" onclick="event.stopPropagation();window._mapExportCSV()">📥 CSV</button>
        <button class="btn-secondary" style="font-size:12px" onclick="event.stopPropagation();window._mapAddAll()">➕ Add all</button>
        <span id="mapSheetChevron" style="font-size:18px;color:#9ca3af">▲</span>
      </div>
    </div>
    <!-- Sheet body -->
    <div id="mapSheetBody" style="overflow-y:auto;flex:1"></div>
  </div>

</div>`;

    document.querySelector("main") && document.querySelector("main").appendChild(panel);
    _initMapPanelEvents();
  }

  /* ── Load Google Maps JS API dynamically ───────────────────────────── */

  function loadGoogleMapsAPI(apiKey) {
    return new Promise((resolve, reject) => {
      if (window.google && window.google.maps) { resolve(); return; }
      window._gm_callback = resolve;
      const s = document.createElement("script");
      s.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places&callback=_gm_callback`;
      s.async = true;
      s.onerror = () => reject(new Error("Failed to load Google Maps API"));
      document.head.appendChild(s);
    });
  }

  async function initMap(apiKey) {
    const canvas = document.getElementById("mapCanvas");
    if (!canvas) return;
    const msg = document.getElementById("mapLoadMsg");

    try {
      if (msg) msg.textContent = "Loading Google Maps…";
      await loadGoogleMapsAPI(apiKey);
      _apiLoaded = true;

      // Clear loading state
      const loading = document.getElementById("mapLoading");
      if (loading) loading.remove();

      _map = new google.maps.Map(canvas, {
        center: { lat: 30.3753, lng: 69.3451 }, // Pakistan center — fits most users
        zoom: 11,
        disableDefaultUI: true,
        zoomControl: true,
        gestureHandling: "greedy",
      });

      // Try to geolocate user
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (pos) => _map.setCenter({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
          () => {}
        );
      }

      _map.addListener("click", (e) => {
        const lat = e.latLng.lat();
        const lng = e.latLng.lng();
        _dropPin(lat, lng);
        window._mapOpenPanel();
      });

      // Address search box
      const searchBox = document.getElementById("mapSearchBox");
      if (searchBox) {
        const autocomplete = new google.maps.places.Autocomplete(searchBox);
        autocomplete.addListener("place_changed", () => {
          const place = autocomplete.getPlace();
          if (place.geometry) {
            _map.setCenter(place.geometry.location);
            _map.setZoom(13);
            _dropPin(place.geometry.location.lat(), place.geometry.location.lng());
            window._mapOpenPanel();
          }
        });
        searchBox.addEventListener("keydown", (e) => {
          if (e.key === "Enter") e.stopPropagation();
        });
      }

    } catch (err) {
      if (msg) msg.textContent = "⚠️ " + (err.message || "Could not load map. Check your Google API key in Settings.");
    }
  }

  function _dropPin(lat, lng) {
    _point = { lat, lng };
    if (_marker) _marker.setMap(null);
    _marker = new google.maps.Marker({ position: { lat, lng }, map: _map });
    _updateCircle();
    document.getElementById("mapHint").textContent = `Pin dropped at ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    document.getElementById("mapPanelStatus").textContent = `Pin: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  }

  function _updateCircle() {
    if (!_point || !_map) return;
    const radius = parseInt(document.getElementById("mpRadius")?.value || 10) * 1000;
    if (_circle) _circle.setMap(null);
    _circle = new google.maps.Circle({
      map: _map,
      center: _point,
      radius: radius,
      strokeColor: "#2563eb",
      strokeOpacity: 0.6,
      strokeWeight: 2,
      fillColor: "#2563eb",
      fillOpacity: 0.08,
    });
  }

  document.getElementById && document.addEventListener("DOMContentLoaded", () => {
    // Update circle when radius slider changes
    const slider = document.getElementById("mpRadius");
    if (slider) slider.addEventListener("input", _updateCircle);
  });

  /* ── Panel open/close ──────────────────────────────────────────────── */

  window._mapOpenPanel = function () {
    const panel = document.getElementById("mapPanel");
    if (panel) panel.style.transform = "translateX(0)";
  };

  window._mapClosePanel = function () {
    const panel = document.getElementById("mapPanel");
    if (panel) panel.style.transform = "translateX(100%)";
  };

  /* ── Run search ────────────────────────────────────────────────────── */

  window._mapRunSearch = async function () {
    const keyword = document.getElementById("mpKeyword")?.value.trim();
    if (!_point) {
      document.getElementById("mpSearchErr").textContent = "Click on the map to drop a pin first.";
      return;
    }
    if (!keyword) {
      document.getElementById("mpSearchErr").textContent = "Enter a keyword first.";
      return;
    }

    const btn = document.getElementById("mpSearchBtn");
    const err = document.getElementById("mpSearchErr");
    btn.disabled = true;
    btn.textContent = "⏳ Searching…";
    err.textContent = "";

    const body = {
      source: document.getElementById("mpSource")?.value || "google",
      query: keyword,
      location: `${_point.lat},${_point.lng}`,
      lat: _point.lat,
      lng: _point.lng,
      radius: parseInt(document.getElementById("mpRadius")?.value || 10) * 1000,
      pages: Math.ceil(parseInt(document.getElementById("mpMax")?.value || 60) / 20),
      hasWebsite: document.getElementById("mpHasWebsite")?.checked,
      noWebsite:  document.getElementById("mpNoWebsite")?.checked,
      hasPhone:   document.getElementById("mpHasPhone")?.checked,
      openNow:    document.getElementById("mpOpenNow")?.checked,
      minRating:  parseFloat(document.getElementById("mpMinRating")?.value || 0),
      minReviews: parseInt(document.getElementById("mpMinReviews")?.value || 0),
    };

    try {
      const r = await fetch("/api/search", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || "Search failed");

      let leads = data.leads || [];

      // Apply client-side filters
      if (body.hasWebsite)  leads = leads.filter(l => l.website);
      if (body.noWebsite)   leads = leads.filter(l => !l.website);
      if (body.hasPhone)    leads = leads.filter(l => l.phone);
      if (body.minRating)   leads = leads.filter(l => (l.rating || 0) >= body.minRating);
      if (body.minReviews)  leads = leads.filter(l => (l.reviews || 0) >= body.minReviews);

      // Drop pins on the map
      _placeLeadMarkers(leads);

      _leads = leads;
      _renderSheet(leads);
      window._mapClosePanel();

    } catch (e) {
      err.textContent = e.message;
    } finally {
      btn.disabled = false;
      btn.textContent = "🔍 Search this area";
    }
  };

  /* ── Lead markers on map ───────────────────────────────────────────── */

  const _leadMarkers = [];

  function _placeLeadMarkers(leads) {
    _leadMarkers.forEach(m => m.setMap(null));
    _leadMarkers.length = 0;
    leads.forEach(lead => {
      if (lead.lat && lead.lng) {
        const m = new google.maps.Marker({
          position: { lat: lead.lat, lng: lead.lng },
          map: _map,
          title: lead.name,
          icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 7,
            fillColor: lead.score >= 70 ? "#16a34a" : lead.score >= 40 ? "#f59e0b" : "#6b7280",
            fillOpacity: 0.9,
            strokeColor: "#fff",
            strokeWeight: 1.5,
          },
        });
        m.addListener("click", () => _highlightLead(lead.id || lead.place_id || ""));
        _leadMarkers.push(m);
      }
    });
  }

  function _highlightLead(id) {
    const sheet = document.getElementById("mapSheetBody");
    if (!sheet) return;
    const row = sheet.querySelector(`[data-lead-id="${id}"]`);
    if (row) {
      row.scrollIntoView({ behavior: "smooth", block: "center" });
      row.style.background = "#fef9c3";
      setTimeout(() => { row.style.background = ""; }, 2000);
    }
  }

  /* ── Results sheet ─────────────────────────────────────────────────── */

  function _renderSheet(leads) {
    const sheet = document.getElementById("mapSheet");
    const title = document.getElementById("mapSheetTitle");
    const body = document.getElementById("mapSheetBody");
    if (!sheet || !body) return;

    title.textContent = `${leads.length} lead${leads.length !== 1 ? "s" : ""} found`;
    sheet.style.display = "flex";
    sheet.style.maxHeight = "55%";

    if (!leads.length) {
      body.innerHTML = `<p style="padding:20px;color:#6b7280;text-align:center">No leads matched the filters. Try a broader search.</p>`;
      return;
    }

    body.innerHTML = `
<table style="width:100%;border-collapse:collapse;font-size:13px">
  <thead><tr style="background:#f8fafc;position:sticky;top:0">
    <th style="padding:8px 12px;text-align:left;border-bottom:1px solid #e2e8f0">Business</th>
    <th style="padding:8px 6px;text-align:center">⭐</th>
    <th style="padding:8px 6px;text-align:center">📞</th>
    <th style="padding:8px 6px;text-align:center">🌐</th>
    <th style="padding:8px 12px;text-align:left">Actions</th>
  </tr></thead>
  <tbody id="mapLeadTbody"></tbody>
</table>`;

    const tbody = body.querySelector("#mapLeadTbody");
    leads.forEach(lead => {
      const lid = lead.id || lead.place_id || "";
      const tr = document.createElement("tr");
      tr.setAttribute("data-lead-id", lid);
      tr.style.borderBottom = "1px solid #f1f5f9";
      tr.style.transition = "background 0.3s";
      tr.innerHTML = `
<td style="padding:8px 12px">
  <div style="font-weight:600">${_esc(lead.name || "")}</div>
  <div style="font-size:11px;color:#9ca3af">${_esc(lead.category || "")} · ${_esc((lead.address || "").substring(0, 40))}</div>
</td>
<td style="padding:8px 6px;text-align:center">
  ${lead.rating ? `<span style="color:#f59e0b">${lead.rating}★</span> <span style="font-size:11px;color:#9ca3af">(${lead.reviews || 0})</span>` : "<span style='color:#d1d5db'>–</span>"}
</td>
<td style="padding:8px 6px;text-align:center">
  ${lead.phone ? `<a href="tel:${_esc(lead.phone)}" style="font-size:12px">📞</a>` : "<span style='color:#d1d5db'>–</span>"}
</td>
<td style="padding:8px 6px;text-align:center">
  ${lead.website ? `<a href="${_esc(lead.website)}" target="_blank" style="font-size:12px">🌐</a>` : "<span style='color:#d1d5db'>–</span>"}
</td>
<td style="padding:8px 12px">
  <div style="display:flex;gap:4px;flex-wrap:wrap">
    <button class="btn-secondary map-add-btn" data-id="${lid}" style="font-size:11px">➕ Add</button>
    <button class="btn-secondary map-enrich-btn" data-id="${lid}" style="font-size:11px">🔍 Enrich</button>
  </div>
  <div class="map-enrich-result" data-id="${lid}" style="font-size:11px;color:#059669;margin-top:4px"></div>
</td>`;
      tbody.appendChild(tr);
    });

    // Add individual buttons
    tbody.querySelectorAll(".map-add-btn").forEach(btn => {
      btn.onclick = () => {
        const lead = leads.find(l => (l.id || l.place_id || "") === btn.dataset.id);
        if (lead) {
          _saveLead(lead);
          btn.textContent = "✅ Added";
          btn.disabled = true;
        }
      };
    });

    tbody.querySelectorAll(".map-enrich-btn").forEach(btn => {
      btn.onclick = async () => {
        const lead = leads.find(l => (l.id || l.place_id || "") === btn.dataset.id);
        if (!lead) return;
        btn.disabled = true; btn.textContent = "⏳";
        try {
          const r = await fetch("/api/enrich/full", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lead }),
          });
          const data = await r.json();
          const resultEl = document.querySelector(`.map-enrich-result[data-id="${btn.dataset.id}"]`);
          if (resultEl) {
            const parts = [];
            if (data.emails_found?.length) parts.push("📧 " + data.emails_found[0]);
            if (data.decision_maker?.name) parts.push("👤 " + data.decision_maker.name);
            if (data.social_handles?.whatsapp) parts.push("💬 WhatsApp");
            if (data.tech_stack?.length) parts.push("⚙️ " + data.tech_stack.slice(0, 2).join(", "));
            resultEl.textContent = parts.join(" · ") || "No extra data found";
          }
        } catch (e) {
          const resultEl = document.querySelector(`.map-enrich-result[data-id="${btn.dataset.id}"]`);
          if (resultEl) resultEl.textContent = "Error: " + e.message;
        } finally {
          btn.disabled = false; btn.textContent = "🔍 Enrich";
        }
      };
    });
  }

  /* ── Sheet toggle ──────────────────────────────────────────────────── */

  window._mapToggleSheet = function () {
    _panelExpanded = !_panelExpanded;
    const sheet = document.getElementById("mapSheet");
    const chevron = document.getElementById("mapSheetChevron");
    if (sheet) sheet.style.maxHeight = _panelExpanded ? "55%" : "52px";
    if (chevron) chevron.textContent = _panelExpanded ? "▲" : "▼";
  };

  /* ── Add all / Export CSV ──────────────────────────────────────────── */

  window._mapAddAll = function () {
    if (!_leads.length) return;
    _leads.forEach(_saveLead);
    alert(`Added ${_leads.length} leads to My List.`);
  };

  window._mapExportCSV = function () {
    if (!_leads.length) return;
    const headers = ["name", "category", "address", "phone", "website", "email", "rating", "reviews"];
    const rows = [headers.join(","),
      ..._leads.map(l => headers.map(h => `"${String(l[h] || "").replace(/"/g, '""')}"`).join(","))
    ];
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([rows.join("\n")], { type: "text/csv" }));
    a.download = `map-leads-${Date.now()}.csv`;
    a.click();
  };

  async function _saveLead(lead) {
    // Ensure lead has an id
    if (!lead.id && !lead.place_id) {
      lead.id = "map:" + Math.random().toString(36).slice(2, 10);
    }
    lead.id = lead.id || lead.place_id;
    try {
      await fetch("/api/db/upsert", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lead }),
      });
      window.LF && window.LF.addLeads && window.LF.addLeads([lead]);
    } catch (e) {}
  }

  /* ── Helpers ───────────────────────────────────────────────────────── */

  function _esc(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function _initMapPanelEvents() {
    const slider = document.getElementById("mpRadius");
    if (slider) slider.addEventListener("input", _updateCircle);
  }

  /* ── Register tab ──────────────────────────────────────────────────── */

  document.addEventListener("DOMContentLoaded", () => {
    const tabBtn = document.querySelector(`[data-tab="${TAB_ID}"]`);
    if (!tabBtn) return;
    window.LF.bindTab(tabBtn, async () => {
      ensurePanel();
      if (_apiLoaded) return;
      // Get the Google API key from /api/health
      try {
        const h = await fetch("/api/health");
        const data = await h.json();
        // Try to get key from assistant config
        const cfg = await fetch("/api/assistant/config", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: "{}"
        }).then(r => r.json()).catch(() => ({}));
        const apiKey = cfg.config?.keys?.google || "";
        if (!apiKey) {
          const msg = document.getElementById("mapLoadMsg");
          if (msg) msg.innerHTML = "⚠️ No Google Maps API key found.<br>Add your key in <b>Settings → Google Places API key</b>.";
          return;
        }
        await initMap(apiKey);
      } catch (err) {
        const msg = document.getElementById("mapLoadMsg");
        if (msg) msg.textContent = "⚠️ Could not initialize map: " + err.message;
      }
    });
  });
})();
