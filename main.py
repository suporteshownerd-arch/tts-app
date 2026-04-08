import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import logging
import json
import os
import shutil

from tts_utils import build_play_cmd, check_executables, generate_audio, list_voices

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.expanduser("~/.tts-app.log")),
        logging.StreamHandler(),
    ],
)

# ── Preferências ──────────────────────────────────────────────────────────────
CONFIG_DIR   = os.path.expanduser("~/.config/tts-app")
PREFS_FILE   = os.path.join(CONFIG_DIR, "prefs.json")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.json")
MAX_HISTORY  = 20

def _load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path, data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_prefs():   return _load_json(PREFS_FILE, {})
def save_prefs(**kw):
    p = load_prefs(); p.update(kw); _save_json(PREFS_FILE, p)

def load_history():  return _load_json(HISTORY_FILE, [])
def add_to_history(text):
    h = load_history()
    if text in h: h.remove(text)
    h.insert(0, text)
    _save_json(HISTORY_FILE, h[:MAX_HISTORY])

# ── Temas ─────────────────────────────────────────────────────────────────────
THEMES = {
    "dark":  dict(BG="#1e1e2e", BG2="#2a2a3e", ACCENT="#7c3aed", ACCENT2="#a855f7",
                  TEXT="#e2e8f0", TEXT2="#94a3b8", GREEN="#22c55e", RED="#dc2626"),
    "light": dict(BG="#f1f5f9", BG2="#ffffff",  ACCENT="#7c3aed", ACCENT2="#6d28d9",
                  TEXT="#1e293b", TEXT2="#64748b", GREEN="#16a34a", RED="#dc2626"),
}
_prefs      = load_prefs()
_theme_name = _prefs.get("theme", "dark")
_font_size  = _prefs.get("font_size", 11)
_themed     = []

def T(key):  return THEMES[_theme_name][key]

def reg(widget, **keys):
    _themed.append((widget, keys)); return widget

def apply_theme():
    t = THEMES[_theme_name]
    for w, keys in _themed:
        try: w.config(**{k: t[v] for k, v in keys.items()})
        except Exception: pass

def toggle_theme():
    global _theme_name
    _theme_name = "light" if _theme_name == "dark" else "dark"
    apply_theme()
    save_prefs(theme=_theme_name)
    btn_theme.config(text="☀️" if _theme_name == "dark" else "🌙")

# ── Estado ────────────────────────────────────────────────────────────────────
_play_proc   = None
_executables = None

def _check_deps_startup():
    global _executables
    _executables = check_executables()

def _deps_ok(need_ffplay=True):
    if not _executables["edge-tts"]:
        messagebox.showerror("Erro", "edge-tts não encontrado.\nInstale: pipx install edge-tts")
        return False
    if need_ffplay and not _executables["ffplay"]:
        messagebox.showerror("Erro", "ffplay não encontrado.\nInstale: sudo apt install ffmpeg")
        return False
    return True

# ── Ações ─────────────────────────────────────────────────────────────────────
def parar():
    global _play_proc
    if _play_proc and _play_proc.poll() is None:
        _play_proc.terminate()
    _play_proc = None
    btn_falar.config(state="normal", text="▶   Falar", command=falar, bg=T("ACCENT"))
    status_var.set("⏹ Parado")

def _pb_show():
    pb.pack(fill="x", padx=20, pady=(0, 4), before=text_frame)
    pb.start(10)

def _pb_hide():
    pb.stop(); pb.pack_forget()

