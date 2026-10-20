"""The window, driven in-process (a Claude session cannot send real mouse or key input to Tk). Real devices are
replaced by fake sources; every dialog is opened and closed once."""

import os
import sys
import time

import pytest

import tinyrecorder_audio as au
import tinyrecorder_core as core
import tinyrecorder_i18n as i18n
import tinyrecorder_player as pl
from conftest import FakeMci, FakeSource, load_app_module


@pytest.fixture
def app(tmp_path, monkeypatch):
    out = tmp_path / "rec"
    cfg = core.load_config()
    cfg["output_dir"] = str(out)
    cfg["hotkey"] = False
    core.save_config(cfg)
    mod = load_app_module()
    fakes = [FakeSource("system", 44100, 2, 440, name="Fake Speakers [Loopback]"), FakeSource("mic", 48000, 1, 880,
                                                                                            name="Fake Mic")]
    monkeypatch.setattr(au, "open_sources", lambda want_sys, want_mic, *a, **k: (
        None, [f for f in fakes if (f.kind == "system" and want_sys) or (f.kind == "mic" and want_mic)], []))
    late_mic = FakeSource("mic", 48000, 1, 880, name="Late Mic")
    monkeypatch.setattr(au, "open_one_source", lambda pa_inst, kind, name="": late_mic)
    fake_mci = FakeMci()
    monkeypatch.setattr(pl, "_mci_send", fake_mci.send)
    shown = []
    for name in ("showerror", "showwarning", "showinfo"):
        monkeypatch.setattr(mod.messagebox, name, lambda *x, _n=name, **k: shown.append((_n, x)))
    monkeypatch.setattr(mod.messagebox, "askyesno", lambda *x, **k: True)
    a = mod.App()
    a.shown = shown
    a.mci = fake_mci
    a.update()
    yield a, mod, out
    try:
        a._destroy()
    except Exception:
        pass
    i18n.set_lang("en")


