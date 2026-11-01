"""v0.1.4 item 9: Transcribe with TranscriptLab. Never the real TranscriptLab: APPDATA is a temp folder (conftest) and
TranscriptLab is a small fake script that writes what it received."""

import json
import os
import sys
import time

import pytest

import tinyrecorder_core as core
import tinyrecorder_winsys as winsys
from test_core import _tiny_mp3
from test_v014_ui import make_app, pump

FAKE_TL = r'''
import json, os, sys, time
out = os.environ["FAKE_TL_OUT"]
with open(out + ".tmp", "w", encoding="utf-8") as f:
    json.dump({"argv": sys.argv[1:], "env": dict(os.environ)}, f)
os.replace(out + ".tmp", out)
time.sleep(3)
'''


def write_install_json(data):
    path = core.transcriptlab_install_json()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(data if isinstance(data, str) else json.dumps(data))
    return path


def fake_exe(tmp_path, name="TranscriptLab_v_0_16_9.exe"):
    p = tmp_path / "tl" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"MZ")
    return str(p)


# ---------------------------------------------------------------- the finder (contract point 5)

def test_install_json_is_read_from_appdata(tmp_path):
    assert core.transcriptlab_install_json() == os.path.join(str(tmp_path / "appdata"), "TranscriptLab", "install.json")


def test_settings_path_comes_first(tmp_path):
    exe = fake_exe(tmp_path)
    write_install_json({"app": "TranscriptLab", "version": "0.16.9", "contract": 1, "command": [fake_exe(tmp_path, "b.exe")]})
    found = core.find_transcriptlab({"transcriptlab_path": exe})
    assert found == {"status": "ok", "command": [exe], "version": "", "source": "settings"}
    assert core.find_transcriptlab({"transcriptlab_path": exe + ".gone"})["status"] == "not_found"


@pytest.mark.parametrize("change, status", [
    ({}, "ok"),
    ({"version": "0.16.10"}, "ok"),                    # numbers, not text: 0.16.10 > 0.16.9
    ({"version": "0.17.0"}, "ok"),
    ({"version": "0.16.8"}, "too_old"),
    ({"contract": 0}, "too_old"),
    ({"contract": None}, "too_old"),
    ({"app": "Other"}, "not_found"),
    ({"command": []}, "not_found"),
    ({"command": "x.exe"}, "not_found"),
    ({"gone": True}, "not_found"),                     # command[0] does not exist
])
def test_install_json_rules(tmp_path, change, status):
    exe = fake_exe(tmp_path)
    data = {"app": "TranscriptLab", "version": "0.16.9", "contract": 1, "command": [exe], "written": "x"}
    if change.pop("gone", False):
        data["command"] = [exe + ".gone"]
    data.update(change)
    write_install_json(data)
    found = core.find_transcriptlab({"transcriptlab_path": ""})
    assert found["status"] == status and found["source"] == "auto"


def test_broken_or_missing_install_json_is_not_found(tmp_path):
    assert core.find_transcriptlab({})["status"] == "not_found"
    write_install_json("{broken")
    assert core.find_transcriptlab({})["status"] == "not_found"


def test_source_install_needs_interpreter_and_script(tmp_path):
    script = tmp_path / "TranscriptLab.py"
    script.write_text("x")
    write_install_json({"app": "TranscriptLab", "version": "0.16.9", "contract": 1,
                        "command": [sys.executable, str(script)]})
    assert core.find_transcriptlab({})["status"] == "ok"
    script.unlink()
    assert core.find_transcriptlab({})["status"] == "not_found"


def test_command_line_follows_the_contract():
    found = {"command": ["C:/TL/TranscriptLab.exe"]}
    assert core.transcribe_command(found, "C:/r/a b.mp3") == [
        "C:/TL/TranscriptLab.exe", "--transcribe", "C:/r/a b.mp3", "--from", "Tiny Recorder 0.1.4"]


# ---------------------------------------------------------------- the detached start (a real child process)

