from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

import omarchy_tweaker.functions.scripts as scripts_module
from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.scripts import (
    ScriptResult,
    discover_scripts,
    get_bin_directory,
    get_script_source_directory,
    link_script,
    make_script_executable,
)


def make_source(tmp_path: Path, *names: str) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    for name in names:
        (source / name).write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    return source


def test_get_bin_directory_uses_home_override(tmp_path: Path) -> None:
    assert get_bin_directory(tmp_path) == tmp_path / ".local" / "bin"


def test_get_script_source_directory_honors_environment_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OMARCHY_TWEAKER_SCRIPTS_DIR", str(tmp_path))
    assert get_script_source_directory() == tmp_path


def test_discover_scripts_returns_regular_visible_files_in_name_order(
    tmp_path: Path,
) -> None:
    source = make_source(tmp_path, "zeta", "alpha", ".hidden")
    (source / "subdir").mkdir()
    (source / "alias").symlink_to(source / "alpha")

    assert [script.name for script in discover_scripts(source)] == ["alpha", "zeta"]


def test_discover_scripts_returns_empty_tuple_for_missing_directory(tmp_path: Path) -> None:
    assert discover_scripts(tmp_path / "missing") == ()


def test_make_script_executable_adds_execute_bits(tmp_path: Path) -> None:
    script = tmp_path / "script"
    script.write_text("#!/bin/bash\n", encoding="utf-8")
    script.chmod(0o644)

    assert make_script_executable(script) is True
    assert stat.S_IMODE(script.stat().st_mode) == 0o755


def test_make_script_executable_is_idempotent(tmp_path: Path) -> None:
    script = tmp_path / "script"
    script.write_text("#!/bin/bash\n", encoding="utf-8")
    script.chmod(0o755)

    assert make_script_executable(script) is False
    assert stat.S_IMODE(script.stat().st_mode) == 0o755


def test_link_script_creates_symlink(tmp_path: Path) -> None:
    source = make_source(tmp_path, "tool") / "tool"
    destination = tmp_path / "bin" / "tool"
    destination.parent.mkdir()

    assert link_script(source, destination) is True
    assert destination.is_symlink()
    assert destination.resolve() == source


def test_link_script_leaves_correct_symlink_unchanged(tmp_path: Path) -> None:
    source = make_source(tmp_path, "tool") / "tool"
    destination = tmp_path / "bin" / "tool"
    destination.parent.mkdir()
    destination.symlink_to(source)

    assert link_script(source, destination) is False
    assert destination.resolve() == source


def test_link_script_replaces_existing_file(tmp_path: Path) -> None:
    source = make_source(tmp_path, "tool") / "tool"
    destination = tmp_path / "bin" / "tool"
    destination.parent.mkdir()
    destination.write_text("old", encoding="utf-8")

    assert link_script(source, destination) is True
    assert destination.is_symlink()
    assert destination.resolve() == source


def test_run_scripts_step_skips_without_bundled_scripts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail(*args: object, **kwargs: object) -> bool:
        raise AssertionError("confirmation should not be requested")

    monkeypatch.setattr(ui, "confirm", fail)

    result = scripts_module.run_scripts_step(
        home=tmp_path,
        source=tmp_path / "missing",
    )

    assert result is ScriptResult.SKIPPED
    assert not (tmp_path / ".local" / "bin").exists()


def test_run_scripts_step_skips_without_interactive_terminal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = make_source(tmp_path, "tool")

    def fail(*args: object, **kwargs: object) -> bool:
        raise AssertionError("confirmation should not be requested")

    monkeypatch.setattr(ui, "is_interactive", lambda: False)
    monkeypatch.setattr(ui, "confirm", fail)

    result = scripts_module.run_scripts_step(home=tmp_path, source=source)

    assert result is ScriptResult.SKIPPED
    assert not (tmp_path / ".local" / "bin").exists()


def test_run_scripts_step_skips_when_declined(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = make_source(tmp_path, "tool")
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)

    result = scripts_module.run_scripts_step(home=tmp_path, source=source)

    assert result is ScriptResult.SKIPPED
    assert not (tmp_path / ".local" / "bin").exists()


def test_run_scripts_step_links_scripts_and_makes_them_executable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = make_source(tmp_path, "tool", "other")
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    result = scripts_module.run_scripts_step(home=tmp_path, source=source)

    assert result is ScriptResult.COMPLETED
    for name in ("tool", "other"):
        destination = tmp_path / ".local" / "bin" / name
        assert destination.is_symlink()
        assert destination.resolve() == source / name
        assert os.access(source / name, os.X_OK)


def test_run_scripts_step_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = make_source(tmp_path, "tool")
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    first = scripts_module.run_scripts_step(home=tmp_path, source=source)
    second = scripts_module.run_scripts_step(home=tmp_path, source=source)

    assert first is ScriptResult.COMPLETED
    assert second is ScriptResult.COMPLETED


def test_run_scripts_step_reports_permission_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = make_source(tmp_path, "tool")
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    def fail(path: Path) -> bool:
        raise OSError("permission denied")

    monkeypatch.setattr(scripts_module, "make_script_executable", fail)

    result = scripts_module.run_scripts_step(home=tmp_path, source=source)

    assert result is ScriptResult.FAILED
    assert not (tmp_path / ".local" / "bin" / "tool").exists()


def test_run_scripts_step_reports_link_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = make_source(tmp_path, "tool")
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    def fail(source: Path, destination: Path) -> bool:
        raise OSError("read-only filesystem")

    monkeypatch.setattr(scripts_module, "link_script", fail)

    result = scripts_module.run_scripts_step(home=tmp_path, source=source)

    assert result is ScriptResult.FAILED


def test_run_scripts_step_reports_bin_directory_creation_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = make_source(tmp_path, "tool")
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "mkdir", fail)

    result = scripts_module.run_scripts_step(home=tmp_path, source=source)

    assert result is ScriptResult.FAILED
