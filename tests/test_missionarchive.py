"""Tests for the generated-mission archive.

Covers the naming (campaign + turn + stamp), the copy, and the three properties
the feature rests on: a re-generated turn never clobbers the copy of the one that
was flown, the prune only ever deletes files the archive itself wrote, and an
archive failure is never fatal to mission generation.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from game import missionarchive as mission_archive
from game.missionarchive import (
    _prune,
    archive_mission,
    archive_name_for,
)

if TYPE_CHECKING:
    from game import Game

WHEN = datetime(2026, 7, 16, 19, 32, 5)


@pytest.fixture
def archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the archive at a throwaway directory."""
    directory = tmp_path / "Retribution Archive"
    directory.mkdir()
    monkeypatch.setattr(mission_archive, "mission_archive_dir", lambda: directory)
    return directory


def _fake_game(
    campaign_name: str | None = "Germany 1980 - Red Tide", turn: int = 3
) -> Game:
    """The archive only reads these two fields; faking them keeps the test fast."""
    return SimpleNamespace(campaign_name=campaign_name, turn=turn)  # type: ignore[return-value]


def _generated_miz(tmp_path: Path, content: bytes = b"miz") -> Path:
    miz = tmp_path / "retribution_nextturn.miz"
    miz.write_bytes(content)
    return miz


def _touch(directory: Path, name: str, mtime: float) -> Path:
    path = directory / name
    path.write_bytes(b"miz")
    os.utime(path, (mtime, mtime))
    return path


def test_archive_name_carries_campaign_and_turn() -> None:
    assert (
        archive_name_for(_fake_game(), WHEN)
        == "germany_1980_red_tide_turn03_20260716-193205.miz"
    )


def test_archive_name_slugifies_awkward_campaign_names() -> None:
    name = archive_name_for(_fake_game("Op. Höllenhund/Phase 2!"), WHEN)
    assert name == "op_h_llenhund_phase_2_turn03_20260716-193205.miz"


def test_archive_name_falls_back_when_the_campaign_is_unnamed() -> None:
    assert archive_name_for(_fake_game(None), WHEN).startswith("campaign_turn03_")


def test_regenerating_a_turn_does_not_clobber_the_flown_copy() -> None:
    """The whole point: two generations of one turn are two distinct files."""
    game = _fake_game()
    flown = archive_name_for(game, WHEN)
    regenerated = archive_name_for(game, datetime(2026, 7, 16, 20, 1, 0))
    assert flown != regenerated


def test_archive_copies_the_generated_mission(tmp_path: Path, archive: Path) -> None:
    miz = _generated_miz(tmp_path, b"the flown mission")

    archived = archive_mission(_fake_game(), miz)

    assert archived is not None
    assert archived.parent == archive
    assert archived.read_bytes() == b"the flown mission"
    # The fixed output is left exactly where DCS and the wiki expect it.
    assert miz.exists()


def test_prune_keeps_only_the_newest(
    archive: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mission_archive, "KEEP_ARCHIVED_MISSIONS", 2)
    oldest = _touch(archive, "rt_turn01_20260716-100000.miz", 1_000)
    older = _touch(archive, "rt_turn02_20260716-110000.miz", 2_000)
    newer = _touch(archive, "rt_turn03_20260716-120000.miz", 3_000)
    newest = _touch(archive, "rt_turn04_20260716-130000.miz", 4_000)

    _prune(archive)

    assert not oldest.exists()
    assert not older.exists()
    assert newer.exists()
    assert newest.exists()


def test_prune_never_touches_files_it_did_not_write(
    archive: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hand-named miz dropped in the archive is not ours to delete."""
    monkeypatch.setattr(mission_archive, "KEEP_ARCHIVED_MISSIONS", 1)
    hand_named = _touch(archive, "Red Tide M1.miz", 1_000)
    backup = _touch(archive, "Red Tide Backup.miz", 1_100)
    notes = _touch(archive, "notes.txt", 1_200)
    ours = _touch(archive, "rt_turn09_20260716-130000.miz", 4_000)

    _prune(archive)

    assert hand_named.exists()
    assert backup.exists()
    assert notes.exists()
    assert ours.exists()


def test_archive_failure_is_not_fatal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A generated mission must survive an unwritable archive."""

    def boom() -> Path:
        raise OSError("read-only filesystem")

    monkeypatch.setattr(mission_archive, "mission_archive_dir", boom)
    miz = _generated_miz(tmp_path)

    assert archive_mission(_fake_game(), miz) is None
    assert miz.exists()


def test_archive_survives_persistency_not_being_set_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Headless tests and dev scripts never call persistency.setup()."""

    def unset() -> Path:
        assert None, "persistency.setup() not called"
        raise AssertionError

    monkeypatch.setattr(mission_archive, "mission_archive_dir", unset)

    assert archive_mission(_fake_game(), _generated_miz(tmp_path)) is None
