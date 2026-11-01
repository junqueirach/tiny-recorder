import os

import pytest

import tinyrecorder_core as core
from tinyrecorder_core import Tags


def test_config_round_trip_and_clamp(isolated_home):
    cfg = core.load_config()
    assert cfg["preset"] == "voice" and cfg["ui_language"] == ""             # v0.1.4: "" = follow Windows
    cfg["preset"], cfg["system_gain"], cfg["ui_language"] = "high", 150, "pt-BR"
    core.save_config(cfg)
    again = core.load_config()
    assert (again["preset"], again["system_gain"], again["ui_language"]) == ("high", 150, "pt-BR")
    with open(core.config_path(), "w", encoding="utf-8") as f:
        f.write('{"preset": "nonsense", "mic_gain": 999, "ui_language": "xx", "hotkey": "yes"}')
    bad = core.load_config()
    assert bad["preset"] == "voice" and bad["mic_gain"] == 200 and bad["ui_language"] == "en" and bad["hotkey"] is True


def test_broken_config_file_falls_back(isolated_home):
    with open(core.config_path(), "w", encoding="utf-8") as f:
        f.write("{not json")
    assert core.load_config()["preset"] == "voice"


@pytest.mark.parametrize("text,iso", [("2026-10-20", "2026-10-20"), ("2026/10/20", "2026-10-20"),
                                       ("20.10.2026", "2026-10-20"), ("20/10/2026", "2026-10-20"),
                                       ("2026-2-3", "2026-02-03"), ("2026-13-01", None), ("tomorrow", None), ("", None)])
def test_parse_date(text, iso):
    assert core.parse_date(text) == iso


def test_file_stem_pattern_and_cleaning():
    assert core.file_stem(Tags("2026-10-20", "Budget review")) == "2026-10-20 - Budget review"
    assert core.file_stem(Tags("2026-10-20", 'Q3: plan / "draft"?  ')) == "2026-10-20 - Q3 plan draft"
    assert core.file_stem(Tags("2026-10-20", "")) == "2026-10-20 - Untitled"
    assert core.file_stem(Tags("20.10.2026", "x")) == "2026-10-20 - x"
    assert core.file_stem(Tags("", "x")).startswith(core.today_iso())
    assert core.clean_title("CON") == "_CON"
    assert core.clean_title("end...") == "end"
    assert len(core.file_stem(Tags("2026-10-20", "a" * 400))) <= core.MAX_NAME_LEN


def test_unique_path(tmp_path):
    p1 = core.unique_path(str(tmp_path), "2026-10-20 - A")
    assert p1.endswith("2026-10-20 - A.mp3")
    open(p1, "w").close()
    p2 = core.unique_path(str(tmp_path), "2026-10-20 - A")
    assert p2.endswith("2026-10-20 - A (2).mp3")
    assert core.unique_path(str(tmp_path), "2026-10-20 - A", ignore=p1) == p1


def _tiny_mp3(path):
    import lameenc
    enc = lameenc.Encoder()
    enc.set_bit_rate(64)
    enc.set_in_sample_rate(44100)
    enc.set_out_sample_rate(44100)
    enc.set_channels(1)
    enc.set_quality(2)
    data = enc.encode(b"\x00\x00" * 44100) + enc.flush()
    with open(path, "wb") as f:
        f.write(data)


def test_tags_round_trip_including_unicode(tmp_path):
    p = str(tmp_path / "a.mp3.part")
    _tiny_mp3(p)
    t = Tags("2026-10-20", "Reunião: orçamento ★", "Ana, José, 李", "Projeto Ω", "linha 1\nlinha 2")
    assert core.write_tags(p, t) is None
    back = core.read_tags(p)
    assert back == t
    assert 0.9 < core.audio_seconds(p) < 1.2


def test_finalize_names_and_never_overwrites(tmp_path):
    folder = str(tmp_path)
    out = []
    for i in range(2):
        p = os.path.join(folder, "x%d.mp3.part" % i)
        _tiny_mp3(p)
        final, err = core.finalize(p, folder, Tags("2026-10-20", "Weekly"))
        assert err is None
        out.append(os.path.basename(final))
    assert out == ["2026-10-20 - Weekly.mp3", "2026-10-20 - Weekly (2).mp3"]
    assert not any(n.endswith(".part") for n in os.listdir(folder))


def test_finalize_renames_even_when_tagging_fails(tmp_path):
    folder = str(tmp_path)
    p = os.path.join(folder, "bad.mp3.part")
    with open(p, "wb") as f:
        f.write(b"this is not an mp3" * 10)
    final, err = core.finalize(p, folder, Tags("2026-10-20", "T"))
    assert os.path.exists(final) and final.endswith("2026-10-20 - T.mp3")


def test_retag_and_rename(tmp_path):
    folder = str(tmp_path)
    p = os.path.join(folder, "old name.mp3")
    _tiny_mp3(p)
    new, err = core.retag_and_rename(p, Tags("2026-10-21", "Fresh title", "Bob"))
    assert err is None and os.path.basename(new) == "2026-10-21 - Fresh title.mp3" and not os.path.exists(p)
    again, _e = core.retag_and_rename(new, Tags("2026-10-21", "Fresh title", "Bob, Ana"))
    assert again == new and core.read_tags(again).people == "Bob, Ana"


def test_list_recordings_newest_first_and_part_files(tmp_path):
    folder = str(tmp_path)
    for i, name in enumerate(["2026-10-01 - A.mp3", "2026-10-02 - B.mp3"]):
        p = os.path.join(folder, name)
        _tiny_mp3(p)
        os.utime(p, (1_700_000_000 + i * 100, 1_700_000_000 + i * 100))
    open(os.path.join(folder, "~recording-1" + core.PART_SUFFIX), "wb").close()
    rows = core.list_recordings(folder)
    assert [r["name"] for r in rows] == ["2026-10-02 - B.mp3", "2026-10-01 - A.mp3"]
    assert len(core.find_part_files(folder)) == 1
    assert core.list_recordings(os.path.join(folder, "missing")) == []


def test_display_helpers():
    assert core.fmt_clock(3725) == "01:02:05" and core.fmt_clock(-3) == "00:00:00"
    assert core.fmt_size(0) == "0 B" and core.fmt_size(1536) == "1.5 KB" and core.fmt_size(5 * 1024 ** 2) == "5.0 MB"
