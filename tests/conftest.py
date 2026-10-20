"""Test setup: every test runs against a temp settings folder (TINYRECORDER_HOME), never the real one."""

import importlib.util
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import tinyrecorder_audio as au                                              # noqa: E402


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("TINYRECORDER_HOME", str(home))
    return home


class FakeSource(au.Source):
    """A sine tone standing in for a device (no sound card needed)."""

    def __init__(self, kind, rate, channels, freq, level=0.4, name=None):
        self.kind, self.rate, self.channels, self.freq, self.level = kind, rate, channels, freq, level
        self.name = name or (kind + "-fake")
        self.t = 0
        self.stopped = False

    def pull(self, n):
        t = (np.arange(n) + self.t) / self.rate
        self.t += n
        x = (self.level * np.sin(2 * np.pi * self.freq * t)).astype(np.float32)
        return np.repeat(x[:, None], self.channels, axis=1)

    def stop(self):
        self.stopped = True


@pytest.fixture
def fake_sources():
    return [FakeSource("system", 44100, 2, 440), FakeSource("mic", 48000, 1, 880)]


def load_app_module():
    """The window module is loaded by path (tinyrecorder.py), as the archived versions have dots in their names."""
    spec = importlib.util.spec_from_file_location("tinyrecorder_app", os.path.join(ROOT, "tinyrecorder.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeMci:
    """Stands in for the Windows MCI: records the commands, plays nothing, and lets a test end the 'playback'."""

    def __init__(self, length_ms=3000):
        self.length_ms = length_ms
        self.log = []
        self.path = ""
        self.is_open = False
        self.playing = False

    def send(self, command):
        self.log.append(command)
        if command.startswith("open "):
            path = command.split('"')[1]
            if not os.path.exists(path):
                return 263, "The specified device is not open or is not recognized by MCI."
            self.path, self.is_open = path, True
            return 0, ""
        if command.startswith("status ") and command.endswith(" length"):
            return 0, str(self.length_ms)
        if command.startswith("status ") and command.endswith(" mode"):
            return 0, "playing" if self.playing else "stopped"
        if command.startswith("status ") and command.endswith(" position"):
            return 0, "1500" if self.playing else str(self.length_ms)
        if command.startswith("play "):
            self.playing = True
        elif command.startswith(("stop ", "close ")):
            self.playing = False
            if command.startswith("close "):
                self.is_open = False
        return 0, ""

    def finish(self):
        self.playing = False
