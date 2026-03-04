import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import webbrowser
from datetime import datetime
import threading

import psycopg  # pip install psycopg[binary]
import requests  # pip install requests

APP_NAME = "SAP SR Tracker"
APP_VERSION = "0.3.4"  # aggiorna quando fai release/tag su GitHub (es. 0.3.4)

# === GitHub repo (per update check) ===
GITHUB_OWNER = "Pasqualeim"
GITHUB_REPO = "sr_tracker"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_LATEST_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

CLIENTI = sorted([
    "Fastweb", "Ansaldo", "Ansaldo UK", "BMC", "Dedem", "Magnaghi",
    "Giesse", "LaDoria", "UCA", "Lamberti", "Carraro", "CNP", "Damiano",
], key=str.lower)


# === DB config via Environment Variables (no password in chiaro) ===
def _env(name: str, default=None, required=False):
    v = os.environ.get(name, default)
    if required and (v is None or str(v).strip() == ""):
        raise RuntimeError(f"Variabile d'ambiente mancante: {name}")
    return v


DB_USER = _env("SRDB_USER", required=True)
DB_PASS = _env("SRDB_PASS", required=True)
DB_HOST = _env("SRDB_HOST", required=True)
DB_PORT = int(_env("SRDB_PORT", "5432"))
DB_NAME = _env("SRDB_NAME", "postgres")


def db_connect():
    return psycopg.connect(
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        connect_timeout=10,
        sslmode="require",
    )


def _parse_version(v: str):
    # accetta "v1.2.3" o "1.2.3" (confronto solo MAJOR.MINOR.PATCH)
    v = (v or "").strip()
    if v.startswith("v"):
        v = v[1:]
    parts = v.split(".")
    out = []
    for p in parts:
        digits = "".join([c for c in p if c.isdigit()])
        out.append(int(digits or "0"))
    while len(out) < 3:
        out.append(0)
    return tuple(out[:3])


class SRTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} (v{APP_VERSION})")
        self.geometry("1220x720")
        self.minsize(1000, 620)

        self._build_ui()
        self.refresh_tree()

        # Check aggiornamenti automatico: popup solo se serve (o errore).
        self.after(1500, lambda: self.check_updates(silent_when_up_to_date=True))

    # ---------- Busy/progress + threading ----------
    def set_busy(self, busy: bool, msg: str = "Operazione in corso..."):
        if busy:
            self.lbl_busy.config(text=msg)
            self.frm_busy.pack(fill="x", padx=10, pady=(0, 8))
            self.pb.start(10)
            self._set_buttons_state("disabled")
        else:
            self.pb.stop()
            self.frm_busy.pack_forget()
            self._set_buttons_state("normal")

    def _set_buttons_state(self, state: str):
        for b in (self.btn_add, self.btn_upd, self.btn_del, self.btn_csv, self.btn_filter, self.btn_reset, self.btn_clear):
            try:
                b.config(state=state)
            except Exception:
                pass

    def run_task(self, task_func, on_success=None, on_error=None, on_error_title="Errore", busy_msg="Operazione in corso..."):
        self.set_busy(True, busy_msg)

        def worker():
            try:
                task_func()
                self.after(0, lambda: (self.set_busy(False), on_success() if on_success else None))
            except Exception as e:
                def _default_error():
                    messagebox.showerror(on_error_title, str(e))
                self.after(0, lambda: (self.set_busy(False), on_error(e) if on_error else _default_error()))

        threading.Thread(target=worker, daemon=True).start()

    # ---------- UI ----------
    def _build_ui(self):
        frm = ttk.LabelFrame(self, text="Dettaglio SR")
        frm.pack(fill="x", padx=10, pady=10)

        self.var_cliente = tk.StringVar()
        self.var_sr = tk.StringVar()
        self.var_aperta_da = tk.StringVar()
        self.var_link = tk.StringVar()
        self.var_status = tk.StringVar(value="Open")
        self.var_prio = tk.StringVar(value="M")

        ttk.Label(frm, text="Cliente").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.cmb_cliente = ttk.Combobox(frm, textvariable=self.var_cliente, values=CLIENTI, width=26, state="readonly")
        self.cmb_cliente.grid(row=0, column=1, sticky="w", padx=6, pady=6)
        if CLIENTI:
            self.cmb_cliente.current(0)

        ttk.Label(frm, text="SR #").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        ttk.Entry(frm, textvariable=self.var_sr, width=18).grid(row=0, column=3, sticky="w", padx=6, pady=6)

        ttk.Label(frm, text="Aperta da").grid(row=0, column=4, sticky="w", padx=6, pady=6)
        ttk.Entry(frm, textvariable=self.var_aperta_da, width=20).grid(row=0, column=5, sticky="w", padx=6, pady=6)

        ttk.Label(frm, text="Link").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(frm, textvariable=self.var_link, width=96).grid(row=1, column=1, columnspan=5, sticky="we", padx=6, pady=6)

        ttk.Label(frm, text="Status").grid(row=2, column=0, sticky="w", padx=6, pady=6)
        ttk.Combobox(frm, textvariable=self.var_status, values=["Open", "Closed"], width=23, state="readonly") \
            .grid(row=2, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(frm, text="Priorità").grid(row=2, column=2, sticky="w", padx=6, pady=6)
        ttk.Combobox(frm, textvariable=self.var_prio, values=["H", "M", "L"], width=15, state="readonly") \
            .grid(row=2, column=3, sticky="w", padx=6, pady=6)

        ttk.Label(frm, text="Descrizione").grid(row=3, column=0, sticky="nw", padx=6, pady=6)
        self.txt_descr = tk.Text(frm, height=4, width=95, wrap="word")
        self.txt_descr.grid(row=3, column=1, columnspan=5, sticky="we", padx=6, pady=6)

        for c in range(6):
            frm.grid_columnconfigure(c, weight=1)

        # Buttons row
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(0, 8))

        self.btn_add = ttk.Button(btns, text="Aggiungi", command=self.add_sr)
        self.btn_upd = ttk.Button(btns, text="Aggiorna selezionata", command=self.update_sr)
        self.btn_del = ttk.Button(btns, text="Elimina selezionata", command=self.delete_sr)
        self.btn_csv = ttk.Button(btns, text="Esporta CSV (vista)", command=self.export_csv)
        self.btn_clear = ttk.Button(btns, text="Pulisci form", command=self.clear_form)

        self.btn_add.pack(side="left", padx=4)
        self.btn_upd.pack(side="left", padx=4)
        self.btn_del.pack(side="left", padx=4)
        self.btn_csv.pack(side="left", padx=12)
        self.btn_clear.pack(side="left", padx=4)

        # Busy bar
        self.frm_busy = ttk.Frame(self)
        self.lbl_busy = ttk.Label(self.frm_busy, text="Operazione in corso...")
        self.pb = ttk.Progressbar(self.frm_busy, mode="indeterminate")
        self.lbl_busy.pack(side="left", padx=(2, 10))
        self.pb.pack(side="left", fill="x", expand=True)
        self.frm_busy.pack_forget()

        # Filters
        flt = ttk.LabelFrame(self, text="Filtro / Ricerca")
        flt.pack(fill="x", padx=10, pady=8)

        self.var_f_cliente = tk.StringVar(value="Tutti")
        self.var_f_testo = tk.StringVar()
        self.var_f_aperta_da = tk.StringVar()
        self.var_f_status = tk.StringVar(value="Tutti")

        ttk.Label(flt, text="Cliente").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.cmb_f_cliente = ttk.Combobox(
            flt,
            textvariable=self.var_f_cliente,
            values=["Tutti"] + CLIENTI,
            width=26,
            state="readonly"
        )
        self.cmb_f_cliente.grid(row=0, column=1, sticky="w", padx=6, pady=6)
        self.cmb_f_cliente.current(0)

        ttk.Label(flt, text="Testo (SR/descr.)").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        ttk.Entry(flt, textvariable=self.var_f_testo, width=30).grid(row=0, column=3, sticky="w", padx=6, pady=6)

        ttk.Label(flt, text="Aperta da").grid(row=0, column=4, sticky="w", padx=6, pady=6)
        ttk.Entry(flt, textvariable=self.var_f_aperta_da, width=22).grid(row=0, column=5, sticky="w", padx=6, pady=6)

        ttk.Label(flt, text="Status").grid(row=0, column=6, sticky="w", padx=6, pady=6)
        ttk.Combobox(flt, textvariable=self.var_f_status, values=["Tutti", "Open", "Closed"], width=10, state="readonly") \
            .grid(row=0, column=7, sticky="w", padx=6, pady=6)

        self.btn_filter = ttk.Button(flt, text="Applica filtro", command=self.refresh_tree)
        self.btn_reset = ttk.Button(flt, text="Reset", command=self.reset_filters)
        self.btn_filter.grid(row=0, column=8, padx=6, pady=6)
        self.btn_reset.grid(row=0, column=9, padx=6, pady=6)

        for c in range(10):
            flt.grid_columnconfigure(c, weight=1)

        # Tree
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("id", "cliente", "sr_numero", "aperta_da", "status", "priorita", "data_update", "link", "descrizione")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=14)

        for c, t, w, a in [
            ("id", "ID", 60, "center"),
            ("cliente", "Cliente", 160, "w"),
            ("sr_numero", "SR #", 120, "w"),
            ("aperta_da", "Aperta da", 130, "w"),
            ("status", "Status", 80, "center"),
            ("priorita", "Prio", 60, "center"),
            ("data_update", "Ultimo update", 150, "w"),
            ("link", "Link", 260, "w"),
            ("descrizione", "Descrizione", 360, "w"),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor=a)

        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.open_link_from_selected)

        ttk.Label(self, text="Tip: doppio click su una riga per aprire il link nel browser.").pack(anchor="w", padx=12, pady=(0, 8))

    # ---------- Form ----------
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
            messagebox.showwarning("Campo mancante", "Inserisci 'Aperta da' (obbligatorio).")
            return False
        return True

    def selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(self.tree.item(sel[0], "values")[0])

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

    # ---------- Query builder ----------
    def build_filter_query(self, for_export=False):
        f_cliente = self.var_f_cliente.get().strip()
        f_testo = self.var_f_testo.get().strip()
        f_aperta_da = self.var_f_aperta_da.get().strip()
        f_status = self.var_f_status.get().strip()

        if for_export:
            select_cols = "id, cliente, sr_numero, aperta_da, status, priorita, data_creazione, data_update, link, descrizione"
        else:
            select_cols = "id, cliente, sr_numero, aperta_da, status, priorita, to_char(data_update,'YYYY-MM-DD HH24:MI') as data_update, link, descrizione"

        q = f"select {select_cols} from sr where 1=1"
        p = []

        if f_cliente and f_cliente != "Tutti":
            q += " and cliente ilike %s"
            p.append(f_cliente)

        if f_testo:
            q += " and (sr_numero ilike %s or descrizione ilike %s)"
            p.extend([f"%{f_testo}%", f"%{f_testo}%"])

        if f_aperta_da:
            q += " and aperta_da ilike %s"
            p.append(f"%{f_aperta_da}%")

        if f_status in ("Open", "Closed"):
            q += " and status = %s"
            p.append(f_status)

        q += " order by data_update desc"
        return q, p

    # ---------- DB actions ----------
    def refresh_tree(self):
        def task():
            q, p = self.build_filter_query(for_export=False)
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(q, p)
                    self._rows = cur.fetchall()

        def ok():
            for row in self.tree.get_children():
                self.tree.delete(row)
            for r in getattr(self, "_rows", []):
                self.tree.insert("", "end", values=r)

        self.run_task(task, on_success=ok, on_error_title="Errore lettura", busy_msg="Carico dati...")

    def add_sr(self):
        if not self.validate_form():
            return

        cliente = self.var_cliente.get().strip()
        sr_numero = self.var_sr.get().strip()
        aperta_da = self.var_aperta_da.get().strip()
        link = self.var_link.get().strip()
        descr = self.txt_descr.get("1.0", "end").strip()
        status = self.var_status.get().strip() or "Open"
        prio = self.var_prio.get().strip() or "M"

        sql = """
            insert into sr (cliente, sr_numero, aperta_da, link, descrizione, status, priorita, data_creazione, data_update)
            values (%s, %s, %s, %s, %s, %s, %s, now(), now())
        """

        def task():
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (cliente, sr_numero, aperta_da, link, descr, status, prio))

        def ok():
            self.refresh_tree()
            self.clear_form()

        self.run_task(task, on_success=ok, on_error_title="Errore insert", busy_msg="Inserisco SR...")

    def update_sr(self):
        rid = self.selected_id()
        if rid is None:
            messagebox.showinfo("Nessuna selezione", "Seleziona una riga da aggiornare.")
            return
        if not self.validate_form():
            return

        cliente = self.var_cliente.get().strip()
        sr_numero = self.var_sr.get().strip()
        aperta_da = self.var_aperta_da.get().strip()
        link = self.var_link.get().strip()
        descr = self.txt_descr.get("1.0", "end").strip()
        status = self.var_status.get().strip() or "Open"
        prio = self.var_prio.get().strip() or "M"

        sql = """
            update sr
            set cliente=%s, sr_numero=%s, aperta_da=%s, link=%s, descrizione=%s, status=%s, priorita=%s, data_update=now()
            where id=%s
        """

        def task():
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (cliente, sr_numero, aperta_da, link, descr, status, prio, rid))

        def ok():
            self.refresh_tree()

        self.run_task(task, on_success=ok, on_error_title="Errore update", busy_msg="Aggiorno SR...")

    def delete_sr(self):
        rid = self.selected_id()
        if rid is None:
            messagebox.showinfo("Nessuna selezione", "Seleziona una riga da eliminare.")
            return
        if not messagebox.askyesno("Conferma", f"Eliminare la SR selezionata (ID {rid})?"):
            return

        def task():
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("delete from sr where id=%s", (rid,))

        def ok():
            self.refresh_tree()
            self.clear_form()

        self.run_task(task, on_success=ok, on_error_title="Errore delete", busy_msg="Elimino SR...")

    def export_csv(self):
        q, p = self.build_filter_query(for_export=True)

        default_name = f"sr_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=default_name,
            title="Salva export CSV"
        )
        if not path:
            return

        def task():
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(q, p)
                    self._csv_rows = cur.fetchall()
                    self._csv_headers = [d.name for d in cur.description]

        def ok():
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(getattr(self, "_csv_headers", []))
                w.writerows(getattr(self, "_csv_rows", []))
            messagebox.showinfo("Export completato", f"Esportate {len(getattr(self, '_csv_rows', []))} righe in:\n{path}")

        self.run_task(task, on_success=ok, on_error_title="Errore export", busy_msg="Esporto CSV...")

    def open_link_from_selected(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        v = self.tree.item(sel[0], "values")
        link = (v[7] or "").strip()
        if not link:
            messagebox.showinfo("Link mancante", "Questa riga non ha un link.")
            return
        webbrowser.open(link)

    # ---------- Updates ----------
    def check_updates(self, silent_when_up_to_date: bool = False):
        def task():
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": f"{GITHUB_REPO}/{APP_VERSION}"
            }
            r = requests.get(GITHUB_LATEST_API, timeout=8, headers=headers)
            if r.status_code != 200:
                raise RuntimeError(f"GitHub API error {r.status_code}: {r.text[:200]}")
            self._latest_tag = (r.json() or {}).get("tag_name", "") or ""

        def ok():
            latest_tag = getattr(self, "_latest_tag", "") or ""
            latest = _parse_version(latest_tag)
            current = _parse_version(APP_VERSION)

            if latest == (0, 0, 0):
                # Tag non interpretabile (es. nessuna release)
                if not silent_when_up_to_date:
                    messagebox.showinfo("Aggiornamenti", "Impossibile determinare la versione latest su GitHub.")
                return

            if latest > current:
                if messagebox.askyesno(
                    "Aggiornamento disponibile",
                    f"Hai la v{APP_VERSION}. Ultima disponibile: {latest_tag}.\n\nAprire la pagina per scaricare la nuova versione?"
                ):
                    webbrowser.open(GITHUB_RELEASES_URL)
            else:
                if not silent_when_up_to_date:
                    messagebox.showinfo("Aggiornamenti", f"Sei aggiornato (v{APP_VERSION}).")

        def on_error(e: Exception):
            # All'avvio: segnala solo con un messaggio corto (così capisci se la rete blocca GitHub)
            messagebox.showwarning("Aggiornamenti", f"Check aggiornamenti non riuscito: {e}")

        self.run_task(task, on_success=ok, on_error=on_error, on_error_title="Errore aggiornamenti", busy_msg="Controllo aggiornamenti...")


if __name__ == "__main__":
    app = SRTrackerApp()
    app.mainloop()
