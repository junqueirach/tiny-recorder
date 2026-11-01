"""v0.1.4 item 8: the interface in English, Portuguese (Brazil) and Spanish.

The three catalogs have the same keys and {placeholders}; every key the code asks for exists; no user-visible string
literal is left in the window code; the Windows language picks the default; the old "lang" setting migrates once."""

import ast
import glob
import json
import os
import re

import pytest

import tinyrecorder_core as core
import tinyrecorder_help as helpmod
import tinyrecorder_i18n as i18n

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def code_files():
    return [p for p in glob.glob(os.path.join(ROOT, "tinyrecorder*.py")) if not p.endswith("tinyrecorder_i18n.py")]


def keys_in_code():
    found = set()
    for path in code_files():
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("t", "tn") and node.args \
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                found.add(node.args[0].value)
    return found


DYNAMIC = {"preset." + k for k in core.PRESETS} | \
    {"upd.err." + c for c in core.UPDATE_ERROR_CODES}       # built as t("preset." + key), t("upd.err." + code)


def names(text):
    return sorted(re.findall(r"\{(\w+)\}", text))


def flat(value):
    return list(value.values()) if isinstance(value, dict) else [value]


def test_three_catalogs_have_the_same_keys():
    assert set(i18n.EN) == set(i18n.PT_BR) == set(i18n.ES)


def test_no_empty_text_and_placeholders_match():
    for key, en in i18n.EN.items():
        for cat in (i18n.PT_BR, i18n.ES):
            other = cat[key]
            assert type(other) is type(en), key
            if isinstance(en, dict):
                assert set(en) == set(other) == {"one", "other"}, key
            for a, b in zip(flat(en), flat(other)):
                assert a.strip() and b.strip(), key
                assert names(a) == names(b), key


def test_every_key_used_by_the_code_exists_and_none_is_unused():
    used = keys_in_code()
    missing = sorted(k for k in used | DYNAMIC if k not in i18n.EN)
    assert not missing, missing
    unused = sorted(k for k in i18n.EN if k not in used | DYNAMIC)
    assert not unused, unused


def test_help_has_the_same_sections_in_three_languages():
    assert len(helpmod.EN) == len(helpmod.PT) == len(helpmod.ES) >= 6
    for (_e, en), (_p, pt), (_s, es) in zip(helpmod.EN, helpmod.PT, helpmod.ES):
        for body in (en, pt, es):
            assert body.strip() and body.count("**") % 2 == 0


def test_missing_text_falls_back_to_english_and_is_logged_once(monkeypatch, capsys):
    monkeypatch.delitem(i18n.ES, "btn.stop")
    i18n._missing.clear()
    i18n.set_lang("es")
    assert i18n.t("btn.stop") == "Stop" and i18n.t("btn.stop") == "Stop"
    assert capsys.readouterr().err.count("btn.stop") == 1
    assert i18n.t("btn.record") == "Grabar ahora"


@pytest.mark.parametrize("lang, zero, one, two", [
    ("en", "Recovered 0 recordings.", "Recovered 1 recording.", "Recovered 2 recordings."),
    ("pt-BR", "0 gravação recuperada.", "1 gravação recuperada.", "2 gravações recuperadas."),
    ("es", "Se recuperaron 0 grabaciones.", "Se recuperó 1 grabación.", "Se recuperaron 2 grabaciones."),
])
def test_plurals(lang, zero, one, two):
    i18n.set_lang(lang)
    assert [i18n.tn("recovery.done", n) for n in (0, 1, 2)] == [zero, one, two]


@pytest.mark.parametrize("langid, code", [
    (0x0416, "pt-BR"), (0x0816, "pt-BR"),          # pt-BR, pt-PT
    (0x0C0A, "es"), (0x080A, "es"),                # es-ES, es-MX
    (0x0409, "en"), (0x0407, "en"), (0x0411, "en"),  # en-US, de-DE, ja-JP
    (0, "en"), (None, "en"), ("broken", "en"),
])
def test_windows_language_decides_the_default(langid, code):
    assert i18n.from_windows(langid) == code


def test_unknown_language_code_gives_english():
    i18n.set_lang("fr")
    assert i18n.LANG == "en"


def _write_cfg(data):
    os.makedirs(core.home_dir(), exist_ok=True)
    with open(core.config_path(), "w", encoding="utf-8") as f:
        json.dump(data, f)


def _saved():
    with open(core.config_path(), encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("old, expected", [({"lang": "pt"}, "pt-BR"), ({"lang": "en"}, ""), ({}, ""),
                                           ({"lang": "pt", "ui_language": "es"}, "es")])
def test_old_lang_setting_migrates_once(old, expected):
    _write_cfg(dict(old, preset="high"))
    cfg = core.load_config()
    assert cfg["ui_language"] == expected and cfg["preset"] == "high"
    core.save_config(cfg)
    saved = _saved()
    assert "lang" not in saved                                      # never written again
    assert saved.get("ui_language", "") == expected
    assert core.load_config()["ui_language"] == expected


def test_same_as_windows_removes_the_key():
    cfg = core.load_config()
    cfg["ui_language"] = "es"
    core.save_config(cfg)
    assert _saved()["ui_language"] == "es"
    cfg["ui_language"] = ""
    core.save_config(cfg)
    assert "ui_language" not in _saved()


# ---------------------------------------------------------------- no text left outside the catalogs

ALLOWED = {"00:00:00", "GitHub", "THIRD_PARTY_LICENSES.md", "MIT"}
TEXT_KW = {"text", "label", "title", "values"}


def _literal_texts(node):
    """String literals with letters inside an expression (f-strings and + included), not inside t() / tn()."""
    out = []
    if isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("t", "tn"):
        return out
    if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "cget":   # w.cget("text") reads an option
        return out
    if isinstance(node, ast.Compare):                               # st == "paused" decides, it is not shown
        return out
    if isinstance(node, ast.Subscript):                             # r["size"] is a dict key
        return _literal_texts(node.value)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        if re.search(r"[A-Za-zÀ-ÿ]{2,}", node.value) and node.value.strip() not in ALLOWED:
            out.append(node.value)
        return out
    for child in ast.iter_child_nodes(node):
        if isinstance(node, ast.BinOp) and isinstance(child, ast.Constant) and "%" in str(getattr(child, "value", "")):
            continue                                                # a "%s %s" format string
        out.extend(_literal_texts(child))
    return out


def test_the_scan_finds_a_plain_text_and_skips_keys():
    call = ast.parse('Label(text="Hello " + t("k"), values=[x for x in y if s == "paused"] + [r["size"]])').body[0].value
    found = [s for kw in call.keywords for s in _literal_texts(kw.value)]
    assert found == ["Hello "]


def test_no_user_visible_literal_in_the_window_code():
    path = [p for p in code_files() if os.path.basename(p).startswith("tinyrecorder_v")][0]
    tree = ast.parse(open(path, encoding="utf-8").read())
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "attr", getattr(func, "id", ""))
        targets = [kw.value for kw in node.keywords if kw.arg in TEXT_KW]
        if name == "title" and node.args:
            targets.append(node.args[0])
        if isinstance(func, ast.Attribute) and getattr(func.value, "id", "") == "messagebox":
            targets.extend(node.args)
        if name in ("insert",) and getattr(func.value, "attr", "") == "lb":
            continue
        for tnode in targets:
            found.extend("line %d: %r" % (node.lineno, s) for s in _literal_texts(tnode))
    assert not found, found