def falar(_event=None):
    global _play_proc
    texto = text_box.get("1.0", tk.END).strip()
    if not texto:
        messagebox.showwarning("Aviso", "Digite algum texto primeiro!"); return
    if not _deps_ok(): return
    voz, vel, vol = voz_var.get(), vel_var.get(), vol_var.get()
    btn_falar.config(state="disabled", text="⏳  Gerando áudio...")
    status_var.set("🔊 Gerando áudio...")
    root.after(0, _pb_show)

    def run():
        global _play_proc
        try:
            rc, out_path = generate_audio(voz, vel, texto, None)
        except Exception:
            logging.exception("generate_audio failed")
            rc, out_path = 1, None
        if rc != 0:
            root.after(0, lambda: [
                _pb_hide(),
                btn_falar.config(state="normal", text="▶   Falar", command=falar, bg=T("ACCENT")),
                status_var.set("❌ Falha ao gerar áudio"),
                messagebox.showerror("Erro", "Falha ao gerar áudio.\nErro 529 = serviço sobrecarregado, tente novamente."),
            ]); return
        add_to_history(texto)
        _play_proc = subprocess.Popen(build_play_cmd(out_path, volume=vol), stderr=subprocess.DEVNULL)
        root.after(0, lambda: [
            _pb_hide(),
            btn_falar.config(state="normal", text="■  Parar", command=parar, bg=T("RED")),
            status_var.set("🔊 Reproduzindo..."),
        ])
        play_rc = _play_proc.wait()
        _play_proc = None
        root.after(0, lambda: [
            btn_falar.config(state="normal", text="▶   Falar", command=falar, bg=T("ACCENT")),
            status_var.set("✅ Pronto!" if play_rc == 0 else "⏹ Parado"),
        ])
        try:
            if out_path and os.path.exists(out_path): os.remove(out_path)
        except Exception: pass

    threading.Thread(target=run, daemon=True).start()

def salvar(_event=None):
    texto = text_box.get("1.0", tk.END).strip()
    if not texto:
        messagebox.showwarning("Aviso", "Digite algum texto primeiro!"); return
    path = filedialog.asksaveasfilename(defaultextension=".mp3",
                                        filetypes=[("MP3","*.mp3")], initialfile="audio.mp3")
    if not path: return
    if not _deps_ok(need_ffplay=False): return
    status_var.set("💾 Gerando áudio...")
    root.after(0, _pb_show)
    def run():
        try:
            rc, tmp = generate_audio(voz_var.get(), vel_var.get(), texto, None)
        except Exception:
            logging.exception("generate_audio failed on save"); rc = 1
        if rc != 0:
            root.after(0, lambda: [_pb_hide(), status_var.set("❌ Falha ao salvar"),
                messagebox.showerror("Erro", "Falha ao gerar áudio com edge-tts")]); return
        try:
            shutil.move(tmp, path)
            root.after(0, lambda: [_pb_hide(), status_var.set(f"✅ Salvo em {os.path.basename(path)}")])
        except Exception:
            logging.exception("move failed")
            root.after(0, lambda: [_pb_hide(), status_var.set("❌ Erro ao salvar"),
                messagebox.showerror("Erro", f"Não foi possível salvar em {path}")])
    threading.Thread(target=run, daemon=True).start()

def limpar():
    if text_box.get("1.0", tk.END).strip() and not messagebox.askyesno("Limpar","Deseja apagar o texto?"): return
    text_box.delete("1.0", tk.END); status_var.set(""); char_var.set("0 caracteres")

def abrir_txt(_event=None):
    path = filedialog.askopenfilename(filetypes=[("Texto","*.txt"),("Todos","*.*")])
    if not path: return
    try:
        with open(path, encoding="utf-8") as f: content = f.read()
        text_box.delete("1.0", tk.END); text_box.insert("1.0", content)
        _atualizar_contador()
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível abrir:\n{e}")

def colar_clipboard():
    try:
        text_box.delete("1.0", tk.END); text_box.insert("1.0", root.clipboard_get())
        _atualizar_contador()
    except tk.TclError: pass

