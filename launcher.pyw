"""
PyCraft Launcher v9 — Eel Web Backend
"""
import eel
import os
import json
import time
import requests
import hashlib
import threading
import subprocess
import uuid
import re
import shutil
import base64
from io import BytesIO
from PIL import Image, ImageDraw
import minecraft_launcher_lib
import tkinter as tk
from tkinter import filedialog

# ── Configuration ────────────────────────────────────────────────────────────
FB_URL       = "https://solarwakes-fd15a-default-rtdb.firebaseio.com"
APP_SECRET   = "pycraft-v5-2024"
MC_DIR       = minecraft_launcher_lib.utils.get_minecraft_directory()
SKINS_DIR    = os.path.join(MC_DIR, "pycraft_skins")
SESSION_FILE = os.path.join(MC_DIR, "pycraft_session.json")

os.makedirs(SKINS_DIR, exist_ok=True)

# ── Helpers ──────────────────────────────────────────────────────────────────
def hash_pw(pw): return hashlib.sha256(f"{APP_SECRET}:{pw}".encode()).hexdigest()
def safe_key(u): return re.sub(r'[.#$\[\]/]', '_', u)

def fb_get(path):
    try: return requests.get(f"{FB_URL}/{path}.json", timeout=5).json()
    except Exception: return None

def fb_patch(path, data):
    try: requests.patch(f"{FB_URL}/{path}.json", json=data, timeout=5)
    except Exception: pass

def fb_delete(path):
    try: requests.delete(f"{FB_URL}/{path}.json", timeout=5)
    except Exception: pass

def img_to_b64(img):
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()

