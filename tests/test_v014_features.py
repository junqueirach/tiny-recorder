"""v0.1.4: the pause sign (0D), auto stop (0C) and Start on Sound (0A). Fake sources only (no sound card)."""

import os
import time

import pytest

import tinyrecorder_audio as au
import tinyrecorder_core as core
from conftest import FakeSource
from test_v014_ui import make_app, pump


@pytest.fixture
def app(tmp_path, monkeypatch):
    a, mod, out = make_app(tmp_path, monkeypatch)
    yield a, mod, out
    try:
        a._destroy()
    except Exception:
        pass


def use_sources(monkeypatch, *sources):
    monkeypatch.setattr(au, "open_sources", lambda *x, **k: (None, list(sources), []))


def mp3s(out):
    return [f for f in os.listdir(out) if f.endswith(".mp3")] if os.path.isdir(out) else []


# ---------------------------------------------------------------- 0D

def test_pause_button_uses_the_usual_pause_sign(app):
    a, mod, out = app
    assert a.b_pause.cget("text").startswith("❚❚") and "⏸" not in a.b_pause.cget("text")
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    a.toggle_pause()
    assert a.b_pause.cget("text").startswith("▶")
    a.toggle_pause()
    assert a.b_pause.cget("text").startswith("❚❚")
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle")


# ---------------------------------------------------------------- 0C auto stop

@pytest.mark.parametrize("text, value", [("5", 5.0), ("1.5", 1.5), ("1,5", 1.5), (" 90 ", 90.0), ("0", None),
                                         ("-2", None), ("abc", None), ("", None), ("2000", None)])
def test_minutes_box_accepts_dot_and_comma(text, value):
    assert core.parse_minutes(text) == value


def test_auto_stop_settings_default_and_round_trip():
    cfg = core.load_config()
    assert cfg["auto_stop_silence"] is True and cfg["silence_minutes"] == 5.0 and cfg["auto_stop_time"] is False
    cfg.update(auto_stop_time=True, time_minutes=1.5, silence_minutes=2.0)
    core.save_config(cfg)
    again = core.load_config()
    assert (again["auto_stop_time"], again["time_minutes"], again["silence_minutes"]) == (True, 1.5, 2.0)


def test_stops_by_itself_after_silence(app, monkeypatch):
    a, mod, out = app
    use_sources(monkeypatch, FakeSource("system", 44100, 2, 440, level=0.0, name="Quiet [Loopback]"))
    a.v_sil_min.set("0,02")                                      # 1.2 s, typed with a comma
    a.v_auto_sil.set(True)
    a._auto_changed()
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    assert pump(a, lambda: a.state == "idle" and a.rows, timeout=10)
    assert "stopped after 0.02 silent minutes" in a.detail.cget("text") and len(mp3s(out)) == 1
    assert not a.shown


def test_sound_keeps_the_silence_counter_at_zero(app, monkeypatch):
    a, mod, out = app
    use_sources(monkeypatch, FakeSource("system", 44100, 2, 440, level=0.3, name="Loud [Loopback]"))
    a.v_sil_min.set("0.02")
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    time.sleep(2.0)
    assert not pump(a, lambda: a.state != "recording", timeout=0.5)  # sound: still recording
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle")


def test_stops_at_the_time_limit_and_shows_when(app, monkeypatch):
    a, mod, out = app
    use_sources(monkeypatch, FakeSource("system", 44100, 2, 440, level=0.3, name="Loud [Loopback]"))
    a.v_time_min.set("0.02")
    a.v_auto_time.set(True)
    a._auto_changed()
    assert a.stop_at.cget("text").startswith("(stops at ")
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    assert pump(a, lambda: a.state == "idle" and a.rows, timeout=10)
    assert "stopped at 0.02 minutes" in a.detail.cget("text")
    assert a.cfg["auto_stop_time"] is True and a.cfg["time_minutes"] == 0.02


def test_a_box_being_typed_in_keeps_the_last_good_value(app):
    a, mod, out = app
    a.v_sil_min.set("7")
    a.v_sil_min.set("7x")
    assert a.cfg["silence_minutes"] == 7.0
    a.v_auto_time.set(False)
    a._auto_changed()
    assert a.stop_at.cget("text") == ""


# ---------------------------------------------------------------- 0A Start on Sound

def test_start_on_sound_waits_then_records_from_the_sound(app, monkeypatch):
    a, mod, out = app
    src = FakeSource("system", 44100, 2, 440, level=0.0, name="Call [Loopback]")
    use_sources(monkeypatch, src)
    a.start_on_sound()
    assert pump(a, lambda: a.state == "waiting")
    assert "Waiting for sound" in a.status.cget("text") and a.title().startswith("◌ WAITING")
    assert str(a.b_rec.cget("state")) == "normal" and str(a.b_wait.cget("state")) == "disabled"
    assert str(a.b_pause.cget("state")) == "disabled" and str(a.b_stop.cget("state")) == "normal"
    time.sleep(1.5)
    a.update()
    assert a.state == "waiting" and a.seconds == 0.0                  # nothing written while it is quiet
    src.level = 0.3                                                  # the call starts
    assert pump(a, lambda: a.state == "recording")
    assert pump(a, lambda: a.seconds >= 1.5)
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle" and a.rows)
    assert len(mp3s(out)) == 1 and a.rows[0]["seconds"] >= 1.0       # the lead-in second is in the file
    assert not a.shown