def mostrar_historico():
    hist = load_history()
    if not hist:
        messagebox.showinfo("Histórico","Nenhum texto no histórico ainda."); return
    pop = tk.Toplevel(root)
    pop.title("Histórico"); pop.configure(bg=T("BG")); pop.geometry("480x300")
    pop.transient(root); pop.grab_set()
    reg(tk.Label(pop, text="Textos recentes", font=("Segoe UI",10,"bold"),
                 bg=T("BG"), fg=T("TEXT2")), bg="BG", fg="TEXT2").pack(anchor="w", padx=12, pady=(10,4))
    fr = reg(tk.Frame(pop, bg=T("BG2"), highlightthickness=1, highlightbackground=T("ACCENT")),
             bg="BG2", highlightbackground="ACCENT")
    fr.pack(fill="both", expand=True, padx=12, pady=(0,6))
    sb = tk.Scrollbar(fr); sb.pack(side="right", fill="y")
    lb = tk.Listbox(fr, bg=T("BG2"), fg=T("TEXT"), selectbackground=T("ACCENT"),
                    font=("Segoe UI",10), relief="flat", bd=0, yscrollcommand=sb.set)
    for item in hist: lb.insert(tk.END, item[:100].replace("\n"," "))
    lb.pack(fill="both", expand=True); sb.config(command=lb.yview)
    def usar():
        sel = lb.curselection()
        if not sel: return
        text_box.delete("1.0", tk.END); text_box.insert("1.0", hist[sel[0]])
        _atualizar_contador(); pop.destroy()
    lb.bind("<Double-Button-1>", lambda e: usar())
    reg(tk.Button(pop, text="Usar", command=usar, bg=T("ACCENT"), fg="white",
                  font=("Segoe UI",10,"bold"), relief="flat", padx=20, pady=6, cursor="hand2"),
        bg="ACCENT").pack(pady=(0,10))

def _atualizar_contador(_event=None):
    char_var.set(f"{len(text_box.get('1.0', tk.END).strip())} caracteres")

def _ajustar_fonte(delta):
    global _font_size
    _font_size = max(8, min(24, _font_size + delta))
    text_box.config(font=("Segoe UI", _font_size))
    save_prefs(font_size=_font_size)

# ── Seletor de Voz ────────────────────────────────────────────────────────────
LANG_TABS   = ["","pt","en","es","fr","de","ja","zh"]
LANG_LABELS = ["ALL","PT","EN","ES","FR","DE","JA","ZH"]

