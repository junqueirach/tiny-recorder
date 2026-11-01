"""
Tiny Recorder — small Windows helpers (v0.1.4). No Tk here: functions take window handles (ints).

single instance · dark title bar, taskbar identity, DPI awareness · Windows display language · global hotkey · show a
file in Explorer.
"""

import hashlib
import os
import queue
import re
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


def is_main_window(title, window_class, app_name="Tiny Recorder"):
    """The main window of a running copy: a Tk toplevel titled 'Tiny Recorder 0.1.4' (idle) or
    '● REC 00:01:02  ·  Tiny Recorder' (recording / paused, any language). An Explorer window on the
    'Tiny Recorder' recordings folder, the Help window or a browser tab never matches."""
    if window_class != "TkTopLevel":
        return False
    return bool(re.match(re.escape(app_name) + r" \d", title)) or title.endswith("·  " + app_name)


def bring_to_front(app_name="Tiny Recorder"):
    """Show the main window of the copy that is already running."""
    if not IS_WIN:
        return False
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        n = user32.GetWindowTextLengthW(hwnd)
        if n and user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            cls = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, cls, 64)
            if is_main_window(buf.value, cls.value, app_name):
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


def windows_ui_langid():
    """The Windows display language as a LANGID (0 when unknown); read at each start."""
    if not IS_WIN:
        return 0
    import ctypes
    try:
        return int(ctypes.windll.kernel32.GetUserDefaultUILanguage())
    except Exception:
        return 0


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


def work_area():
    """(left, top, right, bottom) of the main monitor without the taskbar, in pixels; None when unknown."""
    if not IS_WIN:
        return None
    import ctypes
    from ctypes import wintypes
    r = wintypes.RECT()
    if ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0):        # SPI_GETWORKAREA
        return r.left, r.top, r.right, r.bottom
    return None


def on_a_monitor(x, y):
    """True when the point is on a connected monitor (a window saved on a monitor that was removed is not)."""
    if not IS_WIN:
        return True
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.MonitorFromPoint.restype = ctypes.c_void_p
    return bool(user32.MonitorFromPoint(wintypes.POINT(int(x), int(y)), 0))             # MONITOR_DEFAULTTONULL


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
    """System-wide hotkeys: Ctrl+Alt+R (start / stop, puts "hotkey") and Ctrl+Alt+P (pause / resume, puts
    "hotkey_pause"). A helper thread owns the registrations and the message loop; the Tk thread drains the queue.
    ok is False when Windows refused Ctrl+Alt+R; pause_ok is False when it refused Ctrl+Alt+P (another program
    already uses it)."""

    MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x4000
    WM_HOTKEY, WM_QUIT = 0x312, 0x12

    def __init__(self, q, vk=ord("R"), mods=None, pause_vk=ord("P")):
        self.q = q
        self.vk = vk
        self.pause_vk = pause_vk
        self.mods = mods if mods is not None else (self.MOD_CONTROL | self.MOD_ALT | self.MOD_NOREPEAT)
        self.ok = False
        self.pause_ok = False
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
        self.pause_ok = bool(self.pause_vk) and bool(user32.RegisterHotKey(None, 2, self.mods, self.pause_vk))
        self._ready.set()
        if not (self.ok or self.pause_ok):
            return
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == self.WM_HOTKEY:
                try:
                    self.q.put_nowait("hotkey_pause" if msg.wParam == 2 else "hotkey")
                except queue.Full:
                    pass
        for hotkey_id in (1, 2):
            user32.UnregisterHotKey(None, hotkey_id)

    def stop(self):
        if IS_WIN and self._tid and (self.ok or self.pause_ok):
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(self._tid, self.WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(1.0)
        self.ok = self.pause_ok = False


# ------------------------------------------------------------------ the Windows default output (item 1)

def default_output_device():
    """(id, name) of the Windows default output device, or None. Asks Core Audio (the MMDevice API) directly:
    PortAudio reads the device list only when it starts, so it cannot see a change during a recording. One call
    takes about 4 ms (measured 2026-11-01). Runs on the Tk thread (COM apartment initialised here; a thread that
    already has one keeps it)."""
    if not IS_WIN:
        return None
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("d1", wintypes.DWORD), ("d2", wintypes.WORD), ("d3", wintypes.WORD), ("d4", ctypes.c_ubyte * 8)]

    class PROPERTYKEY(ctypes.Structure):
        _fields_ = [("fmtid", GUID), ("pid", wintypes.DWORD)]

    class PROPVARIANT(ctypes.Structure):
        _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort), ("r2", ctypes.c_ushort),
                    ("r3", ctypes.c_ushort), ("data", ctypes.c_void_p), ("data2", ctypes.c_void_p)]

    ole32 = ctypes.windll.ole32

    def guid(text):
        g = GUID()
        ole32.CLSIDFromString(ctypes.c_wchar_p(text), ctypes.byref(g))
        return g

    def method(obj, index, *argtypes):
        vtbl = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, *argtypes)(vtbl[index])

    def release(obj):
        if obj:
            vtbl = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])(obj)

    enum = ctypes.c_void_p()
    dev = ctypes.c_void_p()
    store = ctypes.c_void_p()
    try:
        ole32.CoInitializeEx(None, 2)                                # COINIT_APARTMENTTHREADED (S_FALSE: already)
        ole32.CoCreateInstance(ctypes.byref(guid("{BCDE0395-E52F-467C-8E3D-C4579291692E}")), None, 0x17,
                               ctypes.byref(guid("{A95664D2-9614-4F35-A746-DE8DB63617E6}")), ctypes.byref(enum))
        if not enum.value:
            return None
        # IMMDeviceEnumerator::GetDefaultAudioEndpoint(eRender, eConsole, &device)
        method(enum, 4, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))(enum, 0, 0, ctypes.byref(dev))
        if not dev.value:
            return None
        pid = ctypes.c_void_p()
        method(dev, 5, ctypes.POINTER(ctypes.c_void_p))(dev, ctypes.byref(pid))          # IMMDevice::GetId
        dev_id = ctypes.wstring_at(pid.value) if pid.value else ""
        ole32.CoTaskMemFree(pid)
        name = ""
        method(dev, 4, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p))(dev, 0, ctypes.byref(store))  # STGM_READ
        if store.value:
            key = PROPERTYKEY(guid("{A45C254E-DF1C-4EFD-8020-67D146A850E0}"), 14)        # Device_FriendlyName
            pv = PROPVARIANT()
            method(store, 5, ctypes.POINTER(PROPERTYKEY), ctypes.POINTER(PROPVARIANT))(
                store, ctypes.byref(key), ctypes.byref(pv))
            if pv.vt == 31 and pv.data:                              # VT_LPWSTR
                name = ctypes.wstring_at(pv.data)
            ole32.PropVariantClear(ctypes.byref(pv))
        return (dev_id, name) if dev_id else None
    except Exception:                                                # noqa: BLE001
        return None
    finally:
        for obj in (store, dev, enum):
            release(obj.value)


