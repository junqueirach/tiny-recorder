"""v0.1.4: the fixes from the sanity check of v0.1.3 (B1–B15)."""

import datetime
import os
import sys
import time

import pytest

import tinyrecorder_audio as au
import tinyrecorder_core as core
import tinyrecorder_winsys as winsys
from conftest import FakeSource
from test_core import _tiny_mp3
from test_v014_ui import make_app, pump


@pytest.fixture
def app(tmp_path, monkeypatch):
    a, mod, out = make_app(tmp_path, monkeypatch)
    yield a, mod, out
    try:
        a._destroy()
    except Exception:
        pass


def record_one(a, title=""):
    if title:
        a.tags.set(core.Tags("2026-10-20", title))
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    time.sleep(1.1)
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle" and a.rows and not a.select_after)


# ---------------------------------------------------------------- B1 the second start finds the main window only

@pytest.mark.parametrize("title, cls, ok", [
    ("Tiny Recorder 0.1.4", "TkTopLevel", True),
    ("● REC 00:12:03  ·  Tiny Recorder", "TkTopLevel", True),
    ("⏸ PAUSADO 00:00:09  ·  Tiny Recorder", "TkTopLevel", True),
    ("Tiny Recorder", "CabinetWClass", False),                       # Explorer on Documents\Tiny Recorder
    ("Tiny Recorder 2", "CabinetWClass", False),
    ("Help — Tiny Recorder", "TkTopLevel", False),
    ("About Tiny Recorder", "TkTopLevel", False),
    ("junqueirach/tiny-recorder: Tiny Recorder - Google Chrome", "Chrome_WidgetWin_1", False),
])
def test_only_the_main_window_is_brought_to_the_front(title, cls, ok):
    assert winsys.is_main_window(title, cls) is ok


# ---------------------------------------------------------------- B2 no Recycle Bin: ask before deleting for good

@pytest.mark.skipif(sys.platform != "win32", reason="Windows drive types")
def test_recycle_bin_exists_only_on_fixed_drives(tmp_path):
    assert winsys.has_recycle_bin(str(tmp_path)) is True             # the temp folder is on a fixed drive
    assert winsys.has_recycle_bin(r"\\server\share\rec.mp3") is False


def test_delete_without_recycle_bin_asks_and_deletes_for_good(app, monkeypatch):
    a, mod, out = app
    record_one(a)
    p = a._selected()
    monkeypatch.setattr(mod.winsys, "has_recycle_bin", lambda path: False)
    monkeypatch.setattr(mod.winsys, "send_to_recycle_bin", lambda path: pytest.fail("no Recycle Bin here"))
    asked = []
    monkeypatch.setattr(mod.messagebox, "askyesno", lambda title, msg, **k: (asked.append(msg), False)[1])
    a.delete_selected()
    assert os.path.exists(p) and "permanently" in asked[0] and "Recycle Bin?" not in asked[0]
    monkeypatch.setattr(mod.messagebox, "askyesno", lambda *x, **k: True)
    a.delete_selected()
    assert not os.path.exists(p)
    assert pump(a, lambda: not a.rows and a.detail.cget("text").startswith("Deleted: "))


# ---------------------------------------------------------------- B3 / B4 rename and file time

def test_case_only_title_change_renames_the_file(tmp_path):
    folder = tmp_path / "rec"
    folder.mkdir()
    p = folder / "2026-10-20 - meeting.mp3"
    _tiny_mp3(str(p))
    new, err = core.retag_and_rename(str(p), core.Tags("2026-10-20", "Meeting"))
    assert err is None and os.listdir(folder) == ["2026-10-20 - Meeting.mp3"]
    assert os.path.basename(new) == "2026-10-20 - Meeting.mp3"


def test_edit_keeps_the_file_time(tmp_path):
    p = tmp_path / "2026-09-01 - Old.mp3"
    _tiny_mp3(str(p))
    old = time.time() - 30 * 86400
    os.utime(p, (old, old))
    new, _err = core.retag_and_rename(str(p), core.Tags("2026-09-01", "Old one", "Ana"))
    assert abs(os.path.getmtime(new) - old) < 2 and core.read_tags(new).people == "Ana"


# ---------------------------------------------------------------- B5 the new / renamed file is selected

