import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import logging
import json
import os
import shutil
import signal

from tts_utils import (build_play_cmd, check_executables, generate_audio, generate_audio_long,
                       list_voices, split_text, transcribe_audio, whisper_available,
                       sounddevice_available, start_mic_recording, stop_mic_recording)

# ── Deps opcionais ────────────────────────────────────────────────────────────
try:
    import pystray
    from PIL import Image as PILImage, ImageDraw
    _TRAY_OK = True
except ImportError:
    _TRAY_OK = False

try:
    from langdetect import detect as _langdetect
    _LANG_OK = True
except ImportError:
    _LANG_OK = False

try:
    import tkinterdnd2 as _dnd
    _DND_OK = True
except ImportError:
    _DND_OK = False

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.expanduser("~/.tts-app.log")),
        logging.StreamHandler(),
    ],
)

# ── Configuração ──────────────────────────────────────────────────────────────
CONFIG_DIR      = os.path.expanduser("~/.config/tts-app")
PREFS_FILE      = os.path.join(CONFIG_DIR, "prefs.json")
HISTORY_FILE    = os.path.join(CONFIG_DIR, "history.json")
LAST_AUDIO_FILE = os.path.join(CONFIG_DIR, "last_audio.mp3")
MAX_HISTORY     = 20
LONG_TEXT_THRESHOLD = 4500

# ── i18n ──────────────────────────────────────────────────────────────────────
_STRINGS = {
    "pt-BR": {
        "speak":   "▶   Falar",
        "stop":    "■  Parar",
        "save":    "💾 Salvar MP3",
        "clear":   "🗑 Limpar",
        "pause":   "⏸ Pausar",
        "resume":  "▶ Retomar",
        "repeat":  "🔁",
        "loading": "⏳  Gerando áudio...",
        "playing": "🔊 Reproduzindo...",
        "ready":   "✅ Pronto!",
        "stopped": "⏹ Parado",
        "saving":  "💾 Gerando áudio...",
        "chars":   "chars",
        "words":   "palavras",
        "chars_long": " ⚠️ texto longo",
        "title_sub": "Converta texto em voz natural",
        "voice_lbl": "🗣 Voz",
        "speed_lbl": "⚡ Velocidade",
        "vol_lbl":   "🔊 Volume",
        "help_title": "Atalhos de teclado",
        "shortcuts": [
            ("Ctrl+Enter", "Falar"),
            ("Ctrl+S",     "Salvar MP3"),
            ("Ctrl+O",     "Abrir .txt"),
            ("Ctrl+P",     "Pausar / Retomar"),
            ("Ctrl+F",     "Buscar no texto"),
            ("Esc",        "Parar reprodução"),
            ("Ctrl+Z",     "Desfazer"),
            ("Ctrl+Y",     "Refazer"),
            ("F1",         "Esta ajuda"),
        ],
    },
    "en-US": {
        "speak":   "▶   Speak",
        "stop":    "■  Stop",
        "save":    "💾 Save MP3",
        "clear":   "🗑 Clear",
        "pause":   "⏸ Pause",
        "resume":  "▶ Resume",
        "repeat":  "🔁",
        "loading": "⏳  Generating audio...",
        "playing": "🔊 Playing...",
        "ready":   "✅ Done!",
        "stopped": "⏹ Stopped",
        "saving":  "💾 Generating audio...",
        "chars":   "chars",
        "words":   "words",
        "chars_long": " ⚠️ long text",
        "title_sub": "Convert text to natural speech",
        "voice_lbl": "🗣 Voice",
        "speed_lbl": "⚡ Speed",
        "vol_lbl":   "🔊 Volume",
        "help_title": "Keyboard shortcuts",
        "shortcuts": [
            ("Ctrl+Enter", "Speak"),
            ("Ctrl+S",     "Save MP3"),
            ("Ctrl+O",     "Open .txt"),
            ("Ctrl+P",     "Pause / Resume"),
            ("Ctrl+F",     "Find in text"),
            ("Esc",        "Stop playback"),
            ("Ctrl+Z",     "Undo"),
            ("Ctrl+Y",     "Redo"),
            ("F1",         "This help"),
        ],
    },
}


def _s(key: str) -> str:
    """Retorna string traduzida para o idioma atual."""
    return _STRINGS.get(_ui_lang, _STRINGS["pt-BR"]).get(key, key)

def _load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def _save_json(path, data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_prefs():  return _load_json(PREFS_FILE, {})
def save_prefs(**kw):
    p = load_prefs(); p.update(kw); _save_json(PREFS_FILE, p)

def load_history():  return _load_json(HISTORY_FILE, [])
def add_to_history(text):
    h = load_history()
    if text in h: h.remove(text)
    h.insert(0, text)
    _save_json(HISTORY_FILE, h[:MAX_HISTORY])

# ── Temas ─────────────────────────────────────────────────────────────────────
def _detect_system_theme() -> str:
    """Detecta tema escuro/claro do sistema via GNOME gsettings."""
    try:
        r = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True, text=True, timeout=3,
        )
        return "dark" if "dark" in r.stdout.lower() else "light"
    except Exception:
        return "dark"

THEMES = {
    "dark":  dict(BG="#1e1e2e", BG2="#2a2a3e", ACCENT="#7c3aed", ACCENT2="#a855f7",
                  TEXT="#e2e8f0", TEXT2="#94a3b8", GREEN="#22c55e", RED="#dc2626"),
    "light": dict(BG="#f1f5f9", BG2="#ffffff",  ACCENT="#7c3aed", ACCENT2="#6d28d9",
                  TEXT="#1e293b", TEXT2="#64748b", GREEN="#16a34a", RED="#dc2626"),
}
_prefs      = load_prefs()
_theme_name = _prefs.get("theme") or _detect_system_theme()
_font_size  = _prefs.get("font_size", 11)
_ui_lang    = _prefs.get("ui_lang", "pt-BR")
_themed     = []

def T(key):  return THEMES[_theme_name][key]
def reg(w, **k): _themed.append((w, k)); return w

def apply_theme():
    t = THEMES[_theme_name]
    for w, k in _themed:
        try: w.config(**{a: t[v] for a, v in k.items()})
        except Exception: pass

def toggle_theme():
    global _theme_name
    _theme_name = "light" if _theme_name == "dark" else "dark"
    apply_theme(); save_prefs(theme=_theme_name)
    btn_theme.config(text="☀️" if _theme_name == "dark" else "🌙")

def toggle_lang():
    global _ui_lang
    _ui_lang = "en-US" if _ui_lang == "pt-BR" else "pt-BR"
    save_prefs(ui_lang=_ui_lang)
    _apply_i18n()

def _apply_i18n():
    """Atualiza labels e botões para o idioma atual."""
    try:
        btn_falar.config(text=_s("speak"))
        btn_lang.config(text="🇧🇷" if _ui_lang == "pt-BR" else "🇺🇸")
        _atualizar_contador()
    except Exception:
        pass