# ------------------------------------------------------------------ starting another program (Transcribe)

def clean_child_env(env=None):
    """A copy of the environment for a program Tiny Recorder starts. A frozen (PyInstaller) Tiny Recorder sets
    TCL_LIBRARY / TK_LIBRARY to its own temporary folder and _PYI_* / _MEIPASS2 for itself; another PyInstaller exe
    would load Tcl from a folder that disappears, or take itself for our child."""
    env = dict(os.environ if env is None else env)
    for k in list(env):
        if k.upper() in ("TCL_LIBRARY", "TK_LIBRARY", "_MEIPASS2") or k.upper().startswith("_PYI_"):
            del env[k]
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def start_detached(command):
    """Start a program that outlives Tiny Recorder: detached, own process group, no handles shared, never waited
    for. Raises OSError when it cannot be started."""
    flags = 0
    if IS_WIN:
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    cwd = os.path.dirname(command[0]) or None
    subprocess.Popen(command, env=clean_child_env(), cwd=cwd, creationflags=flags, close_fds=True,  # noqa: S603
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ------------------------------------------------------------------ Recycle Bin

def has_recycle_bin(path):
    """False for a network folder or a removable drive: Windows deletes there for good, without the Recycle Bin."""
    if not IS_WIN:
        return True
    p = os.path.abspath(path)
    if p.startswith("\\\\"):                                       # \\server\share
        return False
    import ctypes
    drive_type = ctypes.windll.kernel32.GetDriveTypeW(os.path.splitdrive(p)[0] + "\\")
    return drive_type == 3                                         # DRIVE_FIXED (2 removable, 4 network)


def send_to_recycle_bin(path):
    """Move a file to the Recycle Bin (it can be restored). True on success."""
    if not IS_WIN or not os.path.exists(path):
        return False
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_uint16), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]
    op = SHFILEOPSTRUCTW()
    op.wFunc = 3                                                   # FO_DELETE
    op.pFrom = os.path.abspath(path) + "\0"
    op.fFlags = 0x0040 | 0x0010 | 0x0004 | 0x0400                  # ALLOWUNDO|NOCONFIRMATION|SILENT|NOERRORUI
    return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0 and not os.path.exists(path)