def test_fake_transcriptlab_gets_the_file_and_a_clean_environment(tmp_path, monkeypatch):
    script = tmp_path / "fake_tl.py"
    script.write_text(FAKE_TL, encoding="utf-8")
    out = tmp_path / "received.json"
    monkeypatch.setenv("FAKE_TL_OUT", str(out))
    for k, v in (("TCL_LIBRARY", r"C:\_MEI123\tcl"), ("TK_LIBRARY", r"C:\_MEI123\tk"), ("_MEIPASS2", r"C:\_MEI123"),
                 ("_PYI_APPLICATION_HOME_DIR", r"C:\_MEI123"), ("_PYI_ARCHIVE_FILE", "x")):
        monkeypatch.setenv(k, v)
    rec = tmp_path / "Gravações de reunião" / "2026-10-20 - Revisão orçamento.mp3"
    rec.parent.mkdir()
    _tiny_mp3(str(rec))
    write_install_json({"app": "TranscriptLab", "version": "0.16.9", "contract": 1,
                        "command": [sys.executable, str(script)]})
    found = core.find_transcriptlab({})
    t0 = time.monotonic()
    winsys.start_detached(core.transcribe_command(found, str(rec)))
    assert time.monotonic() - t0 < 2.0                              # never waits (the fake stays 3 s)
    end = time.time() + 20
    while not out.exists() and time.time() < end:
        time.sleep(0.1)
    got = json.loads(out.read_text(encoding="utf-8"))
    assert got["argv"] == ["--transcribe", str(rec), "--from", "Tiny Recorder 0.1.4"]
    env = {k.upper(): v for k, v in got["env"].items()}
    assert not [k for k in env if k in ("TCL_LIBRARY", "TK_LIBRARY", "_MEIPASS2") or k.startswith("_PYI_")]
    assert env["PYINSTALLER_RESET_ENVIRONMENT"] == "1"


def test_clean_env_keeps_everything_else():
    env = winsys.clean_child_env({"PATH": "p", "TCL_LIBRARY": "x", "_pyi_lower": "y", "APPDATA": "a"})
    assert env == {"PATH": "p", "APPDATA": "a", "PYINSTALLER_RESET_ENVIRONMENT": "1"}


# ---------------------------------------------------------------- the window

@pytest.fixture
def tlapp(tmp_path, monkeypatch):
    a, mod, out = make_app(tmp_path, monkeypatch)
    started = []
    monkeypatch.setattr(mod.winsys, "start_detached", lambda cmd: started.append(cmd))
    a.started = started
    yield a, mod, out
    a._destroy()


def record_one(a):
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    time.sleep(1.1)
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle" and a.rows)


def dialogs(a, mod):
    return [w for w in a.winfo_children() if isinstance(w, mod.TranscriptLabDialog)]


def test_button_is_off_without_a_selection_and_while_recording(tlapp):
    a, mod, out = tlapp
    assert str(a.b_tx.cget("state")) == "disabled"                 # nothing to select
    record_one(a)
    assert str(a.b_tx.cget("state")) == "normal"
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    assert str(a.b_tx.cget("state")) == "disabled"
    a.transcribe_selected()                                         # ignored while recording
    assert not a.started and not dialogs(a, mod)
    idx = a.menu.index(mod.t("menu.transcribe"))
    a._menu_states()
    assert str(a.menu.entrycget(idx, "state")) == "disabled"
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle")
    a._menu_states()
    assert str(a.menu.entrycget(idx, "state")) == "normal"


def test_transcribe_hands_over_and_says_so(tlapp, tmp_path):
    a, mod, out = tlapp
    exe = fake_exe(tmp_path)
    write_install_json({"app": "TranscriptLab", "version": "0.16.9", "contract": 1, "command": [exe]})
    a.tags.set(core.Tags("2026-10-20", "Budget review"))
    record_one(a)
    a.toggle_play()
    assert a.playing_path
    a.transcribe_selected()
    assert not a.playing_path and not a.mci.is_open                 # the file is released first
    assert pump(a, lambda: "Sent to TranscriptLab: Budget review" in a.detail.cget("text"))
    assert a.started == [[exe, "--transcribe", a._selected(), "--from", "Tiny Recorder 0.1.4"]]
    assert not a.shown and not dialogs(a, mod)


