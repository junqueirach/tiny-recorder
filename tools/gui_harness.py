"""Opens the real window against a temp data folder and fake audio sources, fills it in, and saves screenshots of
the app's OWN windows with PrintWindow (never the screen). Used for the README picture and visual checks.

    python tools/gui_harness.py <output folder>
"""

import ctypes
import os
import sys
import tempfile
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))


def print_window(hwnd, path):
    from PIL import Image
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    user32.PrintWindow(hwnd, mem, 2)                                # PW_RENDERFULLCONTENT

    class BIH(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("a", wintypes.LONG), ("b", wintypes.LONG),
                    ("c", wintypes.DWORD), ("d", wintypes.DWORD)]
    bi = BIH(ctypes.sizeof(BIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB").save(path)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    tmp = tempfile.mkdtemp()
    os.environ["TINYRECORDER_HOME"] = os.path.join(tmp, "home")
    import tinyrecorder_audio as au
    import tinyrecorder_core as core
    from conftest import FakeSource, load_app_module
    import tinyrecorder_winsys as winsys
    cfg = core.load_config()
    cfg["output_dir"] = os.path.join(tmp, "Recordings")
    cfg["hotkey"] = False
    core.save_config(cfg)
    fakes = [FakeSource("system", 44100, 2, 440, 0.25, "Headphones (Demo) [Loopback]"),
             FakeSource("mic", 48000, 1, 880, 0.08, "Headset (Demo)")]
    au.open_sources = lambda *a, **k: (None, fakes, [])
    mod = load_app_module()
    app = mod.App()
    # three finished recordings for the list
    from test_core import _tiny_mp3
    os.makedirs(cfg["output_dir"], exist_ok=True)
    for i, (d, t, p) in enumerate([("2026-10-20", "Budget review", "Ana, Bob"), ("2026-10-19", "Client call: Alpha", "Carla"),
                                   ("2026-10-16", "Weekly sync", "Team")]):
        path = os.path.join(cfg["output_dir"], "x%d.mp3" % i)
        _tiny_mp3(path)
        core.retag_and_rename(path, core.Tags(d, t, p))
    app.update()
    app.reload_list()
    for _i in range(15):
        app.update()
        time.sleep(0.1)
    hwnd = winsys.hwnd_of(app.winfo_id())
    print_window(hwnd, os.path.join(out_dir, "tinyrecorder-idle.png"))
    app.tags.set(core.Tags("2026-10-20", "Budget review", "Ana, Bob", "Alpha", "Quarterly numbers"))
    app.toggle_record()
    t_end = time.time() + 4
    while time.time() < t_end:
        app.update()
        time.sleep(0.05)
    print_window(hwnd, os.path.join(out_dir, "tinyrecorder-recording.png"))
    for cls in (mod.AboutDialog, mod.HelpDialog):
        d = cls(app, app)
        for _i in range(8):
            app.update()
            time.sleep(0.05)
        print_window(winsys.hwnd_of(d.winfo_id()), os.path.join(out_dir, "tinyrecorder-%s.png" % cls.__name__.lower()))
        d.close()
    app.toggle_record()
    t_end = time.time() + 2
    while time.time() < t_end:
        app.update()
        time.sleep(0.05)
    app._destroy()
    print("screenshots in", out_dir)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "screenshots"))
