"""
Google Sheets / Docs export for LeadFinder — blueprint §12.

Exports the full lead list (or a subset) to a Google Spreadsheet using
the Sheets REST API v4.  Authentication: OAuth 2.0 with the user's own
Google Cloud project, standard library only.

Workflow
  1. User creates an OAuth client (Desktop app) in Google Cloud Console,
     downloads credentials.json, pastes the path in Settings > Exports.
  2. First export: opens a browser for the consent screen, saves the token.
  3. Subsequent exports: uses the saved token (auto-refreshes).

Each export creates / updates one spreadsheet with tabs:
  • Leads      – the full list (name, category, phone, email, website, score, stage, notes)
  • Suppressed – do-not-contact domains
  • Blueprint  – current blueprint config

Standard library only: no google-auth, no gspread, no requests.
"""
import base64, json, os, re, threading, time, urllib.parse, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
import leadfinder as LF

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_SCOPES = "https://www.googleapis.com/auth/spreadsheets"
_TOKEN_FILE = os.path.join(DATA, "sheets_token.json")
_CONFIG_FILE = os.path.join(DATA, "sheets_config.json")
_lock = threading.Lock()


# ---------------------------------------------------------------- config
def _cfg():
    try:
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_cfg(c):
    with _lock:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(c, f, indent=2)


