import pytest

import tinyrecorder_player as pl
from conftest import FakeMci


@pytest.fixture
def mp3(tmp_path):
    p = tmp_path / "2026-10-20 - A.mp3"
    p.write_bytes(b"\xff\xfb" * 100)
    return str(p)


def test_play_stop_and_release(mp3):
    fake = FakeMci()
    pr = pl.Player(send=fake.send)
    assert not pr.is_playing() and pr.mode() == "" and pr.position_ms() == 0
    pr.play(mp3, volume=0)
    assert pr.is_playing() and pr.length_ms == 3000 and pr.path == mp3 and pr.position_ms() == 1500
    assert any(c.startswith("setaudio") for c in fake.log)
    pr.stop()
    assert not pr.is_playing() and not fake.is_open and pr.path == "" and pr.length_ms == 0
    pr.stop()                                                      # stopping twice is harmless


def test_end_of_file_is_detected(mp3):
    fake = FakeMci()
    pr = pl.Player(send=fake.send)
    pr.play(mp3)
    assert not pr.finished()
    fake.finish()
    assert pr.finished() and not pr.is_playing()
    pr.stop()
    assert not pr.finished()


def test_playing_another_file_closes_the_first(mp3, tmp_path):
    other = tmp_path / "other.mp3"
    other.write_bytes(b"\xff\xfb" * 100)
    fake = FakeMci()
    pr = pl.Player(send=fake.send)
    pr.play(mp3)
    pr.play(str(other))
    assert fake.path == str(other) and pr.path == str(other)
    assert sum(1 for c in fake.log if c.startswith("close ")) >= 1


def test_missing_and_unplayable_files_raise(tmp_path, mp3):
    fake = FakeMci()
    pr = pl.Player(send=fake.send)
    with pytest.raises(pl.PlayerError):
        pr.play(str(tmp_path / "nope.mp3"))
    assert not fake.is_open

    def refuse(command):
        if command.startswith("open "):
            return 266, "Cannot play this kind of file"
        return 0, ""
    with pytest.raises(pl.PlayerError) as e:
        pl.Player(send=refuse).play(mp3)
    assert "Cannot play" in str(e.value)
