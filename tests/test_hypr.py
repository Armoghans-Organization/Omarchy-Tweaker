from __future__ import annotations

from pathlib import Path

import pytest

import omarchy_tweaker.functions.hypr as hypr_module
from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.hypr import (
    WORKSPACES_REQUIRE,
    HyprResult,
    append_workspaces_require,
    discover_hypr_files,
    get_hypr_config_directory,
    get_hypr_source_directory,
    link_hypr_file,
)


def test_get_hypr_source_directory_uses_bundled_directory() -> None:
    source = get_hypr_source_directory()

    assert source.name == "hypr"
    assert source.is_dir()


def test_get_hypr_source_directory_honors_environment_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OMARCHY_TWEAKER_HYPR_DIR", str(tmp_path))

    assert get_hypr_source_directory() == tmp_path


def test_bundled_hypr_catalog_contains_expected_files() -> None:
    names = {file.name for file in discover_hypr_files(get_hypr_source_directory())}

    assert {"bindings.lua", "input.lua", "looknfeel.lua", "workspaces.lua"} <= names


def test_get_hypr_config_directory_uses_home_override(tmp_path: Path) -> None:
    assert get_hypr_config_directory(tmp_path) == tmp_path / ".config" / "hypr"


def test_discover_hypr_files_returns_regular_files_in_name_order(tmp_path: Path) -> None:
    (tmp_path / "input.lua").write_text("input", encoding="utf-8")
    (tmp_path / "bindings.lua").write_text("bindings", encoding="utf-8")
    (tmp_path / "nested").mkdir()

    assert discover_hypr_files(tmp_path) == (
        tmp_path / "bindings.lua",
        tmp_path / "input.lua",
    )


def test_discover_hypr_files_returns_empty_tuple_for_missing_directory(
    tmp_path: Path,
) -> None:
    assert discover_hypr_files(tmp_path / "missing") == ()


def test_link_hypr_file_creates_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source" / "bindings.lua"
    source.parent.mkdir()
    source.write_text("bindings", encoding="utf-8")
    destination = tmp_path / "config" / "bindings.lua"
    destination.parent.mkdir()

    assert link_hypr_file(source, destination) is True
    assert destination.is_symlink()
    assert destination.resolve() == source.resolve()


def test_link_hypr_file_replaces_existing_file(tmp_path: Path) -> None:
    source = tmp_path / "source" / "bindings.lua"
    source.parent.mkdir()
    source.write_text("new", encoding="utf-8")
    destination = tmp_path / "config" / "bindings.lua"
    destination.parent.mkdir()
    destination.write_text("old", encoding="utf-8")

    assert link_hypr_file(source, destination) is True
    assert destination.is_symlink()
    assert destination.read_text(encoding="utf-8") == "new"


def test_link_hypr_file_leaves_correct_symlink_unchanged(tmp_path: Path) -> None:
    source = tmp_path / "bindings.lua"
    source.write_text("bindings", encoding="utf-8")
    destination = tmp_path / "linked.lua"
    destination.symlink_to(source)

    assert link_hypr_file(source, destination) is False
    assert destination.is_symlink()
    assert destination.resolve() == source.resolve()


def test_link_hypr_file_replaces_wrong_symlink(tmp_path: Path) -> None:
    source = tmp_path / "bindings.lua"
    source.write_text("bindings", encoding="utf-8")
    other = tmp_path / "other.lua"
    other.write_text("other", encoding="utf-8")
    destination = tmp_path / "linked.lua"
    destination.symlink_to(other)

    assert link_hypr_file(source, destination) is True
    assert destination.resolve() == source.resolve()


def test_link_hypr_file_raises_for_directory_conflict(tmp_path: Path) -> None:
    source = tmp_path / "source" / "bindings.lua"
    source.parent.mkdir()
    source.write_text("bindings", encoding="utf-8")
    destination = tmp_path / "config" / "bindings.lua"
    destination.parent.mkdir()
    destination.mkdir()

    with pytest.raises(OSError):
        link_hypr_file(source, destination)


def test_append_workspaces_require_appends_line_at_end(tmp_path: Path) -> None:
    hyprland_lua = tmp_path / "hyprland.lua"
    hyprland_lua.write_text('require("hypr.input")\n', encoding="utf-8")

    assert append_workspaces_require(hyprland_lua) is True
    assert hyprland_lua.read_text(encoding="utf-8") == (
        f'require("hypr.input")\n{WORKSPACES_REQUIRE}\n'
    )