# ---------------------------------------------------------------- OAuth (PKCE-less Desktop flow)
def _load_token():
    try:
        with open(_TOKEN_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _save_token(t):
    with open(_TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(t, f, indent=2)

def _refresh(tok, client_id, client_secret):
    r = LF.http_json("https://oauth2.googleapis.com/token", {
        "client_id": client_id, "client_secret": client_secret,
        "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"}, timeout=30)
    if r.get("error"):
        raise RuntimeError("Token refresh failed: " + r.get("error_description", r["error"]))
    tok.update(r)
    tok.setdefault("refresh_token", tok.get("refresh_token", ""))
    tok["expires_at"] = time.time() + int(tok.get("expires_in", 3599))
    _save_token(tok)
    return tok

def _valid_token(client_id, client_secret):
    tok = _load_token()
    if not tok:
        return None
    if time.time() > tok.get("expires_at", 0) - 120:
        tok = _refresh(tok, client_id, client_secret)
    return tok["access_token"]

def _start_oauth(creds_path):
    """Desktop-app OAuth flow: open the browser, catch the redirect on localhost."""
    with open(creds_path, encoding="utf-8") as f:
        raw = json.load(f)
    web = raw.get("installed") or raw.get("web") or {}
    client_id = web.get("client_id", "")
    client_secret = web.get("client_secret", "")
    if not client_id:
        raise RuntimeError("credentials.json doesn't contain a client_id. Use a Desktop app OAuth client.")

    # Use a fixed redirect_uri registered in the OAuth client
    redirect = "http://localhost:28765"
    state = base64.urlsafe_b64encode(os.urandom(16)).decode().rstrip("=")
    auth_url = ("https://accounts.google.com/o/oauth2/v2/auth?" +
                urllib.parse.urlencode({
                    "client_id": client_id, "redirect_uri": redirect + "/",
                    "response_type": "code", "scope": _SCOPES,
                    "access_type": "offline", "state": state, "prompt": "consent"}))

    code_holder = {}
    class _H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            p = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(p.query)
            code_holder["code"] = (qs.get("code") or [""])[0]
            code_holder["state"] = (qs.get("state") or [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Authorized! You can close this tab and return to LeadFinder.</h2>")

    srv = HTTPServer(("localhost", 28765), _H)
    print(f"\n  Opening browser for Google authorization…\n  If it doesn't open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)
    srv.handle_request()    # wait for one request
    srv.server_close()

    code = code_holder.get("code", "")
    if not code:
        raise RuntimeError("Authorization failed – no code returned.")
    # Exchange code for tokens
    r = LF.http_json("https://oauth2.googleapis.com/token", {
        "code": code, "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": redirect + "/", "grant_type": "authorization_code"}, timeout=30)
    if r.get("error"):
        raise RuntimeError("Token exchange failed: " + r.get("error_description", r["error"]))
    r["expires_at"] = time.time() + int(r.get("expires_in", 3599))
    _save_token(r)
    return client_id, client_secret, r["access_token"]


def _access_token(creds_path):
    with open(creds_path, encoding="utf-8") as f:
        raw = json.load(f)
    web = raw.get("installed") or raw.get("web") or {}
    cid, cs = web.get("client_id", ""), web.get("client_secret", "")
    try:
        tok = _valid_token(cid, cs)
    except Exception:
        tok = None
    if tok:
        return tok
    # need fresh auth
    _, _, tok = _start_oauth(creds_path)
    return tok


# ---------------------------------------------------------------- Sheets API helpers
def _sheets(method, path, token, body=None, timeout=60):
    base = "https://sheets.googleapis.com/v4/spreadsheets"
    return LF.http_json(base + path, body,
                        {"Authorization": "Bearer " + token,
                         "Content-Type": "application/json"}, timeout=timeout,
                        method=method if body is None else None)

def _drive_create(token, title):
    r = LF.http_json("https://sheets.googleapis.com/v4/spreadsheets",
                     {"properties": {"title": title},
                      "sheets": [
                          {"properties": {"title": "Leads"}},
                          {"properties": {"title": "Suppressed"}},
                          {"properties": {"title": "Blueprint"}},
                      ]},
                     {"Authorization": "Bearer " + token,
                      "Content-Type": "application/json"}, timeout=30)
    if r.get("error"):
        raise RuntimeError("Sheets create failed: " + str(r["error"]))
    return r["spreadsheetId"]

def _batch_update(spreadsheet_id, token, requests_body):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
    r = LF.http_json(url, {"requests": requests_body},
                     {"Authorization": "Bearer " + token,
                      "Content-Type": "application/json"}, timeout=60)
    if (r or {}).get("error"):
        raise RuntimeError("Sheets update failed: " + str(r["error"]))
    return r

def _clear_write(spreadsheet_id, sheet_title, rows, token):
    """Clear a sheet and write `rows` (list of lists)."""
    sid_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(sheet_title)}:clear"
    LF.http_json(sid_url, {}, {"Authorization": "Bearer " + token,
                               "Content-Type": "application/json"}, timeout=30)
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
           f"/values/{urllib.parse.quote(sheet_title)}?valueInputOption=RAW")
    r = LF.http_json(url, {"values": rows},
                     {"Authorization": "Bearer " + token,
                      "Content-Type": "application/json"}, timeout=60, method="PUT")
    if (r or {}).get("error"):
        raise RuntimeError("Sheets write failed: " + str(r["error"]))


# ---------------------------------------------------------------- export
def export(leads, suppressed_domains, blueprint_cfg, creds_path, title="LeadFinder Export"):
    """Export leads to Google Sheets. Returns the spreadsheet URL."""
    if not os.path.isfile(creds_path):
        raise RuntimeError(f"credentials.json not found at {creds_path}. "
                           "Download it from Google Cloud Console > APIs & Services > Credentials.")
    token = _access_token(creds_path)
    cfg = _cfg()
    sid = cfg.get("spreadsheet_id")

    # Verify the sheet still exists
    if sid:
        try:
            r = LF.http_json(f"https://sheets.googleapis.com/v4/spreadsheets/{sid}?fields=spreadsheetId",
                             headers={"Authorization": "Bearer " + token}, timeout=15)
            if r.get("error"):
                sid = None
        except Exception:
            sid = None

    if not sid:
        sid = _drive_create(token, title)
        cfg["spreadsheet_id"] = sid
        _save_cfg(cfg)

    # Leads sheet
    lead_rows = [["Name", "Category", "Address", "Phone", "Email", "Email Status",
                  "Website", "Rating", "Reviews", "Score", "Priority", "Stage", "Follow-up",
                  "Source", "Found At", "Notes"]]
    for l in leads:
        lead_rows.append([
            l.get("name", ""), l.get("category", ""), l.get("address", ""),
            l.get("phone", ""), l.get("email", ""),
            l.get("emailStatus") or l.get("emailVerified", ""),
            l.get("website", ""), str(l.get("rating") or ""),
            str(l.get("reviews") or ""), str(l.get("_score") or ""),
            l.get("priority", ""), l.get("stage", ""),
            l.get("followUp", ""), l.get("source", ""),
            l.get("foundAt", ""), (l.get("notes") or "").replace("\n", " | ")
        ])

    # Suppressed sheet
    sup_rows = [["Domain", "Added"]] + [[d, ""] for d in suppressed_domains]

    # Blueprint config sheet
    bp_rows = [["Setting", "Value"]] + [[k, str(v)] for k, v in blueprint_cfg.items()]

    _clear_write(sid, "Leads", lead_rows, token)
    _clear_write(sid, "Suppressed", sup_rows, token)
    _clear_write(sid, "Blueprint", bp_rows, token)

    url = f"https://docs.google.com/spreadsheets/d/{sid}/edit"
    return {"url": url, "spreadsheetId": sid, "rows": len(leads), "exportedAt": time.strftime("%Y-%m-%d %H:%M")}


# ---------------------------------------------------------------- API
def handle(path, req):
    import assistant, pipeline
    if path == "/api/sheets/export":
        creds_path = req.get("credsPath") or _cfg().get("credsPath", "")
        if not creds_path:
            raise RuntimeError("Provide the path to your credentials.json file (Google Cloud Console > APIs & Services > Credentials > Download).")
        # Accept leads array from the frontend or use the full stored list
        leads = req.get("leads", [])
        sup = pipeline.suppressed().get("domains", [])
        bp = pipeline.bp_config()
        return export(leads, sup, bp, creds_path, req.get("title", "LeadFinder Export"))
    if path == "/api/sheets/config":
        if req.get("save"):
            c = _cfg()
            c.update({k: v for k, v in req["save"].items() if k in ("credsPath", "spreadsheet_id")})
            _save_cfg(c)
        return _cfg()
    if path == "/api/sheets/status":
        c = _cfg()
        tok = _load_token()
        return {"configured": bool(c.get("credsPath")), "authorized": bool(tok),
                "spreadsheetId": c.get("spreadsheet_id", ""), "config": c}
    raise RuntimeError("Unknown endpoint")
