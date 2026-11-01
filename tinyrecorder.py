"""
Tiny Recorder v0.1.4 — a very light meeting recorder for Windows.

Records everything the computer plays (Teams, Zoom, Meet, anything) and everything you say into ONE MP3 file, with
the date, title, people, project and notes written into the file's tags, and the file named "date - Title.mp3".
No AI, no transcription, no cloud.

  * big Record / Pause / Stop, timer, two level meters, Ctrl+Alt+R from any program
  * tags written to the MP3 (ID3) and the file renamed to match; edit them later from the list
  * the file is written while recording; an unfinished file is offered for recovery at the next start
  * About, Help (F1), English, Portuguese (Brazil) and Spanish (the Windows language by default), Catppuccin Mocha
    dark theme (like the other apps)

Threads: the recorder, the list loader and the hotkey run on their own threads and only put plain data on
self.q; the Tk thread drains it with after().
"""

import math
import os
import queue
import re
import sys
import threading
import time
import webbrowser

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
import tinyrecorder_player as player                                         # noqa: E402
from tinyrecorder_core import APP_AUTHORS, APP_CONTACT, APP_NAME, APP_VERSION, Tags   # noqa: E402
from tinyrecorder_i18n import t, tn                                             # noqa: E402

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
# The pause sign on the button: U+23F8 (⏸) falls back to a boxed emoji-style glyph in Segoe UI; two heavy bars
# (U+275A) look like the usual pause sign next to ● and ■ (item 0D). The window title keeps ⏸ (drawn well there).
PAUSE_SIGN = "❚❚"
SYSTEM_SILENT_MINUTES = 3           # item 2: warn when a ticked computer audio is exact zero this long


def apply_theme(root, compact=False):
    """compact: a short screen (e.g. 1366 x 768): smaller button padding, so the window fits its work area."""
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
                 padding=(18, 6) if compact else (22, 10), bordercolor=C["red"], focuscolor=C["red"])
    st.map("Rec.TButton", background=[("active", "#f5a3ba"), ("disabled", C["s1"])],
           foreground=[("disabled", C["ov"])])
    st.configure("Play.TButton", background=C["mauve"], foreground=C["crust"], font=FONT_B, padding=(14, 4),
                 bordercolor=C["mauve"], focuscolor=C["mauve"])
    st.map("Play.TButton", background=[("active", "#dcc4fb"), ("disabled", C["s1"])],
           foreground=[("disabled", C["ov"])])
    st.configure("Link.TButton", background=C["base"], foreground=C["blue"], bordercolor=C["base"], padding=(2, 0))
    st.map("Link.TButton", background=[("active", C["base"])], foreground=[("active", C["mauve"])])
    st.configure("Big.TButton", font=("Segoe UI", 11, "bold"), padding=(14, 6) if compact else (18, 10))
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


def _size(path):
    """File size, 0 when the file is gone (another program moved it meanwhile)."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def windows_language():
    """'en', 'pt-BR' or 'es' from the Windows display language (read at each start; English when unknown)."""
    return i18n.from_windows(winsys.windows_ui_langid())


def effective_language(cfg):
    """The language chosen in Settings, else the Windows one."""
    return cfg.get("ui_language") or windows_language()


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

    def reset(self):
        """Empty the meter at once (no slow fall, no peak-hold tick): when a recording ends."""
        self.value = self.hold = 0.0
        self._draw()

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
        super().__init__(master, t("about.title"), app)
        b = self.body
        try:
            self._img = tk.PhotoImage(file=icon_path("icon-128.png"))
            ttk.Label(b, image=self._img).grid(row=0, column=0, rowspan=3, padx=(0, 16), sticky="n")
        except tk.TclError:
            pass
        ttk.Label(b, text=APP_NAME, font=FONT_H, foreground=C["mauve"]).grid(row=0, column=1, sticky="w")
        ttk.Label(b, text="%s %s" % (t("about.version"), APP_VERSION), foreground=C["sub"]).grid(row=1, column=1, sticky="w")
        ttk.Label(b, wraplength=380, justify="left",
                  text=t("about.blurb")).grid(row=2, column=1, sticky="w", pady=(6, 10))
        rows = [(t("about.authors"), APP_AUTHORS, None), (t("about.contact"), APP_CONTACT, "mailto:" + APP_CONTACT),
                ("GitHub", core.APP_REPO_URL.replace("https://", ""), core.APP_REPO_URL),
                (t("about.bugs"), t("about.issues"), core.APP_ISSUES_URL), (t("about.licence"), core.APP_LICENCE, None),
                (t("about.notices"), "THIRD_PARTY_LICENSES.md", None),
                (t("about.settings_folder"), core.home_dir(), None), (t("about.recordings_folder"), core.output_dir(app.cfg), None)]
        info = ttk.Frame(b)
        info.grid(row=3, column=0, columnspan=2, sticky="ew")
        for i, (k, v, link) in enumerate(rows):
            ttk.Label(info, text=k + ":", foreground=C["sub"]).grid(row=i, column=0, sticky="nw", padx=(0, 10))
            if link:
                ttk.Button(info, text=v, style="Link.TButton", command=lambda l=link: app.open_link(l)).grid(
                    row=i, column=1, sticky="w")
            else:
                ttk.Label(info, text=v, wraplength=420, justify="left").grid(row=i, column=1, sticky="w")
        ttk.Label(b, text=t("about.responsible"), foreground=C["peach"], font=FONT_B).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(12, 2))
        ttk.Label(b, wraplength=520, justify="left", foreground=C["sub"],
                  text=t("about.responsible_text")).grid(
            row=5, column=0, columnspan=2, sticky="w")
        bar = ttk.Frame(b)
        bar.grid(row=6, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(bar, text=t("upd.check"), command=lambda: app.check_updates(self)).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text=t("about.open_settings_folder"),
                   command=lambda: winsys.show_in_explorer(core.home_dir())).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text=t("btn.close"), command=self.close).pack(side="left")
        self.show()


class HelpDialog(Dialog):
    def __init__(self, master, app):
        super().__init__(master, t("help.title"), app, modal=False)
        self.resizable(True, True)
        sections = {"pt-BR": helpmod.PT, "es": helpmod.ES}.get(i18n.LANG, helpmod.EN)
        left = ttk.Frame(self.body)
        left.pack(side="left", fill="y")
        width = max(24, max(len(title) for title, _body in sections) + 3)      # the longest title fits (Spanish)
        self.lb = tk.Listbox(left, width=width, height=16, bg=C["crust"], fg=C["text"], bd=0, highlightthickness=1,
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
        for line in paragraphs(self.sections[i][1]):
            parts = line.split("**")
            for j, part in enumerate(parts):
                self.txt.insert("end", part, "b" if j % 2 else "")
            self.txt.insert("end", "\n")
        self.txt.configure(state="disabled")


_NEW_BLOCK = re.compile(r"^(- |\d+\. |\*\*[^*]+\*\*$)")


def paragraphs(text):
    """The help text is written with hard line breaks (easy to edit); a line that continues the previous one is joined
    to it. A blank line, a list item ('- ', '1. ') or a line that is only a bold heading starts a new block."""
    out = []
    closed = True                                      # the previous block is finished (a blank line, a heading)
    for raw in text.strip("\n").split("\n"):
        line = raw.strip()
        if not line:
            out.append("")
            closed = True
        elif closed or _NEW_BLOCK.match(line):
            out.append(line)
            closed = line.startswith("**") and line.endswith("**") and line.count("**") == 2
        else:
            out[-1] += " " + line
    return out


class TagFields(ttk.Frame):
    """Date, Title, People, Project and Notes with a live 'Will be saved as' line. Used on the main window (a
    new recording) and in the edit dialog (an existing one)."""

    def __init__(self, master, style_bg="Card", on_change=None, compact=False):
        super().__init__(master, style="Card.TFrame" if style_bg == "Card" else "TFrame")
        lab = "Card.TLabel" if style_bg == "Card" else "TLabel"
        self.on_change = on_change
        self.vars = {k: tk.StringVar() for k in ("date", "title", "people", "project")}
        self.auto_date = ""                               # the date the box was filled with (not typed by the user)
        self.columnconfigure(1, weight=1)
        py = 1 if compact else 3
        r = 0
        ttk.Label(self, text=t("tags.date"), style=lab).grid(row=r, column=0, sticky="w", pady=py, padx=(0, 10))
        drow = ttk.Frame(self, style="Card.TFrame" if style_bg == "Card" else "TFrame")
        drow.grid(row=r, column=1, sticky="w")
        self.e_date = ttk.Entry(drow, textvariable=self.vars["date"], width=14)
        self.e_date.pack(side="left")
        ttk.Button(drow, text=t("btn.today"), style="Nav.TButton",
                   command=lambda: self.vars["date"].set(core.today_iso())).pack(side="left", padx=(8, 0))
        self.entries = {}
        for key, label in (("title", t("tags.title")), ("people", t("tags.people")), ("project", t("tags.project"))):
            r += 1
            ttk.Label(self, text=label, style=lab).grid(row=r, column=0, sticky="w", pady=py, padx=(0, 10))
            e = ttk.Entry(self, textvariable=self.vars[key])
            e.grid(row=r, column=1, sticky="ew", pady=py)
            self.entries[key] = e
        r += 1
        ttk.Label(self, text=t("tags.notes"), style=lab).grid(row=r, column=0, sticky="nw", pady=py, padx=(0, 10))
        self.notes = tk.Text(self, height=1 if compact else 2, wrap="word", bg=C["crust"], fg=C["text"], insertbackground=C["text"],
                             bd=0, highlightthickness=1, highlightbackground=C["s1"], highlightcolor=C["mauve"],
                             padx=6, pady=4, font=FONT)
        self.notes.grid(row=r, column=1, sticky="ew", pady=py)
        r += 1
        self.preview = ttk.Label(self, text="", style="Sub.TLabel" if style_bg == "Card" else "TLabel",
                                 wraplength=480, justify="left")
        self.preview.grid(row=r, column=0, columnspan=2, sticky="w", pady=(4 if compact else 6, 0))
        for v in self.vars.values():
            v.trace_add("write", lambda *a: self._changed())
        self.notes.bind("<<Modified>>", lambda e: None)
        self.clear()

    def _changed(self):
        tags = self.get()
        text = "%s:  %s.mp3" % (t("tags.saved_as"), core.file_stem(tags))
        if tags.date and not core.parse_date(tags.date):              # it would silently become today
            text += "  ·  " + t("msg.date_not_understood")
        self.preview.configure(text=text)
        if self.on_change:
            self.on_change()

    def refresh_date(self):
        """A date box nobody typed in follows the calendar: the app left open overnight records with today's date."""
        today = core.today_iso()
        if self.vars["date"].get().strip() == self.auto_date and self.auto_date != today:
            self.vars["date"].set(today)
            self.auto_date = today

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
        self.auto_date = core.today_iso()
        self.set(Tags(self.auto_date))