def test_saved_and_renamed_files_are_selected(app):
    a, mod, out = app
    record_one(a, "First")
    time.sleep(1.1)
    record_one(a, "Second")
    a.tree.selection_set(str(next(i for i, r in enumerate(a.rows) if "First" in r["name"])))
    time.sleep(1.1)
    record_one(a, "Third")
    assert a._selected().endswith("2026-10-20 - Third.mp3")
    first = next(r["path"] for r in a.rows if "First" in r["name"])
    a.tree.selection_set(str(next(i for i, r in enumerate(a.rows) if r["path"] == first)))
    d = mod.EditDialog(a, a, first)
    d.tf.set(core.Tags("2026-10-20", "First renamed"))
    d._save()
    assert pump(a, lambda: a._selected() and a._selected().endswith("2026-10-20 - First renamed.mp3"))
    assert a.rows[-1]["name"] == "2026-10-20 - First renamed.mp3"        # still the oldest (B4): order unchanged


# ---------------------------------------------------------------- B6 the date box follows the calendar

def test_untouched_date_becomes_today_on_record(app):
    a, mod, out = app
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    a.tags.auto_date = yesterday
    a.tags.vars["date"].set(yesterday)                               # the app was opened yesterday
    a.tags.refresh_date()
    assert a.tags.get().date == core.today_iso()
    a.tags.vars["date"].set("2026-01-05")                            # typed by the user: kept
    a.tags.refresh_date()
    assert a.tags.get().date == "2026-01-05"


# ---------------------------------------------------------------- B7 the hotkey while Settings is open

def test_hotkey_with_settings_open_cancels_settings(app):
    a, mod, out = app
    a.show_settings()
    s = a._settings
    s.v_lang.set("Español")                                          # an unsaved change
    a._handle("hotkey")
    assert not s.winfo_exists() and a.state == "starting"
    assert core.load_config().get("ui_language", "") == "" and "Record" in a.b_rec.cget("text")
    assert pump(a, lambda: a.state == "recording")
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle")


# ---------------------------------------------------------------- B8 a saved device that is gone

class _FakePA:
    def __init__(self, loops, default_out):
        self.loops, self.default_out = loops, default_out

    def get_loopback_device_info_generator(self):
        return iter([{"name": n, "index": i, "defaultSampleRate": 48000, "maxInputChannels": 2}
                     for i, n in enumerate(self.loops)])

    def get_device_info_by_index(self, i):
        return {"name": self.default_out}


def test_missing_computer_audio_device_falls_back_to_the_default(monkeypatch):
    monkeypatch.setattr(au.DeviceSource, "start", lambda self: None)
    p = _FakePA(["Speakers (Realtek) [Loopback]"], "Speakers (Realtek)")
    s = au._open_system(None, p, {"defaultOutputDevice": 0}, "Headset (gone)")
    assert s.name == "Speakers (Realtek) [Loopback]"
    s = au._open_system(None, p, {"defaultOutputDevice": 0}, "")
    assert s.name == "Speakers (Realtek) [Loopback]"


def test_window_says_which_device_replaced_the_chosen_one(app):
    a, mod, out = app
    a.cfg["system_device"] = "Headset (gone)"
    a.cfg["mic_device"] = "Fake Mic"
    warns = a._fallback_warnings(["Fake Speakers [Loopback]", "Fake Mic"])
    assert warns == ["Headset (gone) was not found: the Windows default is used."]


# ---------------------------------------------------------------- B9 a date that is not understood

def test_wrong_date_is_shown_in_the_preview(app):
    a, mod, out = app
    a.tags.vars["date"].set("31.02.2026")
    assert "date not understood, today is used" in a.tags.preview.cget("text")
    a.tags.vars["date"].set("20/10/2026")
    assert "not understood" not in a.tags.preview.cget("text") and "2026-10-20" in a.tags.preview.cget("text")


# ---------------------------------------------------------------- B10 the hotkey warning follows the hotkey

