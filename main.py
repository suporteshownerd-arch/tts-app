import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os

BG = "#1e1e2e"
BG2 = "#2a2a3e"
ACCENT = "#7c3aed"
ACCENT2 = "#a855f7"
TEXT = "#e2e8f0"
TEXT2 = "#94a3b8"
GREEN = "#22c55e"

def falar():
    texto = text_box.get("1.0", tk.END).strip()
    voz = voz_var.get()
    velocidade = vel_var.get()
    if not texto:
        messagebox.showwarning("Aviso", "Digite algum texto primeiro!")
        return
    btn_falar.config(state="disabled", text="⏳  Gerando áudio...")
    status_var.set("🔊 Falando...")
    def run():
        subprocess.run(["edge-tts","--voice", voz,"--rate", f"{velocidade:+d}%","--text", texto,"--write-media", "/tmp/tts_saida.mp3"])
        subprocess.run(["ffplay", "-nodisp", "-autoexit", "/tmp/tts_saida.mp3"], stderr=subprocess.DEVNULL)
        btn_falar.config(state="normal", text="▶   Falar")
        status_var.set("✅ Pronto!")
    threading.Thread(target=run).start()

def salvar():
    texto = text_box.get("1.0", tk.END).strip()
    voz = voz_var.get()
    velocidade = vel_var.get()
    if not texto:
        messagebox.showwarning("Aviso", "Digite algum texto primeiro!")
        return
    path = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("MP3", "*.mp3")], initialfile="audio.mp3")
    if not path:
        return
    status_var.set("💾 Salvando...")
    def run():
        subprocess.run(["edge-tts","--voice", voz,"--rate", f"{velocidade:+d}%","--text", texto,"--write-media", path])
        status_var.set(f"✅ Salvo em {os.path.basename(path)}")
    threading.Thread(target=run).start()

def limpar():
    text_box.delete("1.0", tk.END)
    status_var.set("")

class VozSelector(tk.Frame):
    def __init__(self, parent, variable, values, **kwargs):
        super().__init__(parent, bg=BG2, highlightthickness=1, highlightbackground=ACCENT, **kwargs)
        self.variable = variable
        self.values = values
        self.popup = None
        self.btn = tk.Button(self, textvariable=variable, bg=BG2, fg=TEXT,
                             font=("Segoe UI", 10), relief="flat", anchor="w",
                             padx=10, cursor="hand2", activebackground=BG2,
                             activeforeground=ACCENT2, command=self.toggle_popup)
        self.btn.pack(side="left", fill="x", expand=True, ipady=6)
        arrow = tk.Label(self, text="▾", bg=BG2, fg=ACCENT2, font=("Segoe UI", 12), cursor="hand2")
        arrow.pack(side="right", padx=8)
        arrow.bind("<Button-1>", lambda e: self.toggle_popup())

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
        self.popup.geometry(f"{w}x{min(len(self.values)*32, 160)}+{x}+{y}")
        self.popup.configure(bg=BG2)
        frame = tk.Frame(self.popup, bg=BG2, highlightthickness=1, highlightbackground=ACCENT)
        frame.pack(fill="both", expand=True)
        for v in self.values:
            def make_cmd(val):
                def cmd():
                    self.variable.set(val)
                    self.popup.destroy()
                    self.popup = None
                return cmd
            tk.Button(frame, text=v, bg=BG2, fg=TEXT, font=("Segoe UI", 10),
                      relief="flat", anchor="w", padx=12, pady=4, cursor="hand2",
                      activebackground=ACCENT, activeforeground="white",
                      command=make_cmd(v)).pack(fill="x")
        self.popup.bind("<FocusOut>", lambda e: self.popup.destroy())
        self.popup.focus_set()

root = tk.Tk()
root.title("Text to Speech")
root.geometry("560x520")
root.configure(bg=BG)
root.resizable(False, False)

tk.Frame(root, bg=ACCENT, height=4).pack(fill="x")
title_frame = tk.Frame(root, bg=BG, pady=15)
title_frame.pack(fill="x")
tk.Label(title_frame, text="🎙 Text to Speech", font=("Segoe UI", 16, "bold"), bg=BG, fg=TEXT).pack()
tk.Label(title_frame, text="Converta texto em voz natural", font=("Segoe UI", 9), bg=BG, fg=TEXT2).pack()

text_frame = tk.Frame(root, bg=BG2, bd=0, highlightthickness=1, highlightbackground=ACCENT)
text_frame.pack(padx=20, pady=(0, 10), fill="both", expand=True)
tk.Label(text_frame, text="Texto", font=("Segoe UI", 9, "bold"), bg=BG2, fg=TEXT2).pack(anchor="w", padx=10, pady=(8, 0))
text_box = tk.Text(text_frame, height=8, font=("Segoe UI", 11), bg=BG2, fg=TEXT,
                   insertbackground=ACCENT2, relief="flat", bd=0, padx=10, pady=8,
                   wrap="word", selectbackground=ACCENT)
text_box.pack(fill="both", expand=True, padx=2, pady=(0, 8))

ctrl_frame = tk.Frame(root, bg=BG)
ctrl_frame.pack(padx=20, fill="x")

left = tk.Frame(ctrl_frame, bg=BG)
left.pack(side="left", fill="x", expand=True, padx=(0, 10))
tk.Label(left, text="🗣 Voz", font=("Segoe UI", 9, "bold"), bg=BG, fg=TEXT2).pack(anchor="w")
voz_var = tk.StringVar(value="pt-BR-FranciscaNeural")
vozes = ["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural", "en-US-JennyNeural", "en-US-GuyNeural", "es-ES-ElviraNeural"]
VozSelector(left, voz_var, vozes).pack(fill="x", pady=(4, 0))

right = tk.Frame(ctrl_frame, bg=BG)
right.pack(side="right")
tk.Label(right, text="⚡ Velocidade", font=("Segoe UI", 9, "bold"), bg=BG, fg=TEXT2).pack(anchor="w")
vel_var = tk.IntVar(value=0)
vel_label = tk.Label(right, text="0%", font=("Segoe UI", 9), bg=BG, fg=ACCENT2, width=5)
vel_label.pack(anchor="e")
def update_label(v):
    val = int(float(v))
    vel_label.config(text=f"{val:+d}%" if val != 0 else "0%")
tk.Scale(right, from_=-50, to=50, orient="horizontal", variable=vel_var, length=160,
         bg=BG, fg=TEXT, troughcolor=BG2, activebackground=ACCENT2,
         highlightthickness=0, bd=0, showvalue=False, command=update_label).pack()

btn_frame = tk.Frame(root, bg=BG)
btn_frame.pack(pady=15, padx=20, fill="x")
tk.Button(btn_frame, text="🗑 Limpar", command=limpar, bg=BG2, fg=TEXT2,
          font=("Segoe UI", 10), relief="flat", padx=15, pady=8, cursor="hand2").pack(side="left")
tk.Button(btn_frame, text="💾 Salvar MP3", command=salvar, bg=BG2, fg=ACCENT2,
          font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=8, cursor="hand2").pack(side="left", padx=10)
btn_falar = tk.Button(btn_frame, text="▶   Falar", command=falar, bg=ACCENT, fg="white",
                      font=("Segoe UI", 11, "bold"), relief="flat", padx=25, pady=8, cursor="hand2")
btn_falar.pack(side="right")

status_var = tk.StringVar()
tk.Label(root, textvariable=status_var, font=("Segoe UI", 9), bg=BG, fg=GREEN).pack(pady=(0, 10))

root.mainloop()
