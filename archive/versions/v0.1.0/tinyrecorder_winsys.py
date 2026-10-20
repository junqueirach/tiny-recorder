"""
Tiny Recorder — small Windows helpers (v0.1.0). No Tk here: functions take window handles (ints).

single instance · dark title bar, taskbar identity, DPI awareness · global hotkey · show a file in Explorer.
"""

import hashlib
import os
import queue
import subprocess
import threading

IS_WIN = os.name == "nt"


# ------------------------------------------------------------------ single instance

class SingleInstance:
    """A named mutex. The name depends on the data folder, so a test copy with TINYRECORDER_HOME never blocks the
    real app (and vice versa)."""

    def __init__(self, data_folder):
        key = hashlib.sha1(os.path.normcase(os.path.abspath(data_folder)).encode("utf-8")).hexdigest()[:12]
        self.name = "Local\\TinyRecorder.SingleInstance." + key
        self.handle = None
        self.already = False
        if IS_WIN:
            import ctypes
            k32 = ctypes.windll.kernel32
            k32.CreateMutexW.restype = ctypes.c_void_p
            self.handle = k32.CreateMutexW(None, False, self.name)
            self.already = k32.GetLastError() == 183              # ERROR_ALREADY_EXISTS

    def release(self):
        if IS_WIN and self.handle:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(self.handle))
            self.handle = None


def bring_to_front(title_part="Tiny Recorder"):
    """Show the window of the copy that is already running (its title contains the app name)."""
    if not IS_WIN:
        return False
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if title_part in buf.value and user32.IsWindowVisible(hwnd):
                found.append(hwnd)
        return True
    user32.EnumWindows(cb, 0)
    for hwnd in found:
        user32.ShowWindow(hwnd, 9)                                  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        return True
    return False


# ------------------------------------------------------------------ window look

def dpi_aware():
    if not IS_WIN:
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def set_app_id(app_id):
    if not IS_WIN:
        return
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def dark_title_bar(hwnd, caption="#11111b"):
    """Dark title bar (Windows 10 1809+; the caption colour needs Windows 11)."""
    if not IS_WIN or not hwnd:
        return
    import ctypes
    dwm = ctypes.windll.dwmapi
    on = ctypes.c_int(1)
    for attr in (20, 19):                                          # DWMWA_USE_IMMERSIVE_DARK_MODE (new, old)
        if dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on), ctypes.sizeof(on)) == 0:
            break
    try:
        r, g, b = int(caption[1:3], 16), int(caption[3:5], 16), int(caption[5:7], 16)
        color = ctypes.c_int(r | (g << 8) | (b << 16))
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), ctypes.sizeof(color))     # DWMWA_CAPTION_COLOR
    except Exception:
        pass


def hwnd_of(tk_widget_id):
    """Top-level window handle for a Tk winfo_id()."""
    if not IS_WIN:
        return 0
    import ctypes
    return ctypes.windll.user32.GetParent(tk_widget_id) or tk_widget_id


# ------------------------------------------------------------------ files

def show_in_explorer(path):
    """Open Explorer with the file selected (or the folder, when path is a folder)."""
    if not IS_WIN:
        return
    path = os.path.normpath(path)
    try:
        if os.path.isdir(path):
            os.startfile(path)                                       # noqa: S606
        else:
            subprocess.Popen(["explorer", "/select,", path])         # noqa: S603,S607
    except Exception:
        pass


def free_bytes(folder):
    """Free space of the drive that holds the folder (None when unknown)."""
    try:
        import shutil
        return shutil.disk_usage(folder).free
    except Exception:
        return None


# ------------------------------------------------------------------ global hotkey

class Hotkey:
    """A system-wide hotkey (default Ctrl+Alt+R). A helper thread owns the registration and the message loop and
    puts "hotkey" on the queue; the Tk thread drains the queue. ok is False when Windows refused the combination
    (another program already uses it)."""

    MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x4000
    WM_HOTKEY, WM_QUIT = 0x312, 0x12

    def __init__(self, q, vk=ord("R"), mods=None):
        self.q = q
        self.vk = vk
        self.mods = mods if mods is not None else (self.MOD_CONTROL | self.MOD_ALT | self.MOD_NOREPEAT)
        self.ok = False
        self._tid = None
        self._thread = None
        self._ready = threading.Event()

    def start(self):
        if not IS_WIN:
            return False
        self._thread = threading.Thread(target=self._run, name="hotkey", daemon=True)
        self._thread.start()
        self._ready.wait(2.0)
        return self.ok

    def _run(self):
        import ctypes
        from ctypes import wintypes
        user32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
        self._tid = k32.GetCurrentThreadId()
        self.ok = bool(user32.RegisterHotKey(None, 1, self.mods, self.vk))
        self._ready.set()
        if not self.ok:
            return
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == self.WM_HOTKEY:
                try:
                    self.q.put_nowait("hotkey")
                except queue.Full:
                    pass
        user32.UnregisterHotKey(None, 1)

    def stop(self):
        if IS_WIN and self._tid and self.ok:
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(self._tid, self.WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(1.0)
        self.ok = False
