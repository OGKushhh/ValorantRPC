import tkinter as tk
from tkinter import ttk, font
import threading
import ctypes
import os
import sys
import time

# ── win32 console handle (kept for hide/show of the legacy console) ──────────
kernel32 = ctypes.WinDLL('kernel32')
user32   = ctypes.WinDLL('user32')
hWnd     = kernel32.GetConsoleWindow()

# ── shared state written by the presence loop ────────────────────────────────
class GUIState:
    status       = "Starting…"
    agent        = ""
    map_name     = ""
    mode         = ""
    rank         = ""
    party        = ""
    game_state   = ""   # MENUS / PREGAME / INGAME / STARTUP
    version      = ""
    config       = None   # set by Startup after config is ready
    presence_ref = None   # set by Startup; used to read live data

# ─────────────────────────────────────────────────────────────────────────────
# Colours & fonts
# ─────────────────────────────────────────────────────────────────────────────
BG          = "#0f0f14"
SURFACE     = "#16161e"
SURFACE2    = "#1e1e2a"
ACCENT      = "#ff4655"          # Valorant red
ACCENT_DIM  = "#992933"
TEXT        = "#e8e8f0"
TEXT_DIM    = "#6e6e8a"
GREEN       = "#4caf50"
YELLOW      = "#ffc107"

FONT_TITLE  = ("Segoe UI", 13, "bold")
FONT_LABEL  = ("Segoe UI", 11)
FONT_VALUE  = ("Segoe UI", 11, "bold")
FONT_SMALL  = ("Segoe UI", 10)
FONT_HEADER = ("Segoe UI", 10, "bold")

WIN_W, WIN_H = 420, 640

# ── locale code → human-readable display name ────────────────────────────────
LOCALE_NAMES = {
    "en-US":  "English (US)",
    "ar-AE":  "العربية",
    "de-DE":  "Deutsch",
    "es-ES":  "Español (España)",
    "es-MX":  "Español (México)",
    "fr-FR":  "Français",
    "id-ID":  "Bahasa Indonesia",
    "it-IT":  "Italiano",
    "ja-JP":  "日本語",
    "ko-KR":  "한국어",
    "pt-BR":  "Português (Brasil)",
    "ru-RU":  "Русский",
    "th-TH":  "ไทย",
    "tr-TR":  "Türkçe",
    "vi-VN":  "Tiếng Việt",
    "pl-PL":  "Polski",
    "zh-CN":  "中文 (简体)",
    "zh-TW":  "中文 (繁體)",
    "fil-PH": "Filipino",
    "sv-SE":  "Svenska",
    "ms-MY":  "Bahasa Melayu",
    "da-DK":  "Dansk",
    "fi-FI":  "Suomi",
    "cs-CZ":  "Čeština",
    "hi-IN":  "हिन्दी",
    "nl-NL":  "Nederlands",
}

# ─────────────────────────────────────────────────────────────────────────────

class StatusDot(tk.Canvas):
    """Small animated dot that pulses green when presence is active."""

    def __init__(self, parent, **kw):
        super().__init__(parent, width=10, height=10,
                         bg=BG, highlightthickness=0, **kw)
        self._dot  = self.create_oval(1, 1, 9, 9, fill=TEXT_DIM, outline="")
        self._on   = False
        self._tick = 0

    def set_active(self, active: bool):
        self._on = active
        self._animate()

    def _animate(self):
        if self._on:
            alpha = abs((self._tick % 20) - 10) / 10   # 0→1→0
            r = int(0x4c + (0x80 - 0x4c) * alpha)
            g = int(0xaf)
            b = int(0x50 + (0x20 - 0x50) * alpha)
            color = f"#{r:02x}{g:02x}{b:02x}"
        else:
            color = TEXT_DIM
        self.itemconfig(self._dot, fill=color)
        self._tick += 1
        self.after(100, self._animate)


class Separator(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, height=1, bg=SURFACE2, **kw)