def test_append_workspaces_require_adds_missing_newline(tmp_path: Path) -> None:
    hyprland_lua = tmp_path / "hyprland.lua"
    hyprland_lua.write_text('require("hypr.input")', encoding="utf-8")

    assert append_workspaces_require(hyprland_lua) is True
    assert hyprland_lua.read_text(encoding="utf-8") == (
        f'require("hypr.input")\n{WORKSPACES_REQUIRE}\n'
    )


def test_append_workspaces_require_is_idempotent(tmp_path: Path) -> None:
    hyprland_lua = tmp_path / "hyprland.lua"
    hyprland_lua.write_text(f"  {WORKSPACES_REQUIRE}  \n", encoding="utf-8")

    assert append_workspaces_require(hyprland_lua) is False
    assert hyprland_lua.read_text(encoding="utf-8") == f"  {WORKSPACES_REQUIRE}  \n"


def test_append_workspaces_require_raises_for_missing_entrypoint(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        append_workspaces_require(tmp_path / "missing.lua")


def test_run_hypr_step_skips_without_interactive_terminal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail(*args: object, **kwargs: object) -> bool:
        raise AssertionError("confirmation should not be requested")

    source = tmp_path / "source"
    source.mkdir()
    (source / "bindings.lua").write_text("bindings", encoding="utf-8")
    monkeypatch.setattr(ui, "is_interactive", lambda: False)
    monkeypatch.setattr(ui, "confirm", fail)

    result = hypr_module.run_hypr_step(home=tmp_path, source=source)

    assert result is HyprResult.SKIPPED
    assert not (get_hypr_config_directory(tmp_path) / "bindings.lua").exists()


def test_run_hypr_step_skips_when_declined(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "bindings.lua").write_text("bindings", encoding="utf-8")
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)

    result = hypr_module.run_hypr_step(home=tmp_path, source=source)

    assert result is HyprResult.SKIPPED
    assert not (get_hypr_config_directory(tmp_path) / "bindings.lua").exists()


def test_run_hypr_step_skips_when_no_bundled_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail(*args: object, **kwargs: object) -> bool:
        raise AssertionError("confirmation should not be requested")

    monkeypatch.setattr(ui, "confirm", fail)

    assert hypr_module.run_hypr_step(home=tmp_path, source=tmp_path / "missing") is (
        HyprResult.SKIPPED
    )


def test_run_hypr_step_links_files_and_adds_require(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "bindings.lua").write_text("bindings", encoding="utf-8")
    (source / "workspaces.lua").write_text("workspaces", encoding="utf-8")
    config = get_hypr_config_directory(tmp_path)
    config.mkdir(parents=True)
    (config / "bindings.lua").write_text("old", encoding="utf-8")
    hyprland_lua = config / "hyprland.lua"
    hyprland_lua.write_text('require("hypr.input")\n', encoding="utf-8")
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    result = hypr_module.run_hypr_step(home=tmp_path, source=source)

    assert result is HyprResult.COMPLETED
    assert (config / "bindings.lua").is_symlink()
    assert (config / "bindings.lua").resolve() == (source / "bindings.lua").resolve()
    assert (config / "workspaces.lua").is_symlink()
    assert hyprland_lua.read_text(encoding="utf-8").endswith(f"{WORKSPACES_REQUIRE}\n")


def test_run_hypr_step_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "bindings.lua").write_text("bindings", encoding="utf-8")
    config = get_hypr_config_directory(tmp_path)
    config.mkdir(parents=True)
    (config / "bindings.lua").symlink_to(source / "bindings.lua")
    hyprland_lua = config / "hyprland.lua"
    hyprland_lua.write_text(f"{WORKSPACES_REQUIRE}\n", encoding="utf-8")
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    result = hypr_module.run_hypr_step(home=tmp_path, source=source)

    assert result is HyprResult.COMPLETED
    assert hyprland_lua.read_text(encoding="utf-8").count(WORKSPACES_REQUIRE) == 1


def test_run_hypr_step_reports_link_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "bindings.lua").write_text("bindings", encoding="utf-8")
    (get_hypr_config_directory(tmp_path)).mkdir(parents=True)
    (get_hypr_config_directory(tmp_path) / "bindings.lua").mkdir()
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    assert hypr_module.run_hypr_step(home=tmp_path, source=source) is HyprResult.FAILED


def test_run_hypr_step_reports_require_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "bindings.lua").write_text("bindings", encoding="utf-8")
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    assert hypr_module.run_hypr_step(home=tmp_path, source=source) is HyprResult.FAILED
