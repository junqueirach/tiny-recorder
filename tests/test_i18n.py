"""Every _("…") string in the code has a Portuguese text, the {names} match, and nothing in PT is unused."""

import glob
import os
import re

import tinyrecorder_core as core
import tinyrecorder_help as helpmod
import tinyrecorder_i18n as i18n

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALL = re.compile(r'(?<![\w.])_\(\s*((?:"(?:[^"\\]|\\.)*"\s*)+)\)')
PIECE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def strings_in_code():
    found = set()
    for path in glob.glob(os.path.join(ROOT, "tinyrecorder*.py")):
        if path.endswith("tinyrecorder_i18n.py"):
            continue
        src = open(path, encoding="utf-8").read()
        for m in CALL.finditer(src):
            text = "".join(PIECE.findall(m.group(1)))
            found.add(text.encode("utf-8").decode("unicode_escape").encode("latin-1", "ignore").decode("utf-8", "ignore")
                      if "\\" in text else text)
    return found


def names(s):
    return sorted(re.findall(r"\{(\w+)\}", s))


def test_every_string_has_portuguese():
    missing = sorted(s for s in strings_in_code() if s not in i18n.PT)
    assert not missing, missing


def test_preset_labels_have_portuguese():
    for p in core.PRESETS.values():
        assert p["label"] in i18n.PT


def test_placeholders_match():
    bad = [k for k, v in i18n.PT.items() if names(k) != names(v)]
    assert not bad, bad


def test_no_unused_portuguese_entries():
    used = strings_in_code() | {p["label"] for p in core.PRESETS.values()}
    # strings that the code builds with _() on a variable or inside a dict are listed here on purpose
    dynamic = set()
    unused = sorted(k for k in i18n.PT if k not in used and k not in dynamic)
    assert not unused, unused


def test_help_sections_match_in_both_languages():
    assert len(helpmod.EN) == len(helpmod.PT) >= 6
    for (en_title, en), (pt_title, pt) in zip(helpmod.EN, helpmod.PT):
        assert en.strip() and pt.strip()
        assert en.count("**") % 2 == 0 and pt.count("**") % 2 == 0


def test_underscore_function():
    i18n.set_lang("pt")
    try:
        assert i18n._("Stop") == "Parar"
        assert i18n._("never translated text") == "never translated text"
    finally:
        i18n.set_lang("en")
    assert i18n._("Stop") == "Stop"
