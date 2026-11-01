"""
Tiny Recorder — core logic (v0.1.4): settings, file names, tags, the recordings list, crash recovery.
No Tk and no audio devices here, so every function can be tested without a screen or a sound card.
"""

import json
import os
import re
import sys
import time
from datetime import date, datetime

APP_NAME = "Tiny Recorder"
APP_VERSION = "0.1.4"
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

PRESETS = {                         # the labels are in tinyrecorder_i18n ("preset.<key>")
    "voice":    {"channels": 1, "kbps": 64},
    "standard": {"channels": 2, "kbps": 128},
    "high":     {"channels": 2, "kbps": 192, "quality": 2},
}

UI_LANGUAGES = ("en", "pt-BR", "es")

DEFAULTS = {
    "ui_language": "",              # empty = follow the Windows display language (the key is then not written)
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
    "transcriptlab_path": "",       # empty = find TranscriptLab automatically (its install.json)
    "auto_stop_silence": True,      # stop after silence_minutes without sound (item 0C, on by default)
    "silence_minutes": 5.0,
    "auto_stop_time": False,        # stop when the recording reaches time_minutes
    "time_minutes": 60.0,
}


def parse_minutes(text):
    """A minutes box: '5', '1.5' and '1,5' are accepted; returns a float > 0, or None."""
    t = str(text or "").strip().replace(",", ".")
    try:
        value = float(t)
    except ValueError:
        return None
    return value if 0 < value <= 24 * 60 else None


def fmt_minutes(value):
    """5.0 -> '5', 1.5 -> '1.5' (the box shows what the user typed, without a needless '.0')."""
    return ("%.2f" % value).rstrip("0").rstrip(".")

# ---------------------------------------------------------------- TranscriptLab (item 9: Transcribe)

TRANSCRIPTLAB_MIN_VERSION = (0, 16, 9)
TRANSCRIPTLAB_RELEASES_URL = "https://github.com/junqueirach/transcriptlab/releases"


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
    data = {}
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k in DEFAULTS:
                if k in data and type(data[k]) is type(DEFAULTS[k]):
                    cfg[k] = data[k]
        else:
            data = {}
    except (OSError, ValueError):
        pass
    if cfg["preset"] not in PRESETS:
        cfg["preset"] = DEFAULTS["preset"]
    if "ui_language" in data:
        if cfg["ui_language"] not in UI_LANGUAGES:          # a broken or unknown stored value -> English
            cfg["ui_language"] = "en"
    elif data.get("lang") == "pt":                          # up to v0.1.3: "pt" was always a choice ...
        cfg["ui_language"] = "pt-BR"                        # ... "en" was the default for everybody: follow Windows
    for key in ("silence_minutes", "time_minutes"):
        if isinstance(data.get(key), int) and not isinstance(data.get(key), bool):
            cfg[key] = float(data[key])                       # 5 written by hand counts as 5.0
        if parse_minutes(cfg[key]) is None:
            cfg[key] = DEFAULTS[key]
    cfg["system_gain"] = max(0, min(200, int(cfg["system_gain"])))
    cfg["mic_gain"] = max(0, min(200, int(cfg["mic_gain"])))
    return cfg


def save_config(cfg):
    """Write the settings atomically (a crash never leaves half a file)."""
    os.makedirs(home_dir(), exist_ok=True)
    tmp = config_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({k: cfg.get(k, DEFAULTS[k]) for k in DEFAULTS if k != "ui_language" or cfg.get(k)}, f, indent=2,
                  ensure_ascii=False)
    os.replace(tmp, config_path())


def output_dir(cfg):
    return cfg.get("output_dir") or default_output_dir()


def version_tuple(text):
    """'0.16.10' -> (0, 16, 10), compared as numbers; () when there is no number."""
    return tuple(int(x) for x in re.findall(r"\d+", str(text or "")))


