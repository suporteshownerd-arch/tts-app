import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import logging
import os
import shutil

from tts_utils import build_play_cmd, check_executables, generate_audio, list_voices

# 9. Logging com destino definido
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.expanduser("~/.tts-app.log")),
        logging.StreamHandler(),
    ],
)

BG     = "#1e1e2e"
BG2    = "#2a2a3e"
ACCENT = "#7c3aed"
ACCENT2= "#a855f7"
TEXT   = "#e2e8f0"
TEXT2  = "#94a3b8"
GREEN  = "#22c55e"
RED    = "#dc2626"

_play_proc   = None
_executables = None  # 8. checado uma vez na inicialização

# B2: history file for recent texts
HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".tts_app_history.txt")
def load_history():
    try:
        if not os.path.exists(HISTORY_FILE):
            return []
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
            # most recent last in file; return newest first, limit 50
            return list(reversed(lines))[:50]
    except Exception:
        logging.exception("Failed to load history")
        return []

def save_to_history(text: str):
    try:
        if not text or not text.strip():
            return
        # append simple one-line entry
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(text.strip().replace("\n", " ") + "\n")
    except Exception:
        logging.exception("Failed to save history")

# B5: theme setting (saved to file)
THEME_FILE = os.path.join(os.path.expanduser("~"), ".tts_app_theme")
def current_theme():
    try:
        if os.path.exists(THEME_FILE):
            with open(THEME_FILE, "r", encoding="utf-8") as f:
                return f.read().strip() or "dark"
    except Exception:
        pass
    return "dark"

def toggle_theme():
    t = current_theme()
    new = "light" if t == "dark" else "dark"
    try:
        with open(THEME_FILE, "w", encoding="utf-8") as f:
            f.write(new)
    except Exception:
        logging.exception("Failed to write theme file")
    set_theme(new)


def set_theme(theme: str):
    """Apply theme dynamically to major widgets."""
    # Define palettes
    palettes = {
        "dark": {
            "BG": "#1e1e2e", "BG2": "#2a2a3e", "ACCENT": "#7c3aed", "ACCENT2": "#a855f7",
            "TEXT": "#e2e8f0", "TEXT2": "#94a3b8", "GREEN": "#22c55e", "RED": "#dc2626",
        },
        "light": {
            "BG": "#f8fafc", "BG2": "#eef2ff", "ACCENT": "#2563eb", "ACCENT2": "#1e40af",
            "TEXT": "#0f172a", "TEXT2": "#475569", "GREEN": "#16a34a", "RED": "#dc2626",
        }
    }
    pal = palettes.get(theme, palettes["dark"])

    # Update global constants used elsewhere
    global BG, BG2, ACCENT, ACCENT2, TEXT, TEXT2, GREEN, RED
    BG = pal["BG"]; BG2 = pal["BG2"]; ACCENT = pal["ACCENT"]; ACCENT2 = pal["ACCENT2"]
    TEXT = pal["TEXT"]; TEXT2 = pal["TEXT2"]; GREEN = pal["GREEN"]; RED = pal["RED"]

    # Walk widgets and update common options
    def apply_rec(widget):
        # Frame
        try:
            cls = widget.winfo_class()
            if cls in ("Frame", "TFrame"):
                widget.configure(bg=BG)
            elif cls in ("Label", "TLabel"):
                widget.configure(bg=BG, fg=TEXT)
            elif cls == "Button":
                # don't override special button colors
                widget.configure(bg=BG2, fg=TEXT)
            elif cls == "Text":
                widget.configure(bg=BG2, fg=TEXT, insertbackground=ACCENT2)
            elif cls == "Scale":
                widget.configure(bg=BG)
        except Exception:
            pass
        for child in widget.winfo_children():
            apply_rec(child)

    apply_rec(root)


def _check_deps_startup():
    global _executables
    _executables = check_executables()


def _deps_ok(need_ffplay=True):
    if not _executables["edge-tts"]:
        messagebox.showerror("Erro", "Executável 'edge-tts' não encontrado.\nInstale via: pipx install edge-tts")
        return False
    if need_ffplay and not _executables["ffplay"]:
        messagebox.showerror("Erro", "Executável 'ffplay' não encontrado.\nInstale via: sudo apt install ffmpeg")
        return False
    return True


def parar():
    global _play_proc
    if _play_proc and _play_proc.poll() is None:
        _play_proc.terminate()
    _play_proc = None
    btn_falar.config(state="normal", text="▶   Falar", command=falar, bg=ACCENT)
    status_var.set("⏹ Parado")


