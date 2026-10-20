import os

import tinyrecorder_core as core
from tinyrecorder_core import Tags
from test_core import _tiny_mp3


def test_every_file_gets_the_fixed_copyright_tag(tmp_path):
    from mutagen.id3 import ID3
    folder = str(tmp_path)
    p = os.path.join(folder, "c.mp3.part")
    _tiny_mp3(p)
    final, err = core.finalize(p, folder, Tags("2026-10-20", "Copyright test"))
    assert err is None
    assert str(ID3(final)["TCOP"].text[0]) == "not for distribution, personal use only" == core.COPYRIGHT_TEXT
    new, err = core.retag_and_rename(final, Tags("2026-10-21", "Edited", "Ana"))          # kept when edited
    assert str(ID3(new)["TCOP"].text[0]) == core.COPYRIGHT_TEXT
    assert len(ID3(new).getall("TCOP")) == 1
    old = os.path.join(folder, "old.mp3")                                                  # a file without the tag
    _tiny_mp3(old)
    core.retag_and_rename(old, Tags("2026-10-22", "Old file"))
    assert str(ID3(os.path.join(folder, "2026-10-22 - Old file.mp3"))["TCOP"].text[0]) == core.COPYRIGHT_TEXT


def test_copyright_tag_is_not_part_of_the_editable_fields(tmp_path):
    p = os.path.join(str(tmp_path), "n.mp3")
    _tiny_mp3(p)
    t = Tags("2026-10-20", "T", "P", "Pr", "a note")
    assert core.write_tags(p, t) is None
    assert core.read_tags(p) == t                                   # notes stay the user's own text


def test_links_and_licence_constants():
    assert core.APP_REPO_URL == "https://github.com/junqueirach/tiny-recorder"
    assert core.APP_ISSUES_URL == core.APP_REPO_URL + "/issues" and core.APP_LICENCE == "MIT"
