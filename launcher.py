"""

Requires: pip install customtkinter minecraft-launcher-lib pillow
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
import minecraft_launcher_lib
import subprocess, threading, urllib.request
import uuid, os, json, re, html, shutil
from PIL import Image, ImageTk, ImageFilter, ImageDraw

# ── Appearance ────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ── Palette ───────────────────────────────────────────────────────────────────
C_BG       = "#090b0f"          # near-black base
C_GLASS    = "#0e1117"          # card/panel glass
C_GLASS2   = "#13181f"          # lighter glass
C_BORDER   = "#1e2736"          # glass border
C_BORDER2  = "#243044"          # highlighted border
C_GREEN    = "#4ade80"          # Minecraft grass neon
C_GREEN2   = "#22c55e"          # deeper green
C_TEAL     = "#2dd4bf"          # accent teal
C_BLUE     = "#38bdf8"          # highlight blue
C_TEXT     = "#e8f0fe"          # primary text
C_MUTED    = "#4a5a6e"          # muted / secondary
C_DIM      = "#2a3545"          # very dim
C_SEL      = "#0f2a1a"          # selected row bg
C_SEL_BD   = "#4ade80"          # selected row border
C_ERROR    = "#f87171"          # error red
C_WARN     = "#fbbf24"          # warning amber

F_TITLE  = ("Outfit", 28, "bold")
F_HEAD   = ("Outfit", 13, "bold")
F_LABEL  = ("Outfit", 9,  "bold")
F_BODY   = ("Outfit", 10)
F_BTN    = ("Outfit", 12, "bold")
F_SMALL  = ("Outfit", 8)
F_LIST   = ("Outfit", 10)
F_MONO   = ("JetBrains Mono", 9)

MINECRAFT_NEWS_URL = "https://launchercontent.mojang.com/news.json"

# ── Skin helpers ──────────────────────────────────────────────────────────────

def extract_face(skin_path, size=38):
    try:
        img  = Image.open(skin_path).convert("RGBA")
        face = img.crop((8, 8, 16, 16)).resize((size, size), Image.NEAREST)
        hat  = img.crop((40, 8, 48, 16)).resize((size, size), Image.NEAREST)
        face.paste(hat, (0, 0), hat)
        return ctk.CTkImage(face, size=(size, size))
    except Exception:
        return _default_face_ctk(size)

def _default_face_ctk(size=38):
    img  = Image.new("RGBA", (size, size), (20, 40, 20, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([size//4, size//4, 3*size//4, 3*size//4], fill=(74, 222, 128))
    return ctk.CTkImage(img, size=(size, size))

def extract_body_preview(skin_path, scale=5):
    try:
        img   = Image.open(skin_path).convert("RGBA")
        head  = img.crop((8,  8,  16, 16))
        torso = img.crop((20, 20, 28, 32))
        l_arm = img.crop((44, 20, 48, 32))
        r_arm = img.crop((36, 52, 40, 64))
        l_leg = img.crop((4,  20, 8,  32))
        r_leg = img.crop((20, 52, 24, 64))
        BW, BH = 16, 28
        body  = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
        for part, pos in [
            (head.resize((8,8),   Image.NEAREST), (4,  0)),
            (torso.resize((8,12), Image.NEAREST), (4,  8)),
            (l_arm.resize((4,12), Image.NEAREST), (0,  8)),
            (r_arm.resize((4,12), Image.NEAREST), (12, 8)),
            (l_leg.resize((4,12), Image.NEAREST), (4,  20)),
            (r_leg.resize((4,12), Image.NEAREST), (8,  20)),
        ]:
            body.paste(part, pos, part)
        final = body.resize((BW*scale, BH*scale), Image.NEAREST)
        return ctk.CTkImage(final, size=(BW*scale, BH*scale))
    except Exception:
        img = Image.new("RGBA", (16*scale, 28*scale), (20, 60, 30, 255))
        return ctk.CTkImage(img, size=(16*scale, 28*scale))

# ── Separator ─────────────────────────────────────────────────────────────────

def glass_sep(parent, color=C_BORDER, pady=0, padx=0):
    ctk.CTkFrame(parent, height=1, fg_color=color, corner_radius=0
                 ).pack(fill="x", padx=padx, pady=pady)

# ── Version icon & name ──────────────────────────────────────────────────────

def get_version_info(mc_dir, ver_id):
    """Return (display_name, icon) for a version ID."""
    vid = ver_id.lower()

    # Icon by loader/type (order matters — neoforge before forge)
    if "neoforge" in vid:                                             icon = "🔥"
    elif "forge" in vid:                                              icon = "🔨"
    elif "fabric" in vid:                                             icon = "🪡"
    elif "quilt" in vid:                                              icon = "🧵"
    elif any(x in vid for x in ("lunar","batmod","badlion","pvp")):   icon = "⚔️"
    elif any(x in vid for x in ("optifine","sodium","iris","optimiz")):icon = "✨"
    elif "snapshot" in vid or re.search(r"\d{2}w\d{2}", vid):       icon = "🔬"
    elif re.match(r"^(1\.|2[0-9]\.)", ver_id):                      icon = "🌿"
    else:                                                             icon = "📦"

    # Read version JSON to get inheritsFrom and any name fields
    name = None
    inherits = None
    vj = os.path.join(mc_dir, "versions", ver_id, f"{ver_id}.json")
    if os.path.exists(vj):
        try:
            with open(vj) as f:
                d = json.load(f)
            inherits = d.get("inheritsFrom")
            for k in ("name", "displayName", "clientName", "title", "label"):
                val = d.get(k)
                if val and isinstance(val, str) and val.strip():
                    name = val.strip()
                    break
        except Exception:
            pass

    # Build clean readable name from id + inheritsFrom
    if not name:
        raw = ver_id
        mc_ver = inherits or ""

        # Fabric: id=fabric-loader-0.19.2-26.1.2  inheritsFrom=26.1.2
        m = re.match(r"fabric-loader-([\d.]+)-([\d.]+.*)", raw, re.I)
        if m:
            base = inherits or m.group(2)
            name = f"Fabric  {base}  (loader {m.group(1)})"

        # Forge: 1.21.4-forge-54.0.4  or  forge-1.21.4-54.0.4
        if not name:
            m = re.match(r"(?:forge-)?([\d]+\.[\d.]+)-(?:forge-)?([\d.]+)", raw, re.I)
            if m and "forge" in vid and "neo" not in vid:
                base = inherits or m.group(1)
                name = f"Forge  {base}  ({m.group(2)})"

        # NeoForge: neoforge-21.4.100
        if not name:
            m = re.match(r"neoforge-([\d.]+)", raw, re.I)
            if m:
                name = f"NeoForge  {inherits or m.group(1)}"

        # Quilt: quilt-loader-0.26.0-1.21.4
        if not name:
            m = re.match(r"quilt-loader-([\d.]+)-([\d.]+)", raw, re.I)
            if m:
                base = inherits or m.group(2)
                name = f"Quilt  {base}  (loader {m.group(1)})"

        # BatMod / other mods with no inheritsFrom — use the id as-is
        if not name:
            name = raw

    return name, icon


def get_all_installed_versions(mc_dir):
    """Scan versions/ directory directly — catches everything lib might miss."""
    versions_dir = os.path.join(mc_dir, "versions")
    ids = []
    if not os.path.isdir(versions_dir):
        return ids
    for entry in sorted(os.scandir(versions_dir), key=lambda e: e.name.lower()):
        if not entry.is_dir():
            continue
        if os.path.exists(os.path.join(entry.path, f"{entry.name}.json")):
            ids.append(entry.name)
    return ids

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════════════

class MinecraftLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Solarwakes Launcher")
        self.geometry("1040x660")
        self.minsize(920, 580)
        self.configure(fg_color=C_BG)

        # Windows titlebar colour match
        try:
            from ctypes import windll, byref, sizeof, c_int
            HWND = windll.user32.GetParent(self.winfo_id())
            color = 0x000f0b09
            windll.dwmapi.DwmSetWindowAttribute(
                HWND, 35, byref(c_int(color)), sizeof(c_int))
        except Exception:
            pass

        self.mc_dir    = minecraft_launcher_lib.utils.get_minecraft_directory()
        self.data_file = os.path.join(self.mc_dir, "solarwakes_accounts.json")
        self.skins_dir = os.path.join(self.mc_dir, "solarwakes_skins")
        os.makedirs(self.skins_dir, exist_ok=True)

        self._accounts         = self._load_accounts()
        self._username         = self._accounts.get("_active")
        self._game_running     = False
        self._ver_id_map       = {}
        self._selected_ver_idx = None
        self._ver_rows         = []
        self._overlay          = None
        self._img_refs         = []

        if self._username:
            self._build_main()
        else:
            self._build_login()

    # ── Accounts ──────────────────────────────────────────────────────────────

    def _load_accounts(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_accounts(self):
        with open(self.data_file, "w") as f:
            json.dump(self._accounts, f, indent=2)

    def _add_account(self, username):
        if username not in self._accounts:
            self._accounts[username] = {"skin": None}
        self._accounts["_active"] = username
        self._save_accounts()

    def _skin_path(self, username=None):
        u = username or self._username
        if u and u in self._accounts:
            sp = self._accounts[u].get("skin")
            if sp and os.path.exists(sp):
                return sp
        return None

    # ── LOGIN SCREEN ──────────────────────────────────────────────────────────

    def _build_login(self):
        self._login_wrap = ctk.CTkFrame(self, fg_color="transparent")
        self._login_wrap.place(relx=.5, rely=.5, anchor="center")

        # Background glow circle (canvas trick)
        glow = tk.Canvas(self._login_wrap, width=340, height=340,
                         bg=C_BG, highlightthickness=0, bd=0)
        glow.pack()
        glow.create_oval(30, 30, 310, 310,
                         fill="", outline=C_GREEN, width=1)
        glow.create_oval(60, 60, 280, 280,
                         fill="#041208", outline="")

        # Logo overlay on canvas
        glow.create_text(170, 90, text="⬛", font=("Segoe UI", 52),
                         fill=C_GREEN)
        glow.create_text(170, 155, text="Solarwakes", font=("Outfit", 26, "bold"),
                         fill=C_TEXT)
        glow.create_text(170, 182, text="offline launcher",
                         font=("Outfit", 10), fill=C_MUTED)

        # Glass card
        card = ctk.CTkFrame(self._login_wrap, fg_color=C_GLASS,
                             border_color=C_BORDER2, border_width=1,
                             corner_radius=20, width=320)
        card.place(relx=.5, rely=.5, anchor="n", y=10)
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=30, pady=28, fill="both", expand=True)

        ctk.CTkLabel(inner, text="USERNAME", font=F_LABEL,
                     text_color=C_MUTED).pack(anchor="w")

        self._login_entry = ctk.CTkEntry(
            inner, placeholder_text="Enter your name…",
            font=("Outfit", 13), height=44,
            fg_color=C_GLASS2, border_color=C_BORDER2,
            text_color=C_TEXT,
            placeholder_text_color=C_DIM,
            corner_radius=10)
        self._login_entry.pack(fill="x", pady=(6, 18))
        self._login_entry.bind("<Return>", lambda e: self._do_login())
        self._login_entry.focus()

        play_btn = ctk.CTkButton(
            inner, text="▶  ENTER GAME", command=self._do_login,
            font=F_BTN, height=46,
            fg_color=C_GREEN2, hover_color=C_GREEN,
            text_color=C_BG, corner_radius=12)
        play_btn.pack(fill="x")

        ctk.CTkLabel(inner, text="offline mode  •  no account needed",
                     font=F_SMALL, text_color=C_MUTED).pack(pady=(10, 0))

    def _do_login(self):
        u = self._login_entry.get().strip()
        if not u:
            return
        self._add_account(u)
        self._username = u
        for w in self.winfo_children():
            w.destroy()
        self._build_main()

    # ── MAIN LAYOUT ───────────────────────────────────────────────────────────

    def _build_main(self):
        # Main body (sidebar + content) above footer
        body = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        body.pack(side="top", fill="both", expand=True)

        # Sidebar
        self._sidebar = ctk.CTkFrame(
            body, fg_color=C_GLASS, width=252,
            border_color=C_BORDER, border_width=0,
            corner_radius=0)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # Thin separator line
        ctk.CTkFrame(body, fg_color=C_BORDER, width=1,
                     corner_radius=0).pack(side="left", fill="y")

        # Content
        self._content = ctk.CTkFrame(body, fg_color=C_BG, corner_radius=0)
        self._content.pack(side="left", fill="both", expand=True)

        # Footer — full width at bottom
        glass_sep(self, C_BORDER)
        self._footer = ctk.CTkFrame(self, fg_color=C_GLASS, height=72,
                                     corner_radius=0)
        self._footer.pack(side="bottom", fill="x")
        self._footer.pack_propagate(False)
        self._build_footer()

        self._build_sidebar()
        self._build_content()

    def _build_footer(self):
        f = self._footer

        # LEFT — player card embedded flat in footer
        self._acct_outer = ctk.CTkFrame(f, fg_color="transparent")
        self._acct_outer.pack(side="left", fill="y", padx=(14, 0))
        self._build_acct_card()

        # Thin vertical sep
        ctk.CTkFrame(f, fg_color=C_BORDER, width=1,
                     corner_radius=0).pack(side="left", fill="y", padx=14, pady=10)

        # CENTER — play button
        center = ctk.CTkFrame(f, fg_color="transparent")
        center.pack(side="left", expand=True, fill="y")

        self._play_btn = ctk.CTkButton(
            center, text="▶   PLAY", font=("Outfit", 14, "bold"),
            width=200, height=46, corner_radius=14,
            fg_color=C_GREEN2, hover_color=C_GREEN,
            text_color=C_BG, command=self._launch_game)
        self._play_btn.place(relx=0.5, rely=0.5, anchor="center")

        # Thin vertical sep
        ctk.CTkFrame(f, fg_color=C_BORDER, width=1,
                     corner_radius=0).pack(side="left", fill="y", padx=14, pady=10)

        # RIGHT — status label
        right = ctk.CTkFrame(f, fg_color="transparent", width=130)
        right.pack(side="right", fill="y", padx=(0, 18))
        right.pack_propagate(False)

        self._status_lbl = ctk.CTkLabel(
            right, text="● IDLE", font=F_LABEL, text_color=C_MUTED)
        self._status_lbl.place(relx=0.5, rely=0.5, anchor="center")

    # ── SIDEBAR ───────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        s = self._sidebar

        # App logo row
        logo_row = ctk.CTkFrame(s, fg_color="transparent")
        logo_row.pack(fill="x", padx=14, pady=(18, 10))
        ctk.CTkLabel(logo_row, text="⬛", font=("Segoe UI", 20),
                     text_color=C_GREEN).pack(side="left")
        ctk.CTkLabel(logo_row, text=" Solarwakes", font=("Outfit", 15, "bold"),
                     text_color=C_TEXT).pack(side="left")

        glass_sep(s, C_BORDER, pady=(0, 8))

        # "INSTALLED VERSIONS" header
        hdr = ctk.CTkFrame(s, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(0, 4))
        ctk.CTkLabel(hdr, text="INSTALLED VERSIONS",
                     font=F_LABEL, text_color=C_MUTED).pack(side="left")

        plus_lbl = ctk.CTkLabel(hdr, text=" ＋ ",
                                 font=("Outfit", 14, "bold"),
                                 text_color=C_GREEN, cursor="hand2")
        plus_lbl.pack(side="right")
        plus_lbl.bind("<Button-1>", lambda e: self._open_manager())
        plus_lbl.bind("<Enter>",    lambda e: plus_lbl.configure(text_color=C_TEXT))
        plus_lbl.bind("<Leave>",    lambda e: plus_lbl.configure(text_color=C_GREEN))

        # Scrollable version list
        self._ver_scroll = ctk.CTkScrollableFrame(
            s, fg_color="transparent",
            scrollbar_button_color=C_BORDER2,
            scrollbar_button_hover_color=C_MUTED)
        self._ver_scroll.pack(fill="both", expand=True, padx=6, pady=(0, 4))

        self._refresh_versions(silent=True)

    def _build_acct_card(self):
        for w in self._acct_outer.winfo_children():
            w.destroy()

        # Flat layout for footer — no extra padding container
        row = ctk.CTkFrame(self._acct_outer, fg_color="transparent")
        row.pack(side="left", fill="y", pady=12)

        sp = self._skin_path()
        face_img = extract_face(sp, 38) if sp else _default_face_ctk(38)
        self._img_refs.append(face_img)

        face_lbl = ctk.CTkLabel(row, image=face_img, text="",
                                 width=38, height=38)
        face_lbl.pack(side="left", padx=(0, 10))

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="y")
        ctk.CTkLabel(info, text="PLAYING AS", font=F_LABEL,
                     text_color=C_MUTED).pack(anchor="w")
        ctk.CTkLabel(info, text=self._username or "—",
                     font=("Outfit", 11, "bold"),
                     text_color=C_TEXT).pack(anchor="w")
        ctk.CTkLabel(info, text="Manage profile →",
                     font=F_SMALL, text_color=C_MUTED,
                     cursor="hand2").pack(anchor="w")

        def _bind_hover(w):
            w.bind("<Button-1>", lambda e: self._open_profile_overlay())
            w.bind("<Enter>",    lambda e: [c.configure(text_color=C_GREEN)
                                            for c in info.winfo_children()
                                            if hasattr(c, "configure")])
            w.bind("<Leave>",    lambda e: None)
            for child in w.winfo_children():
                _bind_hover(child)

        _bind_hover(self._acct_outer)

    # ── VERSION LIST ──────────────────────────────────────────────────────────

    def _refresh_versions(self, silent=False):
        for w in self._ver_scroll.winfo_children():
            w.destroy()
        self._ver_rows         = []
        self._ver_id_map       = {}
        self._selected_ver_idx = None

        # Use filesystem scan so ALL versions (modpacks, Fabric, etc.) show up
        installed_ids = get_all_installed_versions(self.mc_dir)

        for i, vid in enumerate(installed_ids):
            name, icon = get_version_info(self.mc_dir, vid)
            self._ver_id_map[i] = vid

            row = ctk.CTkFrame(
                self._ver_scroll,
                fg_color="transparent",
                corner_radius=10, cursor="hand2")
            row.pack(fill="x", pady=2)

            row_inner = ctk.CTkFrame(row, fg_color=C_GLASS2,
                                      corner_radius=10, border_width=1,
                                      border_color=C_BORDER)
            row_inner.pack(fill="x")

            ctk.CTkLabel(row_inner, text=icon,
                         font=("Segoe UI", 12), width=28
                         ).pack(side="left", padx=(10, 4), pady=8)
            ctk.CTkLabel(row_inner, text=name,
                         font=F_LIST, text_color=C_TEXT,
                         anchor="w").pack(side="left", pady=8)

            def _enter(e, r=row_inner, idx=i):
                if self._selected_ver_idx != idx:
                    r.configure(border_color=C_BORDER2)
            def _leave(e, r=row_inner, idx=i):
                if self._selected_ver_idx != idx:
                    r.configure(border_color=C_BORDER)
            def _click(e, idx=i, r=row_inner): self._select_version(idx)

            row_inner.bind("<Enter>",    _enter)
            row_inner.bind("<Leave>",    _leave)
            row_inner.bind("<Button-1>", _click)
            for child in row_inner.winfo_children():
                child.bind("<Enter>",    _enter)
                child.bind("<Leave>",    _leave)
                child.bind("<Button-1>", _click)

            self._ver_rows.append(row_inner)

        # Auto-select: first try latest release, then latest snapshot
        if installed_ids:
            # find latest non-snapshot first
            best_idx = 0
            for i2, vid2 in enumerate(installed_ids):
                vj2 = os.path.join(self.mc_dir, "versions", vid2, f"{vid2}.json")
                try:
                    with open(vj2) as f2:
                        d2 = json.load(f2)
                    if d2.get("type") == "release":
                        best_idx = i2
                        break
                except Exception:
                    pass
            self.after(50, lambda idx=best_idx: self._select_version(idx))

        if not silent:
            self._log(f"Found {len(installed_ids)} installed version(s).")

    def _select_version(self, idx):
        if self._selected_ver_idx is not None:
            old = self._ver_rows[self._selected_ver_idx]
            old.configure(fg_color=C_GLASS2, border_color=C_BORDER)
        self._selected_ver_idx = idx
        row = self._ver_rows[idx]
        row.configure(fg_color=C_SEL, border_color=C_SEL_BD)
        # Update version details panel
        ver_id = self._ver_id_map.get(idx)
        if ver_id and hasattr(self, "_ver_detail_col"):
            self._render_version_details(ver_id)

    # ── CONTENT AREA ──────────────────────────────────────────────────────────

    def _build_content(self):
        c = self._content

        # Top bar
        top = ctk.CTkFrame(c, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16, 8))

        ctk.CTkLabel(top, text="Version Details  ·  Skin Showcase",
                     font=("Outfit", 12, "bold"),
                     text_color=C_TEXT).pack(side="left")

        glass_sep(c, C_BORDER)

        # Main panel — skin showcase + version details side by side
        self._main_panel = ctk.CTkFrame(c, fg_color="transparent")
        self._main_panel.pack(fill="both", expand=True)
        self._build_main_panel()

        # Log panel (hidden initially)
        self._log_frame = ctk.CTkFrame(c, fg_color="transparent")
        self._build_log_panel()

    def _build_main_panel(self):
        p = self._main_panel

        # ── LEFT: Skin Showcase ───────────────────────────────────────────────
        skin_col = ctk.CTkFrame(p, fg_color=C_GLASS,
                                 border_color=C_BORDER, border_width=1,
                                 corner_radius=16, width=220)
        skin_col.pack(side="left", fill="y", padx=(12, 6), pady=12)
        skin_col.pack_propagate(False)

        ctk.CTkLabel(skin_col, text="SKIN SHOWCASE", font=F_LABEL,
                     text_color=C_MUTED).pack(pady=(16, 0))

        self._skin_preview_lbl = ctk.CTkLabel(skin_col, text="", image=None)
        self._skin_preview_lbl.pack(pady=(12, 4))

        self._skin_name_lbl = ctk.CTkLabel(
            skin_col, text=self._username or "—",
            font=("Outfit", 13, "bold"), text_color=C_TEXT)
        self._skin_name_lbl.pack()

        ctk.CTkLabel(skin_col, text="offline player",
                     font=F_SMALL, text_color=C_MUTED).pack(pady=(2, 12))

        ctk.CTkButton(skin_col, text="🎨  Change Skin",
                       command=self._upload_skin,
                       font=("Outfit", 10, "bold"), height=34,
                       fg_color=C_GLASS2, hover_color=C_BORDER2,
                       text_color=C_TEXT, corner_radius=10,
                       border_width=1, border_color=C_BORDER
                       ).pack(fill="x", padx=14, pady=(0, 14))

        self._refresh_skin_showcase()

        # ── RIGHT: Version Details ────────────────────────────────────────────
        self._ver_detail_col = ctk.CTkFrame(p, fg_color="transparent")
        self._ver_detail_col.pack(side="left", fill="both", expand=True,
                                   padx=(6, 12), pady=12)

        self._render_version_details(None)

    def _refresh_skin_showcase(self):
        sp = self._skin_path()
        if sp:
            img = extract_body_preview(sp, scale=6)
        else:
            # placeholder silhouette
            ph = Image.new("RGBA", (16*6, 28*6), (0, 0, 0, 0))
            draw = ImageDraw.Draw(ph)
            draw.rectangle([24, 0, 72, 48],  fill=(30, 60, 35, 180))
            draw.rectangle([0,  48, 24, 120], fill=(30, 60, 35, 180))
            draw.rectangle([24, 48, 72, 120], fill=(30, 60, 35, 180))
            draw.rectangle([72, 48, 96, 120], fill=(30, 60, 35, 180))
            draw.rectangle([24, 120, 48, 168], fill=(30, 60, 35, 180))
            draw.rectangle([48, 120, 72, 168], fill=(30, 60, 35, 180))
            img = ctk.CTkImage(ph, size=(16*6, 28*6))
        self._img_refs.append(img)
        self._skin_preview_lbl.configure(image=img)

    def _render_version_details(self, ver_id):
        col = self._ver_detail_col
        for w in col.winfo_children():
            w.destroy()

        if ver_id is None:
            # Empty state
            empty = ctk.CTkFrame(col, fg_color=C_GLASS,
                                  border_color=C_BORDER, border_width=1,
                                  corner_radius=16)
            empty.pack(fill="both", expand=True)
            ctk.CTkLabel(empty, text="⬛",
                          font=("Segoe UI", 36), text_color=C_DIM).pack(pady=(60, 8))
            ctk.CTkLabel(empty, text="Select a version to see details",
                          font=("Outfit", 12), text_color=C_MUTED).pack()
            return

        name, icon = get_version_info(self.mc_dir, ver_id)

        # Load version JSON for extra info
        vj_path = os.path.join(self.mc_dir, "versions", ver_id, f"{ver_id}.json")
        v_type = "release"
        v_time = "—"
        inherits = "—"
        jar_size = "—"
        try:
            with open(vj_path) as f:
                d = json.load(f)
            v_type   = d.get("type", "release")
            raw_time = d.get("releaseTime") or d.get("time", "")
            if raw_time:
                v_time = raw_time[:10]          # just YYYY-MM-DD
            inherits = d.get("inheritsFrom", "vanilla")
        except Exception:
            pass

        jar_path = os.path.join(self.mc_dir, "versions", ver_id, f"{ver_id}.jar")
        if os.path.exists(jar_path):
            size_mb  = os.path.getsize(jar_path) / (1024 * 1024)
            jar_size = f"{size_mb:.1f} MB"

        # Card
        card = ctk.CTkFrame(col, fg_color=C_GLASS,
                             border_color=C_SEL_BD, border_width=1,
                             corner_radius=16)
        card.pack(fill="both", expand=True)

        # Header row inside card
        hdr = ctk.CTkFrame(card, fg_color=C_GLASS2, corner_radius=0, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text=icon, font=("Segoe UI", 22)).pack(
            side="left", padx=(18, 8))
        title_col = ctk.CTkFrame(hdr, fg_color="transparent")
        title_col.pack(side="left", fill="y", pady=8)
        ctk.CTkLabel(title_col, text=name,
                      font=("Outfit", 14, "bold"), text_color=C_TEXT,
                      anchor="w").pack(anchor="w")
        ctk.CTkLabel(title_col, text=ver_id,
                      font=F_SMALL, text_color=C_MUTED,
                      anchor="w").pack(anchor="w")

        # Stats grid
        stats = ctk.CTkFrame(card, fg_color="transparent")
        stats.pack(fill="x", padx=20, pady=18)

        def stat_row(label, value, accent=False):
            row = ctk.CTkFrame(stats, fg_color=C_GLASS2,
                                corner_radius=10, border_width=1,
                                border_color=C_BORDER)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=label, font=F_LABEL, text_color=C_MUTED,
                          width=120, anchor="w").pack(side="left", padx=14, pady=10)
            ctk.CTkLabel(row, text=value, font=("Outfit", 10, "bold"),
                          text_color=C_GREEN if accent else C_TEXT,
                          anchor="w").pack(side="left")

        stat_row("TYPE",         v_type.upper())
        stat_row("RELEASE DATE", v_time)
        stat_row("BASE VERSION", inherits)
        stat_row("JAR SIZE",     jar_size)
        stat_row("LOCATION",     os.path.join(".minecraft", "versions", ver_id))

        # Actions row
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 18))

        def open_folder():
            folder = os.path.join(self.mc_dir, "versions", ver_id)
            try:
                import subprocess as sp2
                sp2.Popen(["xdg-open", folder])
            except Exception:
                pass

        ctk.CTkButton(actions, text="📁  Open Folder",
                       command=open_folder,
                       font=("Outfit", 10, "bold"), height=36,
                       fg_color=C_GLASS2, hover_color=C_BORDER2,
                       text_color=C_TEXT, corner_radius=10,
                       border_width=1, border_color=C_BORDER
                       ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(actions, text="▶  Launch This",
                       command=self._launch_game,
                       font=("Outfit", 10, "bold"), height=36,
                       fg_color=C_GREEN2, hover_color=C_GREEN,
                       text_color=C_BG, corner_radius=10
                       ).pack(side="left")

    def _build_log_panel(self):
        p = self._log_frame

        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(hdr, text="Game Output",
                     font=("Outfit", 11, "bold"),
                     text_color=C_MUTED).pack(side="left")
        back_btn = ctk.CTkButton(hdr, text="← News", font=F_SMALL,
                                  width=70, height=26,
                                  fg_color=C_GLASS2,
                                  hover_color=C_BORDER2,
                                  text_color=C_MUTED,
                                  corner_radius=8,
                                  command=self._show_news)
        back_btn.pack(side="right")

        glass_sep(p, C_BORDER)

        log_outer = ctk.CTkFrame(p, fg_color=C_GLASS,
                                  border_color=C_BORDER, border_width=1,
                                  corner_radius=14)
        log_outer.pack(fill="both", expand=True, padx=14, pady=10)

        self._log_area = tk.Text(
            log_outer, state="disabled",
            bg=C_GLASS, fg=C_TEXT,
            insertbackground=C_GREEN,
            font=F_MONO, relief="flat", bd=12,
            wrap="word", highlightthickness=0,
            selectbackground=C_BORDER2)
        self._log_area.pack(fill="both", expand=True)
        self._log_area.tag_config("info",    foreground=C_MUTED)
        self._log_area.tag_config("success", foreground=C_GREEN)
        self._log_area.tag_config("error",   foreground=C_ERROR)

        scrollbar = ctk.CTkScrollbar(log_outer, command=self._log_area.yview,
                                      button_color=C_BORDER2,
                                      button_hover_color=C_MUTED)
        scrollbar.pack(side="right", fill="y")
        self._log_area.configure(yscrollcommand=scrollbar.set)

    def _show_log(self):
        self._main_panel.pack_forget()
        self._log_frame.pack(fill="both", expand=True)

    def _show_news(self):
        self._log_frame.pack_forget()
        self._main_panel.pack(fill="both", expand=True)

    def _log(self, msg, tag="info"):
        self._log_area.configure(state="normal")
        self._log_area.insert("end", f"  > {msg}\n", tag)
        self._log_area.configure(state="disabled")
        self._log_area.see("end")

    def _set_status(self, text, color=None):
        self._status_lbl.configure(text=f"● {text}",
                                    text_color=color or C_MUTED)

    # ── OVERLAY SYSTEM ────────────────────────────────────────────────────────

    def _close_overlay(self):
        if self._overlay:
            try:
                self._overlay.destroy()
            except Exception:
                pass
            self._overlay = None

    def _make_overlay(self, w=500, h=340, title=""):
        self._close_overlay()
        dim = tk.Canvas(self, highlightthickness=0, bd=0, bg="#000000")
        dim.place(relx=0, rely=0, relwidth=1, relheight=1)
        dim.configure(bg="#000000")
        dim.create_rectangle(0, 0, 9999, 9999,
                             fill="#000000", stipple="gray50", outline="")
        self._overlay = dim
        dim.bind("<Button-1>",
                 lambda e: self._close_overlay() if e.widget == dim else None)

        # Glass card
        card = ctk.CTkFrame(dim, fg_color=C_GLASS,
                             border_color=C_BORDER2, border_width=1,
                             corner_radius=18, width=w, height=h)
        card.place(relx=.5, rely=.5, anchor="center")
        card.pack_propagate(False)

        # Header bar
        hdr = ctk.CTkFrame(card, fg_color=C_GLASS2, corner_radius=0,
                            height=46)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        if title:
            ctk.CTkLabel(hdr, text=title, font=("Outfit", 11, "bold"),
                          text_color=C_TEXT).pack(side="left", padx=18)

        x_btn = ctk.CTkLabel(hdr, text="✕", font=("Outfit", 12),
                              text_color=C_MUTED, cursor="hand2")
        x_btn.pack(side="right", padx=14)
        x_btn.bind("<Button-1>", lambda e: self._close_overlay())
        x_btn.bind("<Enter>",    lambda e: x_btn.configure(text_color=C_TEXT))
        x_btn.bind("<Leave>",    lambda e: x_btn.configure(text_color=C_MUTED))

        glass_sep(card, C_BORDER)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=18)

        return dim, body

    # ── PROFILE OVERLAY ───────────────────────────────────────────────────────

    def _open_profile_overlay(self):
        dim, body = self._make_overlay(w=520, h=330, title="Profile")

        cols = ctk.CTkFrame(body, fg_color="transparent")
        cols.pack(fill="both", expand=True)

        # Left buttons
        left = ctk.CTkFrame(cols, fg_color="transparent", width=130)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)

        for txt, cmd in [
            ("Switch\nAccount", self._open_switch_overlay),
            ("Logout",          self._logout),
        ]:
            btn = ctk.CTkButton(left, text=txt, command=cmd,
                                 font=("Outfit", 9, "bold"), height=60,
                                 fg_color=C_GLASS2, hover_color=C_BORDER2,
                                 text_color=C_TEXT, corner_radius=12,
                                 border_width=1, border_color=C_BORDER)
            btn.pack(fill="x", pady=(0, 8))

        # Center skin preview
        center = ctk.CTkFrame(cols, fg_color="transparent")
        center.pack(side="left", expand=True)

        sp = self._skin_path()
        if sp:
            bimg = extract_body_preview(sp, scale=5)
            self._img_refs.append(bimg)
            ctk.CTkLabel(center, image=bimg, text="").pack(pady=(0, 10))
        else:
            ctk.CTkLabel(center, text="👤", font=("Segoe UI", 54),
                          text_color=C_MUTED).pack(pady=(0, 10))

        ctk.CTkLabel(center, text=self._username or "—",
                      font=("Outfit", 12, "bold"),
                      text_color=C_TEXT).pack()

        # Right customize
        right = ctk.CTkFrame(cols, fg_color="transparent", width=130)
        right.pack(side="left", fill="y", padx=(14, 0))
        right.pack_propagate(False)

        ctk.CTkButton(right, text="Customize\nSkin",
                       command=self._upload_skin,
                       font=("Outfit", 9, "bold"), height=60,
                       fg_color=C_GLASS2, hover_color=C_BORDER2,
                       text_color=C_TEXT, corner_radius=12,
                       border_width=1, border_color=C_BORDER
                       ).pack(fill="x")

    # ── SKIN UPLOAD ───────────────────────────────────────────────────────────

    def _upload_skin(self):
        if not self._username:
            messagebox.showerror("Error", "No profile selected.")
            return
        path = filedialog.askopenfilename(
            title="Select Skin PNG",
            filetypes=[("PNG Image", "*.png")])
        if not path:
            return
        try:
            img = Image.open(path)
            if img.width != 64 or img.height not in (32, 64):
                messagebox.showerror(
                    "Invalid Skin",
                    "Skin must be 64×32 or 64×64 pixels.")
                return
        except Exception:
            messagebox.showerror("Error", "Could not read image.")
            return

        dest = os.path.join(self.skins_dir, f"{self._username}.png")
        shutil.copy2(path, dest)
        self._accounts[self._username]["skin"] = dest
        self._save_accounts()
        self._close_overlay()
        self._build_acct_card()
        if hasattr(self, "_skin_preview_lbl"):
            self._refresh_skin_showcase()
        self._open_profile_overlay()
        messagebox.showinfo("Skin Applied",
                            "Local skin saved! Will be applied on next launch.")

    # ── SWITCH ACCOUNT ────────────────────────────────────────────────────────

    def _open_switch_overlay(self):
        accts   = [k for k in self._accounts if not k.startswith("_")]
        ov_w    = max(360, min(500, 90 * (len(accts) + 1) + 80))
        dim, body = self._make_overlay(w=ov_w, h=240, title="Switch Account")

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="both", expand=True)

        for uname in accts:
            is_active = (uname == self._username)
            col = ctk.CTkFrame(row, fg_color="transparent", cursor="hand2")
            col.pack(side="left", padx=6)

            pill = ctk.CTkFrame(col,
                                 fg_color=C_SEL if is_active else C_GLASS2,
                                 border_width=1,
                                 border_color=C_GREEN2 if is_active else C_BORDER,
                                 corner_radius=12, cursor="hand2")
            pill.pack(pady=4)

            sp   = self._skin_path(uname)
            face = extract_face(sp, 44) if sp else _default_face_ctk(44)
            self._img_refs.append(face)

            face_lbl = ctk.CTkLabel(pill, image=face, text="")
            face_lbl.pack(padx=14, pady=(12, 4))
            name_lbl = ctk.CTkLabel(pill, text=uname, font=("Outfit", 8),
                                     text_color=C_GREEN if is_active else C_TEXT,
                                     wraplength=70)
            name_lbl.pack(pady=(0, 10))

            def _sw(u=uname): self._switch_account(u)
            for w in [pill, face_lbl, name_lbl]:
                w.bind("<Button-1>", lambda e, fn=_sw: fn())
                w.bind("<Enter>",    lambda e, p=pill: p.configure(border_color=C_GREEN))
                w.bind("<Leave>",    lambda e, p=pill, a=is_active:
                       p.configure(border_color=C_GREEN2 if a else C_BORDER))

        # Add account pill
        add_col = ctk.CTkFrame(row, fg_color="transparent", cursor="hand2")
        add_col.pack(side="left", padx=6)
        add_pill = ctk.CTkFrame(add_col, fg_color=C_GLASS2,
                                 border_color=C_BORDER, border_width=1,
                                 corner_radius=12, cursor="hand2")
        add_pill.pack(pady=4)
        plus_lbl = ctk.CTkLabel(add_pill, text="＋",
                                 font=("Outfit", 20, "bold"),
                                 text_color=C_GREEN)
        plus_lbl.pack(padx=18, pady=(14, 2))
        ctk.CTkLabel(add_pill, text="Add", font=("Outfit", 8),
                      text_color=C_MUTED).pack(pady=(0, 12))

        for w in [add_pill, plus_lbl]:
            w.bind("<Button-1>", lambda e: self._add_account_dialog())
            w.bind("<Enter>",    lambda e: add_pill.configure(border_color=C_GREEN))
            w.bind("<Leave>",    lambda e: add_pill.configure(border_color=C_BORDER))

    def _switch_account(self, username):
        self._username = username
        self._accounts["_active"] = username
        self._save_accounts()
        self._close_overlay()
        self._build_acct_card()
        if hasattr(self, "_skin_preview_lbl"):
            self._refresh_skin_showcase()
            self._skin_name_lbl.configure(text=username)

    def _add_account_dialog(self):
        dim, body = self._make_overlay(w=320, h=190, title="Add Account")

        ctk.CTkLabel(body, text="Enter a username",
                      font=F_BODY, text_color=C_MUTED).pack(anchor="w", pady=(0, 8))

        entry = ctk.CTkEntry(body, placeholder_text="Username…",
                              font=("Outfit", 12), height=40,
                              fg_color=C_GLASS2, border_color=C_BORDER2,
                              text_color=C_TEXT, corner_radius=10)
        entry.pack(fill="x", pady=(0, 14))
        entry.focus()

        def _confirm():
            u = entry.get().strip()
            if not u:
                return
            self._add_account(u)
            self._username = u
            self._close_overlay()
            self._build_acct_card()

        entry.bind("<Return>", lambda e: _confirm())
        ctk.CTkButton(body, text="Add Account", command=_confirm,
                       font=F_BTN, height=40, corner_radius=10,
                       fg_color=C_GREEN2, hover_color=C_GREEN,
                       text_color=C_BG).pack(fill="x")

    def _logout(self):
        self._close_overlay()
        self._accounts.pop("_active", None)
        self._save_accounts()
        self.destroy()
        MinecraftLauncher()

    # ── DOWNLOAD MANAGER ─────────────────────────────────────────────────────

    def _open_manager(self):
        dim, body = self._make_overlay(w=380, h=210, title="Download Version")

        ctk.CTkLabel(body, text="Choose a version to install",
                      font=F_BODY, text_color=C_MUTED).pack(anchor="w", pady=(0, 12))

        all_v = [v["id"] for v in minecraft_launcher_lib.utils.get_version_list()]

        combo = ctk.CTkComboBox(body, values=all_v, width=300,
                                 font=("Outfit", 10), height=38,
                                 fg_color=C_GLASS2, border_color=C_BORDER2,
                                 text_color=C_TEXT, corner_radius=10,
                                 button_color=C_GREEN2,
                                 button_hover_color=C_GREEN,
                                 dropdown_fg_color=C_GLASS,
                                 dropdown_text_color=C_TEXT,
                                 dropdown_hover_color=C_BORDER2)
        combo.pack(fill="x", pady=(0, 14))

        ctk.CTkButton(body, text="↓  INSTALL", font=F_BTN,
                       height=44, corner_radius=12,
                       fg_color=C_GREEN2, hover_color=C_GREEN,
                       text_color=C_BG,
                       command=lambda: self._download(combo.get())
                       ).pack(fill="x")

    def _download(self, ver):
        if not ver:
            return
        self._close_overlay()
        self._show_log()
        self._log(f"Downloading {ver} …", "info")
        self._set_status("DOWNLOADING", C_WARN)
        threading.Thread(target=self._install_thread,
                         args=(ver,), daemon=True).start()

    def _install_thread(self, ver):
        try:
            minecraft_launcher_lib.install.install_minecraft_version(
                ver, self.mc_dir)
            self._refresh_versions(silent=True)
            self._log(f"Installed {ver} successfully.", "success")
            self._set_status("IDLE")
        except Exception as e:
            self._log(f"Download failed: {e}", "error")
            self._set_status("ERROR", C_ERROR)

    # ── LAUNCH ────────────────────────────────────────────────────────────────

    def _launch_game(self):
        if self._game_running:
            return
        idx = self._selected_ver_idx
        if idx is None:
            messagebox.showwarning("No Version", "Select a version first!")
            return
        version = self._ver_id_map.get(idx, "")
        if not version:
            return

        self._show_log()
        self._log(f"Launching {version} as {self._username} …", "success")
        self._set_status("RUNNING", C_GREEN)
        self._play_btn.configure(state="disabled", text="⏳  RUNNING…",
                                  fg_color=C_GLASS2, text_color=C_MUTED)
        self._game_running = True
        threading.Thread(target=self._run_thread,
                         args=(version,), daemon=True).start()

    def _run_thread(self, version):
        try:
            player_uuid = str(uuid.uuid3(
                uuid.NAMESPACE_DNS, f"OfflinePlayer:{self._username}"))
            java_exe = "java"
            try:
                year = int(version.split(".")[0])
                if year >= 26:
                    for c in [
                        r"C:\Program Files\Eclipse Adoptium\jdk-25\bin\java.exe",
                        r"C:\Program Files\Java\jdk-25\bin\java.exe",
                    ]:
                        if os.path.exists(c):
                            java_exe = c; break
            except Exception:
                pass

            ram = "-Xmx4G" if java_exe != "java" else "-Xmx2G"
            options = {
                "username":       self._username,
                "uuid":           player_uuid,
                "token":          "0",
                "executablePath": java_exe,
                "jvmArguments":   [ram, "-Xms1G"],
            }

            injector_path = os.path.join(self.mc_dir, "authlib-injector.jar")
            if not os.path.exists(injector_path):
                self.after(0, lambda: self._log("Downloading skin injection agent…", "info"))
                try:
                    url = ("https://github.com/yushijinhun/authlib-injector"
                           "/releases/download/v1.2.7/authlib-injector-1.2.7.jar")
                    req = urllib.request.Request(
                        url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req) as resp, \
                         open(injector_path, "wb") as out:
                        out.write(resp.read())
                    self.after(0, lambda: self._log("Skin agent ready.", "info"))
                except Exception as ex:
                    self.after(0, lambda: self._log(f"Skin agent error: {ex}", "error"))

            cmd = minecraft_launcher_lib.command.get_minecraft_command(
                version, self.mc_dir, options)
            cmd = [a for a in cmd
                   if a != "--sun-misc-unsafe-memory-access=allow"]
            if os.path.exists(injector_path):
                cmd.insert(1, f"-javaagent:{injector_path}=ely.by")

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    tag = "error" if ("ERROR" in line or "Exception" in line) else "info"
                    self.after(0, lambda l=line, t=tag: self._log(l, t))
            proc.wait()
            self.after(0, lambda: self._log("Game exited.", "info"))
        except Exception as e:
            self.after(0, lambda: self._log(f"Launch error: {e}", "error"))
        finally:
            self._game_running = False
            self.after(0, self._on_game_exit)

    def _on_game_exit(self):
        self._set_status("IDLE")
        self._play_btn.configure(state="normal", text="▶   PLAY",
                                  fg_color=C_GREEN2, text_color=C_BG)
        self._log("--- session ended ---", "info")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = MinecraftLauncher()
    app.mainloop()
