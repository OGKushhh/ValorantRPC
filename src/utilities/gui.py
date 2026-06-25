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

FONT_TITLE  = ("Segoe UI", 11, "bold")
FONT_LABEL  = ("Segoe UI", 9)
FONT_VALUE  = ("Segoe UI", 9, "bold")
FONT_SMALL  = ("Segoe UI", 8)
FONT_HEADER = ("Segoe UI", 8, "bold")

WIN_W, WIN_H = 380, 480

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
        self._visible = False
        self._root    = None
        self._ready   = threading.Event()

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
        self._root.withdraw()
        self._root.title("valorant-rpc")
        self._root.geometry(f"{WIN_W}x{WIN_H}")
        self._root.resizable(False, False)
        self._root.configure(bg=BG)
        self._root.protocol("WM_DELETE_WINDOW", self._do_hide)

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

        # poll loop
        self._root.after(1000, self._poll)
        self._root.mainloop()

    def _build_ui(self):
        root = self._root

        # ── title bar ─────────────────────────────────────────────────────────
        title_frame = tk.Frame(root, bg=BG)
        title_frame.pack(fill="x", padx=16, pady=(14, 6))

        tk.Label(title_frame, text="VALORANT", fg=ACCENT,
                 bg=BG, font=("Segoe UI", 13, "bold")).pack(side="left")
        tk.Label(title_frame, text=" RPC", fg=TEXT,
                 bg=BG, font=("Segoe UI", 13, "bold")).pack(side="left")

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
                         font=FONT_LABEL, padx=12, pady=6, cursor="hand2")
            b.bind("<Button-1>", lambda e: cmd())
            b.bind("<Enter>",    lambda e: b.config(bg=hv_col))
            b.bind("<Leave>",    lambda e: b.config(bg=bg_col))
            return b

        _btn(btn_frame, "Reload", self._reload).pack(side="left", padx=(0, 6))
        _btn(btn_frame, "Exit", self._exit, danger=True).pack(side="right")

    def _build_settings(self, frame):
        """
        Render toggleable boolean settings from the live config.
        We expose the most useful ones without opening a console.
        """
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

        # Try to get live presence
        try:
            data = pref.client.fetch_presence()
        except Exception:
            data = None

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
        content = getattr(pref, "content_data", {})
        agent_id = data.get("characterId", "")
        agent_name = "—"
        for a in content.get("agents", []):
            if a.get("uuid", "").lower() == agent_id.lower():
                agent_name = a.get("displayName", "—")
                break
        self._sv["agent"].set(agent_name)

        # map (from coregame if available, else presence)
        map_name = "—"
        try:
            cg = pref.client.coregame_fetch_match()
            map_id = cg.get("MapID", "")
            for m in content.get("maps", []):
                if m.get("mapUrl", "").lower() == map_id.lower():
                    map_name = m.get("displayName", "—")
                    break
        except Exception:
            pass
        self._sv["map"].set(map_name)

        # mode
        queue_id = data.get("queueId", "")
        modes    = Localizer.get_localized_text("presences", "modes") or {}
        self._sv["mode"].set(modes.get(queue_id, queue_id or "—"))

        # rank
        try:
            from .presence_utilities import Utilities  # type: ignore
            _, rank_text = Utilities.fetch_rank_data(pref.client, content)
            self._sv["rank"].set(rank_text or "—")
        except Exception:
            self._sv["rank"].set("—")

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

    def _do_show(self):
        self._visible = True
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()

    def _do_hide(self):
        self._visible = False
        self._root.withdraw()

    def _reload(self):
        import subprocess
        self._root.after(200, lambda: os.execl(
            sys.executable, os.path.abspath(sys.executable), *sys.argv))

    def _exit(self):
        self._on_exit()


# ─────────────────────────────────────────────────────────────────────────────
# Toggle widget  (replaces checkboxes with a pill-style on/off)
# ─────────────────────────────────────────────────────────────────────────────

class _Toggle(tk.Canvas):
    W, H = 36, 18
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
