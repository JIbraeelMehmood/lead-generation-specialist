"""
Email verification for LeadFinder — ported from OutLead's verification stage,
rebuilt to use only the Python standard library (no pip, no dnspython, no Playwright).

Pipeline (OutLead's "syntax -> MX -> placeholder -> live mailbox check"):
  1. Syntax check
  2. Disposable / placeholder / known-bad-domain filter
  3. MX lookup via DNS-over-HTTPS (https://dns.google/resolve) — stdlib urllib
  4. SMTP mailbox check via smtplib: connect to the MX host, RCPT TO the address,
     and run a catch-all probe so we never claim "verified" on a catch-all server.

Statuses (honest, not over-claimed):
  verified      - the mail server accepts mail for this exact address (250) and is not a catch-all
  domain-only   - the domain has valid mail servers (MX/A) but we can't confirm the specific box
                  (catch-all server, or SMTP probe was refused/greylisted)
  invalid       - the server rejected the address (550/551 user-unknown)
  unknown       - no MX/A records, or a network/timeout error (often port 25 is blocked locally)

This never invents an email and never marks a guessed address as verified.
"""
import json, random, re, smtplib, socket, time, urllib.parse, urllib.request

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}$")
ROLE_LOCAL = {"info", "sales", "hello", "contact", "admin", "office", "support", "enquiries", "team", "mail"}
DISPOSABLE = ("mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
              "temp-mail.org", "throwawaymail.com", "yopmail.com", "getnada.com",
              "sharklasers.com", "trashmail.com", "maildrop.cc", "dispostable.com")
BAD_DOM = ("example.com", "example.org", "domain.com", "email.com", "test.com",
           "sentry.io", "wixpress.com", "yourdomain.com", "sample.com")

SMTP_TIMEOUT = 10
DOH = "https://dns.google/resolve"


def _doh(name, rtype):
    """One DNS-over-HTTPS query. Returns the parsed JSON or None."""
    url = DOH + "?" + urllib.parse.urlencode({"name": name, "type": rtype})
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None

def mx_hosts(domain):
    """Return ordered list of mail-exchange hostnames (lowest priority first)."""
    res = _doh(domain, "MX")
    if res and res.get("Status") == 0:
        ans = [a for a in (res.get("Answer") or []) if a.get("type") == 15]  # type 15 = MX
        if ans:
            def host(v):   # MX rdata: "10 mx1.example.com."
                return (v or "").split()[-1].rstrip(".").lower()
            items = []
            for a in ans:
                parts = (a.get("data") or "").split()
                if len(parts) >= 2:
                    items.append((int(parts[0]), host(a.get("data"))))
            items.sort()
            return [h for _, h in items if h]
    # fall back to A record (implicit MX)
    res = _doh(domain, "A")
    if res and res.get("Status") == 0 and any(a.get("type") == 1 for a in (res.get("Answer") or [])):
        return [domain.lower()]
    return []


def _smtp_check(host, email_addr):
    """Connect to one MX host and probe the address. Returns (status, reason)."""
    try:
        with smtplib.SMTP(timeout=SMTP_TIMEOUT) as srv:
            srv.connect(host, 25)
            srv.ehlo("leadfinder.local")
            srv.mail("")
            code, _ = srv.rcpt(email_addr)
            # catch-all probe: a random address should NOT also be accepted
            rand = "lf-no-such-%d@%s" % (random.randint(10000, 99999), email_addr.split("@", 1)[1])
            code2, _ = srv.rcpt(rand)
            try:
                srv.quit()
            except Exception:
                pass
            if code == 250 and code2 != 250:
                return "verified", "mail server accepts this address"
            if code == 250 and code2 == 250:
                return "domain-only", "catch-all server accepts any address"
            if code in (550, 551, 552, 553):
                return "invalid", "server rejected the address (%d)" % code
            return "domain-only", "server returned %d (no clear answer)" % code
    except (socket.timeout, TimeoutError):
        return "domain-only", "MX host found but SMTP timed out (port 25 may be blocked locally)"
    except smtplib.SMTPServerDisconnected:
        return "domain-only", "server hung up before answering (often greylisting)"
    except smtplib.SMTPRecipientsRefused:
        return "invalid", "server refused the recipient"
    except ConnectionRefusedError:
        return "domain-only", "no mail service answered on this host"
    except OSError:
        return "domain-only", "MX host found but SMTP probe could not complete (port 25 blocked locally?)"
    except Exception as ex:
        return "domain-only", "SMTP error: " + type(ex).__name__


def verify_email(email_addr):
    """Return the OutLead-style verification result for one address."""
    email_addr = (email_addr or "").strip().lower()
    if not EMAIL_RE.match(email_addr):
        return {"email": email_addr, "status": "invalid", "reason": "bad email format"}
    local, domain = email_addr.split("@", 1)
    if any(domain.endswith(d) for d in DISPOSABLE):
        return {"email": email_addr, "status": "invalid", "reason": "disposable email domain"}
    if domain in BAD_DOM or domain.endswith(BAD_DOM):
        return {"email": email_addr, "status": "invalid", "reason": "placeholder / example domain"}
    hosts = mx_hosts(domain)
    if not hosts:
        return {"email": email_addr, "status": "unknown", "reason": "no MX / A records found"}
    status, reason = "unknown", "no SMTP host answered"
    for h in hosts[:3]:
        status, reason = _smtp_check(h, email_addr)
        if status in ("verified", "invalid"):
            break
        time.sleep(0.3)
    return {"email": email_addr, "status": status, "reason": reason,
            "mxHost": hosts[0], "checkedAt": time.strftime("%Y-%m-%d %H:%M")}


def handle(path, req):
    if path == "/api/emailverify":
        return {"result": verify_email(req.get("email", ""))}
    if path == "/api/emailverify/batch":
        emails = req.get("emails", [])[:50]
        return {"results": [verify_email(e) for e in emails]}
    raise RuntimeError("Unknown endpoint")
