import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import sys
import json

# ─── Colour palette ────────────────────────────────────────────────────────────
BG      = "#1e1e1e"
BG2     = "#252526"
BG3     = "#2d2d30"
WIDGET  = "#3c3c3c"
BORDER  = "#454545"
FG      = "#cccccc"
FG_DIM  = "#666666"
ACCENT  = "#0078d4"
RED     = "#f44747"
YELLOW  = "#dcdcaa"
BLUE    = "#569cd6"
GREEN   = "#4ec9b0"


def _get_config_path() -> str:
    """Return path to the persistent settings JSON file."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "wiz-downloader.json")


def _setup_style():
    s = ttk.Style()
    s.theme_use("clam")

    base = dict(
        background=BG2, foreground=FG,
        fieldbackground=WIDGET, selectbackground=ACCENT, selectforeground=FG,
        bordercolor=BORDER, darkcolor=BG, lightcolor=BG3,
        troughcolor=BG3, arrowcolor=FG, insertcolor=FG,
    )
    s.configure(".", **base)
    s.configure("TFrame",            background=BG2)
    s.configure("TLabel",            background=BG2, foreground=FG)
    s.configure("TLabelframe",       background=BG2, foreground=BLUE, bordercolor=BORDER)
    s.configure("TLabelframe.Label", background=BG2, foreground=BLUE)
    s.configure("TCheckbutton",      background=BG2, foreground=FG)
    s.map("TCheckbutton",            background=[("active", BG2), ("!active", BG2)])
    s.configure("TRadiobutton",      background=BG2, foreground=FG)
    s.map("TRadiobutton",            background=[("active", BG2), ("!active", BG2)])
    s.configure("TEntry",
        fieldbackground=WIDGET, foreground=FG, insertcolor=FG,
        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
    )
    s.configure("TCombobox",
        fieldbackground=WIDGET, foreground=FG, background=WIDGET,
        arrowcolor=FG, insertcolor=FG, bordercolor=BORDER,
        selectbackground=ACCENT, selectforeground=FG,
    )
    s.map("TCombobox",
        fieldbackground=[("readonly", WIDGET), ("disabled", BG3)],
        selectbackground=[("readonly", WIDGET)],
        foreground=[("readonly", FG), ("disabled", FG_DIM)],
        background=[("readonly", WIDGET), ("active", WIDGET)],
    )
    s.configure("TSpinbox",
        fieldbackground=WIDGET, foreground=FG, background=WIDGET,
        arrowcolor=FG, insertcolor=FG, bordercolor=BORDER,
    )
    s.configure("TButton",
        background=WIDGET, foreground=FG,
        bordercolor=BORDER, padding=(8, 4),
    )
    s.map("TButton",
        background=[("active", "#4a4a4a"), ("disabled", BG3)],
        foreground=[("disabled", FG_DIM)],
    )
    s.configure("Accent.TButton", background=ACCENT, foreground="white")
    s.map("Accent.TButton",
        background=[("active", "#106ebe"), ("disabled", BG3)],
        foreground=[("disabled", FG_DIM)],
    )
    s.configure("Stop.TButton",
        background="#5a1f1f", foreground="#ff9090", bordercolor="#7a3030",
    )
    s.map("Stop.TButton",
        background=[("active", "#7a2525"), ("disabled", BG3)],
        foreground=[("disabled", FG_DIM)],
    )
    s.configure("TScrollbar",
        background=WIDGET, troughcolor=BG3, arrowcolor=FG, bordercolor=BORDER,
    )
    s.configure("TProgressbar",
        background=ACCENT, troughcolor=BG3, bordercolor=BORDER,
        lightcolor=ACCENT, darkcolor=ACCENT,
    )
    s.configure("TPanedwindow", background=BG)


def _dark_text(parent, **kw):
    """Create a dark-themed tk.Text widget."""
    defaults = dict(
        bg=WIDGET, fg=FG, insertbackground=FG,
        selectbackground=ACCENT, selectforeground=FG,
        relief="flat", borderwidth=1,
        highlightthickness=1, highlightcolor=BORDER, highlightbackground=BORDER,
    )
    defaults.update(kw)
    return tk.Text(parent, **defaults)


class WizDownloader:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Wiz Downloader")
        self.root.geometry("1360x820")
        self.root.minsize(900, 560)
        self.root.configure(bg=BG)

        self.process = None
        self.downloading = False

        _setup_style()
        self._build_ui()
        self._load_settings()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────────────────────────────────────
    # Layout
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        # ── Left: scrollable settings ─────────────────────────────────────
        left_outer = ttk.Frame(paned)
        left_outer.rowconfigure(0, weight=1)
        left_outer.columnconfigure(0, weight=1)

        self._lcanvas = tk.Canvas(left_outer, bg=BG2, highlightthickness=0, width=490)
        lsb = ttk.Scrollbar(left_outer, orient="vertical", command=self._lcanvas.yview)
        self._lcanvas.configure(yscrollcommand=lsb.set)
        self._lcanvas.grid(row=0, column=0, sticky="nsew")
        lsb.grid(row=0, column=1, sticky="ns")

        settings_frame = ttk.Frame(self._lcanvas)
        self._swin = self._lcanvas.create_window((0, 0), window=settings_frame, anchor="nw")

        settings_frame.bind("<Configure>",
            lambda e: self._lcanvas.configure(scrollregion=self._lcanvas.bbox("all")))
        self._lcanvas.bind("<Configure>",
            lambda e: self._lcanvas.itemconfig(self._swin, width=e.width))
        self._lcanvas.bind("<Enter>",
            lambda e: self._lcanvas.bind_all("<MouseWheel>", self._on_wheel))
        self._lcanvas.bind("<Leave>",
            lambda e: self._lcanvas.unbind_all("<MouseWheel>"))

        paned.add(left_outer, weight=0)

        # ── Right: log panel ──────────────────────────────────────────────
        right = ttk.Frame(paned)
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)
        paned.add(right, weight=1)

        self._build_settings(settings_frame)
        self._build_log_panel(right)

    def _on_wheel(self, event):
        self._lcanvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ─────────────────────────────────────────────────────────────────────────
    # Settings panel
    # ─────────────────────────────────────────────────────────────────────────

    def _build_settings(self, p: ttk.Frame):
        p.columnconfigure(0, weight=1)
        pad = {"padx": 8, "pady": (0, 6)}
        r = 0

        # ── Source URLs ───────────────────────────────────────────────────
        f = ttk.LabelFrame(p, text="Source URLs  (one per line)", padding=8)
        f.grid(row=r, column=0, sticky="ew", **pad); r += 1
        f.columnconfigure(0, weight=1)

        self.w_urls = _dark_text(f, height=4, font=("Consolas", 9), wrap=tk.NONE)
        self.w_urls.insert("1.0",
            "https://www.youtube.com/playlist?list=PLS3F4z7eFMfLae4p5dWTlPtCEukbmLNAs")
        self.w_urls.grid(row=0, column=0, sticky="ew")
        url_xsb = ttk.Scrollbar(f, orient="horizontal", command=self.w_urls.xview)
        self.w_urls.configure(xscrollcommand=url_xsb.set)
        url_xsb.grid(row=1, column=0, sticky="ew")

        # ── Output ────────────────────────────────────────────────────────
        f = ttk.LabelFrame(p, text="Output", padding=8)
        f.grid(row=r, column=0, sticky="ew", **pad); r += 1
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="Folder:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.v_outdir = tk.StringVar(value=r"d:\m\music\youtube")
        ttk.Entry(f, textvariable=self.v_outdir).grid(row=0, column=1, sticky="ew")
        ttk.Button(f, text="Browse…",
                   command=lambda: self._pick_dir(self.v_outdir)).grid(row=0, column=2, padx=(6, 0))

        ttk.Label(f, text="Template:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
        self.v_tmpl = tk.StringVar(value="%(title)s.%(ext)s")
        ttk.Entry(f, textvariable=self.v_tmpl).grid(row=1, column=1, sticky="ew", pady=(6, 0))
        ttk.Label(
            f, foreground=FG_DIM, font=("TkDefaultFont", 8),
            text="%(title)s  %(uploader)s  %(id)s  %(playlist_index)s  %(upload_date)s",
        ).grid(row=2, column=1, sticky="w")

        # ── Format ────────────────────────────────────────────────────────
        f = ttk.LabelFrame(p, text="Format", padding=8)
        f.grid(row=r, column=0, sticky="ew", **pad); r += 1
        f.columnconfigure(1, weight=1)
        f.columnconfigure(3, weight=1)

        ttk.Label(f, text="Mode:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.v_mode = tk.StringVar(value="audio")
        mf = ttk.Frame(f)
        mf.grid(row=0, column=1, columnspan=3, sticky="w")
        for lbl, val in [("Audio Only", "audio"), ("Video + Audio", "video"), ("Custom", "custom")]:
            ttk.Radiobutton(mf, text=lbl, variable=self.v_mode, value=val,
                            command=self._mode_changed).pack(side="left", padx=(0, 16))

        ttk.Label(f, text="Audio Format:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
        self.v_afmt = tk.StringVar(value="mp3")
        self.c_afmt = ttk.Combobox(f, textvariable=self.v_afmt, state="readonly", width=10,
                                    values=["mp3", "m4a", "ogg", "flac", "wav", "opus", "aac"])
        self.c_afmt.grid(row=1, column=1, sticky="w", pady=(6, 0))

        ttk.Label(f, text="Quality:").grid(row=1, column=2, sticky="w", padx=(16, 6), pady=(6, 0))
        self.v_aqual = tk.StringVar(value="320K")
        self.c_aqual = ttk.Combobox(
            f, textvariable=self.v_aqual, state="readonly", width=16,
            values=["320K", "256K", "192K", "128K", "96K", "64K",
                    "0 (VBR best)", "5 (VBR mid)", "9 (VBR worst)"],
        )
        self.c_aqual.grid(row=1, column=3, sticky="w", pady=(6, 0))

        ttk.Label(f, text="Video Quality:").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
        self.v_vqual = tk.StringVar(value="bestvideo+bestaudio")
        self.c_vqual = ttk.Combobox(
            f, textvariable=self.v_vqual, state="readonly", width=30,
            values=[
                "bestvideo+bestaudio",
                "bestvideo[height<=2160]+bestaudio",
                "bestvideo[height<=1080]+bestaudio",
                "bestvideo[height<=720]+bestaudio",
                "bestvideo[height<=480]+bestaudio",
                "bestvideo[height<=360]+bestaudio",
            ],
        )
        self.c_vqual.grid(row=2, column=1, sticky="w", pady=(6, 0))

        ttk.Label(f, text="Merge Into:").grid(row=2, column=2, sticky="w", padx=(16, 6), pady=(6, 0))
        self.v_mfmt = tk.StringVar(value="mp4")
        self.c_mfmt = ttk.Combobox(f, textvariable=self.v_mfmt, state="readonly", width=8,
                                    values=["mp4", "mkv", "webm", "flv"])
        self.c_mfmt.grid(row=2, column=3, sticky="w", pady=(6, 0))

        ttk.Label(f, text="Custom Format:").grid(row=3, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
        self.v_cfmt = tk.StringVar(value="bestaudio/best")
        self.e_cfmt = ttk.Entry(f, textvariable=self.v_cfmt)
        self.e_cfmt.grid(row=3, column=1, columnspan=3, sticky="ew", pady=(6, 0))

        # ── Options ───────────────────────────────────────────────────────
        f = ttk.LabelFrame(p, text="Options", padding=8)
        f.grid(row=r, column=0, sticky="ew", **pad); r += 1

        self.o_ignore_err   = tk.BooleanVar(value=True)
        self.o_embed_thumb  = tk.BooleanVar(value=True)
        self.o_embed_meta   = tk.BooleanVar(value=True)
        self.o_yes_playlist = tk.BooleanVar(value=True)
        self.o_hls_native   = tk.BooleanVar(value=False)
        self.o_no_overwrite = tk.BooleanVar(value=False)
        self.o_write_subs   = tk.BooleanVar(value=False)
        self.o_auto_subs    = tk.BooleanVar(value=False)
        self.o_write_desc   = tk.BooleanVar(value=False)
        self.o_write_info   = tk.BooleanVar(value=False)

        for var, lbl, ri, ci in [
            (self.o_ignore_err,   "Ignore Errors",     0, 0),
            (self.o_embed_thumb,  "Embed Thumbnail",   0, 1),
            (self.o_embed_meta,   "Embed Metadata",    0, 2),
            (self.o_yes_playlist, "Yes Playlist",      1, 0),
            (self.o_hls_native,   "HLS Prefer Native", 1, 1),
            (self.o_no_overwrite, "No Overwrites",     1, 2),
            (self.o_write_subs,   "Write Subtitles",   2, 0),
            (self.o_auto_subs,    "Auto Subtitles",    2, 1),
            (self.o_write_desc,   "Write Description", 2, 2),
            (self.o_write_info,   "Write Info JSON",   3, 0),
        ]:
            ttk.Checkbutton(f, text=lbl, variable=var).grid(
                row=ri, column=ci, sticky="w", padx=(0, 20), pady=2)

        # ── Advanced ──────────────────────────────────────────────────────
        f = ttk.LabelFrame(p, text="Advanced", padding=8)
        f.grid(row=r, column=0, sticky="ew", **pad); r += 1

        self.o_ratelimit = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Rate Limit:", variable=self.o_ratelimit).grid(
            row=0, column=0, sticky="w")
        self.v_ratelimit = tk.StringVar(value="1M")
        ttk.Entry(f, textvariable=self.v_ratelimit, width=8).grid(row=0, column=1, padx=(4, 2))
        ttk.Label(f, text="e.g. 500K, 2M", foreground=FG_DIM,
                  font=("TkDefaultFont", 8)).grid(row=0, column=2, sticky="w", padx=(0, 16))
        ttk.Label(f, text="Retries:").grid(row=0, column=3, sticky="w", padx=(0, 4))
        self.v_retries = tk.StringVar(value="10")
        ttk.Spinbox(f, textvariable=self.v_retries, from_=0, to=100, width=6).grid(row=0, column=4)

        ttk.Label(f, text="Concurrent Fragments:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.v_concurrent = tk.StringVar(value="1")
        ttk.Spinbox(f, textvariable=self.v_concurrent, from_=1, to=32, width=6).grid(
            row=1, column=1, pady=(6, 0))
        ttk.Label(f, text="Sleep Between (sec):").grid(row=1, column=3, sticky="w", pady=(6, 0))
        self.v_sleep = tk.StringVar(value="0")
        ttk.Spinbox(f, textvariable=self.v_sleep, from_=0, to=300, width=6).grid(
            row=1, column=4, pady=(6, 0))

        self.o_cookies = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Cookies from Browser:", variable=self.o_cookies).grid(
            row=2, column=0, sticky="w", pady=(6, 0))
        self.v_browser = tk.StringVar(value="chrome")
        ttk.Combobox(f, textvariable=self.v_browser, width=10, state="readonly",
                     values=["chrome", "firefox", "edge", "opera", "brave", "vivaldi"]).grid(
            row=2, column=1, padx=(4, 0), pady=(6, 0), columnspan=2, sticky="w")

        self.o_proxy = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Proxy:", variable=self.o_proxy).grid(
            row=2, column=3, sticky="w", pady=(6, 0))
        self.v_proxy = tk.StringVar(value="socks5://127.0.0.1:1080")
        ttk.Entry(f, textvariable=self.v_proxy, width=22).grid(
            row=2, column=4, sticky="w", pady=(6, 0))

        # ── Download Archive ──────────────────────────────────────────────
        f = ttk.LabelFrame(p, text="Download Archive", padding=8)
        f.grid(row=r, column=0, sticky="ew", **pad); r += 1
        f.columnconfigure(1, weight=1)

        self.o_archive = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            f, text="Skip already-downloaded files (archive tracking)",
            variable=self.o_archive, command=self._archive_toggled,
        ).grid(row=0, column=0, columnspan=3, sticky="w")

        ttk.Label(f, text="Archive File:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
        self.v_archive = tk.StringVar(value=r"d:\m\music\youtube\downloaded.txt")
        self.e_archive = ttk.Entry(f, textvariable=self.v_archive)
        self.e_archive.grid(row=1, column=1, sticky="ew", pady=(6, 0))
        self.b_archive = ttk.Button(f, text="Browse…", command=self._pick_archive)
        self.b_archive.grid(row=1, column=2, padx=(6, 0), pady=(6, 0))

        # ── yt-dlp Executable ─────────────────────────────────────────────
        f = ttk.LabelFrame(p, text="yt-dlp Executable", padding=8)
        f.grid(row=r, column=0, sticky="ew", **pad); r += 1
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="Path:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.v_exe = tk.StringVar(value="yt-dlp.exe")
        ttk.Entry(f, textvariable=self.v_exe).grid(row=0, column=1, sticky="ew")
        ttk.Button(f, text="Browse…", command=self._pick_exe).grid(row=0, column=2, padx=(6, 0))

        # ── Action buttons ────────────────────────────────────────────────
        act = ttk.Frame(p)
        act.grid(row=r, column=0, sticky="ew", padx=8, pady=(4, 10)); r += 1

        self.b_preview  = ttk.Button(act, text="Preview Command", command=self._preview)
        self.b_download = ttk.Button(act, text="▶  Download",
                                     command=self._start, style="Accent.TButton")
        self.b_stop     = ttk.Button(act, text="■  Stop",
                                     command=self._stop, state="disabled",
                                     style="Stop.TButton")
        self.b_preview.pack(side="left", padx=(0, 8))
        self.b_download.pack(side="left", padx=(0, 8))
        self.b_stop.pack(side="left")

        self._mode_changed()
        self._archive_toggled()

    def _build_log_panel(self, parent: ttk.Frame):
        # ── Header row ────────────────────────────────────────────────────
        hdr = ttk.Frame(parent)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 2))
        hdr.columnconfigure(1, weight=1)

        ttk.Label(hdr, text="Output Log",
                  foreground=BLUE, font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, sticky="w")
        self.l_status = ttk.Label(hdr, text="Ready", foreground=FG_DIM)
        self.l_status.grid(row=0, column=1, sticky="e")
        ttk.Button(hdr, text="Clear", command=self._clear_log).grid(
            row=0, column=2, padx=(8, 0))

        # ── Progress bar ──────────────────────────────────────────────────
        self.w_progress = ttk.Progressbar(parent, mode="indeterminate")
        self.w_progress.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 2))

        # ── Log text area ─────────────────────────────────────────────────
        self.w_log = tk.Text(
            parent, state="disabled",
            bg=BG, fg=FG, insertbackground=FG,
            selectbackground=ACCENT, selectforeground=FG,
            font=("Consolas", 9), wrap=tk.WORD,
            relief="flat", borderwidth=0, highlightthickness=0,
        )
        log_sb = ttk.Scrollbar(parent, orient="vertical", command=self.w_log.yview)
        self.w_log.configure(yscrollcommand=log_sb.set)
        self.w_log.grid(row=2, column=0, sticky="nsew", padx=(4, 0))
        log_sb.grid(row=2, column=1, sticky="ns")

        self.w_log.tag_configure("error",   foreground=RED)
        self.w_log.tag_configure("warning", foreground=YELLOW)
        self.w_log.tag_configure("header",  foreground=BLUE, font=("Consolas", 9, "bold"))
        self.w_log.tag_configure("success", foreground=GREEN)

    # ─────────────────────────────────────────────────────────────────────────
    # Widget state callbacks
    # ─────────────────────────────────────────────────────────────────────────

    def _mode_changed(self):
        m = self.v_mode.get()
        self.c_afmt.config(state="readonly" if m == "audio"              else "disabled")
        self.c_aqual.config(state="readonly" if m == "audio"             else "disabled")
        self.c_vqual.config(state="readonly" if m == "video"             else "disabled")
        self.c_mfmt.config(state="readonly"  if m in ("video", "custom") else "disabled")
        self.e_cfmt.config(state="normal"    if m == "custom"            else "disabled")

    def _archive_toggled(self):
        s = "normal" if self.o_archive.get() else "disabled"
        self.e_archive.config(state=s)
        self.b_archive.config(state=s)

    # ─────────────────────────────────────────────────────────────────────────
    # Settings persistence
    # ─────────────────────────────────────────────────────────────────────────

    def _save_settings(self):
        cfg = {
            "urls":         self.w_urls.get("1.0", tk.END).rstrip("\n"),
            "outdir":       self.v_outdir.get(),
            "tmpl":         self.v_tmpl.get(),
            "mode":         self.v_mode.get(),
            "afmt":         self.v_afmt.get(),
            "aqual":        self.v_aqual.get(),
            "vqual":        self.v_vqual.get(),
            "mfmt":         self.v_mfmt.get(),
            "cfmt":         self.v_cfmt.get(),
            "ignore_err":   self.o_ignore_err.get(),
            "embed_thumb":  self.o_embed_thumb.get(),
            "embed_meta":   self.o_embed_meta.get(),
            "yes_playlist": self.o_yes_playlist.get(),
            "hls_native":   self.o_hls_native.get(),
            "no_overwrite": self.o_no_overwrite.get(),
            "write_subs":   self.o_write_subs.get(),
            "auto_subs":    self.o_auto_subs.get(),
            "write_desc":   self.o_write_desc.get(),
            "write_info":   self.o_write_info.get(),
            "ratelimit":    self.o_ratelimit.get(),
            "ratelimit_val":self.v_ratelimit.get(),
            "retries":      self.v_retries.get(),
            "concurrent":   self.v_concurrent.get(),
            "sleep":        self.v_sleep.get(),
            "cookies":      self.o_cookies.get(),
            "browser":      self.v_browser.get(),
            "proxy":        self.o_proxy.get(),
            "proxy_val":    self.v_proxy.get(),
            "archive":      self.o_archive.get(),
            "archive_path": self.v_archive.get(),
            "exe":          self.v_exe.get(),
        }
        try:
            with open(_get_config_path(), "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2)
        except OSError:
            pass

    def _load_settings(self):
        try:
            with open(_get_config_path(), encoding="utf-8") as fh:
                cfg = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return

        def _s(key, var):
            """Set a StringVar/BooleanVar if the key exists in cfg."""
            if key in cfg:
                var.set(cfg[key])

        if "urls" in cfg:
            self.w_urls.delete("1.0", tk.END)
            self.w_urls.insert("1.0", cfg["urls"])

        _s("outdir",       self.v_outdir)
        _s("tmpl",         self.v_tmpl)
        _s("mode",         self.v_mode)
        _s("afmt",         self.v_afmt)
        _s("aqual",        self.v_aqual)
        _s("vqual",        self.v_vqual)
        _s("mfmt",         self.v_mfmt)
        _s("cfmt",         self.v_cfmt)
        _s("ignore_err",   self.o_ignore_err)
        _s("embed_thumb",  self.o_embed_thumb)
        _s("embed_meta",   self.o_embed_meta)
        _s("yes_playlist", self.o_yes_playlist)
        _s("hls_native",   self.o_hls_native)
        _s("no_overwrite", self.o_no_overwrite)
        _s("write_subs",   self.o_write_subs)
        _s("auto_subs",    self.o_auto_subs)
        _s("write_desc",   self.o_write_desc)
        _s("write_info",   self.o_write_info)
        _s("ratelimit",    self.o_ratelimit)
        _s("ratelimit_val",self.v_ratelimit)
        _s("retries",      self.v_retries)
        _s("concurrent",   self.v_concurrent)
        _s("sleep",        self.v_sleep)
        _s("cookies",      self.o_cookies)
        _s("browser",      self.v_browser)
        _s("proxy",        self.o_proxy)
        _s("proxy_val",    self.v_proxy)
        _s("archive",      self.o_archive)
        _s("archive_path", self.v_archive)
        _s("exe",          self.v_exe)

        # Re-apply widget enable/disable states after loading
        self._mode_changed()
        self._archive_toggled()

    def _on_close(self):
        self._save_settings()
        self.root.destroy()

    # ─────────────────────────────────────────────────────────────────────────
    # File / folder pickers
    # ─────────────────────────────────────────────────────────────────────────

    def _pick_dir(self, var: tk.StringVar):
        d = filedialog.askdirectory(initialdir=var.get() or os.path.expanduser("~"))
        if d:
            var.set(d.replace("/", "\\"))

    def _pick_archive(self):
        init = os.path.dirname(self.v_archive.get()) or os.path.expanduser("~")
        f = filedialog.asksaveasfilename(
            initialdir=init, defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if f:
            self.v_archive.set(f.replace("/", "\\"))

    def _pick_exe(self):
        f = filedialog.askopenfilename(
            filetypes=[("Executables", "*.exe"), ("All files", "*.*")]
        )
        if f:
            self.v_exe.set(f.replace("/", "\\"))

    # ─────────────────────────────────────────────────────────────────────────
    # Command builder
    # ─────────────────────────────────────────────────────────────────────────

    def _get_urls(self) -> list:
        raw = self.w_urls.get("1.0", tk.END)
        urls = [line.strip() for line in raw.splitlines() if line.strip()]
        if not urls:
            raise ValueError("At least one URL is required.")
        return urls

    def _build_cmd(self) -> list:
        urls = self._get_urls()
        cmd = [self.v_exe.get().strip() or "yt-dlp.exe"]

        if self.o_ignore_err.get():
            cmd.append("--ignore-errors")

        mode = self.v_mode.get()
        if mode == "audio":
            cmd += [
                "--format", "bestaudio/best",
                "--extract-audio",
                "--audio-format", self.v_afmt.get(),
                "--audio-quality", self.v_aqual.get().split()[0],
            ]
        elif mode == "video":
            cmd += [
                "--format", self.v_vqual.get(),
                "--merge-output-format", self.v_mfmt.get(),
            ]
        else:  # custom
            cmd += ["--format", self.v_cfmt.get()]
            mfmt = self.v_mfmt.get().strip()
            if mfmt:
                cmd += ["--merge-output-format", mfmt]

        out_path = os.path.join(self.v_outdir.get(), self.v_tmpl.get())
        cmd += ["--output", out_path]

        for var, flag in [
            (self.o_yes_playlist, "--yes-playlist"),
            (self.o_hls_native,   "--hls-prefer-native"),
            (self.o_embed_thumb,  "--embed-thumbnail"),
            (self.o_embed_meta,   "--embed-metadata"),
            (self.o_no_overwrite, "--no-overwrites"),
            (self.o_write_subs,   "--write-subs"),
            (self.o_auto_subs,    "--write-auto-subs"),
            (self.o_write_desc,   "--write-description"),
            (self.o_write_info,   "--write-info-json"),
        ]:
            if var.get():
                cmd.append(flag)

        try:
            retries = int(self.v_retries.get())
            if retries != 10:
                cmd += ["--retries", str(retries)]
        except ValueError:
            pass

        try:
            frags = int(self.v_concurrent.get())
            if frags > 1:
                cmd += ["--concurrent-fragments", str(frags)]
        except ValueError:
            pass

        try:
            sleep_val = float(self.v_sleep.get())
            if sleep_val > 0:
                cmd += ["--sleep-interval", str(sleep_val)]
        except ValueError:
            pass

        if self.o_ratelimit.get():
            rl = self.v_ratelimit.get().strip()
            if rl:
                cmd += ["--rate-limit", rl]

        if self.o_cookies.get():
            cmd += ["--cookies-from-browser", self.v_browser.get()]

        if self.o_proxy.get():
            px = self.v_proxy.get().strip()
            if px:
                cmd += ["--proxy", px]

        if self.o_archive.get():
            af = self.v_archive.get().strip()
            if af:
                cmd += ["--download-archive", af]

        cmd.extend(urls)
        return cmd

    # ─────────────────────────────────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────────────────────────────────

    def _preview(self):
        try:
            cmd = self._build_cmd()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            return
        self._log_header("Command Preview")
        self._log(subprocess.list2cmdline(cmd) + "\n")

    def _start(self):
        if self.downloading:
            return
        try:
            cmd = self._build_cmd()
        except ValueError as exc:
            messagebox.showwarning("Input Required", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Build Error", str(exc))
            return

        self.downloading = True
        self.b_download.config(state="disabled")
        self.b_stop.config(state="normal")
        self.l_status.config(text="Downloading…", foreground=ACCENT)
        self.w_progress.start(14)
        self._log_header("Download Started")
        self._log(subprocess.list2cmdline(cmd) + "\n\n")

        def _worker():
            try:
                if sys.platform == "win32":
                    flags = subprocess.CREATE_NO_WINDOW
                    new_session = False
                else:
                    flags = 0
                    new_session = True  # own process group so killpg works
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=flags,
                    start_new_session=new_session,
                )
                for line in self.process.stdout:
                    self._log_async(line)
                self.process.wait()
                self.root.after(0, self._on_done, self.process.returncode)
            except FileNotFoundError:
                self.root.after(
                    0, self._on_error,
                    "yt-dlp executable not found:\n{}\n\n"
                    "Make sure yt-dlp.exe is on your PATH or set the full path above.".format(
                        self.v_exe.get()),
                )
            except Exception as exc:
                self.root.after(0, self._on_error, str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _stop(self):
        p = self.process
        if p and p.poll() is None:
            if sys.platform == "win32":
                # taskkill /F /T kills the process AND all its children (e.g. ffmpeg)
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                import signal
                try:
                    os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                except ProcessLookupError:
                    p.terminate()

    def _on_done(self, rc: int):
        self.downloading = False
        self.process = None
        self.b_download.config(state="normal")
        self.b_stop.config(state="disabled")
        self.w_progress.stop()
        self.w_progress["value"] = 0
        if rc == 0:
            self.l_status.config(text="Complete \u2713", foreground=GREEN)
            self._log_header("Download Complete")
        else:
            colour = YELLOW if rc == 1 else RED
            self.l_status.config(text="Exited ({})".format(rc), foreground=colour)
            self._log_header("Finished \u2014 exit code {}".format(rc))

    def _on_error(self, msg: str):
        self.downloading = False
        self.process = None
        self.b_download.config(state="normal")
        self.b_stop.config(state="disabled")
        self.w_progress.stop()
        self.w_progress["value"] = 0
        self.l_status.config(text="Error", foreground=RED)
        self._log_header("Error")
        self._log(msg + "\n", "error")
        messagebox.showerror("Download Error", msg)

    # ─────────────────────────────────────────────────────────────────────────
    # Logging helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _write_log(self, text: str, tag=None):
        """Write to log widget — must be called from the main thread."""
        self.w_log.config(state="normal")
        self.w_log.insert(tk.END, text, (tag,) if tag else ())
        self.w_log.see(tk.END)
        self.w_log.config(state="disabled")

    def _log(self, text: str, tag=None):
        """Thread-safe log: direct on main thread, scheduled from worker."""
        if threading.current_thread() is threading.main_thread():
            self._write_log(text, tag)
        else:
            self.root.after(0, self._write_log, text, tag)

    def _log_async(self, line: str):
        """Classify and schedule a log write from the worker thread."""
        ll = line.lower()
        if "error" in ll:
            tag = "error"
        elif "warning" in ll:
            tag = "warning"
        else:
            tag = None
        self.root.after(0, self._write_log, line, tag)

    def _log_header(self, title: str):
        bar = "\u2500" * max(0, 54 - len(title))
        self._log("\n\u2500\u2500 {} {}\n".format(title, bar), "header")

    def _clear_log(self):
        self.w_log.config(state="normal")
        self.w_log.delete("1.0", tk.END)
        self.w_log.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    WizDownloader(root)
    root.mainloop()