class EditDialog(Dialog):
    def __init__(self, master, app, path):
        super().__init__(master, t("edit.title"), app)
        self.path = path
        self.result = None
        tags = core.read_tags(path)
        stem = os.path.splitext(os.path.basename(path))[0]
        if not tags.title and " - " in stem:                      # an untagged file named 'date - Title'
            d, _sep, rest = stem.partition(" - ")
            tags.title = tags.title or rest
            tags.date = tags.date or (core.parse_date(d) or "")
        ttk.Label(self.body, text=os.path.basename(path), foreground=C["sub"], wraplength=460).pack(anchor="w")
        self.tf = TagFields(self.body, style_bg="Base")
        self.tf.pack(fill="x", pady=(10, 0))
        self.tf.set(tags)
        bar = ttk.Frame(self.body)
        bar.pack(anchor="e", pady=(14, 0))
        ttk.Button(bar, text=t("btn.save"), command=self._save).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text=t("btn.cancel"), command=self.close).pack(side="left")
        self.show()
        self.tf.entries["title"].focus_set()

    def _save(self):
        tags = self.tf.get()
        if tags.date and not core.parse_date(tags.date):
            messagebox.showwarning(APP_NAME, t("msg.bad_date"), parent=self)
            return
        tags.date = core.parse_date(tags.date) or core.today_iso()
        try:
            new, err = core.retag_and_rename(self.path, tags)
        except OSError as e:
            messagebox.showerror(APP_NAME, t("msg.rename_failed").format(
                err=e), parent=self)
            return
        self.result = new
        self.app.select_after = new                               # the renamed file stays selected
        self.close()
        self.app.after(50, lambda: self.app.reload_list(
            t("msg.saved").format(name=os.path.basename(new)) if not err
            else t("msg.saved_tags_failed").format(name=os.path.basename(new), err=err)))


