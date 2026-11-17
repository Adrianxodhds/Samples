import tkinter as tk
from tkinter import ttk
import urllib.request
import urllib.error
import json
import xml.etree.ElementTree as ET
import os
import re
import threading
import time
import webbrowser

SESSION_FILE = "steam_session.json"
SETTINGS_FILE = "steam_settings.json"

LANG = {
    "English": {
        "title": "Steam Client",
        "login_hdr": "STEAM LOGIN",
        "login_lbl": "Steam Custom ID, Steam64 ID or Profile URL:",
        "login_hint": "e.g. George_Turd or 76561198000000000",
        "login_btn": "Login",
        "quit_btn": "Quit",
        "settings": "Settings",
        "browser": "Browser",
        "logout": "Logout",
        "refresh": "Refresh",
        "game": "Game:",
        "filter": "Filter:",
        "inspect": "ITEM INSPECT",
        "no_img": "No image",
        "loading": "Loading...",
        "ready": "Ready.",
        "set_title": "SETTINGS",
        "set_id": "Default Steam ID / URL:",
        "set_theme": "Theme:",
        "set_lang": "Language:",
        "set_auto": "Auto-load inventory on login",
        "save": "Save",
        "cancel": "Cancel",
        "load_prof": "Loading profile...",
        "unknown": "Unknown",
        "offline": "Offline",
        "profile": "Profile:",
        "load_inv": "Loading inventory for",
        "empty_inv": "Inventory empty or private.",
        "shown": "Showing",
        "of": "of",
        "items": "items.",
        "name": "NAME:",
        "type": "TYPE:",
        "trade": "TRADABLE:",
        "market": "MARKETABLE:",
        "yes": "Yes",
        "no": "No",
        "err_prof": "Profile error:",
        "err_429": "Rate limited by Steam (429). Try again in a few minutes.",
        "err_in": "Enter a Steam ID or URL.",
        "err_404": "Profile not found."
    },
    "Hrvatski": {
        "title": "Steam Klijent",
        "login_hdr": "STEAM PRIJAVA",
        "login_lbl": "Steam Custom ID, Steam64 ID ili link profila:",
        "login_hint": "npr. George_Turd ili 76561198000000000",
        "login_btn": "Prijava",
        "quit_btn": "Izlaz",
        "settings": "Postavke",
        "browser": "Preglednik",
        "logout": "Odjava",
        "refresh": "Osvježi",
        "game": "Igra:",
        "filter": "Filter:",
        "inspect": "PREGLED PREDMETA",
        "no_img": "Nema slike",
        "loading": "Učitavam...",
        "ready": "Spremno.",
        "set_title": "POSTAVKE",
        "set_id": "Zadani Steam ID / URL:",
        "set_theme": "Tema:",
        "set_lang": "Jezik:",
        "set_auto": "Automatski učitaj inventar",
        "save": "Spremi",
        "cancel": "Odustani",
        "load_prof": "Učitavanje profila...",
        "unknown": "Nepoznato",
        "offline": "Offline",
        "profile": "Profil:",
        "load_inv": "Učitavanje za",
        "empty_inv": "Inventory je prazan ili privatan.",
        "shown": "Prikazano",
        "of": "od",
        "items": "predmeta.",
        "name": "NAZIV:",
        "type": "TIP:",
        "trade": "TRADABLE:",
        "market": "MARKETABLE:",
        "yes": "Da",
        "no": "Ne",
        "err_prof": "Greška profila:",
        "err_429": "Steam blokirao zahtjev (429). Pričekaj par minuta.",
        "err_in": "Unesi Steam ID ili link.",
        "err_404": "Profil nije pronađen."
    }
}

THEMES = {
    "Classic Green": {
        "main": "#4c5844", "dark": "#3e4637", "list": "#292d25",
        "text": "#d8ded3", "accent": "#c4b550", "btn": "#5a6a50",
        "l_bdr": "#6e7d64", "d_bdr": "#282e22"
    },
    "Dark Charcoal": {
        "main": "#2b2b2b", "dark": "#1e1e1e", "list": "#141414",
        "text": "#e0e0e0", "accent": "#66ccff", "btn": "#3c3c3c",
        "l_bdr": "#505050", "d_bdr": "#0f0f0f"
    }
}