def get_face_b64(username):
    path = os.path.join(SKINS_DIR, f"{username}.png")
    size = 64
    if os.path.exists(path):
        try:
            img = Image.open(path).convert("RGBA")
            face = img.crop((8, 8, 16, 16)).resize((size, size), Image.NEAREST)
            hat = img.crop((40, 8, 48, 16)).resize((size, size), Image.NEAREST)
            face.paste(hat, (0, 0), hat)
            return img_to_b64(face)
        except Exception: pass
    
    img = Image.new("RGBA", (size, size), (20, 40, 20, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([size//4, size//4, 3*size//4, 3*size//4], fill=(74, 222, 128))
    return img_to_b64(img)

# ── Multi-Account Session Manager ────────────────────────────────────────────
def load_session_data():
    if not os.path.exists(SESSION_FILE):
        return {"active": None, "accounts": {}}
    
    try:
        # Open in read-only mode, explicitly handle encoding
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure the structure is correct
            if "accounts" not in data: 
                return {"active": None, "accounts": {}}
            return data
    except Exception as e:
        print(f"DEBUG: Session file corrupted or locked: {e}")
        return {"active": None, "accounts": {}}

def save_session_data(data):
    try:
        # Create a temp file first, then rename (atomic operation)
        temp_file = SESSION_FILE + ".tmp"
        with open(temp_file, "w") as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        shutil.move(temp_file, SESSION_FILE) # This replaces the file instantly
    except Exception as e:
        print(f"CRITICAL: Could not save session: {e}")

@eel.expose
def get_saved_session():
    data = load_session_data()
    # Check if 'active' exists and corresponds to a key in 'accounts'
    if data.get("active") and data["active"] in data.get("accounts", {}):
        return {"username": data["active"], "password": data["accounts"][data["active"]]}
    return None 
@eel.expose
def get_all_accounts():
    data = load_session_data()
    accs = []
    for u in data.get("accounts", {}).keys():
        accs.append({"username": u, "avatar": get_face_b64(u)})
    return {"active": data.get("active"), "accounts": accs}

@eel.expose
def switch_to_account(username):
    data = load_session_data()
    if username in data.get("accounts", {}):
        data["active"] = username
        save_session_data(data)
        return True
    return False

@eel.expose
def remove_saved_account(username):
    data = load_session_data()
    if username in data.get("accounts", {}):
        del data["accounts"][username]
        if data.get("active") == username:
            data["active"] = None
    save_session_data(data)
    fb_patch(f"users/{safe_key(username)}", {"status": "offline", "last_seen": int(time.time())})
    return True

@eel.expose
def set_active_account_null():
    data = load_session_data()
    data["active"] = None
    save_session_data(data)

@eel.expose
def get_user_profile(username):
    data = fb_get(f"users/{safe_key(username)}")
    if not data: return None
    return {
        "joined": time.strftime("%B %d, %Y", time.localtime(data.get("joined", 0))),
        "friends": len([k for k, v in data.get("friends", {}).items() if v.get("status") == "accepted"]),
        "status": data.get("status", "offline").upper()
    }

# ── Core Authentication API ──────────────────────────────────────────────────
@eel.expose
def auth_login(username, password):
    key = safe_key(username)
    data = fb_get(f"users/{key}")
    if not data: return {"error": "Account not found."}
    if data.get("password") != hash_pw(password): return {"error": "Wrong password."}
    
    session = load_session_data()
    if "accounts" not in session: session["accounts"] = {}
    session["accounts"][username] = password
    session["active"] = username
    save_session_data(session)

    fb_patch(f"users/{key}", {"status": "online", "last_seen": int(time.time())})
    return {"success": True, "avatar": get_face_b64(username)}

@eel.expose
def auth_register(username, password, email):
    key = safe_key(username)
    if fb_get(f"users/{key}"): return {"error": "Username taken."}
    now = int(time.time())
    fb_patch(f"users/{key}", {
        "username": username, "email": email, "password": hash_pw(password),
        "joined": now, "status": "online", "last_seen": now, "friends": {}
    })
    
    session = load_session_data()
    if "accounts" not in session: session["accounts"] = {}
    session["accounts"][username] = password
    session["active"] = username
    save_session_data(session)

    return {"success": True, "avatar": get_face_b64(username)}

# ── Engine Endpoints ─────────────────────────────────────────────────────────
@eel.expose
def get_versions():
    vdir = os.path.join(MC_DIR, "versions")
    if not os.path.isdir(vdir): return []
    return [d for d in sorted(os.listdir(vdir), reverse=True) if os.path.exists(os.path.join(vdir, d, f"{d}.json"))]

@eel.expose
def get_version_details(ver_id):
    try:
        with open(os.path.join(MC_DIR, "versions", ver_id, f"{ver_id}.json")) as f: 
            d = json.load(f)
        return {"id": ver_id, "type": d.get("type", "release"), "date": (d.get("releaseTime") or d.get("time", ""))[:10], "base": d.get("inheritsFrom", "vanilla")}
    except Exception:
        return {"id": ver_id, "type": "unknown", "date": "unknown", "base": "unknown"}

@eel.expose
def upload_skin(username):
    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
    path = filedialog.askopenfilename(title="Select Skin PNG", filetypes=[("PNG Image","*.png")])
    if path:
        shutil.copy2(path, os.path.join(SKINS_DIR, f"{username}.png"))
        return get_face_b64(username)
    return None

# ── Friends System Endpoints ─────────────────────────────────────────────────
@eel.expose
def fetch_friends(username):
    data = fb_get(f"users/{safe_key(username)}/friends") or {}
    for k in data:
        f_info = fb_get(f"users/{k}") or {}
        data[k]["status_now"] = f_info.get("status", "offline")
        data[k]["avatar"] = get_face_b64(data[k].get("username", k))
    return data

@eel.expose
def search_user(query):
    key = safe_key(query)
    data = fb_get(f"users/{key}")
    if data: return {"key": key, "username": data.get("username", query), "status": data.get("status", "offline"), "avatar": get_face_b64(query)}
    return None

@eel.expose
def friend_action(my_username, target_key, action, target_name=""):
    me = safe_key(my_username)
    if action == "add":
        fb_patch(f"users/{me}/friends/{target_key}", {"status":"pending_outgoing", "username":target_name})
        fb_patch(f"users/{target_key}/friends/{me}", {"status":"pending_incoming", "username":my_username})
    elif action == "accept":
        fb_patch(f"users/{me}/friends/{target_key}", {"status":"accepted", "username":target_name})
        fb_patch(f"users/{target_key}/friends/{me}", {"status":"accepted", "username":my_username})
    elif action in ["remove", "decline", "cancel"]:
        fb_delete(f"users/{me}/friends/{target_key}")
        fb_delete(f"users/{target_key}/friends/{me}")
    return True

# ── Launch Logic ─────────────────────────────────────────────────────────────
@eel.expose
def launch_game(username, version):
    threading.Thread(target=_launch_thread, args=(username, version), daemon=True).start()

def _launch_thread(username, version):
    eel.ui_log(f"Preparing to launch {version}...", "info")()
    fb_patch(f"users/{safe_key(username)}", {"status": "in-game"})
    try:
        player_uuid = str(uuid.uuid3(uuid.NAMESPACE_DNS, f"OfflinePlayer:{username}"))
        options = {"username": username, "uuid": player_uuid, "token": "0", "executablePath": "java", "jvmArguments": ["-Xmx2G", "-Xms1G"]}
        cmd = minecraft_launcher_lib.command.get_minecraft_command(version, MC_DIR, options)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout: eel.ui_log(line.rstrip(), "info")()
        proc.wait()
        eel.ui_log("Game exited.", "info")()
    except Exception as e: eel.ui_log(f"Error: {e}", "error")()
    finally:
        fb_patch(f"users/{safe_key(username)}", {"status": "online"})
        eel.ui_game_exit()()

@eel.expose
def set_offline(username):
    fb_patch(f"users/{safe_key(username)}", {"status": "offline", "last_seen": int(time.time())})

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    eel.init(os.path.join(current_dir, 'web'))
    eel.start('index.html', size=(1100, 700), port=0, mode='chrome')