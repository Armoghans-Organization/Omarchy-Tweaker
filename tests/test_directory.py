from __future__ import annotations

from pathlib import Path

import pytest

import omarchy_tweaker.functions.directory as directory_module
from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.directory import (
    REQUIRED_DIRECTORIES,
    DirectoryResult,
    create_directory,
)


def test_directory_targets_use_expected_paths(tmp_path: Path) -> None:
    assert [target.display_path for target in REQUIRED_DIRECTORIES] == [
        "~/Github",
        "~/Github/Clone",
        "~/Projects",
        "~/Projects/Containers",
        "~/.ISO",
        "~/.VM",
        "~/.Cloud",
    ]
    assert REQUIRED_DIRECTORIES[0].path_for(tmp_path) == tmp_path / "Github"


def test_create_directory_creates_one_directory(tmp_path: Path) -> None:
    path = tmp_path / "single"

    create_directory(path)

    assert path.is_dir()


def test_create_directory_does_not_create_missing_parents(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        create_directory(tmp_path / "missing" / "child")


def test_run_directory_step_skips_without_interactive_terminal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail(*args: object, **kwargs: object) -> bool:
        raise AssertionError("confirmation should not be requested")

    monkeypatch.setattr(ui, "is_interactive", lambda: False)
    monkeypatch.setattr(ui, "confirm", fail)

    assert directory_module.run_directory_step(home=tmp_path) is DirectoryResult.SKIPPED
    assert not any(target.path_for(tmp_path).exists() for target in REQUIRED_DIRECTORIES)


def test_run_directory_step_completes_when_all_directories_exist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail(*args: object, **kwargs: object) -> bool:
        raise AssertionError("confirmation should not be requested")

    for target in REQUIRED_DIRECTORIES:
        target.path_for(tmp_path).mkdir(parents=True)
    monkeypatch.setattr(ui, "confirm", fail)

    assert directory_module.run_directory_step(home=tmp_path) is DirectoryResult.COMPLETED


def test_run_directory_step_creates_accepted_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    result = directory_module.run_directory_step(home=tmp_path)

    assert result is DirectoryResult.COMPLETED
    assert all(target.path_for(tmp_path).is_dir() for target in REQUIRED_DIRECTORIES)


def test_run_directory_step_skips_declined_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)

    result = directory_module.run_directory_step(home=tmp_path)

    assert result is DirectoryResult.SKIPPED
    assert not any(target.path_for(tmp_path).exists() for target in REQUIRED_DIRECTORIES)


def test_run_directory_step_skips_child_when_parent_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    answers = {
        "Create ~/Github?": False,
        "Create ~/Github/Clone?": True,
    }

    def confirm(message: str, **kwargs: object) -> bool:
        return answers.get(message, False)

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", confirm)

    result = directory_module.run_directory_step(home=tmp_path)

    assert result is DirectoryResult.SKIPPED
    assert not (tmp_path / "Github").exists()
    assert not (tmp_path / "Github" / "Clone").exists()


def test_run_directory_step_reports_existing_file_conflict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    conflict = tmp_path / "Github"
    conflict.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)

    result = directory_module.run_directory_step(home=tmp_path)

    assert result is DirectoryResult.FAILED
    assert conflict.is_file()


def test_run_directory_step_reports_creation_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail(path: Path) -> None:
        raise OSError("permission denied")

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(directory_module, "create_directory", fail)

    result = directory_module.run_directory_step(home=tmp_path)

    assert result is DirectoryResult.FAILED
    assert not any(target.path_for(tmp_path).exists() for target in REQUIRED_DIRECTORIES)