# ── Estado ────────────────────────────────────────────────────────────────────
_play_proc    = None
_play_paused  = False
_executables  = None
_tray_icon    = None
_voices_loaded = False
_search_frame  = None
_search_matches: list = []
_search_idx    = -1

def _check_deps_startup():
    global _executables
    _executables = check_executables()

def _deps_ok(need_ffplay=True):
    if not _executables["edge-tts"]:
        messagebox.showerror("Erro", "edge-tts não encontrado.\nInstale: pipx install edge-tts"); return False
    if need_ffplay and not _executables["ffplay"]:
        messagebox.showerror("Erro", "ffplay não encontrado.\nInstale: sudo apt install ffmpeg"); return False
    return True

# ── Notificação desktop ───────────────────────────────────────────────────────
def _notify(title: str, body: str):
    try:
        subprocess.Popen(["notify-send", "-a", "TTS App", title, body],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

# ── Auto-update ───────────────────────────────────────────────────────────────
def _check_update():
    try:
        repo = os.path.expanduser("~/projetos/tts-app")
        if not os.path.isdir(os.path.join(repo, ".git")): return
        subprocess.run(["git", "-C", repo, "fetch", "--quiet"], timeout=10,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        result = subprocess.run(["git", "-C", repo, "rev-list", "--count", "HEAD..origin/main"],
                                capture_output=True, text=True, timeout=5)
        behind = int(result.stdout.strip() or "0")
        if behind > 0:
            root.after(0, lambda: status_var.set(f"🔄 {behind} atualização(ões) disponível(eis) — rode: make install-system"))
    except Exception:
        pass

# ── Detecção de idioma ────────────────────────────────────────────────────────
_lang_timer = None
_LANG_VOICE_MAP = {
    "pt": "pt-BR-FranciscaNeural",
    "en": "en-US-JennyNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "ja": "ja-JP-NanamiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
}

def _detect_and_suggest(_event=None):
    global _lang_timer
    if _lang_timer: root.after_cancel(_lang_timer)
    _lang_timer = root.after(1000, _do_detect)

def _do_detect():
    if not _LANG_OK: return
    texto = text_box.get("1.0", tk.END).strip()
    if len(texto) < 20: return
    try:
        lang = _langdetect(texto[:200])
        suggested = _LANG_VOICE_MAP.get(lang)
        if suggested and suggested != voz_var.get():
            status_var.set(f"💡 Idioma detectado: {lang.upper()} — sugestão: {suggested}")
    except Exception:
        pass

# ── Tray icon ─────────────────────────────────────────────────────────────────
def _build_tray_image():
    img = PILImage.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=(124, 58, 237))
    d.rectangle([28, 16, 36, 40], fill="white")
    d.ellipse([22, 36, 42, 50], fill="white")
    d.rectangle([31, 50, 33, 58], fill="white")
    return img

def _start_tray():
    global _tray_icon
    if not _TRAY_OK: return

    def show(_icon, _item):
        root.after(0, lambda: [root.deiconify(), root.lift()])

    def quit_app(_icon, _item):
        _icon.stop()
        root.after(0, root.destroy)

    menu = pystray.Menu(
        pystray.MenuItem("Mostrar", show, default=True),
        pystray.MenuItem("Sair", quit_app),
    )
    _tray_icon = pystray.Icon("tts-app", _build_tray_image(), "TTS App", menu)
    threading.Thread(target=_tray_icon.run, daemon=True).start()

def _on_minimize(_e):
    if root.state() == "iconic" and _TRAY_OK and _tray_icon:
        root.after(100, root.withdraw)

# ── Ações ─────────────────────────────────────────────────────────────────────
def parar():
    global _play_proc, _play_paused
    if _play_proc and _play_proc.poll() is None:
        if _play_paused:
            try: os.kill(_play_proc.pid, signal.SIGCONT)
            except Exception: pass
            _play_paused = False
        _play_proc.terminate()
    _play_proc = None
    _play_paused = False
    btn_falar.config(state="normal", text=_s("speak"), command=falar, bg=T("ACCENT"))
    try: btn_pause.pack_forget()
    except Exception: pass
    status_var.set(_s("stopped"))

def pausar_retomar():
    global _play_paused
    if not _play_proc or _play_proc.poll() is not None:
        return
    if _play_paused:
        try: os.kill(_play_proc.pid, signal.SIGCONT)
        except Exception: pass
        _play_paused = False
        btn_pause.config(text=_s("pause"))
        status_var.set(_s("playing"))
    else:
        try: os.kill(_play_proc.pid, signal.SIGSTOP)
        except Exception: pass
        _play_paused = True
        btn_pause.config(text=_s("resume"))
        status_var.set("⏸ Pausado")

def _pb_show(): pb.pack(fill="x", padx=20, pady=(0,4), before=text_frame); pb.start(10)
def _pb_hide(): pb.stop(); pb.pack_forget()

def falar(_event=None):
    global _play_proc
    texto = text_box.get("1.0", tk.END).strip()
    if not texto:
        messagebox.showwarning("Aviso", "Digite algum texto primeiro!"); return
    if not _deps_ok(): return
    voz, vel, vol = voz_var.get(), vel_var.get(), vol_var.get()

    # Aviso para texto longo
    chunks = split_text(texto)
    if len(chunks) > 1:
        if not messagebox.askyesno("Texto longo",
            f"O texto tem {len(texto)} caracteres e será dividido em {len(chunks)} partes.\nContinuar?"):
            return

    btn_falar.config(state="disabled", text=_s("loading"))
    status_var.set("🔊 " + (_s("loading").replace("⏳  ", "")))
    root.after(0, _pb_show)

    def run():
        global _play_proc, _play_paused
        try:
            if len(chunks) > 1:
                def _on_progress(cur, total):
                    root.after(0, lambda c=cur, t=total: status_var.set(f"⏳ Gerando parte {c}/{t}..."))
                rc, out_path = generate_audio_long(voz, vel, texto, None, progress_callback=_on_progress)
            else:
                rc, out_path = generate_audio(voz, vel, texto, None)
        except Exception:
            logging.exception("generate_audio failed"); rc, out_path = 1, None

        if rc != 0:
            root.after(0, lambda: [_pb_hide(),
                btn_falar.config(state="normal", text=_s("speak"), command=falar, bg=T("ACCENT")),
                status_var.set("❌ Falha ao gerar áudio"),
                messagebox.showerror("Erro", "Falha ao gerar áudio.\n529 = serviço sobrecarregado, tente novamente.")]); return

        # Salvar cópia como last_audio.mp3
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            shutil.copy2(out_path, LAST_AUDIO_FILE)
            root.after(0, lambda: btn_repeat.config(state="normal"))
        except Exception:
            pass

        add_to_history(texto)
        _play_paused = False
        _play_proc = subprocess.Popen(build_play_cmd(out_path, volume=vol), stderr=subprocess.DEVNULL)
        root.after(0, lambda: [_pb_hide(),
            btn_falar.config(state="normal", text=_s("stop"), command=parar, bg=T("RED")),
            btn_pause.pack(side="right", padx=(0, 6)),
            btn_pause.config(text=_s("pause")),
            status_var.set(_s("playing"))])
        play_rc = _play_proc.wait(); _play_proc = None; _play_paused = False
        root.after(0, lambda: [
            btn_falar.config(state="normal", text=_s("speak"), command=falar, bg=T("ACCENT")),
            btn_pause.pack_forget(),
            status_var.set(_s("ready") if play_rc == 0 else _s("stopped"))])
        if play_rc == 0:
            _notify("TTS App", "Reprodução concluída.")
        try:
            if out_path and os.path.exists(out_path): os.remove(out_path)
        except Exception: pass

    threading.Thread(target=run, daemon=True).start()

def repetir():
    """Reproduz o último áudio gerado."""
    global _play_proc, _play_paused
    if not os.path.exists(LAST_AUDIO_FILE):
        return
    if not _deps_ok(need_ffplay=True):
        return
    vol = vol_var.get()
    _play_paused = False
    _play_proc = subprocess.Popen(build_play_cmd(LAST_AUDIO_FILE, volume=vol), stderr=subprocess.DEVNULL)
    btn_falar.config(state="normal", text=_s("stop"), command=parar, bg=T("RED"))
    btn_pause.pack(side="right", padx=(0, 6))
    btn_pause.config(text=_s("pause"))
    status_var.set(_s("playing"))

    def _wait():
        global _play_proc, _play_paused
        play_rc = _play_proc.wait(); _play_proc = None; _play_paused = False
        root.after(0, lambda: [
            btn_falar.config(state="normal", text=_s("speak"), command=falar, bg=T("ACCENT")),
            btn_pause.pack_forget(),
            status_var.set(_s("ready") if play_rc == 0 else _s("stopped"))])

    threading.Thread(target=_wait, daemon=True).start()

def salvar(_event=None):
    texto = text_box.get("1.0", tk.END).strip()
    if not texto:
        messagebox.showwarning("Aviso", "Digite algum texto primeiro!"); return
    path = filedialog.asksaveasfilename(defaultextension=".mp3",
                                        filetypes=[("MP3","*.mp3")], initialfile="audio.mp3")
    if not path: return
    if not _deps_ok(need_ffplay=False): return
    voz, vel = voz_var.get(), vel_var.get()
    status_var.set(_s("saving")); root.after(0, _pb_show)

    def run():
        try:
            fn = generate_audio_long if len(split_text(texto)) > 1 else generate_audio
            rc, tmp = fn(voz, vel, texto, None)
        except Exception:
            logging.exception("generate_audio failed on save"); rc = 1
        if rc != 0:
            root.after(0, lambda: [_pb_hide(), status_var.set("❌ Falha ao salvar"),
                messagebox.showerror("Erro", "Falha ao gerar áudio com edge-tts")]); return
        try:
            shutil.move(tmp, path)
            root.after(0, lambda: [_pb_hide(), status_var.set(f"✅ Salvo em {os.path.basename(path)}")])
            _notify("TTS App", f"Salvo: {os.path.basename(path)}")
        except Exception:
            root.after(0, lambda: [_pb_hide(), status_var.set("❌ Erro ao salvar"),
                messagebox.showerror("Erro", f"Não foi possível salvar em {path}")])

    threading.Thread(target=run, daemon=True).start()

def limpar():
    if text_box.get("1.0", tk.END).strip() and not messagebox.askyesno("Limpar","Deseja apagar o texto?"): return
    n_str = f"0 {_s('chars')}"
    text_box.delete("1.0", tk.END); status_var.set(""); char_var.set(n_str)

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
    reg(tk.Label(pop, text="Textos recentes", font=("Segoe UI",10,"bold"), bg=T("BG"), fg=T("TEXT2")),
        bg="BG", fg="TEXT2").pack(anchor="w", padx=12, pady=(10,4))
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

def mostrar_fila():
    """Janela de exportação em lote."""
    win = tk.Toplevel(root)
    win.title("Fila de Exportação"); win.configure(bg=T("BG")); win.geometry("500x420")
    win.transient(root)
    reg(tk.Label(win, text="Fila de Exportação em Lote", font=("Segoe UI",11,"bold"),
                 bg=T("BG"), fg=T("TEXT")), bg="BG", fg="TEXT").pack(padx=12, pady=(10,4), anchor="w")
    reg(tk.Label(win, text="Digite um texto por linha e exporte todos como MP3.",
                 font=("Segoe UI",9), bg=T("BG"), fg=T("TEXT2")), bg="BG", fg="TEXT2").pack(padx=12, anchor="w")

    ta = tk.Text(win, height=10, font=("Segoe UI",10), bg=T("BG2"), fg=T("TEXT"),
                 insertbackground=T("ACCENT2"), relief="flat", bd=0, padx=8, pady=8,
                 wrap="word", selectbackground=T("ACCENT"))
    reg(ta, bg="BG2", fg="TEXT", insertbackground="ACCENT2", selectbackground="ACCENT")
    ta.pack(fill="both", expand=True, padx=12, pady=6)

    prog_var = tk.StringVar(value="")
    reg(tk.Label(win, textvariable=prog_var, font=("Segoe UI",9), bg=T("BG"), fg=T("GREEN")),
        bg="BG", fg="GREEN").pack(padx=12, anchor="w")

    def exportar():
        lines = [l.strip() for l in ta.get("1.0", tk.END).splitlines() if l.strip()]
        if not lines:
            messagebox.showwarning("Aviso", "Nenhum texto na fila."); return
        folder = filedialog.askdirectory(title="Escolha a pasta de destino")
        if not folder: return
        voz, vel = voz_var.get(), vel_var.get()

        def run():
            for i, txt in enumerate(lines, 1):
                root.after(0, lambda i=i: prog_var.set(f"⏳ Exportando {i}/{len(lines)}..."))
                out = os.path.join(folder, f"audio_{i:03d}.mp3")
                rc, tmp = generate_audio(voz, vel, txt, None)
                if rc == 0:
                    shutil.move(tmp, out)
                else:
                    root.after(0, lambda i=i: prog_var.set(f"❌ Falha no item {i}"))
                    return
            root.after(0, lambda: [prog_var.set(f"✅ {len(lines)} arquivos exportados!"),
                                   _notify("TTS App", f"{len(lines)} arquivos exportados para {folder}")])
        threading.Thread(target=run, daemon=True).start()

    reg(tk.Button(win, text="📤 Exportar Tudo", command=exportar, bg=T("ACCENT"), fg="white",
                  font=("Segoe UI",10,"bold"), relief="flat", padx=20, pady=8, cursor="hand2"),
        bg="ACCENT").pack(pady=(4,12))


def mostrar_transcricao():
    """Janela de transcrição: arquivo de áudio ou microfone → texto."""
    win = tk.Toplevel(root)
    win.title("🎤 Transcrever Áudio"); win.configure(bg=T("BG"))
    win.geometry("540x540"); win.resizable(True, True); win.transient(root)

    _has_whisper = whisper_available()
    _has_mic     = sounddevice_available()

    # ── Cabeçalho ──────────────────────────────────────────────────────────────
    reg(tk.Label(win, text="🎤 Transcrever Áudio para Texto",
                 font=("Segoe UI",12,"bold"), bg=T("BG"), fg=T("TEXT")),
        bg="BG", fg="TEXT").pack(padx=16, pady=(14,2), anchor="w")

    if not _has_whisper:
        reg(tk.Label(win,
                     text="⚠️  openai-whisper não instalado.\nRode: pip install openai-whisper",
                     font=("Segoe UI",9), bg=T("BG"), fg=T("RED"), justify="left"),
            bg="BG", fg="RED").pack(padx=16, pady=4, anchor="w")

    # ── Arquivo de áudio ───────────────────────────────────────────────────────
    file_frame = reg(tk.Frame(win, bg=T("BG2"), highlightthickness=1,
                              highlightbackground=T("ACCENT")),
                     bg="BG2", highlightbackground="ACCENT")
    file_frame.pack(fill="x", padx=16, pady=(8,4))

    reg(tk.Label(file_frame, text="📁 Arquivo de áudio", font=("Segoe UI",9,"bold"),
                 bg=T("BG2"), fg=T("TEXT2")), bg="BG2", fg="TEXT2").pack(
        anchor="w", padx=10, pady=(8,2))

    file_row = reg(tk.Frame(file_frame, bg=T("BG2")), bg="BG2")
    file_row.pack(fill="x", padx=10, pady=(0,8))

    audio_path_var = tk.StringVar()
    path_entry = tk.Entry(file_row, textvariable=audio_path_var, bg=T("BG2"), fg=T("TEXT"),
                          insertbackground=T("ACCENT2"), relief="flat", font=("Segoe UI",9))
    reg(path_entry, bg="BG2", fg="TEXT", insertbackground="ACCENT2")
    path_entry.pack(side="left", fill="x", expand=True, ipady=4)

    def _escolher_arquivo():
        p = filedialog.askopenfilename(
            title="Escolher arquivo de áudio",
            filetypes=[("Áudio", "*.mp3 *.wav *.m4a *.flac *.ogg *.opus"),
                       ("Todos", "*.*")])
        if p:
            audio_path_var.set(p)

    reg(tk.Button(file_row, text="Escolher", command=_escolher_arquivo,
                  bg=T("ACCENT"), fg="white", font=("Segoe UI",9,"bold"),
                  relief="flat", padx=10, pady=4, cursor="hand2"),
        bg="ACCENT").pack(side="left", padx=(6,0))

    # ── Microfone ──────────────────────────────────────────────────────────────
    mic_frame = reg(tk.Frame(win, bg=T("BG2"), highlightthickness=1,
                             highlightbackground=T("ACCENT")),
                    bg="BG2", highlightbackground="ACCENT")
    mic_frame.pack(fill="x", padx=16, pady=4)

    mic_top = reg(tk.Frame(mic_frame, bg=T("BG2")), bg="BG2")
    mic_top.pack(fill="x", padx=10, pady=(8,6))

    reg(tk.Label(mic_top, text="🎙 Gravar pelo microfone", font=("Segoe UI",9,"bold"),
                 bg=T("BG2"), fg=T("TEXT2")), bg="BG2", fg="TEXT2").pack(side="left")

    if not _has_mic:
        reg(tk.Label(mic_top, text="(sounddevice não instalado)", font=("Segoe UI",8),
                     bg=T("BG2"), fg=T("TEXT2")), bg="BG2", fg="TEXT2").pack(side="left", padx=6)

    mic_status = tk.StringVar(value="")
    _recording = {"active": False, "tmp": ""}
    _timer_id  = {"id": None}

    rec_btn = reg(tk.Button(mic_frame, text="⏺ Iniciar gravação", bg=T("BG2"), fg=T("ACCENT2"),
                            font=("Segoe UI",10,"bold"), relief="flat", padx=12, pady=6,
                            cursor="hand2", state="normal" if _has_mic else "disabled"),
                  bg="BG2", fg="ACCENT2")
    rec_btn.pack(side="left", padx=(10,6), pady=(0,8))

    rec_lbl = reg(tk.Label(mic_frame, textvariable=mic_status, font=("Segoe UI",9),
                           bg=T("BG2"), fg=T("GREEN")), bg="BG2", fg="GREEN")
    rec_lbl.pack(side="left", pady=(0,8))

    _elapsed = {"s": 0}

    def _tick():
        _elapsed["s"] += 1
        secs = _elapsed["s"]
        mic_status.set(f"⏺ {secs//60:02d}:{secs%60:02d} gravando...")
        _timer_id["id"] = win.after(1000, _tick)

    def _toggle_rec():
        if not _recording["active"]:
            _elapsed["s"] = 0
            start_mic_recording()
            _recording["active"] = True
            rec_btn.config(text="⏹ Parar gravação", fg="white",
                           bg=T("RED") if _has_mic else T("BG2"))
            reg(rec_btn, bg="RED")
            mic_status.set("⏺ 00:00 gravando...")
            _tick()
        else:
            if _timer_id["id"]:
                win.after_cancel(_timer_id["id"]); _timer_id["id"] = None
            tmp = stop_mic_recording()
            _recording["active"] = False
            _recording["tmp"] = tmp
            rec_btn.config(text="⏺ Iniciar gravação", fg=T("ACCENT2"), bg=T("BG2"))
            reg(rec_btn, bg="BG2", fg="ACCENT2")
            if tmp:
                audio_path_var.set(tmp)
                mic_status.set("✅ Gravação salva — clique em Transcrever")
            else:
                mic_status.set("⚠️ Nenhum áudio captado")

    rec_btn.config(command=_toggle_rec)

    # ── Opções: modelo e idioma ────────────────────────────────────────────────
    opts = reg(tk.Frame(win, bg=T("BG")), bg="BG")
    opts.pack(fill="x", padx=16, pady=(6,2))

    reg(tk.Label(opts, text="Modelo Whisper:", font=("Segoe UI",9), bg=T("BG"), fg=T("TEXT2")),
        bg="BG", fg="TEXT2").pack(side="left")
    model_var = tk.StringVar(value="base")
    for m in ["tiny", "base", "small", "medium"]:
        tk.Radiobutton(opts, text=m, variable=model_var, value=m,
                       bg=T("BG"), fg=T("TEXT"), selectcolor=T("BG2"),
                       activebackground=T("BG"), font=("Segoe UI",9),
                       cursor="hand2").pack(side="left", padx=4)

    reg(tk.Label(opts, text="  Idioma:", font=("Segoe UI",9), bg=T("BG"), fg=T("TEXT2")),
        bg="BG", fg="TEXT2").pack(side="left", padx=(8,0))
    lang_var = tk.StringVar(value="")
    lang_opts = [("Auto", ""), ("PT", "pt"), ("EN", "en"), ("ES", "es"),
                 ("FR", "fr"), ("DE", "de"), ("JA", "ja"), ("ZH", "zh")]
    for lbl, val in lang_opts:
        tk.Radiobutton(opts, text=lbl, variable=lang_var, value=val,
                       bg=T("BG"), fg=T("TEXT"), selectcolor=T("BG2"),
                       activebackground=T("BG"), font=("Segoe UI",9),
                       cursor="hand2").pack(side="left", padx=2)

    hint = ("tiny ≈ 75 MB · base ≈ 140 MB · small ≈ 460 MB  "
            "(download automático na 1ª execução)")
    reg(tk.Label(win, text=hint, font=("Segoe UI",8), bg=T("BG"), fg=T("TEXT2")),
        bg="BG", fg="TEXT2").pack(padx=16, anchor="w")

    # ── Botão transcrever ──────────────────────────────────────────────────────
    trans_status = tk.StringVar(value="")
    reg(tk.Label(win, textvariable=trans_status, font=("Segoe UI",9),
                 bg=T("BG"), fg=T("GREEN")), bg="BG", fg="GREEN").pack(padx=16, anchor="w")

    trans_pb = ttk.Progressbar(win, mode="indeterminate",
                                style="TTS.Horizontal.TProgressbar")

    def _transcrever():
        path = audio_path_var.get().strip()
        if not path:
            messagebox.showwarning("Aviso", "Selecione um arquivo ou grave pelo microfone.",
                                   parent=win); return
        if not os.path.exists(path):
            messagebox.showerror("Erro", f"Arquivo não encontrado:\n{path}", parent=win); return
        if not _has_whisper:
            messagebox.showerror("Erro",
                                 "openai-whisper não está instalado.\n"
                                 "Rode: pip install openai-whisper", parent=win); return

        btn_trans.config(state="disabled")
        trans_status.set("⏳ Transcrevendo... (pode levar alguns segundos)")
        trans_pb.pack(fill="x", padx=16, pady=(0,4))
        trans_pb.start(10)

        def run():
            try:
                lang = lang_var.get() or None
                text = transcribe_audio(path, model_name=model_var.get(), language=lang)
                root.after(0, lambda: _mostrar_resultado(text))
            except Exception as exc:
                root.after(0, lambda: [
                    trans_pb.stop(), trans_pb.pack_forget(),
                    btn_trans.config(state="normal"),
                    trans_status.set(f"❌ Erro: {exc}"),
                    messagebox.showerror("Erro na transcrição", str(exc), parent=win)])

        threading.Thread(target=run, daemon=True).start()

    btn_trans = reg(tk.Button(win, text="🔍 Transcrever", command=_transcrever,
                              bg=T("ACCENT"), fg="white", font=("Segoe UI",11,"bold"),
                              relief="flat", padx=22, pady=8, cursor="hand2",
                              state="normal" if _has_whisper else "disabled"),
                   bg="ACCENT")
    btn_trans.pack(pady=(4,2))

    # ── Resultado ──────────────────────────────────────────────────────────────
    reg(tk.Label(win, text="Resultado:", font=("Segoe UI",9,"bold"),
                 bg=T("BG"), fg=T("TEXT2")), bg="BG", fg="TEXT2").pack(
        padx=16, pady=(6,0), anchor="w")

    res_frame = reg(tk.Frame(win, bg=T("BG2"), highlightthickness=1,
                             highlightbackground=T("ACCENT")),
                    bg="BG2", highlightbackground="ACCENT")
    res_frame.pack(fill="both", expand=True, padx=16, pady=(2,4))

    res_box = tk.Text(res_frame, height=6, font=("Segoe UI",10), bg=T("BG2"), fg=T("TEXT"),
                      insertbackground=T("ACCENT2"), relief="flat", bd=0, padx=10, pady=8,
                      wrap="word", selectbackground=T("ACCENT"))
    reg(res_box, bg="BG2", fg="TEXT", insertbackground="ACCENT2", selectbackground="ACCENT")
    res_sb = tk.Scrollbar(res_frame, command=res_box.yview)
    res_box.config(yscrollcommand=res_sb.set)
    res_sb.pack(side="right", fill="y")
    res_box.pack(fill="both", expand=True)

    def _mostrar_resultado(text: str):
        trans_pb.stop(); trans_pb.pack_forget()
        btn_trans.config(state="normal")
        trans_status.set(f"✅ {len(text)} chars · {len(text.split())} palavras")
        res_box.delete("1.0", tk.END)
        res_box.insert("1.0", text)
        _notify("TTS App", "Transcrição concluída.")

    # ── Ações do resultado ─────────────────────────────────────────────────────
    act_frame = reg(tk.Frame(win, bg=T("BG")), bg="BG")
    act_frame.pack(fill="x", padx=16, pady=(0,12))

    def _copiar():
        txt = res_box.get("1.0", tk.END).strip()
        if txt:
            root.clipboard_clear(); root.clipboard_append(txt)
            trans_status.set("📋 Copiado!")

    def _usar_no_tts():
        txt = res_box.get("1.0", tk.END).strip()
        if txt:
            text_box.delete("1.0", tk.END); text_box.insert("1.0", txt)
            _atualizar_contador()
            win.destroy()

    for lbl, cmd in [("📋 Copiar", _copiar), ("✏ Usar no TTS", _usar_no_tts)]:
        reg(tk.Button(act_frame, text=lbl, command=cmd, bg=T("BG2"), fg=T("TEXT2"),
                      font=("Segoe UI",10,"bold"), relief="flat", padx=14, pady=6,
                      cursor="hand2"), bg="BG2", fg="TEXT2").pack(side="left", padx=(0,8))

    reg(tk.Button(act_frame, text="❌ Fechar", command=win.destroy,
                  bg=T("BG2"), fg=T("TEXT2"), font=("Segoe UI",10),
                  relief="flat", padx=14, pady=6, cursor="hand2"),
        bg="BG2", fg="TEXT2").pack(side="right")

    win.bind("<Escape>", lambda e: win.destroy())


def _atualizar_contador(_event=None):
    texto = text_box.get("1.0", tk.END).strip()
    n = len(texto)
    words = len(texto.split()) if texto else 0
    char_var.set(
        f"{n} {_s('chars')} · {words} {_s('words')}"
        + (_s("chars_long") if n > LONG_TEXT_THRESHOLD else "")
    )

def _ajustar_fonte(delta):
    global _font_size
    _font_size = max(8, min(24, _font_size + delta))
    text_box.config(font=("Segoe UI", _font_size)); save_prefs(font_size=_font_size)

def _mostrar_busca(_event=None):
    """Exibe barra de busca com highlight no text_box (Ctrl+F)."""
    global _search_frame, _search_matches, _search_idx
    if _search_frame and _search_frame.winfo_exists():
        # Já aberta: apenas focar no campo
        for child in _search_frame.winfo_children():
            if isinstance(child, tk.Entry):
                child.focus_set(); return
        return

    _search_frame = reg(tk.Frame(text_frame, bg=T("BG2")), bg="BG2")
    _search_frame.pack(fill="x", padx=4, pady=(0,4))

    reg(tk.Label(_search_frame, text="🔍", bg=T("BG2"), fg=T("TEXT2"), font=("Segoe UI",9)),
        bg="BG2", fg="TEXT2").pack(side="left", padx=(6,0))

    se = tk.Entry(_search_frame, bg=T("BG2"), fg=T("TEXT"),
                  insertbackground=T("ACCENT2"), relief="flat", font=("Segoe UI",10))
    reg(se, bg="BG2", fg="TEXT", insertbackground="ACCENT2")
    se.pack(side="left", fill="x", expand=True, padx=6, ipady=3)

    match_lbl = reg(tk.Label(_search_frame, text="", width=6, bg=T("BG2"), fg=T("TEXT2"),
                              font=("Segoe UI",8), anchor="w"),
                    bg="BG2", fg="TEXT2")
    match_lbl.pack(side="left")

    def _search(*_):
        global _search_matches, _search_idx
        text_box.tag_remove("search_hl", "1.0", tk.END)
        text_box.tag_remove("search_cur", "1.0", tk.END)
        query = se.get()
        _search_matches = []; _search_idx = -1
        if not query:
            match_lbl.config(text=""); return
        pos = "1.0"
        while True:
            pos = text_box.search(query, pos, stopindex=tk.END, nocase=True)
            if not pos: break
            end = f"{pos}+{len(query)}c"
            text_box.tag_add("search_hl", pos, end)
            _search_matches.append(pos); pos = end
        text_box.tag_config("search_hl", background=T("ACCENT"), foreground="white")
        if _search_matches:
            _jump(0); match_lbl.config(text=f"1/{len(_search_matches)}")
        else:
            match_lbl.config(text="0/0")

    def _jump(i):
        global _search_idx
        if not _search_matches: return
        _search_idx = i % len(_search_matches)
        text_box.tag_remove("search_cur", "1.0", tk.END)
        pos = _search_matches[_search_idx]
        end = f"{pos}+{len(se.get())}c"
        text_box.tag_add("search_cur", pos, end)
        text_box.tag_config("search_cur", background=T("ACCENT2"), foreground="white")
        text_box.see(pos)
        match_lbl.config(text=f"{_search_idx+1}/{len(_search_matches)}")

    def _next(_e=None): _jump(_search_idx + 1)
    def _prev(_e=None): _jump(_search_idx - 1)

    def _fechar(_e=None):
        global _search_frame
        text_box.tag_remove("search_hl", "1.0", tk.END)
        text_box.tag_remove("search_cur", "1.0", tk.END)
        if _search_frame and _search_frame.winfo_exists():
            _search_frame.destroy(); _search_frame = None
        text_box.focus_set()

    se.bind("<KeyRelease>", _search)
    se.bind("<Return>", _next)
    se.bind("<Shift-Return>", _prev)
    se.bind("<Escape>", _fechar)

    for txt, cmd in [("▲", _prev), ("▼", _next)]:
        reg(tk.Button(_search_frame, text=txt, command=cmd, bg=T("BG2"), fg=T("TEXT2"),
                      font=("Segoe UI",8), relief="flat", padx=5, cursor="hand2"),
            bg="BG2", fg="TEXT2").pack(side="left")
    reg(tk.Button(_search_frame, text="✕", command=_fechar, bg=T("BG2"), fg=T("TEXT2"),
                  font=("Segoe UI",8), relief="flat", padx=6, cursor="hand2"),
        bg="BG2", fg="TEXT2").pack(side="left", padx=(0,4))

    se.focus_set()
    return "break"


def _mostrar_ajuda(_event=None):
    """Dialog F1 com todos os atalhos de teclado."""
    win = tk.Toplevel(root)
    win.title(_s("help_title")); win.configure(bg=T("BG")); win.resizable(False, False)
    win.transient(root); win.grab_set()
    reg(tk.Label(win, text=f"⌨  {_s('help_title')}", font=("Segoe UI",11,"bold"),
                 bg=T("BG"), fg=T("TEXT")), bg="BG", fg="TEXT").pack(padx=20, pady=(14,8))
    fr = reg(tk.Frame(win, bg=T("BG2"), highlightthickness=1, highlightbackground=T("ACCENT")),
             bg="BG2", highlightbackground="ACCENT")
    fr.pack(padx=20, pady=(0,12), fill="x")
    for shortcut, desc in _s("shortcuts"):
        row = reg(tk.Frame(fr, bg=T("BG2")), bg="BG2"); row.pack(fill="x", padx=8, pady=3)
        reg(tk.Label(row, text=shortcut, font=("Courier",10,"bold"), bg=T("BG2"), fg=T("ACCENT2"),
                     width=14, anchor="w"), bg="BG2", fg="ACCENT2").pack(side="left")
        reg(tk.Label(row, text=desc, font=("Segoe UI",10), bg=T("BG2"), fg=T("TEXT"), anchor="w"),
            bg="BG2", fg="TEXT").pack(side="left")
    reg(tk.Button(win, text="OK", command=win.destroy, bg=T("ACCENT"), fg="white",
                  font=("Segoe UI",10,"bold"), relief="flat", padx=28, pady=6, cursor="hand2"),
        bg="ACCENT").pack(pady=(0,14))
    win.bind("<Escape>", lambda e: win.destroy())
    win.bind("<F1>", lambda e: win.destroy())

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
        self.arrow.pack(side="right", padx=8); self.arrow.bind("<Button-1>", lambda e: self.toggle_popup())
        # 1. Indicador de carregamento
        self.loading_lbl = tk.Label(self, text="", bg=T("BG2"), fg=T("TEXT2"), font=("Segoe UI",8))
        self.loading_lbl.pack(side="right", padx=4)

    def set_loading(self, loading: bool):
        self.loading_lbl.config(text="⏳ carregando..." if loading else "")

    def update_values(self, values):
        self.values = values
        self.set_loading(False)

    def toggle_popup(self):
        if self.popup and self.popup.winfo_exists():
            self.popup.destroy(); self.popup = None; return
        self.show_popup()

    def show_popup(self):
        x, y, w = self.winfo_rootx(), self.winfo_rooty()+self.winfo_height(), self.winfo_width()
        self.popup = tk.Toplevel(); self.popup.wm_overrideredirect(True); self.popup.configure(bg=T("BG2"))
        outer = tk.Frame(self.popup, bg=T("BG2"), highlightthickness=1, highlightbackground=T("ACCENT"))
        outer.pack(fill="both", expand=True)

        # 2. Vozes recentes no topo
        recent = _prefs.get("recent_voices", [])
        if recent:
            reg(tk.Label(outer, text="Recentes", font=("Segoe UI",8,"bold"),
                         bg=T("BG2"), fg=T("TEXT2")), bg="BG2", fg="TEXT2").pack(anchor="w", padx=8, pady=(4,0))
            for rv in recent:
                def make_r(val):
                    def cmd(): self.variable.set(val); self.popup.destroy(); self.popup = None
                    return cmd
                tk.Button(outer, text=f"★ {rv}", bg=T("ACCENT"), fg="white", font=("Segoe UI",9),
                          relief="flat", anchor="w", padx=10, pady=3, cursor="hand2",
                          activebackground=T("ACCENT2"), activeforeground="white",
                          command=make_r(rv)).pack(fill="x", padx=4, pady=1)
            tk.Frame(outer, bg=T("ACCENT"), height=1).pack(fill="x", pady=(4,0))

        # Abas de idioma
        tabs = tk.Frame(outer, bg=T("BG2")); tabs.pack(fill="x", padx=4, pady=(4,0))
        filter_var = tk.StringVar()
        for lang, label in zip(LANG_TABS, LANG_LABELS):
            tk.Button(tabs, text=label, bg=T("BG2"), fg=T("TEXT2"), font=("Segoe UI",8),
                      relief="flat", padx=5, pady=2, cursor="hand2",
                      activebackground=T("ACCENT"), activeforeground="white",
                      command=lambda l=lang: filter_var.set(l)).pack(side="left", padx=1)
        tk.Frame(outer, bg=T("ACCENT"), height=1).pack(fill="x", pady=(4,0))
        fe = tk.Entry(outer, textvariable=filter_var, bg=T("BG2"), fg=T("TEXT"),
                      insertbackground=T("ACCENT2"), relief="flat", font=("Segoe UI",10))
        fe.pack(fill="x", padx=6, pady=4)
        tk.Frame(outer, bg=T("ACCENT"), height=1).pack(fill="x")

        lf = tk.Frame(outer, bg=T("BG2")); lf.pack(fill="both", expand=True)
        sb = tk.Scrollbar(lf); sb.pack(side="right", fill="y")
        lb = tk.Listbox(lf, bg=T("BG2"), fg=T("TEXT"), selectbackground=T("ACCENT"),
                        selectforeground="white", font=("Segoe UI",10), relief="flat",
                        bd=0, highlightthickness=0, activestyle="none", yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True); sb.config(command=lb.yview)
        lb.bind("<Button-4>", lambda e: lb.yview_scroll(-1, "units"))
        lb.bind("<Button-5>", lambda e: lb.yview_scroll(1, "units"))

        _filtered = []
        def render(ft=""):
            lb.delete(0, tk.END); _filtered.clear()
            for v in self.values:
                if ft.lower() in v.lower():
                    _filtered.append(v); lb.insert(tk.END, v)
            h = min(len(_filtered)*20 + (len(recent)*28 if recent else 0) + 100, 340)
            self.popup.geometry(f"{w}x{h}+{x}+{y}")

        def on_select(_e):
            sel = lb.curselection()
            if not sel: return
            val = _filtered[sel[0]]
            self.variable.set(val)
            # 2. salvar em recentes
            r = _prefs.get("recent_voices", [])
            if val in r: r.remove(val)
            r.insert(0, val); _prefs["recent_voices"] = r[:3]; save_prefs(recent_voices=r[:3])
            self.popup.destroy(); self.popup = None

        lb.bind("<<ListboxSelect>>", on_select)
        lb.bind("<Return>", on_select)
        filter_var.trace_add("write", lambda *_: render(filter_var.get()))
        render()
        self.popup.bind("<FocusOut>", lambda e: self.popup.after(150, lambda:
            self.popup.destroy() or setattr(self, "popup", None)
            if self.popup and self.popup.winfo_exists()
            and self.popup.focus_get() is None else None))
        fe.focus_set()

# ── Janela ────────────────────────────────────────────────────────────────────
if _DND_OK:
    root = _dnd.TkinterDnD.Tk()
else:
    root = tk.Tk()
root.title("Text to Speech"); root.geometry("560x640")
root.minsize(480, 520); root.resizable(True, True)
reg(root, bg="BG")
if _prefs.get("geometry"):
    try: root.geometry(_prefs["geometry"])
    except Exception: pass

# HiDPI scaling: detectar DPI e aplicar escala
try:
    _dpi = root.winfo_fpixels("1i")
    if _dpi > 96:
        root.tk.call("tk", "scaling", _dpi / 72.0)
except Exception:
    pass

reg(tk.Frame(root, bg=T("ACCENT"), height=4), bg="ACCENT").pack(fill="x")
title_frame = reg(tk.Frame(root, bg=T("BG"), pady=10), bg="BG"); title_frame.pack(fill="x")
title_row = reg(tk.Frame(title_frame, bg=T("BG")), bg="BG"); title_row.pack()
reg(tk.Label(title_row, text="🎙 Text to Speech", font=("Segoe UI",16,"bold"), bg=T("BG"), fg=T("TEXT")),
    bg="BG", fg="TEXT").pack(side="left", padx=(0,8))
btn_theme = reg(tk.Button(title_row, text="☀️" if _theme_name=="dark" else "🌙",
                           command=toggle_theme, bg=T("BG"), fg=T("TEXT2"), font=("Segoe UI",11),
                           relief="flat", cursor="hand2", activebackground=T("BG"), activeforeground=T("ACCENT2")),
                bg="BG", activebackground="BG", fg="TEXT2", activeforeground="ACCENT2")
btn_theme.pack(side="left")
btn_lang = reg(tk.Button(title_row, text="🇧🇷" if _ui_lang == "pt-BR" else "🇺🇸",
                          command=toggle_lang, bg=T("BG"), fg=T("TEXT2"),
                          font=("Segoe UI",11), relief="flat", cursor="hand2",
                          activebackground=T("BG"), activeforeground=T("ACCENT2")),
               bg="BG", activebackground="BG", fg="TEXT2", activeforeground="ACCENT2")
btn_lang.pack(side="left", padx=(4,0))
reg(tk.Label(title_frame, text="Converta texto em voz natural", font=("Segoe UI",9), bg=T("BG"), fg=T("TEXT2")),
    bg="BG", fg="TEXT2").pack()

style = ttk.Style(); style.theme_use("clam")
style.configure("TTS.Horizontal.TProgressbar", troughcolor=T("BG2"), background=T("ACCENT"), thickness=5)
pb = ttk.Progressbar(root, mode="indeterminate", style="TTS.Horizontal.TProgressbar")

text_frame = reg(tk.Frame(root, bg=T("BG2"), bd=0, highlightthickness=1, highlightbackground=T("ACCENT")),
                 bg="BG2", highlightbackground="ACCENT")
text_frame.pack(padx=20, pady=(0,4), fill="both", expand=True)

th = reg(tk.Frame(text_frame, bg=T("BG2")), bg="BG2"); th.pack(fill="x", padx=10, pady=(8,0))
reg(tk.Label(th, text="Texto", font=("Segoe UI",9,"bold"), bg=T("BG2"), fg=T("TEXT2")),
    bg="BG2", fg="TEXT2").pack(side="left")

for icon, cmd in [("📋", colar_clipboard), ("📂", abrir_txt), ("🕘", mostrar_historico),
                   ("📤", mostrar_fila), ("🎤", mostrar_transcricao),
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
text_box.bind("<KeyRelease>", lambda e: [_atualizar_contador(e), _detect_and_suggest(e)])

# Drag & drop de arquivos .txt (requer tkinterdnd2)
if _DND_OK:
    def _on_drop(event):
        path = event.data.strip().strip("{}")
        if path.lower().endswith(".txt"):
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                text_box.delete("1.0", tk.END)
                text_box.insert("1.0", content)
                _atualizar_contador()
                status_var.set(f"📂 {os.path.basename(path)}")
            except Exception as exc:
                messagebox.showerror("Erro", f"Não foi possível abrir o arquivo:\n{exc}")
    text_box.drop_target_register("DND_Files")
    text_box.dnd_bind("<<Drop>>", _on_drop)

char_var = tk.StringVar(value="0 caracteres")
reg(tk.Label(text_frame, textvariable=char_var, font=("Segoe UI",8), bg=T("BG2"), fg=T("TEXT2"), anchor="e"),
    bg="BG2", fg="TEXT2").pack(fill="x", padx=10, pady=(0,6))

ctrl_frame = reg(tk.Frame(root, bg=T("BG")), bg="BG"); ctrl_frame.pack(padx=20, fill="x", pady=(4,0))
left = reg(tk.Frame(ctrl_frame, bg=T("BG")), bg="BG"); left.pack(side="left", fill="x", expand=True, padx=(0,10))
reg(tk.Label(left, text="🗣 Voz", font=("Segoe UI",9,"bold"), bg=T("BG"), fg=T("TEXT2")),
    bg="BG", fg="TEXT2").pack(anchor="w")
voz_var = tk.StringVar(value=_prefs.get("voice","pt-BR-FranciscaNeural"))
voz_selector = VozSelector(left, voz_var, ["pt-BR-FranciscaNeural","pt-BR-AntonioNeural",
                                            "en-US-JennyNeural","en-US-GuyNeural","es-ES-ElviraNeural"])
voz_selector.pack(fill="x", pady=(4,0))

right = reg(tk.Frame(ctrl_frame, bg=T("BG")), bg="BG"); right.pack(side="right")
reg(tk.Label(right, text="⚡ Velocidade", font=("Segoe UI",9,"bold"), bg=T("BG"), fg=T("TEXT2")),
    bg="BG", fg="TEXT2").pack(anchor="w")
vel_var = tk.IntVar(value=_prefs.get("speed",0))
vel_label = reg(tk.Label(right, text="0%", font=("Segoe UI",9), bg=T("BG"), fg=T("ACCENT2"), width=5),
                bg="BG", fg="ACCENT2"); vel_label.pack(anchor="e")
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
                bg="BG", fg="ACCENT2"); vol_label.pack(anchor="e")
def _upd_vol(v): vol_label.config(text=f"{int(float(v))}%")
reg(tk.Scale(right, from_=0, to=100, orient="horizontal", variable=vol_var, length=160,
             bg=T("BG"), fg=T("TEXT"), troughcolor=T("BG2"), activebackground=T("ACCENT2"),
             highlightthickness=0, bd=0, showvalue=False, command=_upd_vol),
    bg="BG", fg="TEXT", troughcolor="BG2", activebackground="ACCENT2").pack()

btn_frame = reg(tk.Frame(root, bg=T("BG")), bg="BG"); btn_frame.pack(pady=12, padx=20, fill="x")
reg(tk.Button(btn_frame, text="🗑 Limpar", command=limpar, bg=T("BG2"), fg=T("TEXT2"),
              font=("Segoe UI",10), relief="flat", padx=15, pady=8, cursor="hand2"),
    bg="BG2", fg="TEXT2").pack(side="left")
reg(tk.Button(btn_frame, text="💾 Salvar MP3", command=salvar, bg=T("BG2"), fg=T("ACCENT2"),
              font=("Segoe UI",10,"bold"), relief="flat", padx=15, pady=8, cursor="hand2"),
    bg="BG2", fg="ACCENT2").pack(side="left", padx=10)
btn_falar = reg(tk.Button(btn_frame, text="▶   Falar", command=falar, bg=T("ACCENT"), fg="white",
                            font=("Segoe UI",11,"bold"), relief="flat", padx=25, pady=8, cursor="hand2"), bg="ACCENT")
btn_falar.pack(side="right")

btn_pause = reg(tk.Button(btn_frame, text=_s("pause"), command=pausar_retomar,
                           bg=T("BG2"), fg=T("TEXT2"), font=("Segoe UI",10,"bold"),
                           relief="flat", padx=15, pady=8, cursor="hand2"),
                bg="BG2", fg="TEXT2")
# btn_pause is shown/hidden dynamically during playback

_has_last = os.path.exists(LAST_AUDIO_FILE)
btn_repeat = reg(tk.Button(btn_frame, text="🔁", command=repetir,
                            bg=T("BG2"), fg=T("TEXT2"), font=("Segoe UI",10),
                            relief="flat", padx=10, pady=8, cursor="hand2",
                            state="normal" if _has_last else "disabled"),
                 bg="BG2", fg="TEXT2")
btn_repeat.pack(side="right", padx=(0,6))

status_var = tk.StringVar()
reg(tk.Label(root, textvariable=status_var, font=("Segoe UI",9), bg=T("BG"), fg=T("GREEN")),
    bg="BG", fg="GREEN").pack(pady=(0,8))

root.bind("<Control-Return>", falar)
root.bind("<Control-s>", salvar)
root.bind("<Control-o>", abrir_txt)
root.bind("<Control-f>", _mostrar_busca)
root.bind("<Control-p>", lambda e: pausar_retomar())
root.bind("<F1>", _mostrar_ajuda)
root.bind("<Escape>", lambda e: parar())
root.bind("<Control-z>", lambda e: text_box.edit_undo())
root.bind("<Control-y>", lambda e: text_box.edit_redo())
root.bind("<Map>", lambda e: None)
root.bind("<Unmap>", _on_minimize)

def _on_close():
    save_prefs(voice=voz_var.get(), speed=vel_var.get(), volume=vol_var.get(),
               theme=_theme_name, font_size=_font_size, geometry=root.geometry())
    if _tray_icon: _tray_icon.stop()
    root.destroy()
root.protocol("WM_DELETE_WINDOW", _on_close)

_check_deps_startup()

def _bg_startup():
    # Carregar vozes
    voz_selector.set_loading(True)
    voices = list_voices()
    if voices: root.after(0, lambda: voz_selector.update_values(voices))
    else: root.after(0, lambda: voz_selector.set_loading(False))
    # Verificar atualizações
    _check_update()

threading.Thread(target=_bg_startup, daemon=True).start()

# Iniciar tray
if _TRAY_OK:
    _start_tray()

root.mainloop()