class VozSelector(tk.Frame):
    def __init__(self, parent, variable, values, **kwargs):
        super().__init__(parent, bg=T("BG2"), highlightthickness=1, highlightbackground=T("ACCENT"), **kwargs)
        self.variable = variable; self.values = values; self.popup = None
        self.btn = tk.Button(self, textvariable=variable, bg=T("BG2"), fg=T("TEXT"),
                             font=("Segoe UI",10), relief="flat", anchor="w", padx=10, cursor="hand2",
                             activebackground=T("BG2"), activeforeground=T("ACCENT2"), command=self.toggle_popup)
        self.btn.pack(side="left", fill="x", expand=True, ipady=6)
        self.arrow = tk.Label(self, text="▾", bg=T("BG2"), fg=T("ACCENT2"), font=("Segoe UI",12), cursor="hand2")
        self.arrow.pack(side="right", padx=8)
        self.arrow.bind("<Button-1>", lambda e: self.toggle_popup())

    def update_values(self, values): self.values = values

    def toggle_popup(self):
        if self.popup and self.popup.winfo_exists():
            self.popup.destroy(); self.popup = None; return
        self.show_popup()

    def show_popup(self):
        x, y, w = self.winfo_rootx(), self.winfo_rooty()+self.winfo_height(), self.winfo_width()
        self.popup = tk.Toplevel(); self.popup.wm_overrideredirect(True); self.popup.configure(bg=T("BG2"))
        outer = tk.Frame(self.popup, bg=T("BG2"), highlightthickness=1, highlightbackground=T("ACCENT"))
        outer.pack(fill="both", expand=True)

        # Abas de idioma
        tabs = tk.Frame(outer, bg=T("BG2")); tabs.pack(fill="x", padx=4, pady=(4,0))
        filter_var = tk.StringVar()
        for lang, label in zip(LANG_TABS, LANG_LABELS):
            tk.Button(tabs, text=label, bg=T("BG2"), fg=T("TEXT2"), font=("Segoe UI",8),
                      relief="flat", padx=5, pady=2, cursor="hand2",
                      activebackground=T("ACCENT"), activeforeground="white",
                      command=lambda l=lang: filter_var.set(l)).pack(side="left", padx=1)
        tk.Frame(outer, bg=T("ACCENT"), height=1).pack(fill="x", pady=(4,0))

        # Campo de busca
        fe = tk.Entry(outer, textvariable=filter_var, bg=T("BG2"), fg=T("TEXT"),
                      insertbackground=T("ACCENT2"), relief="flat", font=("Segoe UI",10))
        fe.pack(fill="x", padx=6, pady=4)
        tk.Frame(outer, bg=T("ACCENT"), height=1).pack(fill="x")

        # Listbox com scrollbar nativo — sem problemas de FocusOut
        lf = tk.Frame(outer, bg=T("BG2")); lf.pack(fill="both", expand=True)
        sb = tk.Scrollbar(lf); sb.pack(side="right", fill="y")
        lb = tk.Listbox(lf, bg=T("BG2"), fg=T("TEXT"), selectbackground=T("ACCENT"),
                        selectforeground="white", font=("Segoe UI",10), relief="flat",
                        bd=0, highlightthickness=0, activestyle="none",
                        yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True)
        sb.config(command=lb.yview)
        lb.bind("<MouseWheel>", lambda e: lb.yview_scroll(int(-1*(e.delta/120)), "units"))

        _filtered = []

        def render(ft=""):
            lb.delete(0, tk.END)
            _filtered.clear()
            for v in self.values:
                if ft.lower() in v.lower():
                    _filtered.append(v)
                    lb.insert(tk.END, v)
            self.popup.geometry(f"{w}x{min(len(_filtered)*20+100,320)}+{x}+{y}")

        def on_select(e):
            sel = lb.curselection()
            if not sel: return
            self.variable.set(_filtered[sel[0]])
            self.popup.destroy(); self.popup = None

        lb.bind("<<ListboxSelect>>", on_select)
        lb.bind("<Return>", on_select)
        filter_var.trace_add("write", lambda *_: render(filter_var.get()))
        render()

        # Fechar ao clicar fora
        self.popup.bind("<FocusOut>", lambda e: self.popup.after(150, lambda:
            self.popup.destroy() or setattr(self, "popup", None)
            if self.popup and self.popup.winfo_exists()
            and self.popup.focus_get() is None else None))
        fe.focus_set()

# ── Janela ────────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("Text to Speech")
root.geometry("560x620")
root.minsize(480, 520)
root.resizable(True, True)
reg(root, bg="BG")

reg(tk.Frame(root, bg=T("ACCENT"), height=4), bg="ACCENT").pack(fill="x")

title_frame = reg(tk.Frame(root, bg=T("BG"), pady=10), bg="BG")
title_frame.pack(fill="x")
title_row = reg(tk.Frame(title_frame, bg=T("BG")), bg="BG")
title_row.pack()
reg(tk.Label(title_row, text="🎙 Text to Speech", font=("Segoe UI",16,"bold"), bg=T("BG"), fg=T("TEXT")),
    bg="BG", fg="TEXT").pack(side="left", padx=(0,8))
btn_theme = reg(tk.Button(title_row, text="☀️" if _theme_name=="dark" else "🌙",
                           command=toggle_theme, bg=T("BG"), fg=T("TEXT2"),
                           font=("Segoe UI",11), relief="flat", cursor="hand2",
                           activebackground=T("BG"), activeforeground=T("ACCENT2")),
                bg="BG", activebackground="BG", fg="TEXT2", activeforeground="ACCENT2")
btn_theme.pack(side="left")
reg(tk.Label(title_frame, text="Converta texto em voz natural", font=("Segoe UI",9), bg=T("BG"), fg=T("TEXT2")),
    bg="BG", fg="TEXT2").pack()

