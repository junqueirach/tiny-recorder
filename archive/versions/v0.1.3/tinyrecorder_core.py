"""
Tiny Recorder — core logic (v0.1.3): settings, file names, tags, the recordings list, crash recovery.
No Tk and no audio devices here, so every function can be tested without a screen or a sound card.
"""

import json
import os
import re
import sys
import time
from datetime import date, datetime

APP_NAME = "Tiny Recorder"
APP_VERSION = "0.1.3"
APP_AUTHORS = "Luiz Junqueira & Claude AI"
APP_CONTACT = "junqueira.ch@gmail.com"
APP_ID = "Junqueira.TinyRecorder"
APP_REPO_URL = "https://github.com/junqueirach/tiny-recorder"
APP_ISSUES_URL = APP_REPO_URL + "/issues"
APP_LICENCE = "MIT"

# Written into every recording (the ID3 Copyright tag); the user cannot remove it from the window.
COPYRIGHT_TEXT = "not for distribution, personal use only"

PART_SUFFIX = ".mp3.part"           # a recording in progress: playable, and recoverable after a crash
MAX_NAME_LEN = 120                  # characters of the file name without the extension

# ---------------------------------------------------------------- quality presets

PRESETS = {
    "voice":    {"channels": 1, "kbps": 64,  "label": "Voice: mono, 64 kbps (about 29 MB per hour)"},
    "standard": {"channels": 2, "kbps": 128, "label": "Standard: stereo, 128 kbps (about 58 MB per hour)"},
    "high":     {"channels": 2, "kbps": 192, "quality": 2, "label": "High: stereo, 192 kbps (about 86 MB per hour)"},
}

DEFAULTS = {
    "lang": "en",
    "output_dir": "",               # empty = Documents\Tiny Recorder
    "preset": "voice",
    "use_system": True,             # computer audio (what you hear)
    "use_mic": True,                # your microphone (what you say)
    "system_device": "",            # empty = follow the Windows default output
    "mic_device": "",               # empty = follow the Windows default microphone
    "system_gain": 100,             # percent
    "mic_gain": 100,
    "hotkey": True,                 # Ctrl+Alt+R starts and stops from any program
    "window": "",                   # "WxH+X+Y"
}


# ---------------------------------------------------------------- folders and settings

def home_dir():
    """Settings folder: %APPDATA%\\TinyRecorder, or TINYRECORDER_HOME (tests and manual runs use a temp folder)."""
    env = os.environ.get("TINYRECORDER_HOME")
    if env:
        return env
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "TinyRecorder")


def config_path():
    return os.path.join(home_dir(), "config.json")


def default_output_dir():
    docs = os.path.join(os.path.expanduser("~"), "Documents")
    return os.path.join(docs if os.path.isdir(docs) else os.path.expanduser("~"), "Tiny Recorder")


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k in DEFAULTS:
                if k in data and type(data[k]) is type(DEFAULTS[k]):
                    cfg[k] = data[k]
    except (OSError, ValueError):
        pass
    if cfg["preset"] not in PRESETS:
        cfg["preset"] = DEFAULTS["preset"]
    if cfg["lang"] not in ("en", "pt"):
        cfg["lang"] = "en"
    cfg["system_gain"] = max(0, min(200, int(cfg["system_gain"])))
    cfg["mic_gain"] = max(0, min(200, int(cfg["mic_gain"])))
    return cfg


def save_config(cfg):
    """Write the settings atomically (a crash never leaves half a file)."""
    os.makedirs(home_dir(), exist_ok=True)
    tmp = config_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({k: cfg.get(k, DEFAULTS[k]) for k in DEFAULTS}, f, indent=2, ensure_ascii=False)
    os.replace(tmp, config_path())


def output_dir(cfg):
    return cfg.get("output_dir") or default_output_dir()


# ---------------------------------------------------------------- tags

class Tags:
    """What a recording says about itself. date is ISO (YYYY-MM-DD)."""

    def __init__(self, date_="", title="", people="", project="", notes=""):
        self.date = date_
        self.title = title
        self.people = people
        self.project = project
        self.notes = notes

    def as_dict(self):
        return {"date": self.date, "title": self.title, "people": self.people, "project": self.project,
                "notes": self.notes}

    def __eq__(self, other):
        return isinstance(other, Tags) and self.as_dict() == other.as_dict()

    def __repr__(self):
        return "Tags(%r)" % (self.as_dict(),)