def transcriptlab_install_json():
    """TranscriptLab tells where it is in %APPDATA%\\TranscriptLab\\install.json (written at its every start)."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "TranscriptLab", "install.json")


def find_transcriptlab(cfg):
    """Contract point 5: the path chosen in Settings, else install.json. Returns a dict:
    {"status": "ok" | "not_found" | "too_old", "command": [...], "version": "...", "source": "settings" | "auto"}.
    install.json counts only with app TranscriptLab, contract >= 1, version >= 0.16.9 and existing command files."""
    chosen = cfg.get("transcriptlab_path") or ""
    if chosen:
        if os.path.isfile(chosen):
            return {"status": "ok", "command": [chosen], "version": "", "source": "settings"}
        return {"status": "not_found", "command": [], "version": "", "source": "settings"}
    found = {"status": "not_found", "command": [], "version": "", "source": "auto"}
    try:
        with open(transcriptlab_install_json(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return found
    if not isinstance(data, dict) or data.get("app") != "TranscriptLab":
        return found
    command = data.get("command")
    if not (isinstance(command, list) and command and all(isinstance(c, str) and c for c in command)):
        return found
    if not all(os.path.isfile(c) for c in command[:2]):         # the exe, or the interpreter and the script
        return found
    version = str(data.get("version") or "")
    contract = data.get("contract")
    found.update(command=command, version=version)
    if not isinstance(contract, int) or contract < 1 or version_tuple(version) < TRANSCRIPTLAB_MIN_VERSION:
        found["status"] = "too_old"
        return found
    found["status"] = "ok"
    return found


def transcribe_command(found, path):
    """Contract point 2: <command> --transcribe <file> --from "Tiny Recorder <version>"."""
    return list(found["command"]) + ["--transcribe", path, "--from", "%s %s" % (APP_NAME, APP_VERSION)]


# ---------------------------------------------------------------- updates (item 0B, as RadioSave)
# The check asks GitHub's releases API for the latest release (no login; nothing about the user is sent). "Download
# and install" (frozen exe only) saves the new exe next to the running one as TinyRecorder_v<version>.exe after
# checking its SHA-256 against the release; the old exe is kept. Errors carry a code the window translates.

RELEASES_API = "https://api.github.com/repos/junqueirach/tiny-recorder/releases/latest"
APP_RELEASES_URL = APP_REPO_URL + "/releases"


UPDATE_ERROR_CODES = ("no_release", "http", "offline", "no_version", "no_exe", "not_github", "no_checksum",
                      "mismatch", "cancelled")                     # texts: tinyrecorder_i18n "upd.err.<code>"


class UpdateError(Exception):
    """code: one of UPDATE_ERROR_CODES; values fill the text's {placeholders}."""

    def __init__(self, error_code, **values):                 # not "code": the http error has a {code} value
        super().__init__(error_code)
        self.code, self.values = error_code, values


def update_api_url():
    return os.environ.get("TINYRECORDER_UPDATE_API", "").strip() or RELEASES_API


def _http_get(url, timeout=15):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "%s/%s" % (APP_ID, APP_VERSION),
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:                  # noqa: S310
        return r.read(2_000_000)


def is_newer(version, current=APP_VERSION):
    return version_tuple(version) > version_tuple(current)


