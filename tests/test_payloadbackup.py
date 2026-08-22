from __future__ import annotations

import os
from pathlib import Path

import pytest

from game.payloadbackup import MANIFEST_NAME, backup_payloads


def _library(root: Path, **files: str) -> Path:
    payloads = root / "UnitPayloads"
    payloads.mkdir()
    for name, text in files.items():
        (payloads / name).write_text(text, encoding="utf-8")
    return payloads


def _touch(path: Path, text: str) -> None:
    """Rewrite a payload file so its fingerprint really changes.

    Size alone is not enough -- a same-length edit has to be caught too -- and the
    filesystem's mtime granularity can be coarser than a test's runtime, so stamp it.
    """
    path.write_text(text, encoding="utf-8")
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))


def test_snapshots_the_whole_directory(tmp_path: Path) -> None:
    payloads = _library(
        tmp_path, **{"FA-18C_hornet.lua": "hornet", "F-16C.lua": "viper"}
    )
    backups = tmp_path / "PayloadBackups"

    snapshot = backup_payloads(payloads, backups)

    assert snapshot is not None
    assert (snapshot / "FA-18C_hornet.lua").read_text(encoding="utf-8") == "hornet"
    assert (snapshot / "F-16C.lua").read_text(encoding="utf-8") == "viper"
    assert (snapshot / MANIFEST_NAME).is_file()


def test_second_launch_with_nothing_changed_takes_no_snapshot(tmp_path: Path) -> None:
    payloads = _library(tmp_path, **{"FA-18C_hornet.lua": "hornet"})
    backups = tmp_path / "PayloadBackups"

    assert backup_payloads(payloads, backups) is not None
    assert backup_payloads(payloads, backups) is None
    assert len(list(backups.iterdir())) == 1


def test_an_edited_loadout_takes_a_new_snapshot(tmp_path: Path) -> None:
    payloads = _library(tmp_path, **{"FA-18C_hornet.lua": "hornet"})
    backups = tmp_path / "PayloadBackups"
    backup_payloads(payloads, backups)

    _touch(payloads / "FA-18C_hornet.lua", "hornet+")

    assert backup_payloads(payloads, backups) is not None
    assert len(list(backups.iterdir())) == 2


def test_an_empty_library_is_not_snapshotted(tmp_path: Path) -> None:
    """The case this feature exists for: the directory has just been wiped.

    Snapshotting nothing would push the last real snapshot out of the rotation on every
    launch, destroying the backups exactly when they are the only copy left.
    """
    payloads = _library(tmp_path)
    backups = tmp_path / "PayloadBackups"

    assert backup_payloads(payloads, backups) is None
    assert not backups.exists()


def test_a_wipe_does_not_evict_the_snapshot_that_survives_it(tmp_path: Path) -> None:
    payloads = _library(tmp_path, **{"FA-18C_hornet.lua": "hornet"})
    backups = tmp_path / "PayloadBackups"
    snapshot = backup_payloads(payloads, backups)
    assert snapshot is not None

    for path in payloads.iterdir():
        path.unlink()
    for _ in range(20):
        backup_payloads(payloads, backups, keep=2)

    assert (snapshot / "FA-18C_hornet.lua").read_text(encoding="utf-8") == "hornet"


def test_only_the_newest_snapshots_are_kept(tmp_path: Path) -> None:
    payloads = _library(tmp_path, **{"FA-18C_hornet.lua": "0"})
    backups = tmp_path / "PayloadBackups"

    for generation in range(5):
        _touch(payloads / "FA-18C_hornet.lua", str(generation))
        backup_payloads(payloads, backups, keep=2)

    kept = sorted(backups.iterdir())
    assert len(kept) == 2
    assert (kept[-1] / "FA-18C_hornet.lua").read_text(encoding="utf-8") == "4"


def test_rotation_never_evicts_a_newer_snapshot_for_an_older_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Snapshot order must not depend on the clock or on the directory name.

    Rotation frees a name; a snapshot taken while the clock still reads the same would
    take that freed name back and sort itself before the older snapshots that outlived
    it, and rotation would then keep the oldest and delete the newest. Pinning the clock
    forces every snapshot into that collision.
    """

    class FrozenClock:
        @staticmethod
        def now() -> object:
            class Stamp:
                @staticmethod
                def strftime(fmt: str) -> str:
                    return "20260822-202257-000000"

            return Stamp()

    monkeypatch.setattr("game.payloadbackup.datetime", FrozenClock)
    payloads = _library(tmp_path, **{"FA-18C_hornet.lua": "0"})
    backups = tmp_path / "PayloadBackups"

    for generation in range(5):
        _touch(payloads / "FA-18C_hornet.lua", str(generation))
        backup_payloads(payloads, backups, keep=2)

    kept = [
        (path / "FA-18C_hornet.lua").read_text(encoding="utf-8")
        for path in backups.iterdir()
    ]
    assert sorted(kept) == ["3", "4"]


def test_subdirectories_are_left_out(tmp_path: Path) -> None:
    payloads = _library(tmp_path, **{"FA-18C_hornet.lua": "hornet"})
    (payloads / "_retribution_backups").mkdir()
    backups = tmp_path / "PayloadBackups"

    snapshot = backup_payloads(payloads, backups)

    assert snapshot is not None
    assert not (snapshot / "_retribution_backups").exists()


def test_a_missing_library_is_not_an_error(tmp_path: Path) -> None:
    assert backup_payloads(tmp_path / "gone", tmp_path / "PayloadBackups") is None


def test_a_failure_does_not_propagate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Losing a backup must not stop the app from starting."""
    payloads = _library(tmp_path, **{"FA-18C_hornet.lua": "hornet"})

    def boom(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("game.payloadbackup.shutil.copy2", boom)

    assert backup_payloads(payloads, tmp_path / "PayloadBackups") is None