def parse_date(text):
    """Accepts 2026-10-20, 2026/10/20, 20.10.2026, 20/10/2026 and 20-10-2026. Returns an ISO string or None."""
    t = (text or "").strip()
    for pattern, order in ((r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", "ymd"),
                           (r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$", "dmy")):
        m = re.match(pattern, t)
        if m:
            a, b, c = (int(x) for x in m.groups())
            y, mo, d = (a, b, c) if order == "ymd" else (c, b, a)
            try:
                return date(y, mo, d).isoformat()
            except ValueError:
                return None
    return None


def today_iso():
    return date.today().isoformat()


_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {"COM%d" % i for i in range(1, 10)} | {"LPT%d" % i for i in range(1, 10)}


def clean_title(title):
    """The title as it goes into a file name: no characters Windows refuses, single spaces, no trailing dots."""
    t = _ILLEGAL.sub(" ", title or "")
    t = re.sub(r"\s+", " ", t).strip(" .")
    if t.upper() in _RESERVED:
        t = "_" + t
    return t


def file_stem(tags):
    """'YYYY-MM-DD - Title' (a missing title becomes 'Untitled'; a missing date becomes today)."""
    d = parse_date(tags.date) or today_iso()
    title = clean_title(tags.title) or "Untitled"
    stem = "%s - %s" % (d, title)
    if len(stem) > MAX_NAME_LEN:
        stem = stem[:MAX_NAME_LEN].rstrip(" .")
    return stem


def unique_path(folder, stem, ext=".mp3", ignore=None):
    """folder\\stem.mp3, or 'stem (2).mp3', 'stem (3).mp3'... when the name is taken. A path equal to
    ignore (the file being renamed) counts as free."""
    n = 1
    while True:
        name = stem + ("" if n == 1 else " (%d)" % n) + ext
        path = os.path.join(folder, name)
        if (not os.path.exists(path)) or (ignore and os.path.normcase(path) == os.path.normcase(ignore)):
            return path
        n += 1


# ---------------------------------------------------------------- ID3 tags (mutagen)

def write_tags(path, tags, encoded_by=APP_NAME + " " + APP_VERSION):
    """Date, title, people (artist), project (album) and notes (comment) as ID3v2.4, plus the fixed Copyright tag
    "not for distribution, personal use only". Returns None, or the error
    text when the tags could not be written (the audio is never touched by a failed write)."""
    try:
        from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TCOP, TDRC, TENC, TIT2, TPE1, COMM
        try:
            id3 = ID3(path)
        except ID3NoHeaderError:
            id3 = ID3()
        for key in ("TIT2", "TPE1", "TALB", "TDRC", "TENC", "TCOP", "COMM"):
            id3.delall(key)
        d = parse_date(tags.date) or tags.date
        if tags.title:
            id3.add(TIT2(encoding=3, text=tags.title))
        if tags.people:
            id3.add(TPE1(encoding=3, text=tags.people))
        if tags.project:
            id3.add(TALB(encoding=3, text=tags.project))
        if d:
            id3.add(TDRC(encoding=3, text=d))
        if tags.notes:
            id3.add(COMM(encoding=3, lang="eng", desc="", text=tags.notes))
        id3.add(TENC(encoding=3, text=encoded_by))
        id3.add(TCOP(encoding=3, text=COPYRIGHT_TEXT))
        id3.save(path, v2_version=4)
        return None
    except Exception as e:                                                   # noqa: BLE001
        return "%s: %s" % (type(e).__name__, e)


def read_tags(path):
    """Tags of an MP3 file (empty strings when it has none)."""
    t = Tags()
    try:
        from mutagen.id3 import ID3
        id3 = ID3(path)
    except Exception:                                                        # noqa: BLE001
        return t

    def first(key):
        fr = id3.get(key)
        return str(fr.text[0]) if fr is not None and getattr(fr, "text", None) else ""
    t.title = first("TIT2")
    t.people = first("TPE1")
    t.project = first("TALB")
    d = first("TDRC")
    t.date = parse_date(d[:10]) or d[:10]
    for fr in id3.getall("COMM"):
        if fr.text:
            t.notes = str(fr.text[0])
            break
    return t


def audio_seconds(path):
    """Length of an MP3 file in seconds (0.0 when it cannot be read)."""
    try:
        from mutagen.mp3 import MP3
        return float(MP3(path).info.length)
    except Exception:                                                        # noqa: BLE001
        return 0.0


def finalize(part_path, folder, tags):
    """Tags a finished (or recovered) recording and moves it to its final name 'date - Title.mp3'.
    Returns (final_path, error_text_or_None). The file is renamed even when tagging fails."""
    err = write_tags(part_path, tags)
    final = unique_path(folder, file_stem(tags))
    os.replace(part_path, final)
    return final, err


def retag_and_rename(path, tags):
    """Edit an existing recording: new tags, and the file renamed to match. Returns (new_path, error_or_None)."""
    err = write_tags(path, tags)
    folder = os.path.dirname(path)
    new = unique_path(folder, file_stem(tags), ignore=path)
    if os.path.normcase(new) != os.path.normcase(path):
        os.replace(path, new)
    return new, err


# ---------------------------------------------------------------- the recordings list

def list_recordings(folder, limit=200):
    """Newest first: dicts with path, name, tags, seconds, size, mtime. Reads only the tags of the newest files."""
    out = []
    try:
        with os.scandir(folder) as it:
            files = [e for e in it if e.is_file() and e.name.lower().endswith(".mp3")]
    except OSError:
        return out
    files.sort(key=lambda e: e.stat().st_mtime, reverse=True)
    for e in files[:limit]:
        st = e.stat()
        out.append({"path": e.path, "name": e.name, "tags": read_tags(e.path), "seconds": audio_seconds(e.path),
                    "size": st.st_size, "mtime": st.st_mtime})
    return out


def find_part_files(folder, exclude=None):
    """Recordings that were never finished (the app or the PC stopped first). exclude: a path in use right now."""
    out = []
    try:
        with os.scandir(folder) as it:
            for e in it:
                if e.is_file() and e.name.endswith(PART_SUFFIX):
                    if exclude and os.path.normcase(e.path) == os.path.normcase(exclude):
                        continue
                    out.append(e.path)
    except OSError:
        pass
    return sorted(out)


def part_path_now(folder):
    return os.path.join(folder, "~recording-%s%s" % (datetime.now().strftime("%Y%m%d-%H%M%S"), PART_SUFFIX))


# ---------------------------------------------------------------- display helpers

def fmt_clock(seconds):
    s = int(max(0, seconds))
    return "%02d:%02d:%02d" % (s // 3600, (s % 3600) // 60, s % 60)


def fmt_size(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%d %s" % (n, unit)) if unit == "B" else ("%.1f %s" % (n, unit))
        n /= 1024.0


def log(msg):
    """Plain log line on stderr (kept in English, for bug reports)."""
    try:
        sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), msg))
    except Exception:                                                        # noqa: BLE001
        pass
