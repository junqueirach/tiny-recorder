"""
Tiny Recorder v0.1.0 — a very light meeting recorder for Windows.

Records everything the computer plays (Teams, Zoom, Meet, anything) and everything you say into ONE MP3 file, with
the date, title, people, project and notes written into the file's tags, and the file named "date - Title.mp3".
No AI, no transcription, no cloud.

  * big Record / Pause / Stop, timer, two level meters, Ctrl+Alt+R from any program
  * tags written to the MP3 (ID3) and the file renamed to match; edit them later from the list
  * the file is written while recording; an unfinished file is offered for recovery at the next start
  * About, Help (F1), English and Portuguese, Catppuccin Mocha dark theme (like the other apps)

Threads: the recorder, the list loader and the hotkey run on their own threads and only put plain data on
self.q; the Tk thread drains it with after().
"""

import math
import os
import queue
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import tinyrecorder_winsys as winsys                                         # noqa: E402

winsys.dpi_aware()
winsys.set_app_id("Junqueira.TinyRecorder")

import tkinter as tk                                                         # noqa: E402
from tkinter import filedialog, messagebox, ttk                              # noqa: E402

import tinyrecorder_audio as audio                                           # noqa: E402
import tinyrecorder_core as core                                             # noqa: E402
import tinyrecorder_help as helpmod                                          # noqa: E402
import tinyrecorder_i18n as i18n                                             # noqa: E402
from tinyrecorder_core import APP_AUTHORS, APP_CONTACT, APP_NAME, APP_VERSION, Tags   # noqa: E402
from tinyrecorder_i18n import _                                              # noqa: E402

# ===========================================================================
# Theme (Catppuccin Mocha, like the other apps)
# ===========================================================================

C = {"base": "#1e1e2e", "mantle": "#181825", "crust": "#11111b", "s0": "#313244", "s1": "#45475a",
     "s2": "#585b70", "ov": "#6c7086", "sub": "#a6adc8", "text": "#cdd6f4", "mauve": "#cba6f7",
     "green": "#a6e3a1", "red": "#f38ba8", "peach": "#fab387", "yellow": "#f9e2af", "blue": "#89b4fa",
     "teal": "#94e2d5"}
FONT = ("Segoe UI", 10)
FONT_S = ("Segoe UI", 9)
FONT_B = ("Segoe UI", 10, "bold")
FONT_H = ("Segoe UI", 15, "bold")
FONT_T = ("Consolas", 36, "bold")
MONO = ("Consolas", 10)


