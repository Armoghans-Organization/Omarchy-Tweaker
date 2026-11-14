from __future__ import annotations

import shutil
import subprocess
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import cast

import pytest
from rich.progress import Progress

import omarchy_tweaker.functions.plugins as plugins_module
from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.plugins import PluginResult, PluginSpec


class FakeTerminal:
    def __init__(self, *, returncode: int = 0, error: BaseException | None = None) -> None:
        self.returncode = returncode
        self.error = error
        self.commands: list[tuple[str, ...]] = []
        self.lines: list[str] = []
        self.writes: list[str] = []

    def run(self, command: Sequence[str], **kwargs: object) -> int:
        self.commands.append(tuple(command))
        if self.error is not None:
            raise self.error
        return self.returncode

    def writeline(self, line: str, *, style: str | None = None) -> None:
        self.lines.append(line)

    def write(self, text: str, **kwargs: object) -> None:
        self.writes.append(text)


class FakeProgress:
    def __init__(self) -> None:
        self.tasks: list[tuple[str, int | None]] = []
        self.updated: list[tuple[int, str]] = []
        self.advanced: list[int] = []

    def add_task(self, description: str, *, total: int | None = None) -> int:
        task_id = len(self.tasks)
        self.tasks.append((description, total))
        return task_id

    def update(self, task_id: int, *, description: str) -> None:
        self.updated.append((task_id, description))

    def advance(self, task_id: int) -> None:
        self.advanced.append(task_id)


@contextmanager
def fake_terminal_with_progress(
    **kwargs: object,
) -> Iterator[tuple[ui.VirtualTerminal, Progress]]:
    yield (
        cast(ui.VirtualTerminal, FakeTerminal()),
        cast(Progress, FakeProgress()),
    )


def _plugin(**overrides: object) -> PluginSpec:
    values: dict[str, object] = {
        "name": "Spotlight",
        "url": "https://github.com/maajix/omarchy-spotlight.git",
        "description": "A Raycast-style launcher for Omarchy",
    }
    values.update(overrides)
    return PluginSpec(**values)  # type: ignore[arg-type]


def test_load_plugin_catalog_reads_ini_in_order(tmp_path: Path) -> None:
    catalog = tmp_path / "plugins.ini"
    catalog.write_text(
        """
[Alpha]
name=Alpha
url=https://example.com/alpha.git
description=First plugin
patch=true
patch-file=alpha.patch
position=left

[Beta]
name=Beta
url=https://example.com/beta.git
description=Second plugin
patch=false
patch-file=none
""",
        encoding="utf-8",
    )

    loaded = plugins_module.load_plugin_catalog(catalog)

    assert [plugin.name for plugin in loaded] == ["Alpha", "Beta"]
    assert loaded[0] == PluginSpec(
        name="Alpha",
        url="https://example.com/alpha.git",
        description="First plugin",
        patch=True,
        patch_file="alpha.patch",
        position="left",
    )
    assert loaded[1].patch is False
    assert loaded[1].patch_file is None
    assert loaded[1].position is None


def test_load_plugin_catalog_skips_missing_url(tmp_path: Path) -> None:
    catalog = tmp_path / "plugins.ini"
    catalog.write_text(
        """
[Broken]
name=Broken
description=No URL
""",
        encoding="utf-8",
    )

    assert plugins_module.load_plugin_catalog(catalog) == ()


def test_load_plugin_catalog_ignores_unsafe_patch_and_position(tmp_path: Path) -> None:
    catalog = tmp_path / "plugins.ini"
    catalog.write_text(
        """
[Unsafe]
name=Unsafe
url=https://example.com/unsafe.git
description=Unsafe values
patch=true
patch-file=../outside.patch
position=middle
""",
        encoding="utf-8",
    )

    loaded = plugins_module.load_plugin_catalog(catalog)

    assert loaded[0].patch is False
    assert loaded[0].patch_file is None
    assert loaded[0].position is None


def test_select_plugins_returns_selected_catalog_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = (
        _plugin(name="Alpha"),
        _plugin(name="Beta"),
        _plugin(name="Gamma"),
    )
    shown_choices: list[str] = []

    def fake_checkbox(
        message: str,
        choices: Sequence[str],
        **kwargs: object,
    ) -> list[str]:
        assert message == "Select Omarchy Plugins to install:"
        shown_choices.extend(choices)
        return ["Gamma", "Alpha"]

    monkeypatch.setattr(ui, "checkbox", fake_checkbox)

    assert plugins_module._select_plugins(catalog) == (catalog[0], catalog[2])
    assert shown_choices == ["Alpha", "Beta", "Gamma"]