def falar(_event=None):
    global _play_proc
    texto = text_box.get("1.0", tk.END).strip()
    voz = voz_var.get()
    velocidade = vel_var.get()
    if not texto:
        messagebox.showwarning("Aviso", "Digite algum texto primeiro!")
        return
    if not _deps_ok(need_ffplay=True):
        return

    btn_falar.config(state="disabled", text="⏳  Gerando áudio...")
    status_var.set("🔊 Gerando áudio...")

    def run():
        global _play_proc
        try:
            rc, out_path = generate_audio(voz, velocidade, texto, None)
        except Exception:
            logging.exception("generate_audio failed")
            rc, out_path = 1, None

        if rc != 0:
            root.after(0, lambda: [
                btn_falar.config(state="normal", text="▶   Falar", command=falar, bg=ACCENT),
                status_var.set("❌ Falha ao gerar áudio"),
                messagebox.showerror("Erro", "Falha ao gerar áudio com edge-tts"),
            ])
            return

        # save to history on successful generation
        save_to_history(texto)

        play_cmd = build_play_cmd(out_path)
        _play_proc = subprocess.Popen(play_cmd, stderr=subprocess.DEVNULL)
        root.after(0, lambda: [
            btn_falar.config(state="normal", text="■  Parar", command=parar, bg=RED),
            status_var.set("🔊 Reproduzindo..."),
        ])
        play_rc = _play_proc.wait()
        _play_proc = None
        root.after(0, lambda: [
            btn_falar.config(state="normal", text="▶   Falar", command=falar, bg=ACCENT),
            status_var.set("✅ Pronto!" if play_rc == 0 else "⏹ Parado"),
        ])
        try:
            if out_path and os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass

    threading.Thread(target=run, daemon=True).start()


def salvar(_event=None):
    texto = text_box.get("1.0", tk.END).strip()
    voz = voz_var.get()
    velocidade = vel_var.get()
    if not texto:
        messagebox.showwarning("Aviso", "Digite algum texto primeiro!")
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".mp3",
        filetypes=[("MP3", "*.mp3")],
        initialfile="audio.mp3",
    )
    if not path:
        return
    if not _deps_ok(need_ffplay=False):
        return

    status_var.set("💾 Gerando áudio...")

    def run():
        try:
            rc, tmp_path = generate_audio(voz, velocidade, texto, None)
        except Exception:
            logging.exception("generate_audio failed on save")
            rc = 1

        if rc != 0:
            root.after(0, lambda: [
                status_var.set("❌ Falha ao salvar"),
                messagebox.showerror("Erro", "Falha ao gerar o arquivo de áudio com edge-tts"),
            ])
            return

        try:
            shutil.move(tmp_path, path)
            root.after(0, lambda: status_var.set(f"✅ Salvo em {os.path.basename(path)}"))
        except Exception:
            logging.exception("Failed to move audio file")
            root.after(0, lambda: [
                status_var.set("❌ Erro ao mover arquivo"),
                messagebox.showerror("Erro", f"Não foi possível salvar em {path}"),
            ])

    threading.Thread(target=run, daemon=True).start()


def limpar():
    # 7. Confirma antes de apagar
    texto = text_box.get("1.0", tk.END).strip()
    if texto and not messagebox.askyesno("Limpar", "Deseja apagar o texto?"):
        return
    text_box.delete("1.0", tk.END)
    status_var.set("")
    char_var.set("0 caracteres")


def colar_clipboard():
    # 4. Cola da área de transferência
    try:
        texto = root.clipboard_get()
        text_box.delete("1.0", tk.END)
        text_box.insert("1.0", texto)
        _atualizar_contador()
    except tk.TclError:
        pass


def _atualizar_contador(_event=None):
    # 1. Contador de caracteres em tempo real
    texto = text_box.get("1.0", tk.END).strip()
    char_var.set(f"{len(texto)} caracteres")


