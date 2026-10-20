"""v0.1.3: the meters empty at once, the Help text wraps to the box, the third-party notices ship with the app."""

import os
import re

import tinyrecorder_help as helpmod
from conftest import load_app_module
import test_gui

app = test_gui.app                                                      # the window fixture of test_gui.py
pump = test_gui.pump

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_meters_are_empty_the_moment_a_recording_ends(app):
    a, mod, out = app
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    assert pump(a, lambda: a.m_sys.value > 0.3 and a.m_mic.value > 0.3)
    assert a.m_sys.hold > 0.3
    import time
    time.sleep(0.8)
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle" and a.rows)
    for bar in (a.m_sys, a.m_mic):
        assert bar.value == 0.0 and bar.hold == 0.0                  # no frozen bar, no leftover peak-hold tick


def test_level_bar_reset():
    mod = load_app_module()
    import tkinter as tk
    root = tk.Tk()
    try:
        bar = mod.LevelBar(root)
        bar.set(0.5)
        assert bar.value > 0.3
        bar.set(0.0)
        assert 0.0 < bar.value                                       # set() falls slowly...
        bar.reset()
        assert bar.value == 0.0 and bar.hold == 0.0                  # ...reset() does not
    finally:
        root.destroy()


def test_paragraphs_join_continuation_lines():
    mod = load_app_module()
    text = "\nFirst line\ncontinues here.\n\n- item one\n  goes on\n- item two\n\n**Heading**\nbody text\nmore body\n1. step\nstep goes on\n"
    assert mod.paragraphs(text) == ["First line continues here.", "", "- item one goes on", "- item two", "",
                                    "**Heading**", "body text more body", "1. step step goes on"]


def test_help_text_wraps_in_both_languages():
    mod = load_app_module()
    for sections in (helpmod.EN, helpmod.PT):
        for title, body in sections:
            blocks = mod.paragraphs(body)
            for b in blocks:
                assert "\n" not in b
            assert any(len(b) > 60 for b in blocks)                  # real paragraphs, not one line per row
    pt = dict(helpmod.PT)["Arquivos e privacidade"]
    assert any("As configurações ficam em %APPDATA%" in b for b in mod.paragraphs(pt))


def test_third_party_notices_ship_with_the_app():
    text = open(os.path.join(ROOT, "THIRD_PARTY_LICENSES.md"), encoding="utf-8").read()
    for needle in ("mutagen", "GPL-2.0-or-later", "lameenc", "LAME", "LGPL-3.0-or-later", "PyAudioWPatch", "Apache-2.0",
                   "numpy", "https://github.com/junqueirach/tiny-recorder", "GNU GENERAL PUBLIC LICENSE",
                   "GNU LESSER GENERAL PUBLIC LICENSE"):
        assert needle in text, needle
    assert re.search(r"Version 3, 29 June 2007", text) and "Version 2, June 1991" in text
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    assert "THIRD_PARTY_LICENSES.md" in readme and "GPL" in readme


def test_about_names_the_third_party_notices(app):
    a, mod, out = app
    d = mod.AboutDialog(a, a)
    a.update()
    labels = []

    def walk(w):
        for c in w.winfo_children():
            if c.winfo_class() == "TLabel":
                labels.append(str(c.cget("text")))
            walk(c)
    walk(d)
    assert "THIRD_PARTY_LICENSES.md" in labels
    d.close()