@pytest.mark.parametrize("setup, kind, text", [
    ("none", "not_found", "TranscriptLab was not found"),
    ("old", "too_old", "TranscriptLab 0.16.9 or newer is needed (found 0.16.8)."),
])
def test_not_found_and_too_old_show_the_dialog(tlapp, tmp_path, setup, kind, text):
    a, mod, out = tlapp
    if setup == "old":
        write_install_json({"app": "TranscriptLab", "version": "0.16.8", "contract": 1, "command": [fake_exe(tmp_path)]})
    record_one(a)
    a.transcribe_selected()
    a.update()
    d = dialogs(a, mod)
    assert len(d) == 1 and d[0].kind == kind and not a.started
    shown = [str(w.cget("text")) for w in d[0].body.winfo_children() if w.winfo_class() == "TLabel"]
    assert any(text in s for s in shown), shown
    d[0].close()


def test_a_start_that_fails_shows_the_error_once(tlapp, tmp_path, monkeypatch):
    a, mod, out = tlapp
    write_install_json({"app": "TranscriptLab", "version": "0.16.9", "contract": 1, "command": [fake_exe(tmp_path)]})

    def boom(cmd):
        raise OSError("[WinError 193] not a valid Win32 application")
    monkeypatch.setattr(mod.winsys, "start_detached", boom)
    record_one(a)
    a.transcribe_selected()
    assert pump(a, lambda: dialogs(a, mod))
    d = dialogs(a, mod)
    assert len(d) == 1 and d[0].kind == "failed" and "WinError 193" in d[0].msg.cget("text")
    d[0].close()


def test_locate_saves_the_path_and_sends_the_recording(tlapp, tmp_path, monkeypatch):
    a, mod, out = tlapp
    record_one(a)
    a.transcribe_selected()
    a.update()
    d = dialogs(a, mod)[0]
    exe = fake_exe(tmp_path, "TranscriptLab.exe")
    monkeypatch.setattr(mod.filedialog, "askopenfilename", lambda **k: exe)
    d._locate()
    assert core.load_config()["transcriptlab_path"] == exe
    assert a.started and a.started[0][:2] == [exe, "--transcribe"]


def test_get_transcriptlab_opens_the_releases_page(tlapp, monkeypatch):
    a, mod, out = tlapp
    opened = []
    monkeypatch.setattr(mod.webbrowser, "open", lambda url: opened.append(url))
    record_one(a)
    a.transcribe_selected()
    a.update()
    dialogs(a, mod)[0]._get()
    assert opened == ["https://github.com/junqueirach/transcriptlab/releases"] and not dialogs(a, mod)


def test_settings_row_locate_and_clear(tlapp, tmp_path, monkeypatch):
    a, mod, out = tlapp
    s = mod.SettingsDialog(a, a)
    assert s.tl_label.cget("text") == "Not found"
    exe = fake_exe(tmp_path, "TranscriptLab.exe")
    monkeypatch.setattr(mod.filedialog, "askopenfilename", lambda **k: exe)
    s._tl_locate()
    assert s.tl_label.cget("text") == exe
    s._save()
    assert core.load_config()["transcriptlab_path"] == exe
    s = mod.SettingsDialog(a, a)
    auto = fake_exe(tmp_path, "auto.exe")
    write_install_json({"app": "TranscriptLab", "version": "0.16.9", "contract": 1, "command": [auto]})
    s._tl_clear()
    assert s.tl_label.cget("text") == "%s (found automatically)" % auto
    s._save()
    assert core.load_config()["transcriptlab_path"] == ""