class SettingsDialog(Dialog):
    def __init__(self, master, app):
        super().__init__(master, t("settings.title"), app)
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
        # "" = Same as Windows (shows the language it gives); each language name is written in its own language
        self.lang_opts = [("", t("settings.same_as_windows", language=i18n.NAMES[windows_language()]))] + \
            [(code, i18n.NAMES[code]) for code in i18n.LANGS]
        self.v_lang = tk.StringVar(value=dict(self.lang_opts).get(cfg["ui_language"], self.lang_opts[0][1]))
        follow = t("settings.follow")
        try:
            dev = audio.list_devices()
            self.sys_opts = [follow] + [audio.loopback_label(n) for n in dev["loopbacks"]]
            self.mic_opts = [follow] + dev["mics"]
        except Exception:                                                    # noqa: BLE001
            self.sys_opts, self.mic_opts = [follow], [follow]
            ttk.Label(b, text=t("settings.no_devices"), foreground=C["peach"]).grid(
                row=99, column=0, columnspan=3, sticky="w")
        self.v_sys.set(cfg["system_device"] and audio.loopback_label(cfg["system_device"]) or follow)
        self.v_mic.set(cfg["mic_device"] or follow)
        r = 0
        ttk.Label(b, text=t("settings.output")).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
        ttk.Entry(b, textvariable=self.v_out, width=52).grid(row=r, column=1, sticky="ew", pady=5)
        ttk.Button(b, text=t("btn.browse"), command=self._browse).grid(row=r, column=2, padx=(8, 0))
        r += 1
        ttk.Label(b, text=t("settings.quality")).grid(row=r, column=0, sticky="nw", pady=5, padx=(0, 10))
        qf = ttk.Frame(b)
        qf.grid(row=r, column=1, columnspan=2, sticky="w")
        for key in core.PRESETS:
            ttk.Radiobutton(qf, text=t("preset." + key), value=key, variable=self.v_preset).pack(anchor="w", pady=1)
        r += 1
        ttk.Label(b, text=t("settings.sys_device")).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
        ttk.Combobox(b, textvariable=self.v_sys, values=self.sys_opts, state="readonly", width=50).grid(
            row=r, column=1, columnspan=2, sticky="ew", pady=5)
        r += 1
        ttk.Label(b, text=t("settings.mic_device")).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
        ttk.Combobox(b, textvariable=self.v_mic, values=self.mic_opts, state="readonly", width=50).grid(
            row=r, column=1, columnspan=2, sticky="ew", pady=5)
        for label, var in ((t("settings.sys_volume"), self.v_sg), (t("settings.mic_volume"), self.v_mg)):
            r += 1
            ttk.Label(b, text=label).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
            sc = ttk.Scale(b, from_=0, to=200, variable=var, orient="horizontal",
                           command=lambda v, var=var: var.set(int(float(v)) // 5 * 5))
            sc.grid(row=r, column=1, sticky="ew", pady=5)
            ttk.Label(b, textvariable=var, width=5, foreground=C["sub"]).grid(row=r, column=2, sticky="w", padx=(8, 0))
        r += 1
        ttk.Checkbutton(b, text=t("msg.hotkey_ready"), variable=self.v_hot,
                        style="Base.TCheckbutton").grid(row=r, column=0, columnspan=3, sticky="w", pady=5)
        r += 1
        ttk.Label(b, text=t("settings.language")).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
        ttk.Combobox(b, textvariable=self.v_lang, values=[label for _code, label in self.lang_opts],
                     state="readonly", width=34).grid(row=r, column=1, sticky="w", pady=5)
        r += 1
        self.tl_path = cfg.get("transcriptlab_path", "")              # "" = automatic; saved with Save
        ttk.Label(b, text=t("settings.transcriptlab")).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
        tl = ttk.Frame(b)
        tl.grid(row=r, column=1, columnspan=2, sticky="ew")
        self.tl_label = ttk.Label(tl, text="", foreground=C["sub"], wraplength=360, justify="left")
        self.tl_label.pack(side="left")
        ttk.Button(tl, text=t("btn.clear"), style="Nav.TButton", command=self._tl_clear).pack(side="right")
        ttk.Button(tl, text=t("btn.locate"), style="Nav.TButton", command=self._tl_locate).pack(side="right",
                                                                                              padx=(0, 6))
        self._tl_show()
        r += 1
        ttk.Label(b, text=t("upd.row")).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
        up = ttk.Frame(b)
        up.grid(row=r, column=1, columnspan=2, sticky="ew")
        ttk.Label(up, text="%s %s" % (t("about.version"), APP_VERSION), foreground=C["sub"]).pack(side="left")
        ttk.Button(up, text=t("upd.check"), style="Nav.TButton",
                   command=lambda: self.app.check_updates(self)).pack(side="right")
        bar = ttk.Frame(b)
        bar.grid(row=100, column=0, columnspan=3, sticky="e", pady=(14, 0))
        ttk.Button(bar, text=t("btn.save"), command=self._save).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text=t("btn.cancel"), command=self.close).pack(side="left")
        self.show()

    def _tl_show(self):
        """The TranscriptLab in use: the chosen file, the one found automatically, or Not found."""
        found = core.find_transcriptlab({"transcriptlab_path": self.tl_path})
        if found["status"] == "not_found" or not found["command"]:
            text = t("settings.tl_not_found") if not self.tl_path else "%s — %s" % (self.tl_path,
                                                                                 t("settings.tl_not_found"))
        elif found["source"] == "settings":
            text = self.tl_path
        else:
            text = t("settings.tl_auto", path=found["command"][-1] if len(found["command"]) < 3 else found["command"][0])
            if found["status"] == "too_old":
                text += "  ·  " + t("tl.too_old_text", version=found["version"] or "?")
        self.tl_label.configure(text=text)

    def _tl_locate(self):
        chosen = self.app.locate_transcriptlab(self)
        if chosen:
            self.tl_path = chosen
            self._tl_show()

    def _tl_clear(self):
        self.tl_path = ""
        self._tl_show()

    def _browse(self):
        d = filedialog.askdirectory(parent=self, title=t("settings.choose_folder"),
                                    initialdir=self.v_out.get() or None)
        if d:
            self.v_out.set(os.path.normpath(d))

    def _save(self):
        cfg = self.app.cfg
        follow = t("settings.follow")
        cfg["output_dir"] = self.v_out.get().strip()
        cfg["preset"] = self.v_preset.get()
        s = self.v_sys.get()
        cfg["system_device"] = "" if s == follow else s
        m = self.v_mic.get()
        cfg["mic_device"] = "" if m == follow else m
        cfg["system_gain"], cfg["mic_gain"] = int(self.v_sg.get()), int(self.v_mg.get())
        cfg["hotkey"] = bool(self.v_hot.get())
        cfg["transcriptlab_path"] = self.tl_path
        chosen = self.v_lang.get()
        cfg["ui_language"] = next((code for code, label in self.lang_opts if label == chosen), cfg["ui_language"])
        changed_lang = effective_language(cfg) != i18n.LANG
        self.close()
        self.app.settings_saved(changed_lang)


class TranscriptLabDialog(Dialog):
    """TranscriptLab not found / too old / did not start: Locate… (saved in Settings, then the recording is sent),
    Get TranscriptLab (opens the releases page; Tiny Recorder downloads nothing) and Cancel."""

    def __init__(self, master, app, kind, path="", version="", error=""):
        title = {"not_found": t("tl.not_found_title"), "too_old": t("tl.too_old_title"),
                 "failed": t("tl.failed_title")}[kind]
        super().__init__(master, title, app)
        self.kind, self.path = kind, path
        text = {"not_found": t("tl.not_found_text"),
                "too_old": t("tl.too_old_text", version=version or "?"),
                "failed": t("tl.failed_text", err=error)}[kind]
        ttk.Label(self.body, text=title, foreground=C["mauve"], font=FONT_B).pack(anchor="w")
        self.msg = ttk.Label(self.body, text=text, wraplength=460, justify="left")
        self.msg.pack(anchor="w", pady=(6, 0))
        bar = ttk.Frame(self.body)
        bar.pack(anchor="e", pady=(16, 0))
        ttk.Button(bar, text=t("btn.locate"), command=self._locate).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text=t("btn.get_tl"), command=self._get).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text=t("btn.cancel"), command=self.close).pack(side="left")
        self.show()

    def _locate(self):
        chosen = self.app.locate_transcriptlab(self)
        if not chosen:
            return
        self.app.cfg["transcriptlab_path"] = chosen
        try:
            core.save_config(self.app.cfg)
        except OSError as e:
            core.log("could not save settings: %r" % (e,))
        self.close()
        if self.path:
            self.app.transcribe_path(self.path)

    def _get(self):
        self.app.open_link(core.TRANSCRIPTLAB_RELEASES_URL)
        self.close()


class UpdateDialog(Dialog):
    """A newer release on GitHub (item 0B): what is new, Download and install (the exe only; the new exe is saved
    next to the old one and checked against the release's SHA-256), Open the release page, Later."""

    def __init__(self, master, app, rel):
        super().__init__(master, t("upd.title"), app)
        self.rel = rel
        b = self.body
        ttk.Label(b, text=t("upd.title"), foreground=C["mauve"], font=FONT_B).pack(anchor="w")
        line = t("upd.available", v=rel["version"], cur=APP_VERSION)
        if rel.get("published"):
            line += "  ·  " + t("upd.published", date=rel["published"])
        ttk.Label(b, text=line, wraplength=480, justify="left").pack(anchor="w", pady=(6, 0))
        if rel.get("notes"):
            notes = tk.Text(b, width=64, height=min(10, rel["notes"].count("\n") + 2), wrap="word", bg=C["crust"],
                            fg=C["text"], bd=0, highlightthickness=1, highlightbackground=C["s1"], font=FONT_S,
                            padx=8, pady=6)
            notes.insert("1.0", rel["notes"])
            notes.configure(state="disabled")
            notes.pack(fill="x", pady=(8, 0))
        self.can_install = bool(getattr(sys, "frozen", False) and rel.get("exe"))
        self.status = ttk.Label(b, text="" if self.can_install else t("upd.source_note"), foreground=C["sub"],
                                wraplength=480, justify="left")
        self.status.pack(anchor="w", pady=(8, 0))
        bar = ttk.Frame(b)
        bar.pack(anchor="e", pady=(14, 0))
        self.b_install = None
        if self.can_install:
            self.b_install = ttk.Button(bar, text=t("upd.download"), command=self._install,
                                        state="normal" if app.state == "idle" else "disabled")
            self.b_install.pack(side="left", padx=(0, 8))
        ttk.Button(bar, text=t("upd.page"), command=self._page).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text=t("upd.later"), command=self.close).pack(side="left")
        self.show()

    def _page(self):
        self.app.open_link(self.rel.get("page") or core.APP_RELEASES_URL)
        self.close()

    def _install(self):
        if self.b_install is not None:
            self.b_install.configure(state="disabled")
        self.status.configure(text=t("upd.downloading", pct=0))
        self.app.download_update(self.rel, self)

    def progress(self, done, total):
        pct = int(done * 100 / total) if total else 0
        try:
            self.status.configure(text=t("upd.downloading", pct=pct))
        except tk.TclError:
            pass


# ===========================================================================
# The main window
# ===========================================================================