def apply_theme(root):
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    root.configure(bg=C["base"])
    root.option_add("*Font", FONT)
    root.option_add("*TCombobox*Listbox.background", C["crust"])
    root.option_add("*TCombobox*Listbox.foreground", C["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["s1"])
    root.option_add("*TCombobox*Listbox.selectForeground", C["text"])
    st.configure(".", background=C["base"], foreground=C["text"], fieldbackground=C["crust"], font=FONT,
                 bordercolor=C["s1"], lightcolor=C["base"], darkcolor=C["base"], troughcolor=C["crust"])
    st.configure("TFrame", background=C["base"])
    st.configure("Card.TFrame", background=C["mantle"])
    st.configure("TLabel", background=C["base"], foreground=C["text"])
    st.configure("Card.TLabel", background=C["mantle"], foreground=C["text"])
    st.configure("Sub.TLabel", background=C["mantle"], foreground=C["sub"], font=FONT_S)
    st.configure("Head.TLabel", background=C["mantle"], foreground=C["mauve"], font=FONT_B)
    st.configure("Warn.TLabel", background=C["mantle"], foreground=C["peach"], font=FONT_S)
    st.configure("TButton", background=C["s0"], foreground=C["text"], bordercolor=C["s1"], padding=(12, 6),
                 focuscolor=C["s0"])
    st.map("TButton", background=[("active", C["s1"]), ("disabled", C["mantle"])],
           foreground=[("disabled", C["ov"])])
    st.configure("Rec.TButton", background=C["red"], foreground=C["crust"], font=("Segoe UI", 12, "bold"),
                 padding=(22, 10), bordercolor=C["red"], focuscolor=C["red"])
    st.map("Rec.TButton", background=[("active", "#f5a3ba"), ("disabled", C["s1"])],
           foreground=[("disabled", C["ov"])])
    st.configure("Big.TButton", font=("Segoe UI", 11, "bold"), padding=(18, 10))
    st.configure("Nav.TButton", background=C["mantle"], foreground=C["sub"], padding=(8, 4), bordercolor=C["mantle"])
    st.map("Nav.TButton", background=[("active", C["s0"])], foreground=[("active", C["text"])])
    st.configure("TEntry", fieldbackground=C["crust"], foreground=C["text"], insertcolor=C["text"], padding=4,
                 bordercolor=C["s1"])
    st.configure("TCombobox", fieldbackground=C["crust"], foreground=C["text"], arrowcolor=C["sub"],
                 background=C["s0"], padding=3)
    st.map("TCombobox", fieldbackground=[("readonly", C["crust"])], foreground=[("readonly", C["text"])])
    st.configure("TCheckbutton", background=C["mantle"], foreground=C["text"])
    st.map("TCheckbutton", background=[("active", C["mantle"])])
    st.configure("Base.TCheckbutton", background=C["base"], foreground=C["text"])
    st.configure("TRadiobutton", background=C["base"], foreground=C["text"])
    st.map("TRadiobutton", background=[("active", C["base"])])
    st.configure("Treeview", background=C["crust"], fieldbackground=C["crust"], foreground=C["text"], rowheight=26,
                 bordercolor=C["s1"])
    st.configure("Treeview.Heading", background=C["s0"], foreground=C["sub"], font=FONT_B, relief="flat")
    st.map("Treeview", background=[("selected", C["s1"])], foreground=[("selected", C["text"])])
    st.map("Treeview.Heading", background=[("active", C["s1"])])
    st.configure("Horizontal.TScale", background=C["base"], troughcolor=C["crust"])
    st.configure("Vertical.TScrollbar", background=C["s0"], troughcolor=C["crust"], arrowcolor=C["sub"])


def icon_path(name="icon.ico"):
    return os.path.join(HERE, "assets", name)


def set_window_icon(win):
    try:
        win.iconbitmap(icon_path())
    except tk.TclError:
        pass


# ===========================================================================
# Small widgets and dialogs
# ===========================================================================

class LevelBar(tk.Canvas):
    """A horizontal level meter on a 60 dB scale, with a slow fall and a peak-hold tick."""

    def __init__(self, master, width=360, height=14):
        super().__init__(master, width=width, height=height, bg=C["crust"], highlightthickness=1,
                         highlightbackground=C["s1"], bd=0)
        self.w, self.h = width, height
        self.value = 0.0
        self.hold = 0.0
        self.hold_t = 0.0
        self.bind("<Configure>", self._resize)
        self.set(0.0)

    def _resize(self, e):
        self.w, self.h = max(40, e.width - 2), max(6, e.height - 2)
        self._draw()

    @staticmethod
    def to_scale(peak):
        if peak <= 0.00056:                                    # below -65 dB
            return 0.0
        return max(0.0, min(1.0, (20.0 * math.log10(peak) + 60.0) / 60.0))

    def set(self, peak):
        v = self.to_scale(peak)
        self.value = max(v, self.value - 0.06)                 # falls slowly, rises at once
        now = time.monotonic()
        if v >= self.hold or now - self.hold_t > 1.2:
            self.hold, self.hold_t = v, now
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.w, self.h
        x = int(w * self.value)
        for lo, hi, col in ((0.0, 0.70, C["green"]), (0.70, 0.88, C["yellow"]), (0.88, 1.0, C["red"])):
            a, b = int(w * lo), min(x, int(w * hi))
            if b > a:
                self.create_rectangle(a, 0, b, h, fill=col, outline="")
        hx = int(w * self.hold)
        if hx > 2:
            self.create_line(hx, 0, hx, h, fill=C["text"], width=2)


class Dialog(tk.Toplevel):
    def __init__(self, master, title, app, modal=True):
        super().__init__(master)
        self.app = app
        self.title(title)
        self.configure(bg=C["base"])
        self.resizable(False, False)
        self.transient(master)
        set_window_icon(self)
        self.bind("<Escape>", lambda e: self.close())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.body = ttk.Frame(self, padding=16)
        self.body.pack(fill="both", expand=True)
        self._modal = modal

    def show(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + max(0, (m.winfo_width() - self.winfo_reqwidth()) // 2)
        y = m.winfo_rooty() + max(0, (m.winfo_height() - self.winfo_reqheight()) // 3)
        self.geometry("+%d+%d" % (x, y))
        winsys.dark_title_bar(winsys.hwnd_of(self.winfo_id()))
        if self._modal:
            self.grab_set()
        self.focus_set()

    def close(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()


class AboutDialog(Dialog):
    def __init__(self, master, app):
        super().__init__(master, _("About Tiny Recorder"), app)
        b = self.body
        try:
            self._img = tk.PhotoImage(file=icon_path("icon-128.png"))
            ttk.Label(b, image=self._img).grid(row=0, column=0, rowspan=3, padx=(0, 16), sticky="n")
        except tk.TclError:
            pass
        ttk.Label(b, text=APP_NAME, font=FONT_H, foreground=C["mauve"]).grid(row=0, column=1, sticky="w")
        ttk.Label(b, text="%s %s" % (_("Version"), APP_VERSION), foreground=C["sub"]).grid(row=1, column=1, sticky="w")
        ttk.Label(b, wraplength=380, justify="left",
                  text=_("Tiny Recorder records everything the computer plays and everything you say into one MP3 "
                         "file. No AI, no cloud, no transcription.")).grid(row=2, column=1, sticky="w", pady=(6, 10))
        rows = [(_("Authors"), APP_AUTHORS), (_("Contact"), APP_CONTACT),
                (_("Settings folder"), core.home_dir()), (_("Recordings folder"), core.output_dir(app.cfg))]
        info = ttk.Frame(b)
        info.grid(row=3, column=0, columnspan=2, sticky="ew")
        for i, (k, v) in enumerate(rows):
            ttk.Label(info, text=k + ":", foreground=C["sub"]).grid(row=i, column=0, sticky="nw", padx=(0, 10))
            ttk.Label(info, text=v, wraplength=420, justify="left").grid(row=i, column=1, sticky="w")
        ttk.Label(b, text=_("Responsible use"), foreground=C["peach"], font=FONT_B).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(12, 2))
        ttk.Label(b, wraplength=520, justify="left", foreground=C["sub"],
                  text=_("Tell the people in a meeting that you are recording. In many countries, including "
                         "Switzerland, recording a conversation without the consent of the other participants can "
                         "be a criminal offence. Recordings stay on your PC.")).grid(
            row=5, column=0, columnspan=2, sticky="w")
        bar = ttk.Frame(b)
        bar.grid(row=6, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(bar, text=_("Open") + " " + _("Settings folder").lower(),
                   command=lambda: winsys.show_in_explorer(core.home_dir())).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text=_("Close"), command=self.close).pack(side="left")
        self.show()


class HelpDialog(Dialog):
    def __init__(self, master, app):
        super().__init__(master, _("Help — Tiny Recorder"), app, modal=False)
        self.resizable(True, True)
        sections = helpmod.PT if i18n.LANG == "pt" else helpmod.EN
        left = ttk.Frame(self.body)
        left.pack(side="left", fill="y")
        self.lb = tk.Listbox(left, width=24, height=16, bg=C["crust"], fg=C["text"], bd=0, highlightthickness=1,
                             highlightbackground=C["s1"], selectbackground=C["s1"], selectforeground=C["text"],
                             activestyle="none", font=FONT, exportselection=False)
        self.lb.pack(fill="y", expand=True)
        for title, _body in sections:
            self.lb.insert("end", "  " + title)
        right = ttk.Frame(self.body)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.txt = tk.Text(right, width=78, height=24, wrap="word", bg=C["crust"], fg=C["text"], bd=0, padx=12,
                           pady=10, highlightthickness=1, highlightbackground=C["s1"], font=FONT, spacing3=3,
                           insertbackground=C["text"])
        sb = ttk.Scrollbar(right, command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        self.txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.txt.tag_configure("b", font=FONT_B, foreground=C["mauve"])
        self.sections = sections
        self.lb.bind("<<ListboxSelect>>", self._pick)
        self.lb.selection_set(0)
        self._render(0)
        self.show()

    def _pick(self, _e):
        sel = self.lb.curselection()
        if sel:
            self._render(sel[0])

    def _render(self, i):
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        for line in self.sections[i][1].strip("\n").split("\n"):
            parts = line.split("**")
            for j, part in enumerate(parts):
                self.txt.insert("end", part, "b" if j % 2 else "")
            self.txt.insert("end", "\n")
        self.txt.configure(state="disabled")


class TagFields(ttk.Frame):
    """Date, Title, People, Project and Notes with a live 'Will be saved as' line. Used on the main window (a
    new recording) and in the edit dialog (an existing one)."""

    def __init__(self, master, style_bg="Card", on_change=None):
        super().__init__(master, style="Card.TFrame" if style_bg == "Card" else "TFrame")
        lab = "Card.TLabel" if style_bg == "Card" else "TLabel"
        self.on_change = on_change
        self.vars = {k: tk.StringVar() for k in ("date", "title", "people", "project")}
        self.columnconfigure(1, weight=1)
        r = 0
        ttk.Label(self, text=_("Date"), style=lab).grid(row=r, column=0, sticky="w", pady=3, padx=(0, 10))
        drow = ttk.Frame(self, style="Card.TFrame" if style_bg == "Card" else "TFrame")
        drow.grid(row=r, column=1, sticky="w")
        self.e_date = ttk.Entry(drow, textvariable=self.vars["date"], width=14)
        self.e_date.pack(side="left")
        ttk.Button(drow, text=_("Today"), style="Nav.TButton",
                   command=lambda: self.vars["date"].set(core.today_iso())).pack(side="left", padx=(8, 0))
        self.entries = {}
        for key, label in (("title", _("Title")), ("people", _("People")), ("project", _("Project"))):
            r += 1
            ttk.Label(self, text=label, style=lab).grid(row=r, column=0, sticky="w", pady=3, padx=(0, 10))
            e = ttk.Entry(self, textvariable=self.vars[key])
            e.grid(row=r, column=1, sticky="ew", pady=3)
            self.entries[key] = e
        r += 1
        ttk.Label(self, text=_("Notes"), style=lab).grid(row=r, column=0, sticky="nw", pady=3, padx=(0, 10))
        self.notes = tk.Text(self, height=2, wrap="word", bg=C["crust"], fg=C["text"], insertbackground=C["text"],
                             bd=0, highlightthickness=1, highlightbackground=C["s1"], highlightcolor=C["mauve"],
                             padx=6, pady=4, font=FONT)
        self.notes.grid(row=r, column=1, sticky="ew", pady=3)
        r += 1
        self.preview = ttk.Label(self, text="", style="Sub.TLabel" if style_bg == "Card" else "TLabel",
                                 wraplength=480, justify="left")
        self.preview.grid(row=r, column=0, columnspan=2, sticky="w", pady=(6, 0))
        for v in self.vars.values():
            v.trace_add("write", lambda *a: self._changed())
        self.notes.bind("<<Modified>>", lambda e: None)
        self.vars["date"].set(core.today_iso())

    def _changed(self):
        t = self.get()
        self.preview.configure(text="%s:  %s.mp3" % (_("Will be saved as"), core.file_stem(t)))
        if self.on_change:
            self.on_change()

    def get(self):
        return Tags(self.vars["date"].get().strip(), self.vars["title"].get().strip(),
                    self.vars["people"].get().strip(), self.vars["project"].get().strip(),
                    self.notes.get("1.0", "end").strip())

    def set(self, tags):
        self.vars["date"].set(tags.date or core.today_iso())
        self.vars["title"].set(tags.title)
        self.vars["people"].set(tags.people)
        self.vars["project"].set(tags.project)
        self.notes.delete("1.0", "end")
        self.notes.insert("1.0", tags.notes)

    def clear(self):
        self.set(Tags(core.today_iso()))


class EditDialog(Dialog):
    def __init__(self, master, app, path):
        super().__init__(master, _("Edit details"), app)
        self.path = path
        self.result = None
        tags = core.read_tags(path)
        stem = os.path.splitext(os.path.basename(path))[0]
        if not tags.title and " - " in stem:                      # an untagged file named 'date - Title'
            d, _sep, t = stem.partition(" - ")
            tags.title = tags.title or t
            tags.date = tags.date or (core.parse_date(d) or "")
        ttk.Label(self.body, text=os.path.basename(path), foreground=C["sub"], wraplength=460).pack(anchor="w")
        self.tf = TagFields(self.body, style_bg="Base")
        self.tf.pack(fill="x", pady=(10, 0))
        self.tf.set(tags)
        bar = ttk.Frame(self.body)
        bar.pack(anchor="e", pady=(14, 0))
        ttk.Button(bar, text=_("Save"), command=self._save).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text=_("Cancel"), command=self.close).pack(side="left")
        self.show()
        self.tf.entries["title"].focus_set()

    def _save(self):
        tags = self.tf.get()
        if tags.date and not core.parse_date(tags.date):
            messagebox.showwarning(APP_NAME, _("Date must look like 2026-10-20 (or 20.10.2026)."), parent=self)
            return
        tags.date = core.parse_date(tags.date) or core.today_iso()
        try:
            new, err = core.retag_and_rename(self.path, tags)
        except OSError as e:
            messagebox.showerror(APP_NAME, _("Could not rename the file (is it open in a player?): {err}").format(
                err=e), parent=self)
            return
        self.result = new
        self.close()
        self.app.after(50, lambda: self.app.reload_list(
            _("Saved: {name}").format(name=os.path.basename(new)) if not err
            else _("Saved: {name} (tags not written: {err})").format(name=os.path.basename(new), err=err)))


class SettingsDialog(Dialog):
    def __init__(self, master, app):
        super().__init__(master, _("Settings"), app)
        cfg = app.cfg
        b = self.body
        b.columnconfigure(1, weight=1)
        self.v_out = tk.StringVar(value=core.output_dir(cfg))
        self.v_preset = tk.StringVar(value=cfg["preset"])
        self.v_sys = tk.StringVar()
        self.v_mic = tk.StringVar()
        self.v_sg = tk.IntVar(value=cfg["system_gain"])
        self.v_mg = tk.IntVar(value=cfg["mic_gain"])
        self.v_hot = tk.BooleanVar(value=cfg["hotkey"])
        self.v_lang = tk.StringVar(value="Português" if cfg["lang"] == "pt" else "English")
        follow = _("Follow the Windows default")
        try:
            dev = audio.list_devices()
            self.sys_opts = [follow] + [audio.loopback_label(n) for n in dev["loopbacks"]]
            self.mic_opts = [follow] + dev["mics"]
        except Exception:                                                    # noqa: BLE001
            self.sys_opts, self.mic_opts = [follow], [follow]
            ttk.Label(b, text=_("Could not read the audio devices."), foreground=C["peach"]).grid(
                row=99, column=0, columnspan=3, sticky="w")
        self.v_sys.set(cfg["system_device"] and audio.loopback_label(cfg["system_device"]) or follow)
        self.v_mic.set(cfg["mic_device"] or follow)
        r = 0
        ttk.Label(b, text=_("Output folder")).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
        ttk.Entry(b, textvariable=self.v_out, width=52).grid(row=r, column=1, sticky="ew", pady=5)
        ttk.Button(b, text=_("Browse…"), command=self._browse).grid(row=r, column=2, padx=(8, 0))
        r += 1
        ttk.Label(b, text=_("Quality")).grid(row=r, column=0, sticky="nw", pady=5, padx=(0, 10))
        qf = ttk.Frame(b)
        qf.grid(row=r, column=1, columnspan=2, sticky="w")
        for key, p in core.PRESETS.items():
            ttk.Radiobutton(qf, text=_(p["label"]), value=key, variable=self.v_preset).pack(anchor="w", pady=1)
        r += 1
        ttk.Label(b, text=_("Computer audio device")).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
        ttk.Combobox(b, textvariable=self.v_sys, values=self.sys_opts, state="readonly", width=50).grid(
            row=r, column=1, columnspan=2, sticky="ew", pady=5)
        r += 1
        ttk.Label(b, text=_("Microphone device")).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
        ttk.Combobox(b, textvariable=self.v_mic, values=self.mic_opts, state="readonly", width=50).grid(
            row=r, column=1, columnspan=2, sticky="ew", pady=5)
        for label, var in ((_("Volume of the computer audio"), self.v_sg), (_("Volume of the microphone"), self.v_mg)):
            r += 1
            ttk.Label(b, text=label).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
            sc = ttk.Scale(b, from_=0, to=200, variable=var, orient="horizontal",
                           command=lambda v, var=var: var.set(int(float(v)) // 5 * 5))
            sc.grid(row=r, column=1, sticky="ew", pady=5)
            ttk.Label(b, textvariable=var, width=5, foreground=C["sub"]).grid(row=r, column=2, sticky="w", padx=(8, 0))
        r += 1
        ttk.Checkbutton(b, text=_("Start and stop from any program with Ctrl+Alt+R"), variable=self.v_hot,
                        style="Base.TCheckbutton").grid(row=r, column=0, columnspan=3, sticky="w", pady=5)
        r += 1
        ttk.Label(b, text=_("Language")).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
        ttk.Combobox(b, textvariable=self.v_lang, values=[_("English"), _("Português")], state="readonly",
                     width=16).grid(row=r, column=1, sticky="w", pady=5)
        bar = ttk.Frame(b)
        bar.grid(row=100, column=0, columnspan=3, sticky="e", pady=(14, 0))
        ttk.Button(bar, text=_("Save"), command=self._save).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text=_("Cancel"), command=self.close).pack(side="left")
        self.show()

    def _browse(self):
        d = filedialog.askdirectory(parent=self, title=_("Choose the recordings folder"),
                                    initialdir=self.v_out.get() or None)
        if d:
            self.v_out.set(os.path.normpath(d))

    def _save(self):
        cfg = self.app.cfg
        follow = _("Follow the Windows default")
        cfg["output_dir"] = self.v_out.get().strip()
        cfg["preset"] = self.v_preset.get()
        s = self.v_sys.get()
        cfg["system_device"] = "" if s == follow else s
        m = self.v_mic.get()
        cfg["mic_device"] = "" if m == follow else m
        cfg["system_gain"], cfg["mic_gain"] = int(self.v_sg.get()), int(self.v_mg.get())
        cfg["hotkey"] = bool(self.v_hot.get())
        new_lang = "pt" if self.v_lang.get() == "Português" else "en"
        changed_lang = new_lang != cfg["lang"]
        cfg["lang"] = new_lang
        self.close()
        self.app.settings_saved(changed_lang)


# ===========================================================================
# The main window
# ===========================================================================

STATES = ("idle", "starting", "recording", "paused", "saving")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = core.load_config()
        i18n.set_lang(self.cfg["lang"])
        self.q = queue.Queue(maxsize=2000)
        self.state = "idle"
        self.rec = None
        self.part = ""
        self.seconds = 0.0
        self.size = 0
        self.rows = []
        self.closing = False
        self.hotkey = None
        self._poll_id = None
        self._warn = ""
        apply_theme(self)
        set_window_icon(self)
        self.minsize(820, 760)
        geo = self.cfg.get("window") or "880x900"
        try:
            self.geometry(geo)
        except tk.TclError:
            self.geometry("880x900")
        self._build()
        self.bind("<F1>", lambda e: self.show_help())
        self.bind("<Control-r>", lambda e: self.toggle_record())
        self.bind("<Control-p>", lambda e: self.toggle_pause())
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_idletasks()
        winsys.dark_title_bar(winsys.hwnd_of(self.winfo_id()))
        self._start_hotkey()
        self._poll_id = self.after(80, self._poll)
        self.after(300, self.reload_list)
        self.after(900, self.check_recovery)

    # ------------------------------------------------------------------ building

    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        root = ttk.Frame(self, padding=(18, 14, 18, 10))
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        head = ttk.Frame(root)
        head.grid(row=0, column=0, sticky="ew")
        try:
            self._logo = tk.PhotoImage(file=icon_path("icon-48.png"))
            ttk.Label(head, image=self._logo).pack(side="left", padx=(0, 10))
        except tk.TclError:
            pass
        ttk.Label(head, text=_("Tiny Recorder"), font=FONT_H, foreground=C["mauve"]).pack(side="left")
        for text, cmd in ((_("About"), self.show_about), (_("Help") + "  F1", self.show_help),
                          (_("Settings…"), self.show_settings)):
            ttk.Button(head, text=text, style="Nav.TButton", command=cmd).pack(side="right", padx=2)

        # ---- recorder card
        card = ttk.Frame(root, style="Card.TFrame", padding=16)
        card.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        card.columnconfigure(0, weight=1)
        self.timer = tk.Label(card, text="00:00:00", font=FONT_T, bg=C["mantle"], fg=C["text"])
        self.timer.grid(row=0, column=0, pady=(0, 2))
        self.status = ttk.Label(card, text=_("Ready"), style="Head.TLabel")
        self.status.grid(row=1, column=0)
        self.detail = ttk.Label(card, text="", style="Sub.TLabel", wraplength=700, justify="center")
        self.detail.grid(row=2, column=0, pady=(2, 0))
        self.warnlbl = ttk.Label(card, text="", style="Warn.TLabel", wraplength=700, justify="center")
        self.warnlbl.grid(row=3, column=0)
        btns = ttk.Frame(card, style="Card.TFrame")
        btns.grid(row=4, column=0, pady=(12, 10))
        self.b_rec = ttk.Button(btns, text="●  " + _("Record"), style="Rec.TButton", command=self.toggle_record)
        self.b_rec.pack(side="left", padx=6)
        self.b_pause = ttk.Button(btns, text="⏸  " + _("Pause"), style="Big.TButton", command=self.toggle_pause)
        self.b_pause.pack(side="left", padx=6)
        self.b_stop = ttk.Button(btns, text="■  " + _("Stop"), style="Big.TButton", command=self.toggle_record)
        self.b_stop.pack(side="left", padx=6)
        meters = ttk.Frame(card, style="Card.TFrame")
        meters.grid(row=5, column=0, sticky="ew", pady=(4, 8))
        meters.columnconfigure(1, weight=1)
        self.v_sys = tk.BooleanVar(value=self.cfg["use_system"])
        self.v_mic = tk.BooleanVar(value=self.cfg["use_mic"])
        self.c_sys = ttk.Checkbutton(meters, text=_("Computer audio"), variable=self.v_sys, command=self._src_changed)
        self.c_sys.grid(row=0, column=0, sticky="w", padx=(0, 12), pady=3)
        self.m_sys = LevelBar(meters)
        self.m_sys.grid(row=0, column=1, sticky="ew", pady=3)
        ttk.Label(meters, text=_("What you hear"), style="Sub.TLabel").grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.c_mic = ttk.Checkbutton(meters, text=_("Microphone"), variable=self.v_mic, command=self._src_changed)
        self.c_mic.grid(row=1, column=0, sticky="w", padx=(0, 12), pady=3)
        self.m_mic = LevelBar(meters)
        self.m_mic.grid(row=1, column=1, sticky="ew", pady=3)
        ttk.Label(meters, text=_("What you say"), style="Sub.TLabel").grid(row=1, column=2, sticky="w", padx=(10, 0))
        ttk.Separator(card).grid(row=6, column=0, sticky="ew", pady=(6, 8))
        ttk.Label(card, text=_("About this recording"), style="Head.TLabel").grid(row=7, column=0, sticky="w")
        old = getattr(self, "tags", None)
        self.tags = TagFields(card)
        self.tags.grid(row=8, column=0, sticky="ew", pady=(6, 0))
        if old is not None:
            pass

        # ---- recordings list
        lst = ttk.Frame(root)
        lst.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
        lst.columnconfigure(0, weight=1)
        lst.rowconfigure(1, weight=1)
        top = ttk.Frame(lst)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(top, text=_("Recordings"), font=FONT_B, foreground=C["mauve"]).pack(side="left")
        ttk.Button(top, text=_("Open folder"), style="Nav.TButton",
                   command=lambda: winsys.show_in_explorer(core.output_dir(self.cfg))).pack(side="right")
        cols = ("date", "title", "people", "time", "size")
        self.tree = ttk.Treeview(lst, columns=cols, show="headings", selectmode="browse", height=8)
        for key, text, w, anc in (("date", _("Date"), 96, "w"), ("title", _("Title"), 280, "w"),
                                  ("people", _("People"), 200, "w"), ("time", _("Time"), 80, "e"),
                                  ("size", _("Size"), 80, "e")):
            self.tree.heading(key, text=text)
            self.tree.column(key, width=w, anchor=anc, stretch=(key in ("title", "people")))
        sb = ttk.Scrollbar(lst, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        sb.grid(row=1, column=1, sticky="ns")
        self.tree.bind("<Double-1>", lambda e: self.play_selected())
        self.tree.bind("<Button-3>", self._menu)
        self.tree.bind("<Return>", lambda e: self.play_selected())
        self.menu = tk.Menu(self, tearoff=0, bg=C["mantle"], fg=C["text"], activebackground=C["s1"],
                            activeforeground=C["text"], bd=0)
        self.menu.add_command(label=_("Play"), command=self.play_selected)
        self.menu.add_command(label=_("Show in folder"), command=self.show_selected)
        self.menu.add_command(label=_("Edit details and rename…"), command=self.edit_selected)
        self.menu.add_command(label=_("Copy file path"), command=self.copy_selected)
        self.foot = ttk.Label(root, text=core.output_dir(self.cfg), foreground=C["ov"], font=FONT_S)
        self.foot.grid(row=3, column=0, sticky="w", pady=(8, 0))
        self._render_state()
        self._render_rows()

    # ------------------------------------------------------------------ state

    def _set_state(self, st):
        self.state = st
        self._render_state()

    def _render_state(self):
        st = self.state
        self.b_rec.configure(state="normal" if st == "idle" else "disabled")
        self.b_pause.configure(state="normal" if st in ("recording", "paused") else "disabled",
                               text=("▶  " + _("Resume")) if st == "paused" else ("⏸  " + _("Pause")))
        self.b_stop.configure(state="normal" if st in ("starting", "recording", "paused") else "disabled")
        src_state = "normal" if st == "idle" else "disabled"
        self.c_sys.configure(state=src_state)
        self.c_mic.configure(state=src_state)
        label = {"idle": _("Ready"), "starting": _("Starting…"), "recording": _("Recording"),
                 "paused": _("Paused"), "saving": _("Saving…")}[st]
        colour = {"idle": C["mauve"], "starting": C["yellow"], "recording": C["red"], "paused": C["peach"],
                  "saving": C["yellow"]}[st]
        self.status.configure(text=("● " if st == "recording" else "") + label, foreground=colour)
        if st == "idle":
            self.timer.configure(fg=C["text"])
            self.title(("%s %s" % (APP_NAME, APP_VERSION)))
            self.m_sys.set(0.0)
            self.m_mic.set(0.0)
            if not self.detail.cget("text").startswith(_("Saved: {name}").split("{")[0]):
                self.detail.configure(text=self._ready_text())
        elif st in ("recording", "paused"):
            self.timer.configure(fg=C["red"] if st == "recording" else C["peach"])
            self._title_tick()

    def _ready_text(self):
        return _("Start and stop from any program with Ctrl+Alt+R") if (self.hotkey and self.hotkey.ok) else ""

    def _title_tick(self):
        mark = "● " + _("REC") if self.state == "recording" else "⏸ " + _("PAUSED")
        self.title("%s %s  ·  %s" % (mark, core.fmt_clock(self.seconds), APP_NAME))

    def _src_changed(self):
        self.cfg["use_system"] = bool(self.v_sys.get())
        self.cfg["use_mic"] = bool(self.v_mic.get())

    def _start_hotkey(self):
        if self.hotkey:
            self.hotkey.stop()
            self.hotkey = None
        if self.cfg["hotkey"]:
            hk = winsys.Hotkey(self.q)
            if hk.start():
                self.hotkey = hk
            else:
                self._warn = _("Ctrl+Alt+R is used by another program, so the global hotkey is off.")
                self.warnlbl.configure(text=self._warn)

    # ------------------------------------------------------------------ recording

    def toggle_record(self):
        if self.state == "idle":
            self.start_recording()
        elif self.state in ("starting", "recording", "paused"):
            self.stop_recording()

    def start_recording(self):
        if not (self.v_sys.get() or self.v_mic.get()):
            messagebox.showinfo(APP_NAME, _("Tick Computer audio, Microphone or both before you record."))
            return
        folder = core.output_dir(self.cfg)
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as e:
            messagebox.showerror(APP_NAME, "%s\n%s" % (_("Could not start the recording"), e))
            return
        free = winsys.free_bytes(folder)
        if free is not None and free < audio.LOW_DISK * 3:
            messagebox.showerror(APP_NAME, _("Not enough free space in the recordings folder."))
            return
        self.part = core.part_path_now(folder)
        cfg = self.cfg
        want_sys, want_mic = bool(self.v_sys.get()), bool(self.v_mic.get())
        sysn = cfg["system_device"]
        micn = cfg["mic_device"]
        self.rec = audio.Recorder(
            self.part, core.PRESETS[cfg["preset"]], self.q,
            opener=lambda: audio.open_sources(want_sys, want_mic, sysn, micn),
            system_gain=cfg["system_gain"] / 100.0, mic_gain=cfg["mic_gain"] / 100.0,
            free_check=lambda: winsys.free_bytes(folder))
        self.seconds, self.size = 0.0, 0
        self.timer.configure(text="00:00:00")
        self.warnlbl.configure(text="")
        self.detail.configure(text="")
        self._set_state("starting")
        self.rec.start()

    def toggle_pause(self):
        if not self.rec:
            return
        if self.state == "recording":
            self.rec.pause()
            self._set_state("paused")
        elif self.state == "paused":
            self.rec.resume()
            self._set_state("recording")

    def stop_recording(self):
        if self.rec and self.state in ("starting", "recording", "paused"):
            self.stop_tags = self.tags.get()
            self.rec.request_stop()
            self._set_state("saving")

    # ------------------------------------------------------------------ the event queue

    def _poll(self):
        try:
            for _i in range(300):
                try:
                    ev = self.q.get_nowait()
                except queue.Empty:
                    break
                self._handle(ev)
        except Exception as e:                                               # noqa: BLE001
            core.log("poll error: %r" % (e,))
        self._poll_id = self.after(80, self._poll)

    def _handle(self, ev):
        if ev == "hotkey":
            if self.state in ("idle", "recording", "paused", "starting"):
                self.toggle_record()
            return
        kind = ev[0]
        if kind == "started":
            _k, rate, names, problems = ev
            if self.state == "starting":
                self._set_state("recording")
            self.detail.configure(text=_("Recording from {sources} at {rate} Hz").format(
                sources=" + ".join(audio.loopback_label(n) for n in names), rate=rate))
            if problems:
                self.warnlbl.configure(text="⚠ " + "; ".join(_("Not available: {what}").format(what=p)
                                                              for p in problems))
        elif kind == "levels":
            _k, sp, mp, secs, size = ev
            self.seconds, self.size = secs, size
            if self.state in ("recording", "paused", "saving"):
                self.m_sys.set(sp)
                self.m_mic.set(mp)
                self.timer.configure(text=core.fmt_clock(secs))
                if self.state != "saving":
                    self._title_tick()
                    base = self.detail.cget("text").split("  ·  ")[0]
                    self.detail.configure(text="%s  ·  %s" % (base, core.fmt_size(size)))
        elif kind == "error":
            self.warnlbl.configure(text="⚠ " + ev[1])
            if self.state == "starting":
                messagebox.showerror(APP_NAME, "%s\n\n%s" % (_("Could not start the recording"), ev[1]))
            else:
                messagebox.showerror(APP_NAME, "%s\n\n%s" % (_("Recording stopped because of an error"), ev[1]))
        elif kind == "lowdisk":
            messagebox.showwarning(APP_NAME, _("The disk is almost full. The recording was stopped and saved."))
        elif kind == "stopped":
            _k, secs, part = ev
            self.rec = None
            self._finish(secs, part)
        elif kind == "saved":
            _k, final, err, secs = ev
            self._after_saved(final, err)
        elif kind == "list":
            self.rows = ev[1]
            self._render_rows()
            if len(ev) > 2 and ev[2]:
                self.detail.configure(text=ev[2])

    def _finish(self, secs, part):
        tags = getattr(self, "stop_tags", None) or self.tags.get()
        self.stop_tags = None
        try:
            size = os.path.getsize(part)
        except OSError:
            size = 0
        if size < 2048 or secs < 0.3:                          # nothing recorded (a start that failed, an instant stop)
            try:
                os.remove(part)
            except OSError:
                pass
            self._set_state("idle")
            if self.closing:
                self._destroy()
            elif secs >= 0.3 or size:
                pass
            return
        tags.date = core.parse_date(tags.date) or core.today_iso()
        self._set_state("saving")
        folder = core.output_dir(self.cfg)

        def work():
            try:
                final, err = core.finalize(part, folder, tags)
            except OSError as e:
                final, err = part, "%s" % e
            self.q.put(("saved", final, err, secs))
        threading.Thread(target=work, name="finalize", daemon=True).start()

    def _after_saved(self, final, err):
        name = os.path.basename(final)
        msg = _("Saved: {name}").format(name=name) if not err else \
            _("Saved: {name} (tags not written: {err})").format(name=name, err=err)
        self.tags.clear()
        self._set_state("idle")
        self.detail.configure(text=msg)
        self.reload_list(msg)
        if self.closing:
            self.after(200, self._destroy)

    # ------------------------------------------------------------------ the list

    def reload_list(self, message=""):
        folder = core.output_dir(self.cfg)

        def work():
            self.q.put(("list", core.list_recordings(folder), message))
        threading.Thread(target=work, name="list", daemon=True).start()
        self.foot.configure(text=folder)

    def _render_rows(self):
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(self.rows):
            t = r["tags"]
            stem = os.path.splitext(r["name"])[0]
            date = t.date or stem[:10]
            title = t.title or (stem.split(" - ", 1)[1] if " - " in stem else stem)
            self.tree.insert("", "end", iid=str(i), values=(date, title, t.people, core.fmt_clock(r["seconds"]),
                                                             core.fmt_size(r["size"])))

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return self.rows[int(sel[0])]["path"]
        except (ValueError, IndexError):
            return None

    def _menu(self, e):
        iid = self.tree.identify_row(e.y)
        if iid:
            self.tree.selection_set(iid)
            self.menu.tk_popup(e.x_root, e.y_root)

    def play_selected(self):
        p = self._selected()
        if p and os.path.exists(p):
            os.startfile(p)                                                  # noqa: S606

    def show_selected(self):
        p = self._selected()
        if p:
            winsys.show_in_explorer(p)

    def edit_selected(self):
        p = self._selected()
        if p and os.path.exists(p):
            EditDialog(self, self, p)

    def copy_selected(self):
        p = self._selected()
        if p:
            self.clipboard_clear()
            self.clipboard_append(p)
            self.detail.configure(text=_("Copied to the clipboard."))

    # ------------------------------------------------------------------ recovery

    def check_recovery(self):
        if self.state != "idle":
            return
        parts = core.find_part_files(core.output_dir(self.cfg), exclude=self.part if self.rec else None)
        parts = [p for p in parts if os.path.getsize(p) > 2048]
        if not parts:
            return
        if not messagebox.askyesno(_("Unfinished recordings"),
                                   _("Found {n} unfinished recording(s) in the recordings folder (the program or "
                                     "the PC stopped during a recording). Recover them now?").format(n=len(parts))):
            return
        folder = core.output_dir(self.cfg)
        n = 0
        for p in parts:
            d = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(p)))
            try:
                core.finalize(p, folder, Tags(d, _("Recovered recording")))
                n += 1
            except OSError:
                pass
        self.reload_list(_("Recovered {n} recording(s).").format(n=n))

    # ------------------------------------------------------------------ dialogs and settings

    def show_about(self):
        AboutDialog(self, self)

    def show_help(self):
        HelpDialog(self, self)

    def show_settings(self):
        if self.state != "idle":
            return
        SettingsDialog(self, self)

    def settings_saved(self, changed_lang):
        try:
            core.save_config(self.cfg)
        except OSError as e:
            core.log("could not save settings: %r" % (e,))
        if changed_lang:
            i18n.set_lang(self.cfg["lang"])
            keep = self.tags.get()
            self._build()
            self.tags.set(keep)
        self.foot.configure(text=core.output_dir(self.cfg))
        self._start_hotkey()
        self.detail.configure(text=self._ready_text())
        self.reload_list()

    # ------------------------------------------------------------------ closing

    def on_close(self):
        if self.state in ("starting", "recording", "paused", "saving"):
            if self.state == "saving":
                self.closing = True
                return
            if not messagebox.askyesno(APP_NAME, _("A recording is in progress. Stop and save it before closing?")):
                return
            self.closing = True
            self.stop_recording()
            return
        self._destroy()

    def _destroy(self):
        try:
            self.cfg["window"] = self.geometry()
            self.cfg["use_system"], self.cfg["use_mic"] = bool(self.v_sys.get()), bool(self.v_mic.get())
            core.save_config(self.cfg)
        except Exception:                                                    # noqa: BLE001
            pass
        if self.hotkey:
            self.hotkey.stop()
        if self._poll_id:
            try:
                self.tk.call("after", "cancel", self._poll_id)               # never after_cancel while closing
            except tk.TclError:
                pass
        self.destroy()


def main():
    cfg = core.load_config()
    i18n.set_lang(cfg["lang"])
    inst = winsys.SingleInstance(core.home_dir())
    if inst.already:
        winsys.bring_to_front(APP_NAME)
        return 0
    app = App()
    try:
        app.mainloop()
    finally:
        inst.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