def test_hotkey_warning_follows_the_hotkey_state(app, monkeypatch):
    a, mod, out = app

    class Refused:
        ok = False

        def __init__(self, q):
            pass

        def start(self):
            return False

        def stop(self):
            pass
    monkeypatch.setattr(mod.winsys, "Hotkey", Refused)
    a.cfg["hotkey"] = True
    a._start_hotkey()
    taken = "Ctrl+Alt+R is used by another program"
    assert taken in a.warnlbl.cget("text")
    record_one(a)
    assert taken in a.warnlbl.cget("text")                            # back after the recording
    a.cfg["ui_language"] = "es"
    a.settings_saved(True)                                           # rebuilt in Spanish: still shown
    assert "Ctrl+Alt+R lo usa otro programa" in a.warnlbl.cget("text")
    a.cfg["hotkey"] = False
    a.settings_saved(False)
    assert a.warnlbl.cget("text") == ""


# ---------------------------------------------------------------- B11 one Help window

def test_f1_reuses_the_open_help_window(app):
    a, mod, out = app
    a.show_help()
    a.show_help()
    a.update()
    assert len([w for w in a.winfo_children() if isinstance(w, mod.HelpDialog)]) == 1


# ---------------------------------------------------------------- B12 a window on a monitor that is gone

def test_saved_position_off_screen_is_centred(app, monkeypatch):
    a, mod, out = app
    monkeypatch.setattr(mod.winsys, "on_a_monitor", lambda x, y: False)
    a.work, a.work_h = (0, 0, 1920, 1040), 1040
    a._restore_geometry("880x900+3000+200")
    a.update_idletasks()
    assert a.winfo_x() < 1920 and a.winfo_y() < 1040
    monkeypatch.setattr(mod.winsys, "on_a_monitor", lambda x, y: True)
    a._restore_geometry("880x900+100+50")
    a.update_idletasks()
    assert (a.winfo_x(), a.winfo_y()) == (100, 50) or a.geometry().endswith("+100+50")


# ---------------------------------------------------------------- B13 a file vanishing while the list loads

def test_list_skips_a_file_that_vanished(tmp_path, monkeypatch):
    good = tmp_path / "2026-10-20 - Good.mp3"
    _tiny_mp3(str(good))
    real_scandir = os.scandir

    class Gone:
        name, path = "2026-10-21 - Gone.mp3", str(tmp_path / "2026-10-21 - Gone.mp3")

        def is_file(self):
            return True

        def stat(self):
            raise FileNotFoundError(self.path)

    class Ctx:
        def __init__(self, folder):
            self.items = list(real_scandir(folder)) + [Gone()]

        def __enter__(self):
            return iter(self.items)

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(core.os, "scandir", Ctx)
    rows = core.list_recordings(str(tmp_path))
    assert [r["name"] for r in rows] == ["2026-10-20 - Good.mp3"]


# ---------------------------------------------------------------- B14 a short screen (1366 x 768)

def test_short_screen_gets_a_compact_window_that_fits(tmp_path, monkeypatch):
    monkeypatch.setattr(winsys, "work_area", lambda: (0, 0, 1366, 728))
    a, mod, out = make_app(tmp_path, monkeypatch)
    try:
        assert a.compact
        a.update_idletasks()
        need = a._root_frame.winfo_reqheight()
        assert need <= 728 - 60, need                                  # everything, 4 list rows included, fits
        assert int(a.wm_minsize()[1]) == need
    finally:
        a._destroy()


def test_normal_screen_keeps_four_list_rows_at_the_minimum(app):
    a, mod, out = app
    a.update_idletasks()
    assert int(a.wm_minsize()[1]) == min(a._root_frame.winfo_reqheight(), (a.work_h - 60) if a.work_h else 10 ** 6)


# ---------------------------------------------------------------- B15 warnings of a recording stay

def test_device_warning_stays_during_the_recording(app, monkeypatch):
    a, mod, out = app
    sys_only = [FakeSource("system", 44100, 2, 440, name="Fake Speakers [Loopback]")]
    monkeypatch.setattr(au, "open_sources", lambda *x, **k: (None, sys_only, ["microphone: blocked by Windows"]))
    a.toggle_record()
    assert pump(a, lambda: a.state == "recording")
    time.sleep(0.8)
    a.update()
    assert "Not available: Microphone: blocked by Windows" in a.warnlbl.cget("text")
    a.toggle_record()
    assert pump(a, lambda: a.state == "idle")
    assert a.warnlbl.cget("text") == ""