STATES = ("idle", "starting", "waiting", "recording", "paused", "saving")     # waiting: Start on Sound


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = core.load_config()
        i18n.set_lang(effective_language(self.cfg))
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
        self._rec_warn = ""
        self.player = player.Player()
        self._rec_text = ""
        self.playing_path = ""
        self.now_title = ""
        self._play_id = None
        self.select_after = ""                       # a file to select when the list is next shown (saved, renamed)
        self._hotkey_refused = False
        self._help = None
        self._settings = None
        self.wait_mode = False                       # Start on Sound: waiting until a ticked source has sound
        self.last_sound = 0.0                        # recorded seconds at the last sound (auto stop on silence)
        self.auto_reason = ""                        # why the recording was stopped automatically
        self._auto_id = None
        self._auto_ticks = 0
        self._pause_refused = False
        self._out_dev_start = None                   # (id, name) of the Windows default output at Record (item 1)
        self._device_warn = ""
        self._sys_zero_since = 0.0                   # recorded seconds since the computer audio is exact zero (item 2)
        self._quiet_warn = ""
        area = winsys.work_area()
        self.work = area
        self.work_h = (area[3] - area[1]) if area else 0
        self.compact = bool(self.work_h) and self.work_h < 900
        apply_theme(self, self.compact)
        set_window_icon(self)
        self._restore_geometry(self.cfg.get("window") or "")
        self._build()
        self.bind("<F1>", lambda e: self.show_help())
        self.bind("<Control-r>", lambda e: self.toggle_record())
        self.bind("<Control-p>", lambda e: self.toggle_pause())
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_idletasks()
        winsys.dark_title_bar(winsys.hwnd_of(self.winfo_id()))
        self._start_hotkey()
        self._poll_id = self.after(80, self._poll)
        self._auto_id = self.after(1000, self._auto_tick)
        self.after(300, self.reload_list)
        self.after(900, self.check_recovery)

    # ------------------------------------------------------------------ building

    def _restore_geometry(self, geo):
        """The saved size and place, kept inside the screen: no taller than the work area, and a place on a monitor
        that is gone (a laptop away from its second screen) is replaced by the centre of the main one."""
        m = re.match(r"^(\d+)x(\d+)(?:([+-]-?\d+)([+-]-?\d+))?$", geo or "")
        w, h = (int(m.group(1)), int(m.group(2))) if m else (880, 900)
        w = max(w, 820)
        if self.work_h:
            h = min(h, self.work_h - 60)                           # the title bar and frame are outside h
        if m and m.group(3) is not None:
            x, y = int(m.group(3)), int(m.group(4))
            if winsys.on_a_monitor(x + 60, y + 15):
                self.geometry("%dx%d%+d%+d" % (w, h, x, y))
                return
        if self.work:
            left, top, right, bottom = self.work
            self.geometry("%dx%d%+d%+d" % (w, h, left + max(0, (right - left - w) // 2),
                                          top + max(0, (bottom - top - h - 40) // 2)))
        else:
            self.geometry("%dx%d" % (w, h))

    def _build_auto_stop(self, parent):
        """Item 0C: [x] Stop after [5] silent minutes   [ ] Stop after [60] minutes (stops at 15:42).
        Read live, so a change during a recording counts at once; remembered for the next start."""
        f = ttk.Frame(parent, style="Card.TFrame")
        self.v_auto_sil = tk.BooleanVar(value=self.cfg["auto_stop_silence"])
        self.v_sil_min = tk.StringVar(value=core.fmt_minutes(self.cfg["silence_minutes"]))
        self.v_auto_time = tk.BooleanVar(value=self.cfg["auto_stop_time"])
        self.v_time_min = tk.StringVar(value=core.fmt_minutes(self.cfg["time_minutes"]))
        ttk.Checkbutton(f, text=t("auto.silence_pre"), variable=self.v_auto_sil,
                        command=self._auto_changed).pack(side="left")
        self.e_sil = ttk.Entry(f, textvariable=self.v_sil_min, width=4, justify="center")
        self.e_sil.pack(side="left", padx=4)
        ttk.Label(f, text=t("auto.silence_post"), style="Card.TLabel").pack(side="left", padx=(0, 18))
        ttk.Checkbutton(f, text=t("auto.time_pre"), variable=self.v_auto_time,
                        command=self._auto_changed).pack(side="left")
        self.e_time = ttk.Entry(f, textvariable=self.v_time_min, width=5, justify="center")
        self.e_time.pack(side="left", padx=4)
        ttk.Label(f, text=t("auto.time_post"), style="Card.TLabel").pack(side="left")
        self.stop_at = ttk.Label(f, text="", style="Sub.TLabel")
        self.stop_at.pack(side="left", padx=(8, 0))
        for v in (self.v_sil_min, self.v_time_min):
            v.trace_add("write", lambda *a: self._auto_changed())
        self._update_stop_at()
        return f

    def _auto_changed(self):
        self.cfg["auto_stop_silence"] = bool(self.v_auto_sil.get())
        self.cfg["auto_stop_time"] = bool(self.v_auto_time.get())
        for var, key in ((self.v_sil_min, "silence_minutes"), (self.v_time_min, "time_minutes")):
            value = core.parse_minutes(var.get())
            if value is not None:                         # a box being typed in keeps the last good value
                self.cfg[key] = value
        self._update_stop_at()

    def _update_stop_at(self):
        """'(stops at 15:42)': now plus what is left of the time limit (pauses push it later)."""
        m = core.parse_minutes(self.v_time_min.get())
        text = ""
        if self.v_auto_time.get() and m is not None and self.state != "saving":
            done = self.seconds if self.state in ("recording", "paused") else 0.0
            when = time.localtime(time.time() + max(0.0, m * 60 - done))
            text = t("auto.stops_at", time=time.strftime("%H:%M", when))
        self.stop_at.configure(text=text)

    def _auto_tick(self):
        self._auto_id = None
        try:
            self._update_stop_at()
            self._auto_ticks += 1
            if self._auto_ticks % 5 == 0:
                self._check_output_device()
        except (AttributeError, tk.TclError):
            return
        self._auto_id = self.after(1000, self._auto_tick)

    def _check_output_device(self):
        """Item 1: the recording follows the Windows default output chosen at Record. If Windows moves the sound to
        another device (a headset plugged in, Bluetooth connecting), the loopback would record silence: say so."""
        if self.state not in ("recording", "paused", "waiting") or not self._out_dev_start:
            self._device_warn = ""
            return
        now = winsys.default_output_device()
        changed = bool(now) and now[0] != self._out_dev_start[0]
        warn = t("msg.output_changed", device=now[1] or "?") if changed else ""
        if warn != self._device_warn:
            self._device_warn = warn
            self._refresh_detail()

    def _check_quiet_system(self, sp, secs):
        """Item 2: a ticked computer audio that gives exact zero for 3 minutes (a Bluetooth headset that switched
        profile mid-call can do that) gets a quiet warning; it never stops the recording."""
        if not self.v_sys.get() or sp > 0.0:
            self._sys_zero_since = secs
            warn = ""
        elif secs - self._sys_zero_since >= SYSTEM_SILENT_MINUTES * 60:
            warn = t("msg.system_silent", n=SYSTEM_SILENT_MINUTES)
        else:
            warn = self._quiet_warn
        if warn != self._quiet_warn:
            self._quiet_warn = warn
            self._refresh_detail()

    def _check_auto_stop(self, sp, mp, secs):
        """Called with every level update while recording: silence counter and time limit (item 0C)."""
        heard = max(sp if self.v_sys.get() else 0.0, mp if self.v_mic.get() else 0.0)
        if heard >= audio.SOUND_LEVEL:
            self.last_sound = secs
        n = core.parse_minutes(self.v_sil_min.get())
        if self.v_auto_sil.get() and n is not None and secs - self.last_sound >= n * 60:
            self.auto_reason = t("auto.stopped_silence", n=core.fmt_minutes(n))
            self.stop_recording()
            return
        m = core.parse_minutes(self.v_time_min.get())
        if self.v_auto_time.get() and m is not None and secs >= m * 60:
            self.auto_reason = t("auto.stopped_time", n=core.fmt_minutes(m))
            self.stop_recording()

    def _apply_minsize(self):
        """The minimum height is what the window needs with 4 rows of the list, but never more than the screen."""
        self.update_idletasks()
        need = self._root_frame.winfo_reqheight()
        if self.work_h:
            need = min(need, self.work_h - 60)
        self.minsize(820, need)

    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        cp = self.compact
        root = ttk.Frame(self, padding=(18, 8, 18, 6) if cp else (18, 14, 18, 10))
        root.pack(fill="both", expand=True)
        self._root_frame = root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        head = ttk.Frame(root)
        head.grid(row=0, column=0, sticky="ew")
        try:
            self._logo = tk.PhotoImage(file=icon_path("icon-32.png" if cp else "icon-48.png"))
            ttk.Label(head, image=self._logo).pack(side="left", padx=(0, 10))
        except tk.TclError:
            pass
        ttk.Label(head, text=t("app.name"), font=FONT_H, foreground=C["mauve"]).pack(side="left")
        for text, cmd in ((t("nav.about"), self.show_about), (t("nav.help") + "  F1", self.show_help),
                          (t("nav.settings"), self.show_settings)):
            ttk.Button(head, text=text, style="Nav.TButton", command=cmd).pack(side="right", padx=2)

        # ---- recorder card
        card = ttk.Frame(root, style="Card.TFrame", padding=(16, 8) if cp else 16)
        card.grid(row=1, column=0, sticky="ew", pady=(8 if cp else 12, 0))
        card.columnconfigure(0, weight=1)
        self.timer = tk.Label(card, text="00:00:00", font=("Consolas", 24, "bold") if cp else FONT_T, bg=C["mantle"],
                              fg=C["text"])
        self.timer.grid(row=0, column=0, pady=(0, 2))
        self.status = ttk.Label(card, text=t("state.ready"), style="Head.TLabel")
        self.status.grid(row=1, column=0)
        self.detail = ttk.Label(card, text="", style="Sub.TLabel", wraplength=700, justify="center")
        self.detail.grid(row=2, column=0, pady=(2, 0))
        self.warnlbl = ttk.Label(card, text="", style="Warn.TLabel", wraplength=700, justify="center")
        self.warnlbl.grid(row=3, column=0)
        btns = ttk.Frame(card, style="Card.TFrame")
        btns.grid(row=4, column=0, pady=(4, 2) if cp else (12, 10))
        self.b_rec = ttk.Button(btns, text="●  " + t("btn.record"), style="Rec.TButton", command=self.record_now)
        self.b_rec.pack(side="left", padx=5)
        self.b_wait = ttk.Button(btns, text="◌  " + t("btn.start_on_sound"), style="Big.TButton",
                                 command=self.start_on_sound)
        self.b_wait.pack(side="left", padx=5)
        self.b_pause = ttk.Button(btns, text=PAUSE_SIGN + "  " + t("btn.pause"), style="Big.TButton",
                                  command=self.toggle_pause)
        self.b_pause.pack(side="left", padx=5)
        self.b_stop = ttk.Button(btns, text="■  " + t("btn.stop"), style="Big.TButton", command=self.toggle_record)
        self.b_stop.pack(side="left", padx=5)
        meters = ttk.Frame(card, style="Card.TFrame")
        meters.grid(row=5, column=0, sticky="ew", pady=(2, 4) if cp else (4, 8))
        meters.columnconfigure(1, weight=1)
        self.v_sys = tk.BooleanVar(value=self.cfg["use_system"])
        self.v_mic = tk.BooleanVar(value=self.cfg["use_mic"])
        self.c_sys = ttk.Checkbutton(meters, text=t("src.system"), variable=self.v_sys, command=self._src_changed)
        mp = 0 if cp else 3
        self.c_sys.grid(row=0, column=0, sticky="w", padx=(0, 12), pady=mp)
        self.m_sys = LevelBar(meters)
        self.m_sys.grid(row=0, column=1, sticky="ew", pady=mp)
        ttk.Label(meters, text=t("src.system_hint"), style="Sub.TLabel").grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.c_mic = ttk.Checkbutton(meters, text=t("src.mic"), variable=self.v_mic, command=self._src_changed)
        self.c_mic.grid(row=1, column=0, sticky="w", padx=(0, 12), pady=mp)
        self.m_mic = LevelBar(meters)
        self.m_mic.grid(row=1, column=1, sticky="ew", pady=mp)
        ttk.Label(meters, text=t("src.mic_hint"), style="Sub.TLabel").grid(row=1, column=2, sticky="w", padx=(10, 0))
        self._build_auto_stop(card).grid(row=6, column=0, sticky="w", pady=(0, 2) if cp else (2, 4))
        ttk.Separator(card).grid(row=7, column=0, sticky="ew", pady=(2, 4) if cp else (6, 8))
        ttk.Label(card, text=t("main.about_recording"), style="Head.TLabel").grid(row=8, column=0, sticky="w")
        self.tags = TagFields(card, compact=cp)
        self.tags.grid(row=9, column=0, sticky="ew", pady=(2 if cp else 6, 0))

        # ---- recordings list (it gets the height that is left; 4 rows at least, 2 on a short screen)
        lst = ttk.Frame(root)
        lst.grid(row=2, column=0, sticky="nsew", pady=(8 if cp else 14, 0))
        lst.columnconfigure(0, weight=1)
        lst.rowconfigure(1, weight=1)
        top = ttk.Frame(lst)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 3 if cp else 6))
        ttk.Label(top, text=t("list.title"), font=FONT_B, foreground=C["mauve"]).pack(side="left")
        self.b_play = ttk.Button(top, text="▶  " + t("btn.play"), style="Play.TButton", command=self.toggle_play)
        self.b_play.pack(side="left", padx=(14, 6))
        self.b_tx = ttk.Button(top, text=t("btn.transcribe"), style="Nav.TButton", command=self.transcribe_selected)
        self.b_tx.pack(side="left", padx=(0, 10))
        self.now = ttk.Label(top, text="", foreground=C["sub"], font=FONT_S)
        self.now.pack(side="left")
        ttk.Button(top, text=t("list.open_folder"), style="Nav.TButton",
                   command=lambda: winsys.show_in_explorer(core.output_dir(self.cfg))).pack(side="right")
        cols = ("date", "title", "people", "time", "size")
        self.tree = ttk.Treeview(lst, columns=cols, show="headings", selectmode="browse", height=2 if cp else 4)
        for key, text, w, anc in (("date", t("tags.date"), 96, "w"), ("title", t("tags.title"), 280, "w"),
                                  ("people", t("tags.people"), 200, "w"), ("time", t("list.time"), 80, "e"),
                                  ("size", t("list.size"), 80, "e")):
            self.tree.heading(key, text=text)
            self.tree.column(key, width=w, anchor=anc, stretch=(key in ("title", "people")))
        sb = ttk.Scrollbar(lst, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        sb.grid(row=1, column=1, sticky="ns")
        self.tree.bind("<Double-1>", lambda e: self.toggle_play(restart=True))
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._play_button_state())
        self.tree.bind("<Button-3>", self._menu)
        self.tree.bind("<Return>", lambda e: self.toggle_play(restart=True))
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        self.menu = tk.Menu(self, tearoff=0, bg=C["mantle"], fg=C["text"], activebackground=C["s1"],
                            activeforeground=C["text"], bd=0)
        self.menu.add_command(label=t("btn.play"), command=lambda: self.toggle_play(restart=True))
        self.menu.add_command(label=t("menu.open_default"), command=self.open_default)
        self.menu.add_command(label=t("menu.transcribe"), command=self.transcribe_selected)
        self.menu.add_command(label=t("menu.show"), command=self.show_selected)
        self.menu.add_command(label=t("menu.edit"), command=self.edit_selected)
        self.menu.add_command(label=t("menu.copy"), command=self.copy_selected)
        self.menu.add_separator()
        self.menu.add_command(label=t("menu.delete"), command=self.delete_selected)
        self.foot = ttk.Label(root, text=core.output_dir(self.cfg), foreground=C["ov"], font=FONT_S)
        self.foot.grid(row=3, column=0, sticky="w", pady=(2 if cp else 8, 0))
        self._render_state()
        self._render_rows()
        self._apply_minsize()

    # ------------------------------------------------------------------ state

    def _set_state(self, st):
        self.state = st
        self._render_state()

    def _render_state(self):
        st = self.state
        self.b_rec.configure(state="normal" if st in ("idle", "waiting") else "disabled")   # waiting: start now
        self.b_wait.configure(state="normal" if st == "idle" else "disabled")
        self.b_pause.configure(state="normal" if st in ("recording", "paused") else "disabled",
                               text=("▶  " + t("btn.resume")) if st == "paused" else (PAUSE_SIGN + "  " + t("btn.pause")))
        self.b_stop.configure(state="normal" if st in ("starting", "recording", "paused", "waiting") else "disabled")
        src_state = "normal" if st in ("idle", "recording", "paused", "waiting") else "disabled"
        self.c_sys.configure(state=src_state)
        self.c_mic.configure(state=src_state)
        label = {"idle": t("state.ready"), "starting": t("state.starting"), "recording": t("state.recording"),
                 "paused": t("state.paused"), "saving": t("state.saving"), "waiting": t("state.waiting")}[st]
        colour = {"idle": C["mauve"], "starting": C["yellow"], "recording": C["red"], "paused": C["peach"],
                  "saving": C["yellow"], "waiting": C["teal"]}[st]
        self.status.configure(text=("● " if st == "recording" else "") + label, foreground=colour)
        if st == "idle":
            self.timer.configure(fg=C["text"])
            self.title(("%s %s" % (APP_NAME, APP_VERSION)))
            self.m_sys.reset()
            self.m_mic.reset()
            self._rec_warn = ""
            self.warnlbl.configure(text=self._idle_warning())
            if not self.detail.cget("text").startswith(t("msg.saved").split("{")[0]):
                self.detail.configure(text=self._ready_text())
        elif st in ("recording", "paused", "waiting"):
            self.timer.configure(fg={"recording": C["red"], "paused": C["peach"], "waiting": C["teal"]}[st])
            self._title_tick()
        self._play_button_state()

    def _ready_text(self):
        return t("msg.hotkey_ready") if (self.hotkey and self.hotkey.ok) else ""

    def _idle_warning(self):
        """Shown while idle, from the hotkey's state (not kept in the line): gone when the hotkey is switched off."""
        if not self.cfg["hotkey"]:
            return ""
        if self._hotkey_refused:
            return t("msg.hotkey_taken")
        return t("msg.hotkey_pause_taken") if self._pause_refused else ""

    def _title_tick(self):
        mark = {"recording": "● " + t("title.rec"), "waiting": "◌ " + t("title.waiting")}.get(
            self.state, "⏸ " + t("title.paused"))
        self.title("%s %s  ·  %s" % (mark, core.fmt_clock(self.seconds), APP_NAME))

    def _src_changed(self):
        """Idle: remember the choice for next time. Recording: switch that channel on or off in the file now (this
        is for this recording only; the ticks go back to the remembered choice when it ends)."""
        if self.state == "idle":
            self.cfg["use_system"] = bool(self.v_sys.get())
            self.cfg["use_mic"] = bool(self.v_mic.get())
        elif self.rec and self.state in ("recording", "paused", "waiting"):
            self.rec.set_enabled("system", bool(self.v_sys.get()))
            self.rec.set_enabled("mic", bool(self.v_mic.get()))
            self._refresh_detail()

    def _restore_sources(self):
        self.v_sys.set(self.cfg["use_system"])
        self.v_mic.set(self.cfg["use_mic"])

    def _refresh_detail(self):
        """'Recording from … at … Hz · size', plus which channel is switched off."""
        if self.state not in ("recording", "paused", "waiting"):
            return
        text = self._rec_text
        if self.size:
            text += "  ·  " + core.fmt_size(self.size)
        off = [name for name, var in ((t("src.system"), self.v_sys), (t("src.mic"), self.v_mic)) if not var.get()]
        if off:
            text += "  ·  " + t("msg.off").format(what=", ".join(off))
        self.detail.configure(text=text)
        both_off = not self.v_sys.get() and not self.v_mic.get()
        # the warnings of this recording (a device not available, a fallback) stay until it ends; the live ones
        # (another output device, a silent computer audio) come and go
        live = "  ·  ".join(w for w in (self._device_warn, self._quiet_warn) if w)
        text = "  ·  ".join(w for w in (self._rec_warn, ("⚠ " + live) if live else "") if w)
        self.warnlbl.configure(text="⚠ " + t("msg.both_off") if both_off else text)

    def _start_hotkey(self):
        if self.hotkey:
            self.hotkey.stop()
            self.hotkey = None
        self._hotkey_refused = self._pause_refused = False
        if self.cfg["hotkey"]:
            hk = winsys.Hotkey(self.q)
            if hk.start():
                self.hotkey = hk
            else:
                self._hotkey_refused = True
            self._pause_refused = not getattr(hk, "pause_ok", True)
            if not hk.ok and getattr(hk, "pause_ok", False):
                self.hotkey = hk                                   # Ctrl+Alt+P alone still works
        if self.state == "idle":
            self.warnlbl.configure(text=self._idle_warning())

    # ------------------------------------------------------------------ recording

    def toggle_record(self):
        """Ctrl+Alt+R and Stop: start when idle; otherwise stop (waiting for sound: cancel, nothing is kept)."""
        if self.state == "idle":
            self.start_recording()
        elif self.state in ("starting", "recording", "paused", "waiting"):
            self.stop_recording()

    def record_now(self):
        """Record Now: start at once; while waiting for sound, start writing now."""
        if self.state == "idle":
            self.start_recording()
        elif self.state == "waiting" and self.rec:
            self.rec.trigger_now()

    def start_on_sound(self):
        """Start on Sound (item 0A): the devices open and the meters move; the file starts when a ticked source has
        sound (for example when a call's waiting room ends)."""
        if self.state == "idle":
            self.start_recording(wait=True)

    def start_recording(self, wait=False):
        self.stop_playback()
        if self._settings is not None and self._settings.winfo_exists():
            self._settings.close()                       # Ctrl+Alt+R while Settings is open: Settings is cancelled
        self._settings = None
        self.tags.refresh_date()
        if not (self.v_sys.get() or self.v_mic.get()):
            messagebox.showinfo(APP_NAME, t("msg.tick_source"))
            return
        folder = core.output_dir(self.cfg)
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as e:
            messagebox.showerror(APP_NAME, "%s\n%s" % (t("msg.start_failed"), e))
            return
        free = winsys.free_bytes(folder)
        if free is not None and free < audio.LOW_DISK * 3:
            messagebox.showerror(APP_NAME, t("msg.no_space"))
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
            free_check=lambda: winsys.free_bytes(folder),
            opener_one=lambda pa_inst, kind: audio.open_one_source(pa_inst, kind, sysn if kind == "system" else micn),
            wait_for_sound=wait)
        self.wait_mode = wait
        self.last_sound = 0.0
        self.auto_reason = ""
        self._sys_zero_since = 0.0
        self._quiet_warn = self._device_warn = ""
        self._out_dev_start = winsys.default_output_device() if (want_sys and not sysn) else None
        self.seconds, self.size = 0.0, 0
        self.timer.configure(text="00:00:00")
        self._rec_warn = ""
        self.warnlbl.configure(text="")
        self.detail.configure(text="")
        self._set_state("starting")
        self.rec.start()

    def _fallback_warnings(self, names):
        """A device chosen in Settings that is gone (a headset unplugged) is replaced by the Windows default: say so."""
        out = []
        loops = [audio.loopback_label(n) for n in names if n.endswith(" [Loopback]")]
        mics = [n for n in names if not n.endswith(" [Loopback]")]
        if self.cfg["system_device"] and loops and self.cfg["system_device"] not in loops:
            out.append(t("msg.device_fallback", device=self.cfg["system_device"]))
        if self.cfg["mic_device"] and mics and self.cfg["mic_device"] not in mics:
            out.append(t("msg.device_fallback", device=self.cfg["mic_device"]))
        return out

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
        if self.rec and self.state in ("starting", "recording", "paused", "waiting"):
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
            if self.state in ("idle", "recording", "paused", "starting", "waiting"):
                self.toggle_record()
            return
        if ev == "hotkey_pause":                                   # Ctrl+Alt+P (item 3)
            self.toggle_pause()
            return
        kind = ev[0]
        if kind == "started":
            _k, rate, names, problems = ev
            if self.state == "starting":
                self._set_state("waiting" if self.wait_mode else "recording")
            self._rec_text = t("msg.recording_from").format(
                sources=" + ".join(audio.loopback_label(n) for n in names), rate=rate)
            warns = []
            for p in problems:                                         # a device that could not be opened is shown off
                is_sys = p.startswith("computer audio")
                (self.v_sys if is_sys else self.v_mic).set(False)
                what = p.split(":", 1)[1].strip() if p.startswith(("computer audio:", "microphone:")) else p
                warns.append(t("msg.not_available", what="%s: %s" % (t("src.system") if is_sys else t("src.mic"),
                                                                     what)))
            warns += self._fallback_warnings(names)
            self._rec_warn = ("⚠ " + "; ".join(warns)) if warns else ""
            self._refresh_detail()
        elif kind == "levels":
            _k, sp, mp, secs, size = ev
            self.seconds, self.size = secs, size
            if self.state in ("recording", "paused", "saving", "waiting"):
                self.m_sys.set(sp)
                self.m_mic.set(mp)
                self.timer.configure(text=core.fmt_clock(secs))
                if self.state != "saving":
                    self._title_tick()
                    self._refresh_detail()
                if self.state == "recording":
                    self._check_quiet_system(sp, secs)
                    self._check_auto_stop(sp, mp, secs)
        elif kind == "triggered":                                  # Start on Sound: the sound started
            if self.state == "waiting":
                self.last_sound = self._sys_zero_since = self.seconds
                self._set_state("recording")
        elif kind == "sourcefail":
            _k, which, err = ev
            (self.v_sys if which == "system" else self.v_mic).set(False)
            self._rec_warn = "⚠ " + t("msg.not_available").format(what=err)
            self.warnlbl.configure(text=self._rec_warn)
        elif kind == "error":
            self._rec_warn = "⚠ " + ev[1]
            self.warnlbl.configure(text=self._rec_warn)
            if self.state == "starting":
                messagebox.showerror(APP_NAME, "%s\n\n%s" % (t("msg.start_failed"), ev[1]))
            else:
                messagebox.showerror(APP_NAME, "%s\n\n%s" % (t("msg.stopped_error"), ev[1]))
        elif kind == "lowdisk":
            messagebox.showwarning(APP_NAME, t("msg.low_disk"))
        elif kind == "stopped":
            _k, secs, part = ev
            self.rec = None
            self._finish(secs, part)
        elif kind == "saved":
            _k, final, err, secs = ev
            self._after_saved(final, err)
        elif kind == "tx":
            _k, path, title, err = ev
            self._after_transcribe(path, title, err)
        elif kind == "update":
            self._update_result(ev[1], ev[2])
        elif kind == "upd_progress":
            dialog = getattr(self, "_update_dialog", None)
            if dialog is not None:
                dialog.progress(ev[1], ev[2])
        elif kind == "upd_done":
            self._update_downloaded(ev[1], ev[2], ev[3])
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
            self._restore_sources()
            self._set_state("idle")
            if self.closing:
                self._destroy()
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
        msg = t("msg.saved").format(name=name) if not err else \
            t("msg.saved_tags_failed").format(name=name, err=err)
        if self.auto_reason:                                       # stopped by auto stop: say why
            msg += "  ·  " + self.auto_reason
            self.auto_reason = ""
        self.tags.clear()
        self._restore_sources()
        self._set_state("idle")
        self.detail.configure(text=msg)
        self.select_after = final                                  # the new recording is selected (ready to Transcribe)
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
        keep = self.select_after or self._selected()
        if self.select_after and any(os.path.normcase(r["path"]) == os.path.normcase(self.select_after)
                                     for r in self.rows):
            self.select_after = ""
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(self.rows):
            tg = r["tags"]
            stem = os.path.splitext(r["name"])[0]
            date = tg.date or stem[:10]
            title = tg.title or (stem.split(" - ", 1)[1] if " - " in stem else stem)
            self.tree.insert("", "end", iid=str(i), values=(date, title, tg.people, core.fmt_clock(r["seconds"]),
                                                             core.fmt_size(r["size"])))
        if self.rows:
            idx = next((i for i, r in enumerate(self.rows)
                        if keep and os.path.normcase(r["path"]) == os.path.normcase(keep)), 0)
            self.tree.selection_set(str(idx))
            self.tree.see(str(idx))
        self._play_button_state()

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
            self._menu_states()
            self.menu.tk_popup(e.x_root, e.y_root)

    def _menu_states(self):
        """Transcribe is off while recording (the file being recorded is not finished)."""
        self.menu.entryconfigure(self.menu.index(t("menu.transcribe")),
                                 state="normal" if self.state == "idle" else "disabled")

    def open_default(self):
        p = self._selected()
        if p and os.path.exists(p):
            os.startfile(p)                                                  # noqa: S606

    # ------------------------------------------------------------------ Transcribe with TranscriptLab (item 9)

    def transcribe_selected(self):
        """Hand the selected recording to TranscriptLab (a separate app). Not during a recording: the file being
        recorded is not finished. Nothing is transcribed or sent anywhere by Tiny Recorder itself."""
        self.transcribe_path(self._selected())

    def transcribe_path(self, p):
        if self.state != "idle" or not p or not os.path.exists(p):
            return
        if self.playing_path and os.path.normcase(self.playing_path) == os.path.normcase(p):
            self.stop_playback()                                       # release the file first
        found = core.find_transcriptlab(self.cfg)
        if found["status"] != "ok":
            TranscriptLabDialog(self, self, found["status"], path=p, version=found["version"])
            return
        r = self._row_for(p)
        title = self._row_title(r) if r else os.path.basename(p)
        command = core.transcribe_command(found, p)

        def work():
            try:
                winsys.start_detached(command)
                self.q.put(("tx", p, title, ""))
            except OSError as e:
                self.q.put(("tx", p, title, str(e)))
        threading.Thread(target=work, name="transcribe", daemon=True).start()

    def _after_transcribe(self, path, title, err):
        if err:
            core.log("TranscriptLab did not start: %s" % err)
            TranscriptLabDialog(self, self, "failed", path=path, error=err)
            return
        msg = t("tl.sent", title=title)
        self.detail.configure(text=msg)
        self.after(6000, lambda: self.state == "idle" and self.detail.cget("text") == msg
                   and self.detail.configure(text=self._ready_text()))

    def locate_transcriptlab(self, parent):
        """Pick TranscriptLab's program; saved in Settings. Returns the path or ""."""
        p = filedialog.askopenfilename(parent=parent, title=t("tl.pick_title"),
                                       filetypes=[("TranscriptLab", "TranscriptLab*.exe"),
                                                  (t("tl.filetype_programs"), "*.exe")])
        return os.path.normpath(p) if p else ""

    # ------------------------------------------------------------------ the built-in player

    def _row_for(self, path):
        for r in self.rows:
            if os.path.normcase(r["path"]) == os.path.normcase(path):
                return r
        return None

    def _row_title(self, r):
        stem = os.path.splitext(r["name"])[0]
        return r["tags"].title or (stem.split(" - ", 1)[1] if " - " in stem else stem)

    def toggle_play(self, restart=False):
        """Play the selected recording (the newest when none is selected); press again to stop. restart=True (a
        double-click) starts the chosen one even when another is playing."""
        if self.state != "idle":
            return
        if self.playing_path and not restart:
            self.stop_playback()
            return
        self.play_selected()

    def play_selected(self):
        p = self._selected() or (self.rows[0]["path"] if self.rows else "")
        if not p or not os.path.exists(p) or self.state != "idle":
            return
        try:
            self.player.play(p)
        except player.PlayerError as e:
            self.stop_playback()
            messagebox.showerror(APP_NAME, t("msg.play_failed").format(err=e))
            return
        self.playing_path = p
        r = self._row_for(p)
        self.now_title = self._row_title(r) if r else os.path.basename(p)
        self._play_button_state()
        self._play_tick()

    def stop_playback(self):
        if self._play_id is not None:
            try:
                self.tk.call("after", "cancel", self._play_id)               # never after_cancel while closing
            except tk.TclError:
                pass
            self._play_id = None
        self.player.stop()
        self.playing_path = ""
        try:
            self.now.configure(text="")
        except (AttributeError, tk.TclError):
            pass
        self._play_button_state()

    def _play_tick(self):
        self._play_id = None
        if not self.playing_path:
            return
        if self.player.finished():
            self.stop_playback()
            return
        self.now.configure(text="%s   %s / %s" % (t("msg.playing").format(title=self.now_title),
                                                   core.fmt_clock(self.player.position_ms() / 1000.0),
                                                   core.fmt_clock(self.player.length_ms / 1000.0)))
        self._play_id = self.after(250, self._play_tick)

    def _play_button_state(self):
        try:
            if self.state != "idle":
                self.b_play.configure(state="disabled", text="▶  " + t("btn.play"))
            elif self.playing_path:
                self.b_play.configure(state="normal", text="■  " + t("btn.stop"))
            else:
                self.b_play.configure(state="normal" if (self.rows or self._selected()) else "disabled",
                                      text="▶  " + t("btn.play"))
            self.b_tx.configure(state="normal" if self.state == "idle" and self._selected() else "disabled")
        except (AttributeError, tk.TclError):
            pass

    def show_selected(self):
        p = self._selected()
        if p:
            winsys.show_in_explorer(p)

    def edit_selected(self):
        p = self._selected()
        if p and os.path.exists(p):
            self.stop_playback()
            EditDialog(self, self, p)

    def delete_selected(self):
        """Move the selected recording to the Recycle Bin (it can be restored from there)."""
        p = self._selected()
        if not p or not os.path.exists(p):
            return
        name = os.path.basename(p)
        if not winsys.has_recycle_bin(p):                          # network share, USB stick: gone for good
            if not messagebox.askyesno(APP_NAME, t("msg.delete_permanent_ask") + "\n\n" + name, icon="warning",
                                       default="no"):
                return
            self.stop_playback()
            try:
                os.remove(p)
            except OSError as e:
                messagebox.showerror(APP_NAME, t("msg.delete_failed", err=e))
                return
            self.reload_list(t("msg.deleted", name=name))
            return
        if not messagebox.askyesno(APP_NAME, t("msg.recycle_ask") + "\n\n" + name):
            return
        self.stop_playback()                                       # a playing file cannot be deleted
        if winsys.send_to_recycle_bin(p):
            self.reload_list(t("msg.recycled").format(name=name))
        else:
            messagebox.showerror(APP_NAME, t("msg.recycle_failed"))

    def open_link(self, url):
        if url:
            webbrowser.open(url)

    def copy_selected(self):
        p = self._selected()
        if p:
            self.clipboard_clear()
            self.clipboard_append(p)
            self.detail.configure(text=t("msg.copied"))

    # ------------------------------------------------------------------ recovery

    def check_recovery(self):
        if self.state != "idle":
            return
        parts = core.find_part_files(core.output_dir(self.cfg), exclude=self.part if self.rec else None)
        parts = [p for p in parts if _size(p) > 2048]
        if not parts:
            return
        if not messagebox.askyesno(t("recovery.title"), tn("recovery.ask", len(parts))):
            return
        folder = core.output_dir(self.cfg)
        n = 0
        for p in parts:
            try:
                d = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(p)))
                core.finalize(p, folder, Tags(d, t("recovery.default_title")))
                n += 1
            except OSError:
                pass
        self.reload_list(tn("recovery.done", n))

    # ------------------------------------------------------------------ dialogs and settings

    def show_about(self):
        AboutDialog(self, self)

    def show_help(self):
        """One Help window: F1 again brings the open one to the front."""
        if self._help is not None and self._help.winfo_exists():
            self._help.deiconify()
            self._help.lift()
            self._help.focus_set()
            return
        self._help = HelpDialog(self, self)

    def show_settings(self):
        if self.state != "idle":
            return
        self._settings = SettingsDialog(self, self)

    # ------------------------------------------------------------------ updates (item 0B, as RadioSave)

    def check_updates(self, parent=None):
        """Ask GitHub for the latest release on a worker; the answer comes back on the queue."""
        self._update_parent = parent
        self.detail.configure(text=t("upd.checking"))

        def work():
            try:
                self.q.put(("update", core.check_update(), None))
            except core.UpdateError as e:
                self.q.put(("update", None, e))
        threading.Thread(target=work, name="update-check", daemon=True).start()

    def _parent_for(self, win):
        try:
            return win if (win is not None and win.winfo_exists()) else self
        except tk.TclError:
            return self

    def update_error_text(self, err):
        return t("upd.err." + err.code, **{k: str(v) for k, v in err.values.items()})

    def _update_result(self, rel, err):
        parent = self._parent_for(getattr(self, "_update_parent", None))
        if self.detail.cget("text") == t("upd.checking"):
            self.detail.configure(text=self._ready_text() if self.state == "idle" else self.detail.cget("text"))
        if err is not None:
            messagebox.showwarning(APP_NAME, self.update_error_text(err), parent=parent)
        elif not rel["newer"]:
            messagebox.showinfo(APP_NAME, t("upd.latest", v=APP_VERSION), parent=parent)
        else:
            UpdateDialog(parent, self, rel)

    def download_update(self, rel, dialog):
        folder = os.path.dirname(sys.executable)
        self._update_dialog = dialog

        def work():
            try:
                path = core.download_update(rel, folder,
                                            progress=lambda d, n: self.q.put(("upd_progress", d, n)))
                self.q.put(("upd_done", rel["version"], path, None))
            except core.UpdateError as e:
                self.q.put(("upd_done", rel["version"], "", e))
            except OSError as e:
                self.q.put(("upd_done", rel["version"], "", core.UpdateError("offline", reason=e)))
        threading.Thread(target=work, name="update-download", daemon=True).start()

    def _update_downloaded(self, version, path, err):
        dialog = self._parent_for(getattr(self, "_update_dialog", None))
        if err is not None:
            messagebox.showwarning(APP_NAME, self.update_error_text(err), parent=dialog)
            return
        if dialog is not self:
            dialog.close()
        if self.state != "idle":
            messagebox.showinfo(APP_NAME, t("upd.ready_later", v=version, path=path))
            return
        if not messagebox.askyesno(APP_NAME, t("upd.ready_restart", v=version)):
            return
        try:
            winsys.start_detached([path])                     # a cleaned environment (one exe starting another)
        except OSError as e:
            messagebox.showerror(APP_NAME, t("upd.start_failed", path=path, err=e))
            return
        self.on_close()

    def settings_saved(self, changed_lang):
        try:
            core.save_config(self.cfg)
        except OSError as e:
            core.log("could not save settings: %r" % (e,))
        if changed_lang:
            i18n.set_lang(effective_language(self.cfg))
            keep = self.tags.get()
            self._build()
            self.tags.set(keep)
        self.foot.configure(text=core.output_dir(self.cfg))
        self._start_hotkey()
        self.detail.configure(text=self._ready_text())
        self.reload_list()

    # ------------------------------------------------------------------ closing

    def on_close(self):
        if self.state in ("starting", "recording", "paused", "saving", "waiting"):
            if self.state == "saving":
                self.closing = True
                return
            if self.state == "waiting":                           # nothing recorded yet: just stop waiting
                self.closing = True
                self.stop_recording()
                return
            if not messagebox.askyesno(APP_NAME, t("msg.close_ask")):
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
        self.stop_playback()
        if self.hotkey:
            self.hotkey.stop()
        for after_id in (self._poll_id, self._auto_id):
            if after_id:
                try:
                    self.tk.call("after", "cancel", after_id)                # never after_cancel while closing
                except tk.TclError:
                    pass
        self.destroy()


def main():
    cfg = core.load_config()
    i18n.set_lang(effective_language(cfg))
    inst =winsys.SingleInstance(core.home_dir())
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
