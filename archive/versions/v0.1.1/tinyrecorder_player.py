"""
Tiny Recorder — the built-in player (v0.1.1): Play and Stop for a saved recording.

Uses the Windows Media Control Interface (winmm, MCI) that ships with Windows: no extra package, no decoder to
install, nothing running in the background. One file plays at a time. The MCI call is injectable, so tests run the
whole logic with a fake and never make a sound.
"""

import os

IS_WIN = os.name == "nt"
ALIAS = "tinyrecorder_play"


class PlayerError(Exception):
    pass


def _mci_send(command):
    """Send one MCI command. Returns (error_code, text)."""
    import ctypes
    winmm = ctypes.windll.winmm
    buf = ctypes.create_unicode_buffer(256)
    code = winmm.mciSendStringW(command, buf, 255, 0)
    if code:
        err = ctypes.create_unicode_buffer(256)
        winmm.mciGetErrorStringW(code, err, 255)
        return code, err.value
    return 0, buf.value


class Player:
    def __init__(self, send=None):
        self._send = send or _mci_send
        self.path = ""
        self.length_ms = 0
        self._open = False

    # ---- helpers
    def _cmd(self, command, check=True):
        code, text = self._send(command)
        if code and check:
            raise PlayerError(text or ("MCI error %d" % code))
        return code, text

    def _status(self, what):
        code, text = self._cmd("status %s %s" % (ALIAS, what), check=False)
        return "" if code else text.strip()

    # ---- control
    def play(self, path, volume=None):
        """Start playing path from the beginning (anything playing is stopped first). volume: 0 to 1000, or None."""
        self.stop()
        if not os.path.exists(path):
            raise PlayerError("file not found: %s" % path)
        self._cmd('open "%s" type mpegvideo alias %s' % (path, ALIAS))
        self._open = True
        try:
            self._cmd("set %s time format milliseconds" % ALIAS)
            if volume is not None:
                self._cmd("setaudio %s volume to %d" % (ALIAS, int(volume)), check=False)
            self.length_ms = int(self._status("length") or 0)
            self._cmd("play %s" % ALIAS)
        except PlayerError:
            self.stop()
            raise
        self.path = path

    def stop(self):
        """Stop and release the file (so it can be renamed). Safe to call when nothing plays."""
        if self._open:
            self._cmd("stop %s" % ALIAS, check=False)
            self._cmd("close %s" % ALIAS, check=False)
        self._open = False
        self.path = ""
        self.length_ms = 0

    def mode(self):
        """'playing', 'stopped', 'paused', or '' when nothing is open."""
        return self._status("mode") if self._open else ""

    def position_ms(self):
        if not self._open:
            return 0
        try:
            return int(self._status("position") or 0)
        except ValueError:
            return 0

    def is_playing(self):
        return self._open and self.mode() == "playing"

    def finished(self):
        """True once an open file has played to its end (the caller then calls stop())."""
        return self._open and self.mode() in ("stopped", "")
