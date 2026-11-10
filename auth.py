"""
auth.py — Simple multi-user workspace support for LeadFinder.

Features:
  - User registration and login (username + password)
  - Token-based sessions (stored in data/sessions.json)
  - Per-user data isolation (each user gets their own lead list prefix)
  - Admin can manage users
  - Can be disabled (single-user mode by default)

No external dependencies — uses only stdlib (hashlib, secrets, json, os, time).
"""
import json, os, time, secrets, hashlib

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")
SESSION_TTL = 7 * 24 * 3600  # 7 days

def _ensure_dir():
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

def _load(path, default):
    _ensure_dir()
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def _save(path, data):
    _ensure_dir()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)

def _hash_pw(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt, h

def _verify_pw(password, salt, stored_hash):
    _, h = _hash_pw(password, salt)
    return h == stored_hash

def load_users():
    return _load(USERS_FILE, {"users": [], "enabled": False, "next_id": 1})

def save_users(data):
    _save(USERS_FILE, data)

def load_sessions():
    return _load(SESSIONS_FILE, {"sessions": {}})

def save_sessions(data):
    _save(SESSIONS_FILE, data)

def create_session(user_id, username):
    token = secrets.token_urlsafe(32)
    sessions = load_sessions()
    sessions["sessions"][token] = {
        "user_id": user_id,
        "username": username,
        "created": time.time(),
        "expires": time.time() + SESSION_TTL,
    }
    save_sessions(sessions)
    return token

def validate_session(token):
    if not token:
        return None
    sessions = load_sessions()
    sess = sessions["sessions"].get(token)
    if not sess:
        return None
    if time.time() > sess.get("expires", 0):
        del sessions["sessions"][token]
        save_sessions(sessions)
        return None
    # Extend session
    sess["expires"] = time.time() + SESSION_TTL
    save_sessions(sessions)
    return sess

def destroy_session(token):
    sessions = load_sessions()
    if token in sessions["sessions"]:
        del sessions["sessions"][token]
        save_sessions(sessions)

def is_enabled():
    return load_users().get("enabled", False)

def set_enabled(enabled):
    data = load_users()
    data["enabled"] = bool(enabled)
    save_users(data)

def register(username, password, display_name=""):
    """Register a new user. Returns (success, token_or_error)."""
    data = load_users()
    username = (username or "").strip().lower()
    if not username or len(username) < 2:
        return False, "Username must be at least 2 characters."
    if not password or len(password) < 4:
        return False, "Password must be at least 4 characters."
    if any(u["username"] == username for u in data["users"]):
        return False, "Username already taken."
    salt, h = _hash_pw(password)
    user_id = data["next_id"]
    is_first_user = len(data["users"]) == 0
    data["users"].append({
        "id": user_id,
        "username": username,
        "display_name": display_name or username,
        "salt": salt,
        "hash": h,
        "role": "admin" if is_first_user else "member",
        "created": time.time(),
    })
    data["next_id"] = user_id + 1
    save_users(data)
    token = create_session(user_id, username)
    return True, {"token": token, "user": {"id": user_id, "username": username, "display_name": display_name or username, "role": "admin" if is_first_user else "member"}}

def login(username, password):
    """Login an existing user. Returns (success, token_or_error)."""
    data = load_users()
    username = (username or "").strip().lower()
    user = next((u for u in data["users"] if u["username"] == username), None)
    if not user:
        return False, "User not found."
    if not _verify_pw(password, user["salt"], user["hash"]):
        return False, "Incorrect password."
    token = create_session(user["id"], username)
    return True, {"token": token, "user": {"id": user["id"], "username": username, "display_name": user.get("display_name", username), "role": user.get("role", "member")}}

def logout(token):
    destroy_session(token)
    return True

def get_user_by_id(user_id):
    data = load_users()
    return next((u for u in data["users"] if u["id"] == user_id), None)

def list_users():
    data = load_users()
    return [{"id": u["id"], "username": u["username"], "display_name": u.get("display_name", u["username"]), "role": u.get("role", "member"), "created": u.get("created")} for u in data["users"]]

def delete_user(user_id):
    data = load_users()
    data["users"] = [u for u in data["users"] if u["id"] != user_id]
    save_users(data)
    return True

def update_user(user_id, updates):
    data = load_users()
    user = next((u for u in data["users"] if u["id"] == user_id), None)
    if not user:
        return False, "User not found."
    if "display_name" in updates:
        user["display_name"] = updates["display_name"]
    if "password" in updates and updates["password"]:
        salt, h = _hash_pw(updates["password"])
        user["salt"] = salt
        user["hash"] = h
    if "role" in updates:
        user["role"] = updates["role"]
    save_users(data)
    return True, {"id": user["id"], "username": user["username"], "display_name": user.get("display_name", user["username"]), "role": user.get("role", "member")}

def handle(path, req):
    """Route handler for /api/auth/* endpoints."""
    if path == "/api/auth/status":
        data = load_users()
        return {
            "enabled": data.get("enabled", False),
            "user_count": len(data.get("users", [])),
            "users": [{"id": u["id"], "username": u["username"], "display_name": u.get("display_name", u["username"]), "role": u.get("role", "member")} for u in data.get("users", [])] if data.get("enabled") else [],
        }

    if path == "/api/auth/enable":
        set_enabled(True)
        return {"enabled": True, "message": "Multi-user mode enabled."}

    if path == "/api/auth/disable":
        set_enabled(False)
        return {"enabled": False, "message": "Multi-user mode disabled."}

    if path == "/api/auth/register":
        username = req.get("username", "")
        password = req.get("password", "")
        display_name = req.get("display_name", "")
        ok, result = register(username, password, display_name)
        if ok:
            return {"success": True, "token": result["token"], "user": result["user"]}
        return {"error": result}

    if path == "/api/auth/login":
        username = req.get("username", "")
        password = req.get("password", "")
        ok, result = login(username, password)
        if ok:
            return {"success": True, "token": result["token"], "user": result["user"]}
        return {"error": result}

    if path == "/api/auth/logout":
        token = req.get("token", "")
        logout(token)
        return {"success": True}

    if path == "/api/auth/verify":
        token = req.get("token", "")
        sess = validate_session(token)
        if sess:
            user = get_user_by_id(sess["user_id"])
            if user:
                return {"valid": True, "user": {"id": user["id"], "username": user["username"], "display_name": user.get("display_name", user["username"]), "role": user.get("role", "member")}}
        return {"valid": False}

    if path == "/api/auth/users":
        return {"users": list_users()}

    if path == "/api/auth/user/delete":
        user_id = req.get("user_id")
        delete_user(user_id)
        return {"success": True}

    if path == "/api/auth/user/update":
        user_id = req.get("user_id")
        updates = req.get("updates", {})
        ok, result = update_user(user_id, updates)
        if ok:
            return {"success": True, "user": result}
        return {"error": result}

    return {"error": "Unknown auth endpoint"}