def test_record_now_while_waiting_starts_at_once(app, monkeypatch):
    a, mod, out = app
    use_sources(monkeypatch, FakeSource("system", 44100, 2, 440, level=0.0, name="Call [Loopback]"))
    a.start_on_sound()
    assert pump(a, lambda: a.state == "waiting")
    a.record_now()
    assert pump(a, lambda: a.state == "recording")
    a.v_auto_sil.set(False)                                          # quiet source: no auto stop in this test
    time.sleep(1.0)
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle" and a.rows)


# ---------------------------------------------------------------- 1 the Windows default output changes

def test_output_device_change_is_reported_and_cleared(app, monkeypatch):
    a, mod, out = app
    now = [("{id-speakers}", "Speakers (Realtek)")]
    monkeypatch.setattr(mod.winsys, "default_output_device", lambda: now[0])
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    assert a._out_dev_start == ("{id-speakers}", "Speakers (Realtek)")
    a._check_output_device()
    assert "Windows is now playing" not in a.warnlbl.cget("text")
    now[0] = ("{id-headset}", "Headset (Jabra)")                     # Bluetooth connected mid-call
    a._check_output_device()
    assert "Windows is now playing on Headset (Jabra): stop and record again" in a.warnlbl.cget("text")
    now[0] = ("{id-speakers}", "Speakers (Realtek)")
    a._check_output_device()
    assert "Windows is now playing" not in a.warnlbl.cget("text")
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle")


def test_a_chosen_output_device_is_not_watched(app, monkeypatch):
    a, mod, out = app
    monkeypatch.setattr(mod.winsys, "default_output_device", lambda: pytest.fail("not asked"))
    a.cfg["system_device"] = "Speakers (Realtek)"
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    a._check_output_device()
    assert a._out_dev_start is None
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle")


@pytest.mark.skipif(os.name != "nt", reason="Windows Core Audio")
def test_core_audio_reader_answers_on_this_pc():
    import tinyrecorder_winsys as winsys
    found = winsys.default_output_device()                           # read-only; None on a PC without output
    assert found is None or (isinstance(found[0], str) and found[0] and isinstance(found[1], str))


# ---------------------------------------------------------------- 2 the computer audio is silent

def test_silent_computer_audio_warns_after_three_minutes(app):
    a, mod, out = app
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    a._sys_zero_since = 0.0
    a._check_quiet_system(0.0, 120.0)
    assert "No sound from Computer audio" not in a.warnlbl.cget("text")
    a._check_quiet_system(0.0, 181.0)
    assert "No sound from Computer audio for 3 minutes: check the device." in a.warnlbl.cget("text")
    a._check_quiet_system(0.2, 182.0)                                # sound again: the warning goes
    assert "No sound from Computer audio" not in a.warnlbl.cget("text")
    a.v_sys.set(False)                                               # an unticked channel is not watched
    a._check_quiet_system(0.0, 500.0)
    assert "No sound from Computer audio" not in a.warnlbl.cget("text")
    a.v_sys.set(True)
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle")


# ---------------------------------------------------------------- 3 Ctrl+Alt+P

def test_pause_hotkey_pauses_and_resumes(app):
    a, mod, out = app
    a._handle("hotkey_pause")
    assert a.state == "idle"                                         # nothing to pause
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    a._handle("hotkey_pause")
    assert a.state == "paused"
    a._handle("hotkey_pause")
    assert a.state == "recording"
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle")


def test_pause_hotkey_taken_is_said(app, monkeypatch):
    a, mod, out = app

    class PauseRefused:
        ok, pause_ok = True, False

        def __init__(self, q):
            pass

        def start(self):
            return True

        def stop(self):
            pass
    monkeypatch.setattr(mod.winsys, "Hotkey", PauseRefused)
    a.cfg["hotkey"] = True
    a._start_hotkey()
    assert "Ctrl+Alt+P is used by another program" in a.warnlbl.cget("text")
    assert a._ready_text().endswith("pause with Ctrl+Alt+P")


@pytest.mark.parametrize("how", ["stop", "hotkey", "close"])
def test_cancel_while_waiting_leaves_nothing(tmp_path, monkeypatch, how):
    a, mod, out = make_app(tmp_path, monkeypatch)
    asked = []
    monkeypatch.setattr(mod.messagebox, "askyesno", lambda *x, **k: asked.append(x) or True)
    use_sources(monkeypatch, FakeSource("system", 44100, 2, 440, level=0.0, name="Call [Loopback]"))
    a.start_on_sound()
    assert pump(a, lambda: a.state == "waiting")
    time.sleep(0.5)
    if how == "stop":
        a.toggle_record()
    elif how == "hotkey":
        a._handle("hotkey")
    else:
        a.on_close()                                                  # no "recording in progress?" question
    end = time.time() + 8
    while time.time() < end:
        try:
            a.update()
        except Exception:                                            # destroyed by the close
            break
        if how != "close" and a.state == "idle":
            break
        time.sleep(0.03)
    assert not asked
    assert not [f for f in (os.listdir(out) if os.path.isdir(out) else []) if f.endswith((".mp3", ".part"))]
    if how != "close":
        assert a.state == "idle"
        a._destroy()
