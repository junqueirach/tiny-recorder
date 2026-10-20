"""Switching the computer audio and the microphone off and on during a recording."""

import queue
import time

import numpy as np

import tinyrecorder_audio as au
import tinyrecorder_core as core
from conftest import FakeSource


def _events(ev):
    items = []
    while not ev.empty():
        items.append(ev.get())
    return items


def _peaks(events, after_seconds=0.0):
    lv = [e for e in events if e[0] == "levels" and e[3] >= after_seconds]
    return (max([l[1] for l in lv] or [0.0]), max([l[2] for l in lv] or [0.0]))


def test_lane_disabled_is_silent_but_keeps_the_source_in_step():
    src = FakeSource("mic", 48000, 1, 440)
    lane = au.Lane(src, 44100, 1, 1.0)
    assert float(np.max(np.abs(lane.get(4410)))) > 0.3
    lane.enabled = False
    block = lane.get(4410)
    assert block.shape == (4410, 1) and float(np.max(np.abs(block))) == 0.0 and lane.peak == 0.0
    lane.enabled = True
    assert float(np.max(np.abs(lane.get(4410)))) > 0.3
    assert abs(lane.consumed - 3 * 4800) <= 1                      # the disabled block was still consumed


def test_switch_a_source_off_and_on_during_a_recording(tmp_path, fake_sources):
    ev = queue.Queue()
    part = str(tmp_path / "sw.mp3.part")
    rec = au.Recorder(part, core.PRESETS["voice"], ev, lambda: (None, fake_sources, []))
    rec.start()
    time.sleep(1.0)
    rec.set_enabled("mic", False)
    time.sleep(0.4)
    _events(ev)                                                    # forget what happened before the switch
    time.sleep(1.0)
    off = _events(ev)
    rec.set_enabled("mic", True)
    time.sleep(0.6)
    _events(ev)
    time.sleep(0.8)
    on = _events(ev)
    rec.stop()
    sp, mp = _peaks(off)
    assert sp > 0.3 and mp == 0.0                                  # the computer audio goes on, the microphone is off
    sp, mp = _peaks(on)
    assert sp > 0.3 and mp > 0.3                                   # and back on at once
    assert 3.0 < core.audio_seconds(part) < 4.4                    # the file kept its timeline throughout


def test_both_switched_off_records_silence_not_a_gap(tmp_path, fake_sources):
    ev = queue.Queue()
    part = str(tmp_path / "b.mp3.part")
    rec = au.Recorder(part, core.PRESETS["voice"], ev, lambda: (None, fake_sources, []))
    rec.start()
    time.sleep(0.5)
    rec.set_enabled("system", False)
    rec.set_enabled("mic", False)
    time.sleep(1.5)
    rec.stop()
    assert 1.6 < core.audio_seconds(part) < 2.4
    assert _peaks(_events(ev), 1.0) == (0.0, 0.0)


def test_a_source_that_was_not_open_is_opened_when_switched_on(tmp_path):
    ev = queue.Queue()
    part = str(tmp_path / "late.mp3.part")
    sys_only = [FakeSource("system", 44100, 2, 440)]
    mic = FakeSource("mic", 48000, 1, 880)
    opened = []

    def opener_one(pa_inst, kind):
        opened.append(kind)
        time.sleep(0.3)                                           # a slow device
        return mic
    rec = au.Recorder(part, core.PRESETS["voice"], ev, lambda: (None, sys_only, []), opener_one=opener_one)
    rec.start()
    time.sleep(0.8)
    assert _peaks(_events(ev))[1] == 0.0
    rec.set_enabled("mic", True)
    time.sleep(1.2)
    late = _events(ev)
    rec.stop()
    assert opened == ["mic"] and _peaks(late, 1.4)[1] > 0.3 and mic.stopped
    assert 1.6 < core.audio_seconds(part) < 2.6


def test_a_source_that_cannot_be_opened_reports_and_the_recording_goes_on(tmp_path):
    ev = queue.Queue()
    part = str(tmp_path / "fail.mp3.part")

    def opener_one(pa_inst, kind):
        raise OSError("blocked by privacy settings")
    rec = au.Recorder(part, core.PRESETS["voice"], ev, lambda: (None, [FakeSource("system", 44100, 2, 440)], []),
                      opener_one=opener_one)
    rec.start()
    time.sleep(0.4)
    rec.set_enabled("mic", True)
    time.sleep(1.0)
    rec.stop()
    items = _events(ev)
    fails = [e for e in items if e[0] == "sourcefail"]
    assert len(fails) == 1 and fails[0][1] == "mic" and "blocked" in fails[0][2]
    assert items[-1][0] == "stopped" and core.audio_seconds(part) > 1.0


def test_switched_on_then_off_before_it_opened_closes_the_device(tmp_path):
    ev = queue.Queue()
    part = str(tmp_path / "quick.mp3.part")
    mic = FakeSource("mic", 48000, 1, 880)

    def opener_one(pa_inst, kind):
        time.sleep(0.6)
        return mic
    rec = au.Recorder(part, core.PRESETS["voice"], ev, lambda: (None, [FakeSource("system", 44100, 2, 440)], []),
                      opener_one=opener_one)
    rec.start()
    time.sleep(0.3)
    rec.set_enabled("mic", True)
    time.sleep(0.3)
    rec.set_enabled("mic", False)
    time.sleep(1.2)
    rec.stop()
    assert mic.stopped and _peaks(_events(ev))[1] == 0.0
