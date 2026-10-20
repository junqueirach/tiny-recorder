import os
import queue
import time

import numpy as np

import tinyrecorder_audio as au
import tinyrecorder_core as core
from conftest import FakeSource


def run_recorder(tmp_path, sources, preset="voice", seconds=2.0, pause_at=None, **kw):
    ev = queue.Queue()
    part = str(tmp_path / ("t" + core.PART_SUFFIX))
    rec = au.Recorder(part, core.PRESETS[preset], ev, lambda: (None, sources, []), **kw)
    rec.start()
    if pause_at is not None:
        time.sleep(pause_at)
        rec.pause()
        time.sleep(1.0)
        rec.resume()
        time.sleep(max(0.2, seconds - pause_at))
    else:
        time.sleep(seconds)
    rec.stop()
    events = []
    while not ev.empty():
        events.append(ev.get())
    return part, events, rec


def test_two_sources_different_rates_make_one_valid_mp3(tmp_path, fake_sources):
    part, events, rec = run_recorder(tmp_path, fake_sources, "voice", 2.0)
    kinds = [e[0] for e in events]
    assert kinds[0] == "started" and kinds[-1] == "stopped" and "levels" in kinds
    assert events[0][1] == 44100                                  # the computer audio keeps its own rate
    dur = core.audio_seconds(part)
    assert 1.7 < dur < 2.4
    assert all(s.stopped for s in fake_sources)
    levels = [e for e in events if e[0] == "levels"]
    assert max(l[1] for l in levels) > 0.3 and max(l[2] for l in levels) > 0.3     # both meters saw their tone


def test_stereo_presets_and_info(tmp_path, fake_sources):
    from mutagen.mp3 import MP3
    part, _events, _rec = run_recorder(tmp_path, fake_sources, "standard", 1.5)
    info = MP3(part).info
    assert info.channels in (1, 2) and info.bitrate == 128000
    assert 1.2 < info.length < 2.0


def test_silent_source_does_not_stall_or_drift(tmp_path):
    class Silent(FakeSource):
        def pull(self, n):                                        # loopback while nothing plays: no data at all
            return np.zeros((n, self.channels), np.float32)
    srcs = [Silent("system", 48000, 2, 0), FakeSource("mic", 48000, 1, 600)]
    part, events, _rec = run_recorder(tmp_path, srcs, "voice", 2.0)
    assert 1.7 < core.audio_seconds(part) < 2.4
    lv = [e for e in events if e[0] == "levels"]
    assert max(l[1] for l in lv) == 0.0 and max(l[2] for l in lv) > 0.3


def test_pause_leaves_a_gap_out_of_the_file(tmp_path, fake_sources):
    part, events, rec = run_recorder(tmp_path, fake_sources, "voice", 2.0, pause_at=0.8)
    dur = core.audio_seconds(part)
    assert dur < 2.6                                              # about 2.0 s of 3.0 s on the clock
    assert 1.5 < dur


def test_no_source_reports_an_error_and_no_crash(tmp_path):
    ev = queue.Queue()
    rec = au.Recorder(str(tmp_path / "e.mp3.part"), core.PRESETS["voice"], ev, lambda: (None, [], ["microphone: blocked"]))
    rec.start()
    rec.stop()
    items = []
    while not ev.empty():
        items.append(ev.get())
    assert items[0][0] == "error" and "blocked" in items[0][1] and items[-1][0] == "stopped"


def test_low_disk_stops_and_keeps_the_audio(tmp_path, fake_sources, monkeypatch):
    monkeypatch.setattr(au, "TICK", 0.05)
    ev = queue.Queue()
    part = str(tmp_path / "l.mp3.part")
    calls = {"n": 0}

    def free():
        calls["n"] += 1
        return 1024
    rec = au.Recorder(part, core.PRESETS["voice"], ev, lambda: (None, fake_sources, []), free_check=free)
    monkeypatch.setattr(au.time, "monotonic", _fast_clock())
    rec.start()
    deadline = time.time() + 20                                   # generous: the machine may be busy
    while rec._thread.is_alive() and time.time() < deadline:
        time.sleep(0.05)
    items = []
    while not ev.empty():
        items.append(ev.get())
    assert any(e[0] == "lowdisk" for e in items) and items[-1][0] == "stopped"
    assert os.path.getsize(part) > 0


def _fast_clock():
    """A clock that runs 40 times faster than the real one (so the 20-second disk check happens at once)."""
    real = time.monotonic
    t0 = real()
    return lambda: t0 + (real() - t0) * 40


def test_resample_layout_and_rate_helpers():
    block = np.linspace(-1, 1, 480, dtype=np.float32)[:, None]
    out = au.resample(np.repeat(block, 2, axis=1), 441)
    assert out.shape == (441, 2) and abs(out[0, 0] + 1) < 1e-6 and abs(out[-1, 0] - 1) < 1e-6
    assert au.to_layout(np.ones((4, 2), np.float32), 1).shape == (4, 1)
    assert au.to_layout(np.ones((4, 1), np.float32), 2).shape == (4, 2)
    assert au.to_layout(np.ones((4, 4), np.float32), 2).shape == (4, 2)
    srcs = [FakeSource("mic", 44100, 1, 1), FakeSource("system", 96000, 2, 1)]
    assert au.choose_out_rate(srcs) == 44100                       # no system MP3 rate: falls to the mic's
    assert au.choose_out_rate([FakeSource("system", 96000, 2, 1)]) == 48000
    assert au.loopback_label("Speakers (Realtek) [Loopback]") == "Speakers (Realtek)"


def test_lane_keeps_rate_without_drift():
    src = FakeSource("mic", 48000, 1, 440)
    lane = au.Lane(src, 44100, 1, 1.0)
    total_out = 0
    for _i in range(100):
        total_out += len(lane.get(4410))
    assert total_out == 441000
    assert abs(lane.consumed - 480000) <= 1                        # 10 s at 48 kHz, to the frame


def test_stop_before_any_audio_is_clean(tmp_path, fake_sources):
    ev = queue.Queue()
    part = str(tmp_path / "i.mp3.part")
    rec = au.Recorder(part, core.PRESETS["voice"], ev, lambda: (None, fake_sources, []))
    rec.start()
    rec.stop()                                                     # LAME cannot flush before it has encoded anything
    items = []
    while not ev.empty():
        items.append(ev.get())
    assert [e[0] for e in items if e[0] != "levels"] == ["started", "stopped"]