def _row(parent, label, var, row_idx):
    """Helper: label + value pair in a two-column grid."""
    tk.Label(parent, text=label, fg=TEXT_DIM, bg=SURFACE,
             font=FONT_LABEL, anchor="w").grid(
        row=row_idx, column=0, sticky="w", padx=(12, 6), pady=3)
    lbl = tk.Label(parent, textvariable=var, fg=TEXT, bg=SURFACE,
                   font=FONT_VALUE, anchor="w")
    lbl.grid(row=row_idx, column=1, sticky="w", padx=(0, 12), pady=3)
    return lbl


# ─────────────────────────────────────────────────────────────────────────────

class MainWindow:
    """
    The main GUI window.  Lives on the tkinter main thread.
    Call MainWindow.show() / .hide() from any thread.
    """

    _instance = None   # singleton

    def __init__(self, on_exit_callback):
        MainWindow._instance = self
        self._on_exit = on_exit_callback
        self._visible = True
        self._root    = None
        self._ready   = threading.Event()
        self._close_notice_shown = False

        # StringVars — created after root exists
        self._sv = {}

        # Build in main thread via after()
        threading.Thread(target=self._run, daemon=True, name="gui-thread").start()
        self._ready.wait(timeout=5)

    # ── public API ────────────────────────────────────────────────────────────

    @classmethod
    def get(cls):
        return cls._instance

    def show(self):
        if self._root:
            self._root.after(0, self._do_show)

    def hide(self):
        if self._root:
            self._root.after(0, self._do_hide)

    def toggle(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def destroy(self):
        if self._root:
            self._root.after(0, self._root.destroy)

    # ── internal ──────────────────────────────────────────────────────────────

    def _run(self):
        self._root = tk.Tk()
        self._root.title("valorant-rpc")
        self._root.geometry(f"{WIN_W}x{WIN_H}")
        self._center_window()
        self._root.resizable(False, False)
        self._root.configure(bg=BG)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close_attempt)

        # Windows: remove from taskbar when hidden, use app icon
        self._root.wm_attributes("-topmost", False)
        try:
            ico_path = os.path.join(
                os.environ.get("APPDATA", ""), "valorant-rpc", "favicon.ico")
            if os.path.exists(ico_path):
                self._root.iconbitmap(ico_path)
        except Exception:
            pass

        # ── string variables ──────────────────────────────────────────────────
        for key in ("status", "agent", "map", "mode", "rank",
                    "party", "game_state", "version"):
            self._sv[key] = tk.StringVar(value="—")

        self._build_ui()
        self._ready.set()

        # hide the old console window permanently now that we have a real GUI
        user32.ShowWindow(hWnd, 0)

        # background worker does all the blocking network calls — the Tk
        # main thread only ever reads the cache it fills in, so the GUI
        # never freezes waiting on the Riot client API
        self._fetch_cache = {"ready": False}
        self._fetch_lock = threading.Lock()
        threading.Thread(target=self._fetch_worker, daemon=True,
                         name="gui-fetch-worker").start()

        # poll loop
        self._root.after(1000, self._poll)
        self._root.mainloop()

    def _fetch_worker(self):
        """Runs forever on its own thread, doing the blocking presence/rank/
        map lookups, and stashing the results for the UI thread to read."""
        while True:
            cache = {"ready": True}
            try:
                pref = GUIState.presence_ref
                if pref is None or pref.client is None:
                    cache["no_client"] = True
                else:
                    try:
                        data = pref.client.fetch_presence()
                    except Exception:
                        data = None
                    cache["data"] = data

                    if data is not None:
                        content = getattr(pref, "content_data", {})
                        cache["content"] = content

                        map_name = None
                        try:
                            cg = pref.client.coregame_fetch_match()
                            map_name = cg.get("MapID", "")
                        except Exception:
                            pass
                        cache["map_id"] = map_name

                        try:
                            from .presence_utilities import Utilities  # type: ignore
                            _, rank_text = Utilities.fetch_rank_data(pref.client, content)
                            cache["rank_text"] = rank_text
                        except Exception:
                            cache["rank_text"] = None
            except Exception:
                pass

            with self._fetch_lock:
                self._fetch_cache = cache

            time.sleep(1)

    def _build_ui(self):
        root = self._root

        # ── title bar ─────────────────────────────────────────────────────────
        title_frame = tk.Frame(root, bg=BG)
        title_frame.pack(fill="x", padx=16, pady=(14, 6))

        tk.Label(title_frame, text="VALORANT", fg=ACCENT,
                 bg=BG, font=("Segoe UI", 16, "bold")).pack(side="left")
        tk.Label(title_frame, text=" RPC", fg=TEXT,
                 bg=BG, font=("Segoe UI", 16, "bold")).pack(side="left")

        ver_lbl = tk.Label(title_frame, textvariable=self._sv["version"],
                           fg=TEXT_DIM, bg=BG, font=FONT_SMALL)
        ver_lbl.pack(side="left", padx=(6, 0), pady=(3, 0))

        # status dot + label
        dot_frame = tk.Frame(title_frame, bg=BG)
        dot_frame.pack(side="right")
        self._dot = StatusDot(dot_frame)
        self._dot.pack(side="left", padx=(0, 4))
        self._status_lbl = tk.Label(dot_frame, textvariable=self._sv["status"],
                                    fg=TEXT_DIM, bg=BG, font=FONT_SMALL)
        self._status_lbl.pack(side="left")

        Separator(root).pack(fill="x", padx=16, pady=4)

        # ── status card ───────────────────────────────────────────────────────
        tk.Label(root, text="PRESENCE", fg=TEXT_DIM, bg=BG,
                 font=FONT_HEADER).pack(anchor="w", padx=16, pady=(6, 2))

        card = tk.Frame(root, bg=SURFACE, bd=0)
        card.pack(fill="x", padx=16, pady=(0, 8))
        card.columnconfigure(1, weight=1)

        self._rows = {}
        fields = [
            ("State",  "game_state"),
            ("Agent",  "agent"),
            ("Map",    "map"),
            ("Mode",   "mode"),
            ("Rank",   "rank"),
            ("Party",  "party"),
        ]
        for i, (label, key) in enumerate(fields):
            self._rows[key] = _row(card, label, self._sv[key], i)

        Separator(root).pack(fill="x", padx=16, pady=4)

        # ── settings card ─────────────────────────────────────────────────────
        tk.Label(root, text="QUICK SETTINGS", fg=TEXT_DIM, bg=BG,
                 font=FONT_HEADER).pack(anchor="w", padx=16, pady=(6, 2))

        settings_frame = tk.Frame(root, bg=SURFACE)
        settings_frame.pack(fill="x", padx=16, pady=(0, 8))

        self._setting_vars  = {}
        self._setting_keys  = {}   # maps display label → config key path

        self._build_settings(settings_frame)

        Separator(root).pack(fill="x", padx=16, pady=4)

        # ── bottom buttons ────────────────────────────────────────────────────
        btn_frame = tk.Frame(root, bg=BG)
        btn_frame.pack(fill="x", padx=16, pady=(4, 14))

        def _btn(parent, text, cmd, danger=False):
            fg_col = "#ffffff"
            bg_col = ACCENT if danger else SURFACE2
            hv_col = ACCENT_DIM if danger else "#2a2a3a"
            b = tk.Label(parent, text=text, fg=fg_col, bg=bg_col,
                         font=("Segoe UI", 11), padx=18, pady=10, cursor="hand2")
            b.bind("<Button-1>", lambda e: cmd())
            b.bind("<Enter>",    lambda e: b.config(bg=hv_col))
            b.bind("<Leave>",    lambda e: b.config(bg=bg_col))
            return b

        _btn(btn_frame, "Exit", self._exit, danger=True).pack(side="right")

    def _build_settings(self, frame):
        """
        Render toggleable boolean settings from the live config.
        We expose the most useful ones without opening a console.
        """
        # ── locale selector ──────────────────────────────────────────────────
        from ..localization.locales import Locales

        locale_row = tk.Frame(frame, bg=SURFACE)
        locale_row.pack(fill="x", padx=12, pady=(8, 3))

        tk.Label(locale_row, text="Locale", fg=TEXT, bg=SURFACE,
                 font=FONT_LABEL, anchor="w").pack(side="left", fill="x", expand=True)

        locale_codes = sorted(code for code, data in Locales.items() if data != {})
        # display-name → code and code → display-name (fall back to the
        # raw code itself for any locale not in our name map)
        self._locale_code_to_name = {
            code: LOCALE_NAMES.get(code, code) for code in locale_codes
        }
        self._locale_name_to_code = {
            name: code for code, name in self._locale_code_to_name.items()
        }
        display_names = sorted(self._locale_code_to_name.values())

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Locale.TCombobox",
                         fieldbackground=SURFACE2, background=SURFACE2,
                         foreground=TEXT, arrowcolor=TEXT,
                         bordercolor=SURFACE2, lightcolor=SURFACE2,
                         darkcolor=SURFACE2, relief="flat")
        style.map("Locale.TCombobox",
                  fieldbackground=[("readonly", SURFACE2)],
                  foreground=[("readonly", TEXT)])

        self._locale_var = tk.StringVar(value=self._locale_code_to_name["en-US"])
        locale_box = ttk.Combobox(locale_row, textvariable=self._locale_var,
                                  values=display_names, state="readonly",
                                  style="Locale.TCombobox", width=18,
                                  font=FONT_LABEL)
        locale_box.pack(side="right")
        locale_box.bind("<<ComboboxSelected>>", self._on_locale_change)

        TOGGLES = [
            # (display label,  config path as tuple of keys)
            ("Show rank in comp lobby",   ("presences", "menu", "show_rank_in_comp_lobby")),
            ("Show rank in range",        ("presences", "modes", "range", "show_rank_in_range")),
            ("Show GitHub link",          ("startup", "show_github_link")),
            ("Auto-launch SkinCLI",       ("startup", "auto_launch_skincli")),
        ]

        for i, (label, path) in enumerate(TOGGLES):
            var = tk.BooleanVar(value=False)
            self._setting_vars[label] = (var, path)

            row = tk.Frame(frame, bg=SURFACE)
            row.pack(fill="x", padx=12, pady=3)

            tk.Label(row, text=label, fg=TEXT, bg=SURFACE,
                     font=FONT_LABEL, anchor="w").pack(side="left", fill="x", expand=True)

            toggle = _Toggle(row, var, command=lambda l=label: self._on_toggle(l))
            toggle.pack(side="right")

        # refresh interval spinner
        spin_row = tk.Frame(frame, bg=SURFACE)
        spin_row.pack(fill="x", padx=12, pady=(3, 8))

        tk.Label(spin_row, text="Refresh interval (s)", fg=TEXT, bg=SURFACE,
                 font=FONT_LABEL, anchor="w").pack(side="left", fill="x", expand=True)

        self._interval_var = tk.IntVar(value=3)
        spin = tk.Spinbox(spin_row, from_=1, to=30, width=4,
                          textvariable=self._interval_var,
                          bg=SURFACE2, fg=TEXT, buttonbackground=SURFACE2,
                          relief="flat", font=FONT_LABEL,
                          command=self._on_interval_change)
        spin.pack(side="right")
        self._interval_var.trace_add("write", lambda *_: self._on_interval_change())

    # ── poll ──────────────────────────────────────────────────────────────────

    def _poll(self):
        """Called every second from the tkinter event loop to refresh UI."""
        try:
            self._refresh_status()
            self._refresh_settings()
        except Exception:
            pass
        self._root.after(1000, self._poll)

    def _refresh_status(self):
        cfg = GUIState.config
        if cfg is None:
            self._sv["status"].set("Waiting for config…")
            self._dot.set_active(False)
            return

        from ..localization.localization import Localizer

        ver = Localizer.get_config_value("version") if cfg else "—"
        self._sv["version"].set(ver)

        pref = GUIState.presence_ref
        if pref is None or pref.client is None:
            self._sv["status"].set("Waiting for Valorant…")
            self._dot.set_active(False)
            for key in ("game_state", "agent", "map", "mode", "rank", "party"):
                self._sv[key].set("—")
            return

        with self._fetch_lock:
            cache = self._fetch_cache

        if not cache.get("ready") or cache.get("no_client"):
            self._sv["status"].set("Waiting for Valorant…")
            self._dot.set_active(False)
            for key in ("game_state", "agent", "map", "mode", "rank", "party"):
                self._sv[key].set("—")
            return

        data = cache.get("data")
        if data is None:
            self._sv["status"].set("Presence unavailable")
            self._dot.set_active(False)
            return

        self._dot.set_active(True)
        self._sv["status"].set("Active")
        self._status_lbl.config(fg=GREEN)

        gs = GUIState.game_state or data.get("sessionLoopState", "—")
        self._sv["game_state"].set(gs.title() if gs else "—")

        # agent
        content = cache.get("content", {})
        agent_id = data.get("characterId", "")
        agent_name = "—"
        for a in content.get("agents", []):
            if a.get("uuid", "").lower() == agent_id.lower():
                agent_name = a.get("displayName", "—")
                break
        self._sv["agent"].set(agent_name)

        # map (from coregame if available, else presence)
        map_name = "—"
        map_id = cache.get("map_id") or ""
        for m in content.get("maps", []):
            if m.get("mapUrl", "").lower() == map_id.lower():
                map_name = m.get("displayName", "—")
                break
        self._sv["map"].set(map_name)

        # mode
        queue_id = data.get("queueId", "")
        modes    = Localizer.get_localized_text("presences", "modes") or {}
        self._sv["mode"].set(modes.get(queue_id, queue_id or "—"))

        # rank
        self._sv["rank"].set(cache.get("rank_text") or "—")

        # party
        party_state, party_size = self._build_party(data)
        if party_size:
            self._sv["party"].set(f"{party_state}  {party_size[0]}/{party_size[1]}")
        else:
            self._sv["party"].set(party_state or "—")

    @staticmethod
    def _build_party(data):
        from ..localization.localization import Localizer
        size     = data.get("partySize", 1)
        access   = data.get("partyAccessibility", "CLOSED")
        max_size = data.get("maxPartySize", 5)
        if size > 1:
            state = Localizer.get_localized_text("presences", "party_states", "in_party")
            return state, [max(size, 1), max_size]
        elif access == "OPEN":
            state = Localizer.get_localized_text("presences", "party_states", "open")
            return state, [1, max_size]
        else:
            return Localizer.get_localized_text("presences", "party_states", "solo"), None

    def _refresh_settings(self):
        cfg = GUIState.config
        if cfg is None:
            return
        from ..localization.localization import Localizer

        try:
            code = cfg.get("locale", [None, None])[0]
            name = self._locale_code_to_name.get(code, code)
            if name and self._locale_var.get() != name:
                self._locale_var.set(name)
        except Exception:
            pass

        for label, (var, path) in self._setting_vars.items():
            try:
                val = cfg
                for k in path:
                    loc_k = Localizer.get_config_key(k)
                    val = val.get(loc_k, val.get(k, None))
                if isinstance(val, bool):
                    var.set(val)
            except Exception:
                pass

        try:
            interval = Localizer.get_config_value("presence_refresh_interval")
            if isinstance(interval, (int, float)):
                self._interval_var.set(int(interval))
        except Exception:
            pass

    # ── settings callbacks ────────────────────────────────────────────────────

    def _on_locale_change(self, _event=None):
        cfg = GUIState.config
        if cfg is None:
            return
        from ..localization.localization import Localizer
        from .config.app_config import Config

        selected_name = self._locale_var.get()
        new_locale = self._locale_name_to_code.get(selected_name, selected_name)

        # Config keys (e.g. "presences", "presence_refresh_interval") are
        # stored translated to the *current* locale's words. To switch
        # locales we must: unlocalize keys back to canonical English,
        # swap the active locale, then relocalize keys to the new locale.
        # Skipping this leaves stale (old-locale) key names that the new
        # locale's Localizer.get_config_key() can't find → KeyError.
        cfg = Config.localize_config(cfg, unlocalize=True)
        cfg["locale"][0] = new_locale
        Localizer.locale = new_locale
        cfg = Config.localize_config(cfg, unlocalize=False)

        Localizer.config = cfg
        GUIState.config  = cfg
        Config.modify_config(cfg)

    def _on_toggle(self, label):
        cfg = GUIState.config
        if cfg is None:
            return
        var, path = self._setting_vars[label]
        new_val = var.get()
        self._write_config(path, new_val)

    def _on_interval_change(self):
        cfg = GUIState.config
        if cfg is None:
            return
        try:
            val = int(self._interval_var.get())
            if 1 <= val <= 30:
                self._write_config(("presence_refresh_interval",), val)
        except (ValueError, tk.TclError):
            pass

    @staticmethod
    def _write_config(path, value):
        from ..utilities.config.app_config import Config
        from ..localization.localization import Localizer
        cfg = GUIState.config
        if cfg is None:
            return
        node = cfg
        for k in path[:-1]:
            loc_k = Localizer.get_config_key(k)
            node = node.get(loc_k, node.get(k, {}))
        last = path[-1]
        loc_last = Localizer.get_config_key(last)
        if loc_last in node:
            node[loc_last] = value
        elif last in node:
            node[last] = value
        Config.modify_config(cfg)

    # ── window management ─────────────────────────────────────────────────────

    def _center_window(self):
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = (sw - WIN_W) // 2
        y = (sh - WIN_H) // 2
        self._root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

    def _do_show(self):
        self._visible = True
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()

    def _do_hide(self):
        self._visible = False
        self._root.withdraw()

    def _on_close_attempt(self):
        """Clicking the X minimizes (hides) the window instead of quitting —
        show a one-time-per-launch toast explaining that, then hide."""
        if not self._close_notice_shown:
            self._close_notice_shown = True
            self._show_toast(
                "The app will keep running in the background.\n"
                "Press Exit if you want to close it for good.")
        self._do_hide()

    def _show_toast(self, message, duration_ms=4000):
        """Small borderless notification that appears in the bottom-right
        corner above the taskbar and disappears on its own."""
        try:
            toast = tk.Toplevel(self._root)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            toast.configure(bg=SURFACE2)

            frame = tk.Frame(toast, bg=SURFACE2,
                             highlightbackground=ACCENT, highlightthickness=1)
            frame.pack(fill="both", expand=True)

            tk.Label(frame, text="valorant-rpc", fg=ACCENT, bg=SURFACE2,
                     font=FONT_HEADER, anchor="w").pack(
                fill="x", padx=12, pady=(10, 2))
            tk.Label(frame, text=message, fg=TEXT, bg=SURFACE2,
                     font=FONT_LABEL, justify="left", anchor="w",
                     wraplength=260).pack(fill="x", padx=12, pady=(0, 10))

            toast.update_idletasks()
            w, h = toast.winfo_width(), toast.winfo_height()
            sw = toast.winfo_screenwidth()
            sh = toast.winfo_screenheight()
            x = sw - w - 16
            y = sh - h - 60   # clear the taskbar
            toast.geometry(f"{w}x{h}+{x}+{y}")

            toast.after(duration_ms, toast.destroy)
        except Exception:
            pass

    def _exit(self):
        self._on_exit()


