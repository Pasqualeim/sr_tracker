import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import webbrowser
from datetime import datetime
import threading

import psycopg
import requests

APP_NAME    = "SAP SR Tracker"
APP_VERSION = "0.3.5"

GITHUB_OWNER        = "Pasqualeim"
GITHUB_REPO         = "sr_tracker"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_LATEST_API   = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

CLIENTI = sorted([
    "Fastweb", "Ansaldo", "Ansaldo UK", "BMC", "Dedem", "Magnaghi",
    "Giesse", "LaDoria", "UCA", "Lamberti", "Carraro", "CNP", "Damiano",
], key=str.lower)


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def _env(name: str, default=None, required=False):
    v = os.environ.get(name, default)
    if required and (v is None or str(v).strip() == ""):
        raise RuntimeError(f"Variabile d'ambiente mancante: {name}")
    return v


def get_db_config():
    return {
        "user":     _env("SRDB_USER", required=True),
        "password": _env("SRDB_PASS", required=True),
        "host":     _env("SRDB_HOST", required=True),
        "port":     int(_env("SRDB_PORT", "5432")),
        "dbname":   _env("SRDB_NAME", "postgres"),
    }


def db_connect():
    cfg = get_db_config()
    return psycopg.connect(
        user=cfg["user"], password=cfg["password"],
        host=cfg["host"], port=cfg["port"], dbname=cfg["dbname"],
        connect_timeout=10, sslmode="require",
    )


def _parse_version(v: str):
    v = (v or "").strip().lstrip("v")
    parts = v.split(".")
    out = []
    for p in parts:
        digits = "".join(c for c in p if c.isdigit())
        out.append(int(digits or "0"))
    while len(out) < 3:
        out.append(0)
    return tuple(out[:3])


