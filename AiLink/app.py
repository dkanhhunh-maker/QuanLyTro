"""AiLink - giao dien Windows (tkinter, co san trong Python)."""
import glob, json, os, threading, tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from ailink import config, engine


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AiLink - Noi cac AI")
        self.geometry("980x680")
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.run_tab, self.set_tab = ttk.Frame(nb), ttk.Frame(nb)
        nb.add(self.run_tab, text="Chay day chuyen")
        nb.add(self.set_tab, text="Cai dat AI")
        self._build_run()
        self._build_settings()

    # ---- tab chay ----
    def _build_run(self):
        f = self.run_tab
        top = ttk.Frame(f); top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Day chuyen:").pack(side="left")
        self.pl_var = tk.StringVar()
        self.pl_box = ttk.Combobox(top, textvariable=self.pl_var, state="readonly", width=60)
        self.pl_box.pack(side="left", padx=6)
        ttk.Button(top, text="Tai lai", command=self._reload_pl).pack(side="left")
        ttk.Label(f, text="Dau vao (chu de / noi dung):").pack(anchor="w", padx=8)
        self.inp = scrolledtext.ScrolledText(f, height=5)
        self.inp.pack(fill="x", padx=8)
        self.btn = ttk.Button(f, text="CHAY", command=self._run)
        self.btn.pack(pady=6)
        self.out = scrolledtext.ScrolledText(f, state="disabled")
        self.out.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._reload_pl()

    def _reload_pl(self):
        self.files = sorted(glob.glob(os.path.join(config.PIPELINE_DIR, "*.json")))
        self.pl_box["values"] = [os.path.basename(x) for x in self.files]
        if self.files and not self.pl_var.get():
            self.pl_box.current(0)

    def _log(self, text):
        self.out.config(state="normal")
        self.out.insert("end", text + "\n")
        self.out.see("end")
        self.out.config(state="disabled")

    def _run(self):
        idx = self.pl_box.current()
        text = self.inp.get("1.0", "end").strip()
        if idx < 0 or not text:
            return messagebox.showwarning("Thieu", "Chon day chuyen va nhap dau vao.")
        try:
            pl = engine.load_pipeline(self.files[idx])
        except Exception as e:
            return messagebox.showerror("Loi day chuyen", str(e))
        self.out.config(state="normal"); self.out.delete("1.0", "end"); self.out.config(state="disabled")
        self.btn.config(state="disabled")

        def cb(i, s, status, t):
            msg = {"start": f"\n>>> Buoc {i+1}: {s['name']} ({s['provider']}) ...",
                   "done": t, "error": f"!!! LOI: {t}"}[status]
            self.after(0, self._log, msg)

        def work():
            engine.run(pl, text, on_step=cb)
            self.after(0, lambda: (self.btn.config(state="normal"), self._log("\n=== Xong (luu trong thu muc runs) ===")))
        threading.Thread(target=work, daemon=True).start()

    # ---- tab cai dat ----
    def _build_settings(self):
        f = self.set_tab
        ttk.Label(f, text="Dien API key cho tung AI. Key luu trong config.json tren may anh.").pack(anchor="w", padx=8, pady=6)
        self.cfg = config.load()
        self.entries = {}
        grid = ttk.Frame(f); grid.pack(fill="x", padx=8)
        for r, (name, p) in enumerate(self.cfg["providers"].items()):
            ttk.Label(grid, text=f"{name} ({p['type']})").grid(row=r, column=0, sticky="w", pady=3)
            key = tk.StringVar(value=p.get("api_key", ""))
            model = tk.StringVar(value=p.get("model", ""))
            ttk.Entry(grid, textvariable=key, width=50, show="*").grid(row=r, column=1, padx=6)
            ttk.Entry(grid, textvariable=model, width=24).grid(row=r, column=2)
            self.entries[name] = (key, model)
        ttk.Button(f, text="Luu", command=self._save_cfg).pack(pady=10)

    def _save_cfg(self):
        for name, (k, m) in self.entries.items():
            self.cfg["providers"][name]["api_key"] = k.get().strip()
            self.cfg["providers"][name]["model"] = m.get().strip()
        config.save(self.cfg)
        messagebox.showinfo("OK", "Da luu.")


if __name__ == "__main__":
    App().mainloop()
