"""v0.1.4 item 8 in the window: every screen builds in the three languages with nothing clipped at the minimum width,
Settings switches the language live, the Windows language is the default, and the recording itself (tags, file name)
is the same in every language."""

import os
import sys
import time
from tkinter import font as tkfont

import pytest

import tinyrecorder_audio as au
import tinyrecorder_core as core
import tinyrecorder_i18n as i18n
import tinyrecorder_player as pl
import tinyrecorder_winsys as winsys
from conftest import FakeMci, FakeSource, load_app_module
from test_core import _tiny_mp3

LANGS = ("en", "pt-BR", "es")


def make_app(tmp_path, monkeypatch, ui_language="", windows=0x0409):
    out = tmp_path / "rec"
    cfg = core.load_config()
    cfg["output_dir"] = str(out)
    cfg["hotkey"] = False
    cfg["ui_language"] = ui_language
    core.save_config(cfg)
    monkeypatch.setattr(winsys, "windows_ui_langid", lambda: windows)
    mod = load_app_module()
    fakes = [FakeSource("system", 44100, 2, 440, name="Fake Speakers [Loopback]"),
             FakeSource("mic", 48000, 1, 880, name="Fake Mic")]
    monkeypatch.setattr(au, "open_sources", lambda want_sys, want_mic, *a, **k: (None, fakes, []))
    monkeypatch.setattr(au, "list_devices", lambda: {"loopbacks": ["Fake Speakers [Loopback]"], "mics": ["Fake Mic"],
                                                     "default_out": "Fake Speakers", "default_in": "Fake Mic"})
    fake_mci = FakeMci()                                            # never a real sound
    monkeypatch.setattr(pl, "_mci_send", fake_mci.send)
    shown = []
    for name in ("showerror", "showwarning", "showinfo"):
        monkeypatch.setattr(mod.messagebox, name, lambda *x, _n=name, **k: shown.append((_n, x)))
    monkeypatch.setattr(mod.messagebox, "askyesno", lambda *x, **k: True)
    a = mod.App()
    a.shown = shown
    a.mci = fake_mci
    a.geometry("820x760")
    a.update()
    return a, mod, out


def pump(a, until, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        a.update()
        if until():
            return True
        time.sleep(0.03)
    return False


def clipped(win):
    """Labels, buttons and boxes narrower than their text."""
    bad = []

    def walk(w):
        for c in w.winfo_children():
            if c.winfo_class() in ("TLabel", "TButton", "TCheckbutton", "TRadiobutton") and c.winfo_ismapped():
                if c.winfo_width() + 1 < c.winfo_reqwidth():
                    bad.append((c.winfo_class(), str(c.cget("text")), c.winfo_width(), c.winfo_reqwidth()))
            walk(c)
    win.update_idletasks()
    walk(win)
    return bad


@pytest.mark.skipif(sys.platform != "win32", reason="the layout is checked with the Windows fonts (Linux fonts are wider)")
@pytest.mark.parametrize("lang", LANGS)
def test_every_screen_builds_with_nothing_clipped(tmp_path, monkeypatch, lang):
    a, mod, out = make_app(tmp_path, monkeypatch, ui_language=lang)
    try:
        assert i18n.LANG == lang
        assert a.winfo_width() <= 830 and not clipped(a), clipped(a)
        os.makedirs(out, exist_ok=True)
        path = str(out / "2026-10-20 - One.mp3")
        _tiny_mp3(path)
        dialogs = [mod.AboutDialog(a, a), mod.HelpDialog(a, a), mod.SettingsDialog(a, a), mod.EditDialog(a, a, path)]
        for d in dialogs:
            a.update()
            assert not clipped(d), (type(d).__name__, clipped(d))
            d.close()
        help_titles = {"en": "Quick start", "pt-BR": "Primeiros passos", "es": "Primeros pasos"}[lang]
        h = mod.HelpDialog(a, a)
        assert help_titles in h.lb.get(0)
        a.update()
        font = tkfont.Font(font=h.lb.cget("font"))
        widest = max(font.measure(h.lb.get(i)) for i in range(h.lb.size()))
        assert widest <= h.lb.winfo_width() - 4, (widest, h.lb.winfo_width())    # no section title cut off
        h.close()
        assert not a.shown
    finally:
        a._destroy()


def test_windows_language_is_the_default(tmp_path, monkeypatch):
    a, mod, out = make_app(tmp_path, monkeypatch, windows=0x080A)            # es-MX, nothing chosen in Settings
    try:
        assert i18n.LANG == "es" and "Grabar" in a.b_rec.cget("text")
        d = mod.SettingsDialog(a, a)
        assert d.v_lang.get() == "Igual que Windows (Español)"
        d.close()
    finally:
        a._destroy()


def test_settings_switches_the_language_live_and_keeps_the_details(tmp_path, monkeypatch):
    a, mod, out = make_app(tmp_path, monkeypatch)
    try:
        a.tags.set(core.Tags("2026-10-20", "Kept title", "Ana"))
        d = mod.SettingsDialog(a, a)
        assert d.lang_opts[0] == ("", "Same as Windows (English)")
        assert [label for _c, label in d.lang_opts[1:]] == ["English", "Português (Brasil)", "Español"]
        d.v_lang.set("Español")
        d._save()
        a.update()
        assert i18n.LANG == "es" and "Grabar" in a.b_rec.cget("text") and a.tags.get().title == "Kept title"
        assert core.load_config()["ui_language"] == "es"
        d = mod.SettingsDialog(a, a)
        d.v_lang.set(d.lang_opts[0][1])                                       # Same as Windows (English here)
        d._save()
        a.update()
        assert i18n.LANG == "en" and "Record" in a.b_rec.cget("text")
        with open(core.config_path(), encoding="utf-8") as f:
            assert "ui_language" not in f.read()
    finally:
        a._destroy()


def test_the_recording_is_the_same_in_every_language(tmp_path, monkeypatch):
    from mutagen.id3 import ID3
    frames = {}
    for lang in LANGS:
        a, mod, out = make_app(tmp_path / lang, monkeypatch, ui_language=lang)
        try:
            a.tags.set(core.Tags("2026-10-20", "Budget review", "Ana, Bob", "Alpha", "note"))
            a.toggle_record()
            assert pump(a, lambda: a.state == "recording")
            time.sleep(1.0)
            a.toggle_record()
            assert pump(a, lambda: a.state == "idle" and a.rows)
            names = sorted(os.listdir(out))
            assert names == ["2026-10-20 - Budget review.mp3"]
            id3 = ID3(str(out / names[0]))
            frames[lang] = {k: [str(x) for x in id3[k].text] for k in ("TIT2", "TPE1", "TALB", "TDRC", "TENC", "TCOP")}
            assert frames[lang]["TCOP"] == [core.COPYRIGHT_TEXT] == ["not for distribution, personal use only"]
        finally:
            a._destroy()
    assert frames["en"] == frames["pt-BR"] == frames["es"]