def check_update(getter=None, timeout=15):
    """{'version', 'newer', 'notes', 'page', 'published', 'exe': {name, url, size, sha256, sha256_url} | None}."""
    import urllib.error
    try:
        data = json.loads((getter or _http_get)(update_api_url(), timeout).decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:                       # GitHub's answer while no release is published
            raise UpdateError("no_release")
        raise UpdateError("http", code=exc.code)
    except Exception as exc:                                                 # noqa: BLE001
        raise UpdateError("offline", reason=getattr(exc, "reason", None) or exc)
    tag = str(data.get("tag_name") or data.get("name") or "").strip() if isinstance(data, dict) else ""
    if not tag:
        raise UpdateError("no_version")
    version = tag.lstrip("vV")
    assets = data.get("assets") or []
    sums = {str(a.get("name") or "")[:-7].lower(): a.get("browser_download_url") or ""
            for a in assets if str(a.get("name") or "").lower().endswith(".sha256")}
    exe = None
    for a in assets:
        name = str(a.get("name") or "")
        if name.lower().endswith(".exe"):
            digest = str(a.get("digest") or "")
            exe = {"name": name, "url": a.get("browser_download_url") or "", "size": int(a.get("size") or 0),
                   "sha256": digest.split(":", 1)[1].lower() if digest.lower().startswith("sha256:") else "",
                   "sha256_url": sums.get(name.lower(), "")}
            break
    return {"version": version, "newer": is_newer(version), "notes": str(data.get("body") or "").strip(),
            "page": data.get("html_url") or APP_RELEASES_URL, "published": str(data.get("published_at") or "")[:10],
            "exe": exe}


def update_url_allowed(url):
    if os.environ.get("TINYRECORDER_UPDATE_API"):
        return True                                                          # tests: a file:// fake release
    return bool(re.match(r"^https://(github\.com|objects\.githubusercontent\.com|"
                         r"release-assets\.githubusercontent\.com)/", url or ""))


def expected_sha256(exe, getter=None):
    if exe.get("sha256"):
        return exe["sha256"]
    if exe.get("sha256_url"):
        if not update_url_allowed(exe["sha256_url"]):
            raise UpdateError("not_github")
        m = re.search(r"\b([0-9a-fA-F]{64})\b", (getter or _http_get)(exe["sha256_url"], 15).decode("utf-8", "replace"))
        if m:
            return m.group(1).lower()
    raise UpdateError("no_checksum")


def update_target(version, folder):
    return os.path.join(folder, "TinyRecorder_v%s.exe" % version)


def download_update(info, folder, progress=None, cancel=None, opener=None, getter=None):
    """Download the release exe into folder and verify it. Returns the new exe path."""
    import hashlib
    import urllib.request
    exe = info.get("exe")
    if not exe or not exe.get("url"):
        raise UpdateError("no_exe")
    if not update_url_allowed(exe["url"]):
        raise UpdateError("not_github")
    want = expected_sha256(exe, getter)
    dest = update_target(info["version"], folder)
    part = dest + ".part"
    opener = opener or (lambda u: urllib.request.urlopen(                     # noqa: S310
        urllib.request.Request(u, headers={"User-Agent": "%s/%s" % (APP_ID, APP_VERSION)}), timeout=60))
    h = hashlib.sha256()
    done = 0
    try:
        with opener(exe["url"]) as r, open(part, "wb") as f:
            total = int(getattr(r, "headers", {}).get("Content-Length") or exe.get("size") or 0)
            while True:
                if cancel and cancel():
                    raise UpdateError("cancelled")
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
                h.update(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
        if h.hexdigest().lower() != want:
            raise UpdateError("mismatch")
        os.replace(part, dest)
        return dest
    except Exception:
        try:
            os.remove(part)
        except OSError:
            pass
        raise


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
    """Edit an existing recording: new tags, and the file renamed to match. Returns (new_path, error_or_None).
    The file keeps its time (the list is sorted by it: an edit must not move an old recording to the top), and a
    title that only changes its capitals renames the file too (Windows allows a case-only rename)."""
    try:
        st = os.stat(path)
    except OSError:
        st = None
    err = write_tags(path, tags)
    folder = os.path.dirname(path)
    new = unique_path(folder, file_stem(tags), ignore=path)
    if os.path.basename(new) != os.path.basename(path):
        os.replace(path, new)
    if st is not None:
        try:
            os.utime(new, (st.st_atime, st.st_mtime))
        except OSError:
            pass
    return new, err


# ---------------------------------------------------------------- the recordings list

def list_recordings(folder, limit=200):
    """Newest first: dicts with path, name, tags, seconds, size, mtime. Reads only the tags of the newest files."""
    out = []
    files = []
    try:
        with os.scandir(folder) as it:
            for e in it:
                try:                                      # a file deleted or renamed meanwhile is skipped
                    if e.is_file() and e.name.lower().endswith(".mp3"):
                        files.append((e, e.stat()))
                except OSError:
                    continue
    except OSError:
        return out
    files.sort(key=lambda es: es[1].st_mtime, reverse=True)
    for e, st in files[:limit]:
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