class VozSelector(tk.Frame):
    def __init__(self, parent, variable, values, **kwargs):
        super().__init__(parent, bg=BG2, highlightthickness=1, highlightbackground=ACCENT, **kwargs)
        self.variable = variable
        self.values = values
        self.popup = None
        self.btn = tk.Button(
            self, textvariable=variable, bg=BG2, fg=TEXT,
            font=("Segoe UI", 10), relief="flat", anchor="w",
            padx=10, cursor="hand2", activebackground=BG2,
            activeforeground=ACCENT2, command=self.toggle_popup,
        )
        self.btn.pack(side="left", fill="x", expand=True, ipady=6)
        arrow = tk.Label(self, text="▾", bg=BG2, fg=ACCENT2, font=("Segoe UI", 12), cursor="hand2")
        arrow.pack(side="right", padx=8)
        arrow.bind("<Button-1>", lambda e: self.toggle_popup())

    def update_values(self, values):
        self.values = values

    def toggle_popup(self):
        if self.popup and self.popup.winfo_exists():
            self.popup.destroy()
            self.popup = None
            return
        self.show_popup()

    def show_popup(self):
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = self.winfo_width()

        self.popup = tk.Toplevel()
        self.popup.wm_overrideredirect(True)
        self.popup.configure(bg=BG2)

        outer = tk.Frame(self.popup, bg=BG2, highlightthickness=1, highlightbackground=ACCENT)
        outer.pack(fill="both", expand=True)

        # 3. Filtro de vozes
        filter_var = tk.StringVar()
        filter_entry = tk.Entry(
            outer, textvariable=filter_var, bg=BG2, fg=TEXT,
            insertbackground=ACCENT2, relief="flat", font=("Segoe UI", 10),
        )
        filter_entry.pack(fill="x", padx=6, pady=4)
        tk.Frame(outer, bg=ACCENT, height=1).pack(fill="x")

        list_frame = tk.Frame(outer, bg=BG2)
        list_frame.pack(fill="both", expand=True)

        def render_buttons(filter_text=""):
            for child in list_frame.winfo_children():
                child.destroy()
            filtered = [v for v in self.values if filter_text.lower() in v.lower()]
            for v in filtered:
                def make_cmd(val):
                    def cmd():
                        self.variable.set(val)
                        self.popup.destroy()
                        self.popup = None
                    return cmd
                tk.Button(
                    list_frame, text=v, bg=BG2, fg=TEXT, font=("Segoe UI", 10),
                    relief="flat", anchor="w", padx=12, pady=4, cursor="hand2",
                    activebackground=ACCENT, activeforeground="white",
                    command=make_cmd(v),
                ).pack(fill="x")
            h = min(len(filtered) * 32 + 40, 240)
            self.popup.geometry(f"{w}x{h}+{x}+{y}")

        filter_var.trace_add("write", lambda *_: render_buttons(filter_var.get()))
        render_buttons()

        self.popup.bind("<FocusOut>", lambda e: self.popup.destroy() if self.popup and self.popup.winfo_exists() else None)
        filter_entry.focus_set()


# --- UI ---

root = tk.Tk()
root.title("Text to Speech")
root.geometry("560x540")
root.configure(bg=BG)
root.minsize(480, 480)  # 5. janela redimensionável
root.resizable(True, True)

tk.Frame(root, bg=ACCENT, height=4).pack(fill="x")

title_frame = tk.Frame(root, bg=BG, pady=12)
title_frame.pack(fill="x")
tk.Label(title_frame, text="🎙 Text to Speech", font=("Segoe UI", 16, "bold"), bg=BG, fg=TEXT).pack()
tk.Label(title_frame, text="Converta texto em voz natural", font=("Segoe UI", 9), bg=BG, fg=TEXT2).pack()

# History dropdown (B2)
history_var = tk.StringVar()
history_menu = tk.OptionMenu(title_frame, history_var, *load_history())
history_menu.config(bg=BG, fg=TEXT, activebackground=BG2)
history_menu.pack(side="right", padx=10)

# Theme toggle (B5)
tk.Button(title_frame, text="Tema", command=toggle_theme, bg=BG2, fg=TEXT2, relief="flat").pack(side="right", padx=6)

text_frame = tk.Frame(root, bg=BG2, bd=0, highlightthickness=1, highlightbackground=ACCENT)
text_frame.pack(padx=20, pady=(0, 4), fill="both", expand=True)

text_header = tk.Frame(text_frame, bg=BG2)
text_header.pack(fill="x", padx=10, pady=(8, 0))
tk.Label(text_header, text="Texto", font=("Segoe UI", 9, "bold"), bg=BG2, fg=TEXT2).pack(side="left")

# 4. Botão colar clipboard
tk.Button(
    text_header, text="📋 Colar", command=colar_clipboard,
    bg=BG2, fg=TEXT2, font=("Segoe UI", 8), relief="flat",
    cursor="hand2", padx=6, pady=0, activebackground=BG2, activeforeground=ACCENT2,
).pack(side="right")