def test_install_plugin_runs_add_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = FakeTerminal()
    progress = FakeProgress()
    monkeypatch.setattr(plugins_module, "_list_plugin_ids", lambda: frozenset())

    assert plugins_module._install_plugin(
        _plugin(),
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
        patches_directory=Path("/missing"),
    )

    assert terminal.commands == [
        (
            "omarchy",
            "plugin",
            "add",
            "https://github.com/maajix/omarchy-spotlight.git",
            "--yes",
            "--enable",
        )
    ]
    assert progress.tasks == [("Installing Spotlight", None)]
    assert progress.updated == [(0, "Installed Spotlight")]
    assert progress.advanced == [0]


def test_install_plugin_applies_configured_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = FakeTerminal()
    progress = FakeProgress()
    snapshots = iter(
        [
            frozenset({"existing"}),
            frozenset({"existing", "io.github.maajix.spotlight"}),
        ]
    )
    monkeypatch.setattr(plugins_module, "_list_plugin_ids", lambda: next(snapshots))

    assert plugins_module._install_plugin(
        _plugin(position="center"),
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
        patches_directory=Path("/missing"),
    )

    assert terminal.commands == [
        (
            "omarchy",
            "plugin",
            "add",
            "https://github.com/maajix/omarchy-spotlight.git",
            "--yes",
            "--enable",
        ),
        (
            "omarchy",
            "plugin",
            "enable",
            "io.github.maajix.spotlight",
            "--section",
            "center",
        ),
    ]


def test_install_plugin_keeps_default_when_id_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = FakeTerminal()
    progress = FakeProgress()
    snapshots = iter([frozenset({"existing"}), frozenset({"existing"})])
    monkeypatch.setattr(plugins_module, "_list_plugin_ids", lambda: next(snapshots))

    assert plugins_module._install_plugin(
        _plugin(position="right"),
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
        patches_directory=Path("/missing"),
    )

    assert terminal.commands == [
        (
            "omarchy",
            "plugin",
            "add",
            "https://github.com/maajix/omarchy-spotlight.git",
            "--yes",
            "--enable",
        )
    ]
    assert any("default placement" in line for line in terminal.lines)


def test_install_plugin_applies_patch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    terminal = FakeTerminal()
    progress = FakeProgress()
    patch = tmp_path / "spotlight.patch"
    patch.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    calls: list[tuple[Sequence[str], dict[str, object]]] = []

    def fake_run(
        command: Sequence[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "patched\n", "")

    monkeypatch.setattr(shutil, "which", lambda name: "/bin/bash")
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(plugins_module, "_list_plugin_ids", lambda: frozenset())

    assert plugins_module._install_plugin(
        _plugin(patch=True, patch_file="spotlight.patch"),
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
        patches_directory=tmp_path,
    )

    assert calls[0][0] == ["/bin/bash", str(patch)]
    assert calls[0][1]["input"] == plugins_module.PATCH_CONFIRM_INPUT
    assert terminal.writes == ["patched\n"]


def test_install_plugin_reports_missing_patch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    terminal = FakeTerminal()
    progress = FakeProgress()
    monkeypatch.setattr(plugins_module, "_list_plugin_ids", lambda: frozenset())

    assert not plugins_module._install_plugin(
        _plugin(patch=True, patch_file="missing.patch"),
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
        patches_directory=tmp_path,
    )

    assert progress.updated == [(0, "Failed Spotlight")]
    assert any("patch was not found" in line for line in terminal.lines)


def test_installed_plugin_id_matches_repository_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plugin_dir = tmp_path / ".config" / "omarchy" / "plugins" / "io.github.maajix.spotlight"
    git_dir = plugin_dir / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/maajix/omarchy-spotlight.git\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    assert (
        plugins_module._installed_plugin_id(
            _plugin(),
            frozenset({"io.github.maajix.spotlight"}),
        )
        == "io.github.maajix.spotlight"
    )


def test_install_plugin_skips_when_already_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = FakeTerminal()
    progress = FakeProgress()
    monkeypatch.setattr(plugins_module, "_list_plugin_ids", lambda: frozenset())
    monkeypatch.setattr(
        plugins_module,
        "_installed_plugin_id",
        lambda plugin, installed_ids: "io.github.maajix.spotlight",
    )

    assert plugins_module._install_plugin(
        _plugin(),
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
        patches_directory=Path("/missing"),
    )

    assert terminal.commands == []
    assert any("already installed" in line for line in terminal.lines)
    assert progress.updated == [(0, "Already installed Spotlight")]


def test_run_plugins_step_skips_without_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ui, "is_interactive", lambda: False)
    monkeypatch.setattr(ui, "section", lambda *args, **kwargs: None)
    monkeypatch.setattr(ui, "warning", lambda *args, **kwargs: None)

    assert plugins_module.run_plugins_step(plugins=(_plugin(),)) is PluginResult.SKIPPED