GAMES = {
    "Team Fortress 2": ("440", "2"),
    "Counter-Strike 2": ("730", "2"),
    "Steam Community": ("753", "6"),
    "Dota 2": ("570", "2"),
    "Garry's Mod / Other": ("4000", "2")
}


class SteamClient:
    def __init__(self, root):
        self.root = root
        self.cfg = self.load_cfg()
        self.set_colors()

        self.root.title(self.t("title"))
        self.root.geometry("780x630")
        self.root.resizable(False, False)

        self.id64 = None
        self.name = self.t("unknown")
        self.state = self.t("offline")
        self.items = []
        self.filtered = []
        self.last_req = 0
        self.img_cache = {}
        self.base_img = None
        self.zoom = 0

        self.init_styles()
        self.boot()

    def t(self, key):
        lang = self.cfg.get("language", "English")
        return LANG.get(lang, LANG["English"]).get(key, key)

    def load_cfg(self):
        cfg = {"default_id": "", "theme": "Classic Green", "language": "English", "auto_inv": True}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    cfg.update(json.load(f))
            except Exception:
                pass
        return cfg

    def save_cfg(self, data):
        self.cfg.update(data)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, indent=2)
        self.set_colors()
        self.root.title(self.t("title"))

    def set_colors(self):
        c = THEMES.get(self.cfg.get("theme", "Classic Green"), THEMES["Classic Green"])
        self.c_main = c["main"]
        self.c_dark = c["dark"]
        self.c_list = c["list"]
        self.c_text = c["text"]
        self.c_acc = c["accent"]
        self.c_btn = c["btn"]
        self.c_lbdr = c["l_bdr"]
        self.c_dbdr = c["d_bdr"]
        self.root.configure(bg=self.c_main)

    def init_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(
            "TCombobox", fieldbackground=self.c_list, background=self.c_btn,
            foreground=self.c_text, darkcolor=self.c_dbdr, lightcolor=self.c_lbdr,
            selectbackground=self.c_dark, selectforeground=self.c_acc
        )

    def wipe(self):
        for w in self.root.winfo_children():
            w.destroy()

    def boot(self):
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("id64"):
                        self.id64 = data["id64"]
                        self.draw_main()
                        self.fetch_profile()
                        return
            except Exception:
                pass
        self.draw_login()

    def logout(self):
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        self.id64 = None
        self.items = []
        self.img_cache.clear()
        self.draw_login()

    def draw_login(self):
        self.wipe()

        hdr = tk.Frame(self.root, bg=self.c_dark, height=50, bd=1, relief="raised")
        hdr.pack(fill="x")
        tk.Label(hdr, text=self.t("login_hdr"), bg=self.c_dark, fg=self.c_text, font=("Tahoma", 12, "bold")).pack(side="left", padx=15, pady=12)
        tk.Button(hdr, text=self.t("settings"), command=self.open_settings, bg=self.c_btn, fg=self.c_text, font=("Tahoma", 8), bd=1, cursor="hand2").pack(side="right", padx=15, pady=10)

        wrap = tk.Frame(self.root, bg=self.c_main)
        wrap.pack(expand=True, fill="both", padx=40, pady=30)

        box = tk.Frame(wrap, bg=self.c_dark, bd=2, relief="groove", padx=25, pady=25)
        box.pack(expand=True)

        tk.Label(box, text=self.t("login_lbl"), bg=self.c_dark, fg=self.c_text, font=("Tahoma", 10, "bold")).pack(anchor="w", pady=(0, 5))
        tk.Label(box, text=self.t("login_hint"), bg=self.c_dark, fg=self.c_acc, font=("Tahoma", 8)).pack(anchor="w", pady=(0, 12))

        self.ent_login = tk.Entry(box, width=48, bg=self.c_list, fg=self.c_text, insertbackground=self.c_text, font=("Consolas", 10), bd=2, relief="sunken")
        self.ent_login.pack(pady=(0, 15))
        if self.cfg.get("default_id"):
            self.ent_login.insert(0, self.cfg["default_id"])
        self.ent_login.bind("<Return>", lambda e: self.do_login())

        self.lbl_err = tk.Label(box, text="", bg=self.c_dark, fg="#ff6b6b", font=("Tahoma", 9))
        self.lbl_err.pack(pady=(0, 10))

        btns = tk.Frame(box, bg=self.c_dark)
        btns.pack(fill="x")
        tk.Button(btns, text=self.t("login_btn"), command=self.do_login, bg=self.c_btn, fg=self.c_text, font=("Tahoma", 9, "bold"), width=18, bd=2, cursor="hand2").pack(side="left")
        tk.Button(btns, text=self.t("quit_btn"), command=self.root.quit, bg=self.c_btn, fg=self.c_text, font=("Tahoma", 9), width=12, bd=2, cursor="hand2").pack(side="right")

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title(self.t("settings"))
        win.geometry("420x350")
        win.configure(bg=self.c_main)
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text=self.t("set_title"), bg=self.c_main, fg=self.c_acc, font=("Tahoma", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 10))

        frm = tk.Frame(win, bg=self.c_dark, bd=2, relief="groove", padx=15, pady=15)
        frm.pack(fill="x", padx=20, pady=5)

        tk.Label(frm, text=self.t("set_id"), bg=self.c_dark, fg=self.c_text, font=("Tahoma", 9)).pack(anchor="w", pady=(0, 2))
        e_id = tk.Entry(frm, width=38, bg=self.c_list, fg=self.c_text, insertbackground=self.c_text, font=("Consolas", 9), bd=2, relief="sunken")
        e_id.pack(anchor="w", pady=(0, 10))
        if self.cfg.get("default_id"):
            e_id.insert(0, self.cfg["default_id"])

        tk.Label(frm, text=self.t("set_theme"), bg=self.c_dark, fg=self.c_text, font=("Tahoma", 9)).pack(anchor="w", pady=(0, 2))
        v_thm = tk.StringVar(value=self.cfg.get("theme", "Classic Green"))
        ttk.Combobox(frm, textvariable=v_thm, values=list(THEMES.keys()), state="readonly", width=36).pack(anchor="w", pady=(0, 10))

        tk.Label(frm, text=self.t("set_lang"), bg=self.c_dark, fg=self.c_text, font=("Tahoma", 9)).pack(anchor="w", pady=(0, 2))
        v_lng = tk.StringVar(value=self.cfg.get("language", "English"))
        ttk.Combobox(frm, textvariable=v_lng, values=list(LANG.keys()), state="readonly", width=36).pack(anchor="w", pady=(0, 10))

        v_auto = tk.BooleanVar(value=self.cfg.get("auto_inv", True))
        tk.Checkbutton(frm, text=self.t("set_auto"), variable=v_auto, bg=self.c_dark, fg=self.c_text, selectcolor=self.c_list, activebackground=self.c_dark, activeforeground=self.c_text, font=("Tahoma", 8)).pack(anchor="w")

        btns = tk.Frame(win, bg=self.c_main)
        btns.pack(fill="x", padx=20, pady=15)

        def save():
            self.save_cfg({"default_id": e_id.get().strip(), "theme": v_thm.get(), "language": v_lng.get(), "auto_inv": v_auto.get()})
            win.destroy()
            if self.id64:
                self.draw_main()
                self.fetch_profile()
            else:
                self.draw_login()

        tk.Button(btns, text=self.t("save"), command=save, bg=self.c_btn, fg=self.c_acc, font=("Tahoma", 9, "bold"), width=15, bd=2, cursor="hand2").pack(side="left")
        tk.Button(btns, text=self.t("cancel"), command=win.destroy, bg=self.c_btn, fg=self.c_text, font=("Tahoma", 9), width=12, bd=2, cursor="hand2").pack(side="right")

    def get_url(self, url, tries=3):
        hdrs = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        diff = time.time() - self.last_req
        if diff < 1.2:
            time.sleep(1.2 - diff)

        for i in range(tries):
            try:
                self.last_req = time.time()
                req = urllib.request.Request(url, headers=hdrs)
                with urllib.request.urlopen(req, timeout=12) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                if e.code == 429 and i < tries - 1:
                    time.sleep(3 * (i + 1))
                    continue
                raise e
            except Exception as e:
                if i < tries - 1:
                    time.sleep(2)
                    continue
                raise e
        raise Exception("Connection failed")

    def resolve_id(self, val):
        s = val.strip().rstrip("/")
        if "steamcommunity.com/profiles/" in s:
            m = re.search(r"profiles/(\d+)", s)
            return m.group(1) if m else None
        if s.isdigit() and len(s) >= 16:
            return s
        cid = s.split("/id/")[-1].split("/")[0] if "steamcommunity.com/id/" in s else s
        xml = self.get_url(f"https://steamcommunity.com/id/{cid}/?xml=1")
        node = ET.fromstring(xml).find("steamID64")
        return node.text.strip() if node is not None and node.text else None

    def do_login(self):
        val = self.ent_login.get().strip()
        if not val:
            self.lbl_err.config(text=self.t("err_in"))
            return

        self.lbl_err.config(text=self.t("loading"), fg=self.c_acc)
        self.root.update()

        def run():
            try:
                res = self.resolve_id(val)
                if res:
                    self.id64 = res
                    with open(SESSION_FILE, "w", encoding="utf-8") as f:
                        json.dump({"id64": res}, f)
                    self.root.after(0, self.on_logged_in)
                else:
                    self.root.after(0, lambda: self.lbl_err.config(text=self.t("err_404"), fg="#ff6b6b"))
            except urllib.error.HTTPError as e:
                msg = self.t("err_429") if e.code == 429 else f"HTTP {e.code}"
                self.root.after(0, lambda: self.lbl_err.config(text=msg, fg="#ff6b6b"))
            except Exception as e:
                self.root.after(0, lambda: self.lbl_err.config(text=str(e), fg="#ff6b6b"))

        threading.Thread(target=run, daemon=True).start()

    def on_logged_in(self):
        self.draw_main()
        self.fetch_profile()

    def draw_main(self):
        self.wipe()

        top = tk.Frame(self.root, bg=self.c_dark, height=65, bd=2, relief="raised")
        top.pack(fill="x")

        inf = tk.Frame(top, bg=self.c_dark)
        inf.pack(side="left", padx=15, pady=8)
        self.lbl_user = tk.Label(inf, text=self.t("load_prof"), bg=self.c_dark, fg=self.c_acc, font=("Tahoma", 12, "bold"))
        self.lbl_user.pack(anchor="w")
        self.lbl_sub = tk.Label(inf, text=f"SteamID64: {self.id64}", bg=self.c_dark, fg=self.c_text, font=("Tahoma", 8))
        self.lbl_sub.pack(anchor="w")

        r_btns = tk.Frame(top, bg=self.c_dark)
        r_btns.pack(side="right", padx=15)
        tk.Button(r_btns, text=self.t("settings"), command=self.open_settings, bg=self.c_btn, fg=self.c_text, font=("Tahoma", 8), bd=2, cursor="hand2").pack(side="left", padx=4)
        tk.Button(r_btns, text=self.t("browser"), command=lambda: webbrowser.open(f"https://steamcommunity.com/profiles/{self.id64}"), bg=self.c_btn, fg=self.c_text, font=("Tahoma", 8), bd=2, cursor="hand2").pack(side="left", padx=4)
        tk.Button(r_btns, text=self.t("logout"), command=self.logout, bg=self.c_btn, fg="#ff9999", font=("Tahoma", 8, "bold"), bd=2, cursor="hand2").pack(side="left", padx=4)

        ctrl = tk.Frame(self.root, bg=self.c_main, pady=10, padx=15)
        ctrl.pack(fill="x")

        tk.Label(ctrl, text=self.t("game"), bg=self.c_main, fg=self.c_text, font=("Tahoma", 9, "bold")).pack(side="left", padx=(0, 8))
        self.v_game = tk.StringVar(value="Team Fortress 2")
        cb = ttk.Combobox(ctrl, textvariable=self.v_game, values=list(GAMES.keys()), state="readonly", width=22)
        cb.pack(side="left", padx=(0, 10))
        cb.bind("<<ComboboxSelected>>", lambda e: self.fetch_inv())

        tk.Button(ctrl, text=self.t("refresh"), command=self.fetch_inv, bg=self.c_btn, fg=self.c_text, font=("Tahoma", 8, "bold"), bd=2, cursor="hand2").pack(side="left", padx=(0, 15))

        tk.Label(ctrl, text=self.t("filter"), bg=self.c_main, fg=self.c_text, font=("Tahoma", 9)).pack(side="left", padx=(0, 5))
        self.v_q = tk.StringVar()
        self.v_q.trace_add("write", lambda *a: self.apply_filter())
        tk.Entry(ctrl, textvariable=self.v_q, bg=self.c_list, fg=self.c_text, insertbackground=self.c_text, width=16, font=("Tahoma", 9), bd=2, relief="sunken").pack(side="left")

        body = tk.Frame(self.root, bg=self.c_main, padx=15, pady=5)
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=self.c_dark, bd=2, relief="sunken")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        sb = tk.Scrollbar(left)
        sb.pack(side="right", fill="y")

        self.lb = tk.Listbox(left, bg=self.c_list, fg=self.c_text, selectbackground=self.c_btn, selectforeground=self.c_acc, font=("Consolas", 9), bd=0, highlightthickness=0, yscrollcommand=sb.set)
        self.lb.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        sb.config(command=self.lb.yview)
        self.lb.bind("<<ListboxSelect>>", self.on_select)

        right = tk.Frame(body, bg=self.c_dark, width=280, bd=2, relief="groove")
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(right, text=self.t("inspect"), bg=self.c_dark, fg=self.c_acc, font=("Tahoma", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 5))

        img_box = tk.Frame(right, bg=self.c_list, width=130, height=130, bd=1, relief="sunken")
        img_box.pack(pady=2)
        img_box.pack_propagate(False)
        self.lbl_img = tk.Label(img_box, text=self.t("no_img"), bg=self.c_list, fg=self.c_text, font=("Tahoma", 8))
        self.lbl_img.pack(expand=True, fill="both")

        zbar = tk.Frame(right, bg=self.c_dark)
        zbar.pack(pady=4)
        tk.Button(zbar, text=" - ", command=lambda: self.do_zoom(-1), bg=self.c_btn, fg=self.c_text, font=("Tahoma", 8, "bold"), width=3, bd=1, cursor="hand2").pack(side="left", padx=2)
        tk.Button(zbar, text=" 1:1 ", command=lambda: self.do_zoom(0), bg=self.c_btn, fg=self.c_text, font=("Tahoma", 8), width=4, bd=1, cursor="hand2").pack(side="left", padx=2)
        tk.Button(zbar, text=" + ", command=lambda: self.do_zoom(1), bg=self.c_btn, fg=self.c_text, font=("Tahoma", 8, "bold"), width=3, bd=1, cursor="hand2").pack(side="left", padx=2)

        self.txt_det = tk.Text(right, bg=self.c_list, fg=self.c_text, font=("Tahoma", 8), wrap="word", bd=1, relief="sunken", state="disabled")
        self.txt_det.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.stat = tk.Label(self.root, text=self.t("ready"), bg=self.c_dark, fg=self.c_text, font=("Tahoma", 8), anchor="w", padx=10, pady=4, bd=1, relief="sunken")
        self.stat.pack(fill="x", side="bottom")

    def fetch_profile(self):
        def run():
            try:
                xml = self.get_url(f"https://steamcommunity.com/profiles/{self.id64}/?xml=1")
                r = ET.fromstring(xml)
                n = r.find("steamID")
                st = r.find("stateMessage")
                pr = r.find("privacyState")

                self.name = n.text if n is not None else self.t("unknown")
                self.state = st.text if st is not None else self.t("offline")
                priv = pr.text.upper() if pr is not None else "UNKNOWN"

                self.root.after(0, lambda: self.lbl_user.config(text=f"{self.name}  [{self.state}]"))
                self.root.after(0, lambda: self.lbl_sub.config(text=f"SteamID64: {self.id64}  |  {self.t('profile')} {priv}"))

                if self.cfg.get("auto_inv", True):
                    self.root.after(0, self.fetch_inv)
            except urllib.error.HTTPError as e:
                msg = self.t("err_429") if e.code == 429 else f"{self.t('err_prof')} {e.code}"
                self.root.after(0, lambda: self.stat.config(text=msg))
            except Exception as e:
                self.root.after(0, lambda: self.stat.config(text=f"{self.t('err_prof')} {e}"))

        threading.Thread(target=run, daemon=True).start()

    def fetch_inv(self):
        g = self.v_game.get()
        app, ctx = GAMES[g]

        self.stat.config(text=f"{self.t('load_inv')} {g}...")
        self.lb.delete(0, tk.END)
        self.set_det("")
        self.lbl_img.config(image="", text=self.t("no_img"))
        self.base_img = None
        self.zoom = 0

        def run():
            try:
                raw = self.get_url(f"https://steamcommunity.com/inventory/{self.id64}/{app}/{ctx}?l=english&count=500")
                data = json.loads(raw.decode("utf-8"))
                if not data or not data.get("success"):
                    self.root.after(0, lambda: self.stat.config(text=self.t("empty_inv")))
                    return

                descs = {f"{d.get('classid')}_{d.get('instanceid')}": d for d in data.get("descriptions", [])}
                parsed = []

                for a in data.get("assets", []):
                    info = descs.get(f"{a.get('classid')}_{a.get('instanceid')}", {})
                    icon = info.get("icon_url", "")
                    lines = [re.sub(r"<[^>]+>", "", l.get("value", "")).strip() for l in info.get("descriptions", []) if l.get("value")]
                    parsed.append({
                        "name": info.get("market_hash_name") or info.get("name") or "Unknown",
                        "type": info.get("type", ""),
                        "trade": self.t("yes") if info.get("tradable") == 1 else self.t("no"),
                        "market": self.t("yes") if info.get("marketable") == 1 else self.t("no"),
                        "url": f"https://community.cloudflare.steamstatic.com/economy/image/{icon}" if icon else "",
                        "desc": "\n".join(lines)
                    })

                self.items = parsed
                self.root.after(0, self.apply_filter)
            except urllib.error.HTTPError as e:
                msg = self.t("err_429") if e.code == 429 else f"HTTP {e.code}"
                self.root.after(0, lambda: self.stat.config(text=msg))
            except Exception as e:
                self.root.after(0, lambda: self.stat.config(text=str(e)))

        threading.Thread(target=run, daemon=True).start()

    def apply_filter(self):
        q = self.v_q.get().lower().strip()
        self.lb.delete(0, tk.END)
        self.filtered = [x for x in self.items if q in x["name"].lower() or q in x["type"].lower()]
        for x in self.filtered:
            self.lb.insert(tk.END, f" {x['name']}")
        self.stat.config(text=f"{self.t('shown')} {len(self.filtered)} {self.t('of')} {len(self.items)} {self.t('items')}")

    def on_select(self, e):
        sel = self.lb.curselection()
        if not sel:
            return
        it = self.filtered[sel[0]]
        self.set_det(f"{self.t('name')}\n{it['name']}\n\n{self.t('type')}\n{it['type']}\n\n{self.t('trade')} {it['trade']}\n{self.t('market')} {it['market']}\n{'-'*32}\n{it['desc']}")
        self.load_img(it["url"])

    def load_img(self, url):
        if not url:
            self.lbl_img.config(image="", text=self.t("no_img"))
            self.base_img = None
            return

        if url in self.img_cache:
            self.base_img = self.img_cache[url]
            self.zoom = 0
            self.render_img()
            return

        self.lbl_img.config(image="", text=self.t("loading"))
        self.base_img = None

        def run():
            try:
                b = self.get_url(url)
                self.root.after(0, lambda: self.set_img(url, b))
            except Exception:
                self.root.after(0, lambda: self.lbl_img.config(image="", text="Error"))

        threading.Thread(target=run, daemon=True).start()

    def set_img(self, url, b):
        try:
            p = tk.PhotoImage(data=b)
            self.img_cache[url] = p
            self.base_img = p
            self.zoom = 0
            self.render_img()
        except Exception:
            self.lbl_img.config(image="", text="Format error")

    def render_img(self):
        if not self.base_img:
            return
        try:
            if self.zoom == 0:
                img = self.base_img
            elif self.zoom > 0:
                img = self.base_img.zoom(self.zoom + 1, self.zoom + 1)
            else:
                img = self.base_img.subsample(abs(self.zoom) + 1, abs(self.zoom) + 1)
            self.disp_img = img
            self.lbl_img.config(image=img, text="")
        except Exception:
            self.lbl_img.config(image="", text="Error")

    def do_zoom(self, step):
        if not self.base_img:
            return
        if step == 0:
            self.zoom = 0
        elif step > 0 and self.zoom < 3:
            self.zoom += 1
        elif step < 0 and self.zoom > -2:
            self.zoom -= 1
        self.render_img()

    def set_det(self, txt):
        self.txt_det.config(state="normal")
        self.txt_det.delete("1.0", tk.END)
        self.txt_det.insert("1.0", txt)
        self.txt_det.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    SteamClient(root)
    root.mainloop()