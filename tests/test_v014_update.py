"""v0.1.4 item 0B: check for updates and install them, as RadioSave. Never GitHub: a getter or a file:// fake
release (TINYRECORDER_UPDATE_API), and the download goes to a temp folder."""

import hashlib
import io
import json
import os
import sys
import urllib.error

import pytest

import tinyrecorder_core as core
from test_v014_ui import make_app, pump

EXE_BYTES = b"MZ fake Tiny Recorder 0.2.0 " * 100
REAL_CHECK = core.check_update                               # the tests below replace core.check_update


def release(version="0.2.0", exe=True, digest=True, sums_url=""):
    assets = []
    if exe:
        a = {"name": "TinyRecorder_v%s.exe" % version, "browser_download_url": "https://github.com/x/TinyRecorder.exe",
             "size": len(EXE_BYTES)}
        if digest:
            a["digest"] = "sha256:" + hashlib.sha256(EXE_BYTES).hexdigest()
        assets.append(a)
    if sums_url:
        assets.append({"name": "TinyRecorder_v%s.exe.sha256" % version, "browser_download_url": sums_url})
    return {"tag_name": "v" + version, "body": "- Start on Sound\n- Transcribe", "html_url": "https://github.com/r",
            "published_at": "2026-11-20T10:00:00Z", "assets": assets}


def getter_for(data):
    return lambda url, timeout: json.dumps(data).encode("utf-8")


# ---------------------------------------------------------------- the check

def test_newer_release_with_its_exe():
    rel = core.check_update(getter_for(release()))
    assert rel["version"] == "0.2.0" and rel["newer"] is True and rel["published"] == "2026-11-20"
    assert rel["exe"]["name"] == "TinyRecorder_v0.2.0.exe" and len(rel["exe"]["sha256"]) == 64


@pytest.mark.parametrize("version, newer", [("0.1.4", False), ("0.1.3", False), ("0.1.10", True), ("1.0", True)])
def test_versions_compare_as_numbers(version, newer):
    assert core.check_update(getter_for(release(version)))["newer"] is newer


@pytest.mark.parametrize("raise_, code", [
    (urllib.error.HTTPError("u", 404, "Not Found", {}, io.BytesIO()), "no_release"),
    (urllib.error.HTTPError("u", 503, "Unavailable", {}, io.BytesIO()), "http"),
    (urllib.error.URLError("getaddrinfo failed"), "offline"),
])
def test_check_errors_have_codes(raise_, code):
    def getter(url, timeout):
        raise raise_
    with pytest.raises(core.UpdateError) as e:
        core.check_update(getter)
    assert e.value.code == code


def test_answer_without_a_version():
    with pytest.raises(core.UpdateError) as e:
        core.check_update(getter_for({"assets": []}))
    assert e.value.code == "no_version"


def test_check_through_a_file_url_fake_release(tmp_path, monkeypatch):
    p = tmp_path / "latest.json"
    p.write_text(json.dumps(release("0.3.0")), encoding="utf-8")
    monkeypatch.setenv("TINYRECORDER_UPDATE_API", p.as_uri())
    assert core.check_update()["version"] == "0.3.0"


# ---------------------------------------------------------------- the download

class FakeResponse(io.BytesIO):
    headers = {"Content-Length": str(len(EXE_BYTES))}


def test_download_checks_the_sha256_and_keeps_the_old_exe(tmp_path):
    old = tmp_path / "TinyRecorder_v0.1.4.exe"
    old.write_bytes(b"old")
    rel = core.check_update(getter_for(release()))
    seen = []
    path = core.download_update(rel, str(tmp_path), progress=lambda d, n: seen.append((d, n)),
                                opener=lambda url: FakeResponse(EXE_BYTES))
    assert path == str(tmp_path / "TinyRecorder_v0.2.0.exe") and open(path, "rb").read() == EXE_BYTES
    assert old.read_bytes() == b"old" and seen[-1] == (len(EXE_BYTES), len(EXE_BYTES))


def test_a_wrong_download_is_deleted(tmp_path):
    folder = tmp_path / "exe"
    folder.mkdir()
    rel = core.check_update(getter_for(release()))
    with pytest.raises(core.UpdateError) as e:
        core.download_update(rel, str(folder), opener=lambda url: FakeResponse(b"tampered"))
    assert e.value.code == "mismatch" and os.listdir(folder) == []        # no exe, no .part


def test_checksum_from_a_sha256_file_and_none_at_all(tmp_path):
    sums = "https://github.com/x/TinyRecorder_v0.2.0.exe.sha256"
    rel = core.check_update(getter_for(release(digest=False, sums_url=sums)))
    text = (hashlib.sha256(EXE_BYTES).hexdigest() + "  TinyRecorder_v0.2.0.exe").encode()
    path = core.download_update(rel, str(tmp_path), opener=lambda url: FakeResponse(EXE_BYTES),
                                getter=lambda url, timeout: text)
    assert os.path.exists(path)
    rel = core.check_update(getter_for(release(version="0.2.1", digest=False)))
    with pytest.raises(core.UpdateError) as e:
        core.download_update(rel, str(tmp_path), opener=lambda url: FakeResponse(EXE_BYTES))
    assert e.value.code == "no_checksum"