style = ttk.Style(); style.theme_use("clam")
style.configure("TTS.Horizontal.TProgressbar", troughcolor=T("BG2"), background=T("ACCENT"), thickness=5)
pb = ttk.Progressbar(root, mode="indeterminate", style="TTS.Horizontal.TProgressbar")

text_frame = reg(tk.Frame(root, bg=T("BG2"), bd=0, highlightthickness=1, highlightbackground=T("ACCENT")),
                 bg="BG2", highlightbackground="ACCENT")
text_frame.pack(padx=20, pady=(0,4), fill="both", expand=True)

th = reg(tk.Frame(text_frame, bg=T("BG2")), bg="BG2")
th.pack(fill="x", padx=10, pady=(8,0))
reg(tk.Label(th, text="Texto", font=("Segoe UI",9,"bold"), bg=T("BG2"), fg=T("TEXT2")),
    bg="BG2", fg="TEXT2").pack(side="left")

for icon, cmd in [("📋", colar_clipboard), ("📂", abrir_txt), ("🕘", mostrar_historico),
                   ("A-", lambda: _ajustar_fonte(-1)), ("A+", lambda: _ajustar_fonte(+1))]:
    reg(tk.Button(th, text=icon, command=cmd, bg=T("BG2"), fg=T("TEXT2"),
                  font=("Segoe UI", 9 if len(icon)==1 else 8), relief="flat", cursor="hand2",
                  padx=5, activebackground=T("BG2"), activeforeground=T("ACCENT2")),
        bg="BG2", fg="TEXT2", activebackground="BG2", activeforeground="ACCENT2").pack(side="right", padx=1)

text_box = tk.Text(text_frame, height=8, font=("Segoe UI",_font_size), bg=T("BG2"), fg=T("TEXT"),
                   insertbackground=T("ACCENT2"), relief="flat", bd=0, padx=10, pady=8,
                   wrap="word", selectbackground=T("ACCENT"), undo=True, maxundo=50)
reg(text_box, bg="BG2", fg="TEXT", insertbackground="ACCENT2", selectbackground="ACCENT")
text_box.pack(fill="both", expand=True, padx=2, pady=(2,0))
text_box.bind("<KeyRelease>", _atualizar_contador)

char_var = tk.StringVar(value="0 caracteres")
reg(tk.Label(text_frame, textvariable=char_var, font=("Segoe UI",8), bg=T("BG2"), fg=T("TEXT2"), anchor="e"),
    bg="BG2", fg="TEXT2").pack(fill="x", padx=10, pady=(0,6))

ctrl_frame = reg(tk.Frame(root, bg=T("BG")), bg="BG")
ctrl_frame.pack(padx=20, fill="x", pady=(4,0))

left = reg(tk.Frame(ctrl_frame, bg=T("BG")), bg="BG")
left.pack(side="left", fill="x", expand=True, padx=(0,10))
reg(tk.Label(left, text="🗣 Voz", font=("Segoe UI",9,"bold"), bg=T("BG"), fg=T("TEXT2")),
    bg="BG", fg="TEXT2").pack(anchor="w")
voz_var = tk.StringVar(value=_prefs.get("voice","pt-BR-FranciscaNeural"))
voz_selector = VozSelector(left, voz_var, ["pt-BR-FranciscaNeural","pt-BR-AntonioNeural",
                                            "en-US-JennyNeural","en-US-GuyNeural","es-ES-ElviraNeural"])
voz_selector.pack(fill="x", pady=(4,0))

right = reg(tk.Frame(ctrl_frame, bg=T("BG")), bg="BG")
right.pack(side="right")

reg(tk.Label(right, text="⚡ Velocidade", font=("Segoe UI",9,"bold"), bg=T("BG"), fg=T("TEXT2")),
    bg="BG", fg="TEXT2").pack(anchor="w")
vel_var = tk.IntVar(value=_prefs.get("speed",0))
vel_label = reg(tk.Label(right, text="0%", font=("Segoe UI",9), bg=T("BG"), fg=T("ACCENT2"), width=5),
                bg="BG", fg="ACCENT2")