# ═══════════════════════════════════════════════════════════
class SRTrackerApp(tk.Tk):

    # ── Palette nero / giallo / bianco ──────────────────────
    BG       = "#1a1a1a"      # sfondo principale
    BG2      = "#242424"      # sfondo campi input
    BG_HDR   = "#111111"      # header nero profondo
    PANEL    = "#2e2e2e"      # pannelli secondari e status bar
    BORDER   = "#484848"      # contorni visibili
    FG       = "#f0f0f0"      # testo principale bianco
    FG2      = "#aaaaaa"      # testo secondario grigio chiaro
    FG_HDR   = "#f5c518"      # testo header giallo oro
    ACCENT   = "#f5c518"      # giallo principale
    GREEN    = "#4ade80"      # Open → verde chiaro leggibile su nero
    RED      = "#f87171"      # Prio H / Elimina
    ORANGE   = "#fb923c"      # Prio M
    SEL_BG   = "#3a3000"      # selezione riga → giallo scuro
    SEL_FG   = "#f5c518"      # testo selezione → giallo
    ROW_ODD  = "#1e1e1e"      # riga dispari
    ROW_EVEN = "#272727"      # riga pari

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  —  v{APP_VERSION}")
        self.geometry("1380x800")
        self.minsize(1100, 640)
        self.configure(bg=self.BG)
        self._apply_theme()
        try:
            self.iconbitmap(resource_path("app_icon.ico"))
        except Exception:
            pass
        self._build_header()
        self._build_ui()
        self._tag_rows()
        self.refresh_tree()
        self.after(1500, lambda: self.check_updates(silent_when_up_to_date=True))

    # ── Header ──────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=self.BG_HDR, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(
            hdr, text=f"  {APP_NAME}",
            bg=self.BG_HDR, fg=self.FG_HDR,
            font=("Segoe UI", 15, "bold"),
        ).pack(side="left", padx=16, pady=10)
        tk.Label(
            hdr, text=f"v{APP_VERSION}",
            bg=self.BG_HDR, fg="#888888",
            font=("Segoe UI", 10),
        ).pack(side="left", pady=14)

    # ── Theme ───────────────────────────────────────────────
    def _apply_theme(self):
        s = ttk.Style(self)
        s.theme_use("clam")

        s.configure(".",
            background=self.BG, foreground=self.FG,
            fieldbackground=self.BG2, bordercolor=self.BORDER,
            font=("Segoe UI", 10),
        )
        s.configure("TFrame",  background=self.BG)
        s.configure("TLabel",  background=self.BG, foreground=self.FG, font=("Segoe UI", 10))
        s.configure("TEntry",
            fieldbackground=self.BG2, foreground=self.FG,
            insertcolor=self.FG, bordercolor=self.BORDER,
            relief="flat", padding=4,
        )
        s.configure("TCombobox",
            fieldbackground=self.BG2, foreground=self.FG,
            background=self.BG2, bordercolor=self.BORDER,
            arrowcolor=self.FG2, padding=4,
        )
        s.map("TCombobox",
            fieldbackground=[("readonly", self.BG2)],
            foreground=[("readonly", self.FG)],
            selectbackground=[("readonly", self.SEL_BG)],
            selectforeground=[("readonly", self.SEL_FG)],
        )
        s.configure("TLabelframe",
            background=self.BG, bordercolor=self.BORDER, relief="groove",
        )
        s.configure("TLabelframe.Label",
            background=self.BG, foreground=self.ACCENT,
            font=("Segoe UI", 9, "bold"),
        )

        # ── Bottone base
        s.configure("TButton",
            background=self.PANEL, foreground=self.FG,
            bordercolor=self.BORDER, relief="flat",
            padding=(12, 7), font=("Segoe UI", 10),
        )
        s.map("TButton", background=[("active", "#3a3a3a")])

        # ── Aggiungi: sfondo verde scuro, testo verde chiaro
        s.configure("Green.TButton",
            background="#14532d", foreground="#4ade80",
            bordercolor="#166534", relief="flat",
            padding=(12, 7), font=("Segoe UI", 10, "bold"),
        )
        s.map("Green.TButton", background=[("active", "#166534")])

        # ── Aggiorna: sfondo giallo, testo nero
        s.configure("Primary.TButton",
            background=self.ACCENT, foreground="#111111",
            bordercolor="#d4a800", relief="flat",
            padding=(12, 7), font=("Segoe UI", 10, "bold"),
        )
        s.map("Primary.TButton", background=[("active", "#d4a800")])

        # ── Elimina: sfondo rosso scuro, testo rosso chiaro
        s.configure("Red.TButton",
            background="#7f1d1d", foreground="#f87171",
            bordercolor="#991b1b", relief="flat",
            padding=(12, 7), font=("Segoe UI", 10),
        )
        s.map("Red.TButton", background=[("active", "#991b1b")])

        # ── Ghost: neutro
        s.configure("Ghost.TButton",
            background=self.PANEL, foreground=self.FG2,
            bordercolor=self.BORDER, relief="flat",
            padding=(12, 7), font=("Segoe UI", 10),
        )
        s.map("Ghost.TButton", background=[("active", "#3a3a3a")])

        # ── Treeview
        s.configure("Treeview",
            background=self.ROW_ODD, foreground=self.FG,
            fieldbackground=self.ROW_ODD,
            bordercolor=self.BORDER, rowheight=30,
            font=("Segoe UI", 10),
        )
        s.configure("Treeview.Heading",
            background=self.ACCENT, foreground="#111111",
            bordercolor=self.BORDER, relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        s.map("Treeview",
            background=[("selected", self.SEL_BG)],
            foreground=[("selected", self.SEL_FG)],
        )

        s.configure("TProgressbar",
            troughcolor=self.PANEL, background=self.ACCENT,
            bordercolor=self.BORDER,
        )
        s.configure("TScrollbar",
            background=self.PANEL, troughcolor=self.BG2,
            bordercolor=self.BORDER, arrowcolor=self.FG2,
        )
        s.configure("TSeparator", background=self.BORDER)

    def _tag_rows(self):
        self.tree.tag_configure("odd",    background=self.ROW_ODD)
        self.tree.tag_configure("even",   background=self.ROW_EVEN)
        self.tree.tag_configure("open",   foreground=self.GREEN)
        self.tree.tag_configure("closed", foreground=self.FG2)
        self.tree.tag_configure("high",   foreground=self.RED)
        self.tree.tag_configure("medium", foreground=self.ORANGE)
        self.tree.tag_configure("low",    foreground=self.FG2)

    # ── Busy + threading ────────────────────────────────────
    def set_busy(self, busy: bool, msg: str = "Operazione in corso..."):
        if busy:
            self.lbl_busy.config(text=f"  ⏳  {msg}")
            self.frm_busy.pack(fill="x", padx=14, pady=(0, 6))
            self.pb.start(10)
            self._set_buttons_state("disabled")
        else:
            self.pb.stop()
            self.frm_busy.pack_forget()
            self._set_buttons_state("normal")

    def _set_buttons_state(self, state: str):
        for b in (self.btn_add, self.btn_upd, self.btn_del,
                  self.btn_csv, self.btn_filter, self.btn_reset, self.btn_clear):
            try:
                b.config(state=state)
            except Exception:
                pass

    def run_task(self, task_func, on_success=None, on_error=None,
                 on_error_title="Errore", busy_msg="Operazione in corso..."):
        self.set_busy(True, busy_msg)

        def worker():
            try:
                task_func()
                self.after(0, lambda: (self.set_busy(False), on_success() if on_success else None))
            except Exception as e:
                def _err():
                    messagebox.showerror(on_error_title, str(e))
                self.after(0, lambda: (self.set_busy(False), on_error(e) if on_error else _err()))

        threading.Thread(target=worker, daemon=True).start()

    # ── UI ──────────────────────────────────────────────────
    def _build_ui(self):
        # ── Sezione Form ──
        frm = ttk.LabelFrame(self, text="  Nuova / Modifica SR  ")
        frm.pack(fill="x", padx=14, pady=(10, 4))

        self.var_cliente   = tk.StringVar()
        self.var_sr        = tk.StringVar()
        self.var_aperta_da = tk.StringVar()
        self.var_link      = tk.StringVar()
        self.var_status    = tk.StringVar(value="Open")
        self.var_prio      = tk.StringVar(value="M")

        def lbl(parent, text):
            return ttk.Label(parent, text=text, foreground=self.FG2,
                             font=("Segoe UI", 9, "bold"), background=self.BG)

        # riga 0
        lbl(frm, "Cliente").grid(row=0, column=0, sticky="w", padx=(10, 4), pady=8)
        self.cmb_cliente = ttk.Combobox(frm, textvariable=self.var_cliente,
                                        values=CLIENTI, width=24, state="readonly")
        self.cmb_cliente.grid(row=0, column=1, sticky="w", padx=(0, 16), pady=8)
        if CLIENTI:
            self.cmb_cliente.current(0)

        lbl(frm, "SR #").grid(row=0, column=2, sticky="w", padx=(0, 4), pady=8)
        ttk.Entry(frm, textvariable=self.var_sr, width=20).grid(
            row=0, column=3, sticky="w", padx=(0, 16), pady=8)

        lbl(frm, "Aperta da").grid(row=0, column=4, sticky="w", padx=(0, 4), pady=8)
        ttk.Entry(frm, textvariable=self.var_aperta_da, width=20).grid(
            row=0, column=5, sticky="w", padx=(0, 10), pady=8)

        lbl(frm, "Status").grid(row=0, column=6, sticky="w", padx=(0, 4), pady=8)
        ttk.Combobox(frm, textvariable=self.var_status,
                     values=["Open", "Closed"], width=12, state="readonly").grid(
            row=0, column=7, sticky="w", padx=(0, 16), pady=8)

        lbl(frm, "Priorità").grid(row=0, column=8, sticky="w", padx=(0, 4), pady=8)
        ttk.Combobox(frm, textvariable=self.var_prio,
                     values=["H", "M", "L"], width=8, state="readonly").grid(
            row=0, column=9, sticky="w", padx=(0, 10), pady=8)

        # riga 1 – link
        lbl(frm, "Link").grid(row=1, column=0, sticky="w", padx=(10, 4), pady=(0, 8))
        ttk.Entry(frm, textvariable=self.var_link).grid(
            row=1, column=1, columnspan=9, sticky="we", padx=(0, 10), pady=(0, 8))

        # riga 2 – descrizione
        lbl(frm, "Descrizione").grid(row=2, column=0, sticky="nw", padx=(10, 4), pady=(0, 10))
        self.txt_descr = tk.Text(
            frm, height=3, wrap="word",
            bg=self.BG2, fg=self.FG, insertbackground=self.ACCENT,
            relief="flat", bd=0, font=("Segoe UI", 10),
            highlightthickness=1, highlightbackground=self.BORDER,
            highlightcolor=self.ACCENT,
            selectbackground=self.SEL_BG, selectforeground=self.SEL_FG,
        )
        self.txt_descr.grid(row=2, column=1, columnspan=9, sticky="we",
                            padx=(0, 10), pady=(0, 10))

        for c in range(10):
            frm.grid_columnconfigure(c, weight=1 if c in (1, 3, 5) else 0)

        # ── Bottoni ──
        btns = tk.Frame(self, bg=self.BG)
        btns.pack(fill="x", padx=14, pady=(2, 6))

        self.btn_add   = ttk.Button(btns, text="＋  Aggiungi",    command=self.add_sr,     style="Green.TButton")
        self.btn_upd   = ttk.Button(btns, text="✎  Aggiorna",     command=self.update_sr,  style="Primary.TButton")
        self.btn_del   = ttk.Button(btns, text="✕  Elimina",      command=self.delete_sr,  style="Red.TButton")
        self.btn_clear = ttk.Button(btns, text="↺  Pulisci form", command=self.clear_form, style="Ghost.TButton")
        self.btn_csv   = ttk.Button(btns, text="⬇  Esporta CSV",  command=self.export_csv, style="Ghost.TButton")

        self.btn_add.pack(side="left", padx=(0, 4))
        self.btn_upd.pack(side="left", padx=4)
        self.btn_del.pack(side="left", padx=4)
        ttk.Separator(btns, orient="vertical").pack(side="left", fill="y", padx=10, pady=3)
        self.btn_clear.pack(side="left", padx=4)
        self.btn_csv.pack(side="left", padx=4)

        # ── Busy bar ──
        self.frm_busy = tk.Frame(self, bg=self.PANEL, bd=0)
        self.lbl_busy = ttk.Label(self.frm_busy, text="", background=self.PANEL,
                                  foreground=self.ACCENT, font=("Segoe UI", 9, "bold"))
        self.pb = ttk.Progressbar(self.frm_busy, mode="indeterminate", length=300)
        self.lbl_busy.pack(side="left", padx=(8, 16), pady=4)
        self.pb.pack(side="left", pady=4)
        self.frm_busy.pack_forget()

        # ── Filtri ──
        flt = ttk.LabelFrame(self, text="  Ricerca e Filtri  ")
        flt.pack(fill="x", padx=14, pady=(4, 6))

        self.var_f_cliente   = tk.StringVar(value="Tutti")
        self.var_f_testo     = tk.StringVar()
        self.var_f_aperta_da = tk.StringVar()
        self.var_f_status    = tk.StringVar(value="Tutti")

        lbl(flt, "Cliente").grid(row=0, column=0, sticky="w", padx=(10, 4), pady=8)
        self.cmb_f_cliente = ttk.Combobox(flt, textvariable=self.var_f_cliente,
                                          values=["Tutti"] + CLIENTI, width=22, state="readonly")
        self.cmb_f_cliente.grid(row=0, column=1, sticky="w", padx=(0, 16), pady=8)
        self.cmb_f_cliente.current(0)

        lbl(flt, "Testo (SR / descr.)").grid(row=0, column=2, sticky="w", padx=(0, 4), pady=8)
        ttk.Entry(flt, textvariable=self.var_f_testo, width=28).grid(
            row=0, column=3, sticky="w", padx=(0, 16), pady=8)

        lbl(flt, "Aperta da").grid(row=0, column=4, sticky="w", padx=(0, 4), pady=8)
        ttk.Entry(flt, textvariable=self.var_f_aperta_da, width=18).grid(
            row=0, column=5, sticky="w", padx=(0, 16), pady=8)

        lbl(flt, "Status").grid(row=0, column=6, sticky="w", padx=(0, 4), pady=8)
        ttk.Combobox(flt, textvariable=self.var_f_status,
                     values=["Tutti", "Open", "Closed"], width=10, state="readonly").grid(
            row=0, column=7, sticky="w", padx=(0, 16), pady=8)

        self.btn_filter = ttk.Button(flt, text="🔍  Cerca", command=self.refresh_tree, style="Primary.TButton")
        self.btn_reset  = ttk.Button(flt, text="↺  Reset",  command=self.reset_filters, style="Ghost.TButton")
        self.btn_filter.grid(row=0, column=8, padx=(0, 6), pady=8)
        self.btn_reset.grid( row=0, column=9, padx=(0, 10), pady=8)

        # ── Tabella ──
        tree_outer = tk.Frame(self, bg=self.BORDER, bd=1)
        tree_outer.pack(fill="both", expand=True, padx=14, pady=(2, 0))

        tree_frame = tk.Frame(tree_outer, bg=self.ROW_ODD)
        tree_frame.pack(fill="both", expand=True, padx=1, pady=1)

        cols = ("id", "cliente", "sr_numero", "aperta_da", "status",
                "priorita", "data_update", "link", "descrizione")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=16)

        for c, t, w, a, stretch in [
            ("id",          "ID",            48,  "center", False),
            ("cliente",     "Cliente",       130, "w",      False),
            ("sr_numero",   "SR #",          130, "w",      False),
            ("aperta_da",   "Aperta da",     110, "w",      False),
            ("status",      "Status",        72,  "center", False),
            ("priorita",    "Prio",          50,  "center", False),
            ("data_update", "Ultimo update", 148, "w",      False),
            ("link",        "Link",          0,   "w",      False),  # nascosta
            ("descrizione", "Descrizione",   200, "w",      True),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, minwidth=w, anchor=a, stretch=stretch)

        yscroll = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.tree.yview)
        xscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.open_link_from_selected)

        # ── Status bar ──
        sb = tk.Frame(self, bg=self.PANEL, height=28)
        sb.pack(fill="x", padx=0, pady=0)
        sb.pack_propagate(False)
        self.lbl_statusbar = tk.Label(
            sb, text="", bg=self.PANEL, fg=self.ACCENT,
            font=("Segoe UI", 9, "bold"), anchor="w",
        )
        self.lbl_statusbar.pack(side="left", padx=14, pady=4)
        tk.Label(
            sb, text="Doppio click su una riga per aprire il link nel browser",
            bg=self.PANEL, fg=self.FG2, font=("Segoe UI", 9), anchor="e",
        ).pack(side="right", padx=14, pady=4)

    # ── Form helpers ────────────────────────────────────────
    def clear_form(self):
        if CLIENTI:
            self.cmb_cliente.current(0)
        else:
            self.var_cliente.set("")
        self.var_sr.set("")
        self.var_aperta_da.set("")
        self.var_link.set("")
        self.var_status.set("Open")
        self.var_prio.set("M")
        self.txt_descr.delete("1.0", "end")

    def reset_filters(self):
        self.cmb_f_cliente.current(0)
        self.var_f_testo.set("")
        self.var_f_aperta_da.set("")
        self.var_f_status.set("Tutti")
        self.refresh_tree()

    def validate_form(self):
        if not self.var_cliente.get().strip():
            messagebox.showwarning("Campo mancante", "Inserisci il Cliente.")
            return False
        if not self.var_sr.get().strip():
            messagebox.showwarning("Campo mancante", "Inserisci il numero SR.")
            return False
        if not self.var_aperta_da.get().strip():
            messagebox.showwarning("Campo mancante", "Inserisci 'Aperta da'.")
            return False
        return True

    def selected_id(self):
        sel = self.tree.selection()
        return int(self.tree.item(sel[0], "values")[0]) if sel else None

    def on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        v = self.tree.item(sel[0], "values")
        self.var_cliente.set(v[1])
        self.var_sr.set(v[2])
        self.var_aperta_da.set(v[3])
        self.var_status.set(v[4])
        self.var_prio.set(v[5])
        self.var_link.set(v[7])
        self.txt_descr.delete("1.0", "end")
        self.txt_descr.insert("1.0", v[8] or "")

    # ── Query builder ───────────────────────────────────────
    def build_filter_query(self, for_export=False):
        f_cliente   = self.var_f_cliente.get().strip()
        f_testo     = self.var_f_testo.get().strip()
        f_aperta_da = self.var_f_aperta_da.get().strip()
        f_status    = self.var_f_status.get().strip()

        if for_export:
            cols = "id, cliente, sr_numero, aperta_da, status, priorita, data_creazione, data_update, link, descrizione"
        else:
            cols = "id, cliente, sr_numero, aperta_da, status, priorita, to_char(data_update,'YYYY-MM-DD HH24:MI') as data_update, link, descrizione"

        q, p = f"select {cols} from sr where 1=1", []
        if f_cliente and f_cliente != "Tutti":
            q += " and cliente ilike %s";  p.append(f_cliente)
        if f_testo:
            q += " and (sr_numero ilike %s or descrizione ilike %s)"
            p.extend([f"%{f_testo}%", f"%{f_testo}%"])
        if f_aperta_da:
            q += " and aperta_da ilike %s"; p.append(f"%{f_aperta_da}%")
        if f_status in ("Open", "Closed"):
            q += " and status = %s";        p.append(f_status)
        q += " order by data_update desc"
        return q, p

    # ── DB actions ──────────────────────────────────────────
    def refresh_tree(self):
        def task():
            q, p = self.build_filter_query()
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(q, p)
                    self._rows = cur.fetchall()

        def ok():
            for row in self.tree.get_children():
                self.tree.delete(row)
            rows = getattr(self, "_rows", [])
            for i, r in enumerate(rows):
                tags = ["odd" if i % 2 == 0 else "even"]
                st = str(r[4]).lower()
                pr = str(r[5]).upper()
                tags.append("open" if st == "open" else "closed")
                tags.append({"H": "high", "M": "medium", "L": "low"}.get(pr, "low"))
                self.tree.insert("", "end", values=r, tags=tags)
            total = len(rows)
            open_ = sum(1 for r in rows if str(r[4]).lower() == "open")
            self.lbl_statusbar.config(
                text=f"  {total} SR  |  Aperte: {open_}  |  Chiuse: {total - open_}"
            )

        self.run_task(task, on_success=ok, on_error_title="Errore lettura", busy_msg="Carico dati...")

    def add_sr(self):
        if not self.validate_form():
            return
        vals = (
            self.var_cliente.get().strip(), self.var_sr.get().strip(),
            self.var_aperta_da.get().strip(), self.var_link.get().strip(),
            self.txt_descr.get("1.0", "end").strip(),
            self.var_status.get().strip() or "Open", self.var_prio.get().strip() or "M",
        )
        sql = """insert into sr (cliente, sr_numero, aperta_da, link, descrizione, status, priorita, data_creazione, data_update)
                 values (%s,%s,%s,%s,%s,%s,%s,now(),now())"""

        def task():
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, vals)

        def ok():
            self.refresh_tree(); self.clear_form()

        self.run_task(task, on_success=ok, on_error_title="Errore insert", busy_msg="Inserisco SR...")

    def update_sr(self):
        rid = self.selected_id()
        if rid is None:
            messagebox.showinfo("Nessuna selezione", "Seleziona una riga da aggiornare."); return
        if not self.validate_form():
            return
        vals = (
            self.var_cliente.get().strip(), self.var_sr.get().strip(),
            self.var_aperta_da.get().strip(), self.var_link.get().strip(),
            self.txt_descr.get("1.0", "end").strip(),
            self.var_status.get().strip() or "Open", self.var_prio.get().strip() or "M", rid,
        )
        sql = """update sr set cliente=%s, sr_numero=%s, aperta_da=%s, link=%s,
                 descrizione=%s, status=%s, priorita=%s, data_update=now() where id=%s"""

        def task():
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, vals)

        self.run_task(task, on_success=self.refresh_tree, on_error_title="Errore update", busy_msg="Aggiorno SR...")

    def delete_sr(self):
        rid = self.selected_id()
        if rid is None:
            messagebox.showinfo("Nessuna selezione", "Seleziona una riga da eliminare."); return
        if not messagebox.askyesno("Conferma", f"Eliminare la SR selezionata (ID {rid})?"):
            return

        def task():
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("delete from sr where id=%s", (rid,))

        def ok():
            self.refresh_tree(); self.clear_form()

        self.run_task(task, on_success=ok, on_error_title="Errore delete", busy_msg="Elimino SR...")

    def export_csv(self):
        q, p = self.build_filter_query(for_export=True)
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"sr_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            title="Salva export CSV",
        )
        if not path:
            return

        def task():
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(q, p)
                    self._csv_rows    = cur.fetchall()
                    self._csv_headers = [d.name for d in cur.description]

        def ok():
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(getattr(self, "_csv_headers", []))
                w.writerows(getattr(self, "_csv_rows", []))
            messagebox.showinfo("Export completato",
                f"Esportate {len(getattr(self, '_csv_rows', []))} righe in:\n{path}")

        self.run_task(task, on_success=ok, on_error_title="Errore export", busy_msg="Esporto CSV...")

    def open_link_from_selected(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        link = (self.tree.item(sel[0], "values")[7] or "").strip()
        if not link:
            messagebox.showinfo("Link mancante", "Questa riga non ha un link."); return
        webbrowser.open(link)

    # ── Updates ─────────────────────────────────────────────
    def check_updates(self, silent_when_up_to_date: bool = False):
        def task():
            r = requests.get(GITHUB_LATEST_API, timeout=8, headers={
                "Accept":     "application/vnd.github+json",
                "User-Agent": f"{GITHUB_REPO}/{APP_VERSION}",
            })
            if r.status_code != 200:
                raise RuntimeError(f"GitHub API error {r.status_code}: {r.text[:200]}")
            self._latest_tag = (r.json() or {}).get("tag_name", "") or ""

        def ok():
            latest_tag = getattr(self, "_latest_tag", "") or ""
            latest  = _parse_version(latest_tag)
            current = _parse_version(APP_VERSION)
            if latest == (0, 0, 0):
                if not silent_when_up_to_date:
                    messagebox.showinfo("Aggiornamenti", "Impossibile determinare la versione latest.")
                return
            if latest > current:
                if messagebox.askyesno("Aggiornamento disponibile",
                    f"Hai la v{APP_VERSION}. Disponibile: {latest_tag}.\n\nAprire la pagina di download?"):
                    webbrowser.open(GITHUB_RELEASES_URL)
            elif not silent_when_up_to_date:
                messagebox.showinfo("Aggiornamenti", f"Sei aggiornato (v{APP_VERSION}).")

        def on_error(e: Exception):
            messagebox.showwarning("Aggiornamenti", f"Check non riuscito: {e}")

        self.run_task(task, on_success=ok, on_error=on_error,
                      on_error_title="Errore aggiornamenti", busy_msg="Controllo aggiornamenti...")


if __name__ == "__main__":
    app = SRTrackerApp()
    app.mainloop()