def test_only_github_addresses_are_used(monkeypatch):
    monkeypatch.delenv("TINYRECORDER_UPDATE_API", raising=False)
    assert core.update_url_allowed("https://github.com/junqueirach/tiny-recorder/releases/download/x.exe")
    assert core.update_url_allowed("https://objects.githubusercontent.com/x")
    assert not core.update_url_allowed("http://github.com/x.exe")
    assert not core.update_url_allowed("https://evil.example/github.com/x.exe")
    rel = {"version": "9", "exe": {"url": "https://evil.example/x.exe", "sha256": "0" * 64}}
    with pytest.raises(core.UpdateError) as e:
        core.download_update(rel, ".")
    assert e.value.code == "not_github"


def test_release_without_exe(tmp_path):
    rel = core.check_update(getter_for(release(exe=False)))
    with pytest.raises(core.UpdateError) as e:
        core.download_update(rel, str(tmp_path))
    assert e.value.code == "no_exe"


# ---------------------------------------------------------------- the window

@pytest.fixture
def app(tmp_path, monkeypatch):
    a, mod, out = make_app(tmp_path, monkeypatch)
    yield a, mod, out
    try:
        a._destroy()
    except Exception:
        pass


def dialogs(a, mod, cls):
    found = []

    def walk(w):
        for c in w.winfo_children():
            if isinstance(c, cls):
                found.append(c)
            walk(c)
    walk(a)
    return found


def test_about_and_settings_have_the_button(app):
    a, mod, out = app
    for d in (mod.AboutDialog(a, a), mod.SettingsDialog(a, a)):
        a.update()
        texts = []

        def walk(w):
            for c in w.winfo_children():
                if c.winfo_class() == "TButton":
                    texts.append(c.cget("text"))
                walk(c)
        walk(d)
        assert "Check for updates" in texts
        d.close()


def test_latest_version_says_so(app, monkeypatch):
    a, mod, out = app
    monkeypatch.setattr(mod.core, "check_update", lambda: REAL_CHECK(getter_for(release("0.1.4"))))
    a.check_updates()
    assert pump(a, lambda: a.shown)
    assert a.shown[0][0] == "showinfo" and "You have the latest version (0.1.4)." in a.shown[0][1][1]


def test_an_error_is_shown_in_the_interface_language(app, monkeypatch):
    a, mod, out = app
    a.cfg["ui_language"] = "es"
    a.settings_saved(True)

    def fail():
        raise core.UpdateError("no_release")
    monkeypatch.setattr(mod.core, "check_update", fail)
    a.check_updates()
    assert pump(a, lambda: a.shown)
    assert a.shown[0][0] == "showwarning" and "Todavía no se publicó" in a.shown[0][1][1]


def test_newer_version_from_source_offers_the_page_only(app, monkeypatch):
    a, mod, out = app
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(mod.core, "check_update", lambda: REAL_CHECK(getter_for(release())))
    opened = []
    monkeypatch.setattr(mod.webbrowser, "open", lambda url: opened.append(url))
    a.check_updates()
    assert pump(a, lambda: dialogs(a, mod, mod.UpdateDialog))
    d = dialogs(a, mod, mod.UpdateDialog)[0]
    assert d.b_install is None and "download the new version from the release page" in d.status.cget("text")
    d._page()
    assert opened == ["https://github.com/r"]


def test_frozen_exe_downloads_starts_the_new_one_and_closes(app, monkeypatch, tmp_path):
    a, mod, out = app
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "TinyRecorder_v0.1.4.exe"))
    monkeypatch.setattr(mod.core, "check_update", lambda: REAL_CHECK(getter_for(release())))
    new_exe = str(tmp_path / "TinyRecorder_v0.2.0.exe")
    monkeypatch.setattr(mod.core, "download_update", lambda rel, folder, progress=None: (
        progress(50, 100), open(new_exe, "wb").write(EXE_BYTES), new_exe)[2])
    started = []
    monkeypatch.setattr(mod.winsys, "start_detached", lambda cmd: started.append(cmd))
    closed = []
    monkeypatch.setattr(a, "on_close", lambda: closed.append(True))
    a.check_updates()
    assert pump(a, lambda: dialogs(a, mod, mod.UpdateDialog))
    d = dialogs(a, mod, mod.UpdateDialog)[0]
    assert d.b_install is not None and str(d.b_install.cget("state")) == "normal"
    d._install()
    assert pump(a, lambda: started)
    assert started == [[new_exe]] and closed == [True]