# B3: Botão Abrir .txt
def abrir_txt():
    path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        text_box.delete("1.0", tk.END)
        text_box.insert("1.0", content)
        _atualizar_contador()
    except Exception:
        logging.exception("Failed to open txt file")

tk.Button(text_header, text="📂 Abrir", command=abrir_txt, bg=BG2, fg=TEXT2, font=("Segoe UI", 8), relief="flat", cursor="hand2").pack(side="right", padx=(0,6))

text_box = tk.Text(
    text_frame, height=8, font=("Segoe UI", 11), bg=BG2, fg=TEXT,
    insertbackground=ACCENT2, relief="flat", bd=0, padx=10, pady=8,
    wrap="word", selectbackground=ACCENT,
)
text_box.pack(fill="both", expand=True, padx=2, pady=(2, 0))
text_box.bind("<KeyRelease>", _atualizar_contador)

# 1. Contador de caracteres
char_var = tk.StringVar(value="0 caracteres")
tk.Label(text_frame, textvariable=char_var, font=("Segoe UI", 8), bg=BG2, fg=TEXT2, anchor="e").pack(
    fill="x", padx=10, pady=(0, 6)
)

ctrl_frame = tk.Frame(root, bg=BG)
ctrl_frame.pack(padx=20, fill="x")

left = tk.Frame(ctrl_frame, bg=BG)
left.pack(side="left", fill="x", expand=True, padx=(0, 10))
tk.Label(left, text="🗣 Voz", font=("Segoe UI", 9, "bold"), bg=BG, fg=TEXT2).pack(anchor="w")
voz_var = tk.StringVar(value="pt-BR-FranciscaNeural")
vozes = ["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural", "en-US-JennyNeural", "en-US-GuyNeural", "es-ES-ElviraNeural"]
voz_selector = VozSelector(left, voz_var, vozes)
voz_selector.pack(fill="x", pady=(4, 0))

right = tk.Frame(ctrl_frame, bg=BG)
right.pack(side="right")
tk.Label(right, text="⚡ Velocidade", font=("Segoe UI", 9, "bold"), bg=BG, fg=TEXT2).pack(anchor="w")
vel_var = tk.IntVar(value=0)
vel_label = tk.Label(right, text="0%", font=("Segoe UI", 9), bg=BG, fg=ACCENT2, width=5)
vel_label.pack(anchor="e")

def update_label(v):
    val = int(float(v))
    vel_label.config(text=f"{val:+d}%" if val != 0 else "0%")

tk.Scale(
    right, from_=-50, to=50, orient="horizontal", variable=vel_var, length=160,
    bg=BG, fg=TEXT, troughcolor=BG2, activebackground=ACCENT2,
    highlightthickness=0, bd=0, showvalue=False, command=update_label,
).pack()

btn_frame = tk.Frame(root, bg=BG)
btn_frame.pack(pady=12, padx=20, fill="x")
tk.Button(
    btn_frame, text="🗑 Limpar", command=limpar, bg=BG2, fg=TEXT2,
    font=("Segoe UI", 10), relief="flat", padx=15, pady=8, cursor="hand2",
).pack(side="left")
tk.Button(
    btn_frame, text="💾 Salvar MP3", command=salvar, bg=BG2, fg=ACCENT2,
    font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=8, cursor="hand2",
).pack(side="left", padx=10)
btn_falar = tk.Button(
    btn_frame, text="▶   Falar", command=falar, bg=ACCENT, fg="white",
    font=("Segoe UI", 11, "bold"), relief="flat", padx=25, pady=8, cursor="hand2",
)
btn_falar.pack(side="right")

status_var = tk.StringVar()
tk.Label(root, textvariable=status_var, font=("Segoe UI", 9), bg=BG, fg=GREEN).pack(pady=(0, 8))

# 2. Atalhos de teclado
root.bind("<Control-Return>", falar)
root.bind("<Control-s>", salvar)
root.bind("<Escape>", lambda e: parar())

# 8. Checar deps uma vez na inicialização
_check_deps_startup()

# Carregar vozes dinamicamente
def _carregar_vozes():
    vozes_api = list_voices()
    if vozes_api:
        root.after(0, lambda: voz_selector.update_values(vozes_api))

threading.Thread(target=_carregar_vozes, daemon=True).start()

root.mainloop()