vel_label.pack(anchor="e")
def _upd_vel(v):
    val = int(float(v)); vel_label.config(text=f"{val:+d}%" if val != 0 else "0%")
reg(tk.Scale(right, from_=-50, to=50, orient="horizontal", variable=vel_var, length=160,
             bg=T("BG"), fg=T("TEXT"), troughcolor=T("BG2"), activebackground=T("ACCENT2"),
             highlightthickness=0, bd=0, showvalue=False, command=_upd_vel),
    bg="BG", fg="TEXT", troughcolor="BG2", activebackground="ACCENT2").pack()
_upd_vel(vel_var.get())

reg(tk.Label(right, text="🔊 Volume", font=("Segoe UI",9,"bold"), bg=T("BG"), fg=T("TEXT2")),
    bg="BG", fg="TEXT2").pack(anchor="w", pady=(6,0))
vol_var = tk.IntVar(value=_prefs.get("volume",100))
vol_label = reg(tk.Label(right, text=f"{_prefs.get('volume',100)}%", font=("Segoe UI",9), bg=T("BG"), fg=T("ACCENT2"), width=5),
                bg="BG", fg="ACCENT2")
vol_label.pack(anchor="e")
def _upd_vol(v): vol_label.config(text=f"{int(float(v))}%")
reg(tk.Scale(right, from_=0, to=100, orient="horizontal", variable=vol_var, length=160,
             bg=T("BG"), fg=T("TEXT"), troughcolor=T("BG2"), activebackground=T("ACCENT2"),
             highlightthickness=0, bd=0, showvalue=False, command=_upd_vol),
    bg="BG", fg="TEXT", troughcolor="BG2", activebackground="ACCENT2").pack()

btn_frame = reg(tk.Frame(root, bg=T("BG")), bg="BG")
btn_frame.pack(pady=12, padx=20, fill="x")
reg(tk.Button(btn_frame, text="🗑 Limpar", command=limpar, bg=T("BG2"), fg=T("TEXT2"),
              font=("Segoe UI",10), relief="flat", padx=15, pady=8, cursor="hand2"),
    bg="BG2", fg="TEXT2").pack(side="left")
reg(tk.Button(btn_frame, text="💾 Salvar MP3", command=salvar, bg=T("BG2"), fg=T("ACCENT2"),
              font=("Segoe UI",10,"bold"), relief="flat", padx=15, pady=8, cursor="hand2"),
    bg="BG2", fg="ACCENT2").pack(side="left", padx=10)
btn_falar = reg(tk.Button(btn_frame, text="▶   Falar", command=falar, bg=T("ACCENT"), fg="white",
                            font=("Segoe UI",11,"bold"), relief="flat", padx=25, pady=8, cursor="hand2"),
                bg="ACCENT")
btn_falar.pack(side="right")

status_var = tk.StringVar()
reg(tk.Label(root, textvariable=status_var, font=("Segoe UI",9), bg=T("BG"), fg=T("GREEN")),
    bg="BG", fg="GREEN").pack(pady=(0,8))

root.bind("<Control-Return>", falar)
root.bind("<Control-s>", salvar)
root.bind("<Control-o>", abrir_txt)
root.bind("<Escape>", lambda e: parar())
root.bind("<Control-z>", lambda e: text_box.edit_undo())
root.bind("<Control-y>", lambda e: text_box.edit_redo())

def _on_close():
    save_prefs(voice=voz_var.get(), speed=vel_var.get(), volume=vol_var.get(),
               theme=_theme_name, font_size=_font_size)
    root.destroy()
root.protocol("WM_DELETE_WINDOW", _on_close)

_check_deps_startup()

def _load_voices_bg():
    voices = list_voices()
    if voices:
        root.after(0, lambda: voz_selector.update_values(voices))
threading.Thread(target=_load_voices_bg, daemon=True).start()

root.mainloop()