def pump(a, until, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        a.update()
        if until():
            return True
        time.sleep(0.03)
    return False


def test_record_tag_stop_save_and_list(app):
    a, mod, out = app
    a.tags.set(core.Tags("2026-10-20", "Budget: review", "Ana, Bob", "Alpha", "first note"))
    a.toggle_record()
    assert a.state == "starting"
    assert pump(a, lambda: a.state == "recording")
    assert pump(a, lambda: a.seconds > 1.0)
    assert "Recording" in a.status.cget("text") and a.title().startswith("● REC")
    a.toggle_pause()
    assert a.state == "paused" and "⏸" in a.title()
    a.toggle_pause()
    a.toggle_record()                                              # stop
    assert pump(a, lambda: a.state == "idle" and a.rows)
    files = [f for f in os.listdir(out) if f.endswith(".mp3")]
    assert files == ["2026-10-20 - Budget review.mp3"]
    t = core.read_tags(str(out / files[0]))
    assert (t.title, t.people, t.project, t.notes, t.date) == ("Budget: review", "Ana, Bob", "Alpha", "first note",
                                                              "2026-10-20")
    assert a.tags.get().title == "" and a.tags.get().date == core.today_iso()          # fields cleared for the next
    assert a.tree.get_children() and a.tree.item("0", "values")[1] == "Budget: review"
    assert not any(f.endswith(".part") for f in os.listdir(out))
    assert not a.shown


def test_edit_dialog_retags_and_renames(app):
    a, mod, out = app
    a.toggle_record()
    pump(a, lambda: a.state == "recording")
    time.sleep(1.2)
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle" and a.rows)
    a.tree.selection_set("0")
    path = a._selected()
    dlg = mod.EditDialog(a, a, path)
    dlg.tf.set(core.Tags("2026-11-02", "Renamed one", "Cy"))
    dlg._save()
    assert pump(a, lambda: any(r["name"] == "2026-11-02 - Renamed one.mp3" for r in a.rows))
    assert core.read_tags(str(out / "2026-11-02 - Renamed one.mp3")).people == "Cy"


def test_dialogs_open_and_close_and_language_switch(app):
    a, mod, out = app
    for cls in (mod.AboutDialog, mod.HelpDialog, mod.SettingsDialog):
        d = cls(a, a)
        a.update()
        d.close()
    a.cfg["lang"] = "pt"
    a.settings_saved(True)
    a.update()
    assert i18n.LANG == "pt" and "Gravar" in a.b_rec.cget("text")
    d = mod.HelpDialog(a, a)
    a.update()
    assert "Primeiros passos" in d.lb.get(0)
    d.close()
    a.cfg["lang"] = "en"
    a.settings_saved(True)
    assert "Record" in a.b_rec.cget("text")


def test_nothing_ticked_does_not_start(app, monkeypatch):
    a, mod, out = app
    shown = []
    monkeypatch.setattr(mod.messagebox, "showinfo", lambda *x, **k: shown.append(x))
    a.v_sys.set(False)
    a.v_mic.set(False)
    a.toggle_record()
    assert a.state == "idle" and shown


def test_instant_stop_leaves_no_file(app):
    a, mod, out = app
    a.toggle_record()
    a.toggle_record()                                              # stop while still starting
    assert pump(a, lambda: a.state == "idle")
    assert not [f for f in os.listdir(out) if f.endswith((".mp3", ".part"))]
    assert not a.shown                                             # no error box for a stop before any audio


def test_recovery_offers_unfinished_files(app, monkeypatch):
    a, mod, out = app
    os.makedirs(out, exist_ok=True)
    from test_core import _tiny_mp3
    _tiny_mp3(str(out / ("~recording-1" + core.PART_SUFFIX)))
    monkeypatch.setattr(mod.messagebox, "askyesno", lambda *x, **k: True)
    a.check_recovery()
    assert pump(a, lambda: any("Recovered recording" in r["name"] for r in a.rows))
    assert not core.find_part_files(str(out))


def test_level_bar_scale():
    mod = load_app_module()
    assert mod.LevelBar.to_scale(0.0) == 0.0
    assert mod.LevelBar.to_scale(1.0) == 1.0
    assert 0.45 < mod.LevelBar.to_scale(0.03) < 0.6               # about -30 dB


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only (named mutex)")
def test_single_instance_name_depends_on_data_folder(tmp_path):
    import tinyrecorder_winsys as w
    a, b = w.SingleInstance(str(tmp_path / "a")), w.SingleInstance(str(tmp_path / "b"))
    assert a.name != b.name and not a.already and not b.already
    again = w.SingleInstance(str(tmp_path / "a"))
    assert again.already
    for s in (a, b, again):
        s.release()


def record_one(a, seconds=1.2, expect=1):
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    time.sleep(seconds)
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle" and len(a.rows) >= expect)


def test_play_and_stop_a_saved_recording(app):
    a, mod, out = app
    assert str(a.b_play.cget("state")) == "disabled"             # nothing saved yet
    a.tags.set(core.Tags("2026-10-20", "Playable", "Ana"))
    record_one(a)
    assert str(a.b_play.cget("state")) == "normal" and "Play" in a.b_play.cget("text")
    assert a.tree.selection() == ("0",)                          # the newest is selected for you
    a.toggle_play()
    assert a.playing_path.endswith("2026-10-20 - Playable.mp3") and a.mci.playing
    assert "Stop" in a.b_play.cget("text")
    assert pump(a, lambda: "Playable" in a.now.cget("text") and "00:03" in a.now.cget("text"))
    a.toggle_play()                                              # press again = Stop
    assert not a.playing_path and not a.mci.is_open and "Play" in a.b_play.cget("text") and a.now.cget("text") == ""
    assert not a.shown


def test_playback_returns_to_play_when_the_file_ends(app):
    a, mod, out = app
    record_one(a)
    a.toggle_play()
    assert a.playing_path
    a.mci.finish()
    assert pump(a, lambda: not a.playing_path)
    assert "Play" in a.b_play.cget("text") and not a.mci.is_open


def test_recording_stops_playback_and_play_is_off_while_recording(app):
    a, mod, out = app
    record_one(a)
    a.toggle_play()
    assert a.playing_path
    a.toggle_record()                                            # a new recording would capture the playback
    assert not a.playing_path and not a.mci.is_open
    assert pump(a, lambda: a.state == "recording")
    assert str(a.b_play.cget("state")) == "disabled"
    a.toggle_play()                                              # ignored while recording
    assert not a.playing_path
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle")
    assert str(a.b_play.cget("state")) == "normal"


def test_editing_a_playing_file_stops_it_first(app):
    a, mod, out = app
    record_one(a)
    a.toggle_play()
    assert a.playing_path
    a.edit_selected()
    assert not a.playing_path and not a.mci.is_open
    for w in a.winfo_children():
        if isinstance(w, mod.EditDialog):
            w.close()


def test_unplayable_file_shows_one_message_and_stays_idle(app, monkeypatch):
    a, mod, out = app
    record_one(a)
    monkeypatch.setattr(a.player, "_send", lambda c: (266, "Cannot play") if c.startswith("open ") else (0, ""))
    a.toggle_play()
    assert not a.playing_path and len(a.shown) == 1 and "Cannot play" in a.shown[0][1][1]


def test_double_click_switches_to_another_recording(app):
    a, mod, out = app
    record_one(a)
    time.sleep(1.1)
    record_one(a, expect=2)
    assert len(a.rows) == 2
    a.tree.selection_set("0")
    a.toggle_play(restart=True)
    first = a.playing_path
    a.tree.selection_set("1")
    a.toggle_play(restart=True)
    assert a.playing_path and a.playing_path != first and a.mci.path == a.playing_path


# ---------------------------------------------------------------- v0.1.2: channel boxes, Delete, About links
def test_channel_boxes_work_during_a_recording_and_reset_afterwards(app):
    a, mod, out = app
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    assert str(a.c_sys.cget("state")) == "normal" and str(a.c_mic.cget("state")) == "normal"
    a.v_mic.set(False)
    a._src_changed()
    assert pump(a, lambda: "Off: Microphone" in a.detail.cget("text"))
    assert pump(a, lambda: a.m_mic.value == 0.0 and a.m_sys.value > 0.2)
    a.v_sys.set(False)
    a._src_changed()
    assert pump(a, lambda: "only silence" in a.warnlbl.cget("text"))
    a.v_sys.set(True)
    a.v_mic.set(True)
    a._src_changed()
    assert pump(a, lambda: a.warnlbl.cget("text") == "" and "Off:" not in a.detail.cget("text"))
    a.toggle_pause()
    assert str(a.c_mic.cget("state")) == "normal"
    a.toggle_pause()
    a.v_mic.set(False)                                             # left off when the recording stops...
    a._src_changed()
    time.sleep(1.0)                                                # (a recording under 0.3 s is thrown away)
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle" and a.rows), (a.state, len(a.rows), a.detail.cget("text"), a.shown)
    assert a.v_mic.get() is True and a.cfg["use_mic"] is True        # ...but not remembered for the next one
    assert not a.shown


def test_unticked_channel_at_start_is_remembered_and_can_be_added_later(app):
    a, mod, out = app
    a.v_mic.set(False)
    a._src_changed()                                               # idle: remembered
    assert a.cfg["use_mic"] is False
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    a.v_mic.set(True)
    a._src_changed()                                               # switched on mid-recording: opened in the background
    assert pump(a, lambda: a.m_mic.value > 0.2, timeout=6)
    time.sleep(1.0)
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle" and a.rows)
    assert a.v_mic.get() is False and a.cfg["use_mic"] is False


def test_delete_moves_to_the_recycle_bin_after_asking(app, monkeypatch):
    a, mod, out = app
    record_one(a)
    path = a._selected()
    sent = []
    monkeypatch.setattr(mod.winsys, "send_to_recycle_bin", lambda p: (sent.append(p), os.remove(p), True)[2])
    answers = iter([False, True])
    monkeypatch.setattr(mod.messagebox, "askyesno", lambda *x, **k: next(answers))
    a.toggle_play()
    assert a.playing_path
    a.delete_selected()                                            # No: nothing happens, playback goes on
    assert os.path.exists(path) and not sent and a.playing_path
    a.delete_selected()                                            # Yes: playback stops, the file goes, the list refreshes
    assert sent == [path] and not os.path.exists(path) and not a.playing_path
    assert pump(a, lambda: not a.rows)
    assert str(a.b_play.cget("state")) == "disabled" and not a.shown


def test_delete_reports_a_failure(app, monkeypatch):
    a, mod, out = app
    record_one(a)
    monkeypatch.setattr(mod.winsys, "send_to_recycle_bin", lambda p: False)
    monkeypatch.setattr(mod.messagebox, "askyesno", lambda *x, **k: True)
    a.delete_selected()
    assert len(a.shown) == 1 and a.shown[0][0] == "showerror" and a.rows


def test_about_has_the_github_links_and_the_licence(app, monkeypatch):
    a, mod, out = app
    opened = []
    monkeypatch.setattr(mod.webbrowser, "open", lambda url: opened.append(url))
    d = mod.AboutDialog(a, a)
    a.update()
    buttons, labels = [], []

    def walk(w):
        for c in w.winfo_children():
            if c.winfo_class() == "TButton" and str(c.cget("style")) == "Link.TButton":
                buttons.append(c)
            if c.winfo_class() == "TLabel":
                labels.append(str(c.cget("text")))
            walk(c)
    walk(d)
    texts = {b.cget("text"): b for b in buttons}
    assert "github.com/junqueirach/tiny-recorder" in texts and "GitHub issues" in texts
    texts["github.com/junqueirach/tiny-recorder"].invoke()
    texts["GitHub issues"].invoke()
    assert opened == ["https://github.com/junqueirach/tiny-recorder", "https://github.com/junqueirach/tiny-recorder/issues"]
    assert "MIT" in labels
    d.close()