def test_run_plugins_step_skips_when_nothing_is_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "section", lambda *args, **kwargs: None)
    monkeypatch.setattr(ui, "checkbox", lambda *args, **kwargs: [])
    monkeypatch.setattr(ui, "info", lambda *args, **kwargs: None)

    assert plugins_module.run_plugins_step(plugins=(_plugin(),)) is PluginResult.SKIPPED


def test_run_plugins_step_reports_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "section", lambda *args, **kwargs: None)
    monkeypatch.setattr(ui, "checkbox", lambda *args, **kwargs: ["Spotlight"])
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(ui, "terminal_with_progress", fake_terminal_with_progress)
    monkeypatch.setattr(ui, "error", lambda *args, **kwargs: None)
    monkeypatch.setattr(plugins_module, "_install_plugin", lambda *args, **kwargs: False)

    assert plugins_module.run_plugins_step(plugins=(_plugin(),)) is PluginResult.FAILED


def test_run_plugins_step_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "section", lambda *args, **kwargs: None)
    monkeypatch.setattr(ui, "checkbox", lambda *args, **kwargs: ["Spotlight"])
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(ui, "terminal_with_progress", fake_terminal_with_progress)
    monkeypatch.setattr(ui, "success", lambda *args, **kwargs: None)
    monkeypatch.setattr(plugins_module, "_install_plugin", lambda *args, **kwargs: True)
    monkeypatch.setattr(plugins_module, "_install_shell_config", lambda *args, **kwargs: True)

    assert plugins_module.run_plugins_step(plugins=(_plugin(),)) is PluginResult.COMPLETED


def test_install_shell_config_copies_and_sets_permissions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "config" / "shell.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"plugins": []}')

    dest_dir = tmp_path / ".config" / "omarchy"
    dest_dir.mkdir(parents=True)
    dest = dest_dir / "shell.json"
    dest.write_text('{"old": true}')

    monkeypatch.setattr(plugins_module, "_get_shell_config_source", lambda: source)
    monkeypatch.setattr(plugins_module, "_get_shell_config_destination", lambda: dest)
    monkeypatch.setattr(
        plugins_module, "_set_shell_config_permissions", lambda *args, **kwargs: True
    )
    monkeypatch.setattr(time, "strftime", lambda fmt: "20240101000000")

    terminal = FakeTerminal()
    progress = FakeProgress()

    assert plugins_module._install_shell_config(
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
    )

    assert dest.exists()
    assert dest.read_text() == '{"plugins": []}'

    backup = dest_dir / "shell.json.bak.20240101000000"
    assert backup.exists()
    assert backup.read_text() == '{"old": true}'

    assert any("Backed up" in line for line in terminal.lines)


def test_install_shell_config_handles_missing_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "config" / "shell.json"
    dest = tmp_path / ".config" / "omarchy" / "shell.json"

    monkeypatch.setattr(plugins_module, "_get_shell_config_source", lambda: source)
    monkeypatch.setattr(plugins_module, "_get_shell_config_destination", lambda: dest)

    terminal = FakeTerminal()
    progress = FakeProgress()

    assert not plugins_module._install_shell_config(
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
    )

    assert any("not found" in line for line in terminal.lines)


def test_install_shell_config_handles_permission_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "config" / "shell.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"plugins": []}')

    dest_dir = tmp_path / ".config" / "omarchy"
    dest_dir.mkdir(parents=True)
    dest = dest_dir / "shell.json"

    monkeypatch.setattr(plugins_module, "_get_shell_config_source", lambda: source)
    monkeypatch.setattr(plugins_module, "_get_shell_config_destination", lambda: dest)
    monkeypatch.setattr(
        plugins_module, "_set_shell_config_permissions", lambda *args, **kwargs: False
    )

    terminal = FakeTerminal()
    progress = FakeProgress()

    assert not plugins_module._install_shell_config(
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
    )

    assert any("Shell config permissions could not be set" in line for line in terminal.lines)