# ─────────────────────────────────────────────────────────────────────────────
# Toggle widget  (replaces checkboxes with a pill-style on/off)
# ─────────────────────────────────────────────────────────────────────────────

class _Toggle(tk.Canvas):
    W, H = 44, 22
    PAD  = 2

    def __init__(self, parent, variable: tk.BooleanVar, command=None, **kw):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=SURFACE, highlightthickness=0, cursor="hand2", **kw)
        self._var     = variable
        self._command = command
        self._track   = self.create_rounded_rect(0, 0, self.W, self.H, 9, fill=SURFACE2)
        self._knob    = self.create_oval(self.PAD, self.PAD,
                                         self.H - self.PAD, self.H - self.PAD,
                                         fill=TEXT_DIM, outline="")
        self._var.trace_add("write", lambda *_: self._redraw())
        self.bind("<Button-1>", self._click)
        self._redraw()

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1+r, y1, x2-r, y1, x2, y1,
               x2, y1+r, x2, y2-r, x2, y2,
               x2-r, y2, x1+r, y2, x1, y2,
               x1, y2-r, x1, y1+r, x1, y1]
        return self.create_polygon(pts, smooth=True, **kw)

    def _click(self, _event):
        self._var.set(not self._var.get())
        if self._command:
            self._command()

    def _redraw(self):
        on = self._var.get()
        self.itemconfig(self._track, fill=ACCENT if on else SURFACE2)
        x = self.W - self.H + self.PAD if on else self.PAD
        self.coords(self._knob, x, self.PAD, x + self.H - 2*self.PAD, self.H - self.PAD)
        self.itemconfig(self._knob, fill=TEXT if on else TEXT_DIM)
