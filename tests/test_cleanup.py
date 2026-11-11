from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import cast

import pytest
from rich.progress import Progress

import omarchy_tweaker.functions.cleanup as cleanup_module
from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.cleanup import (
    CleanupCategory,
    CleanupItem,
    CleanupReport,
    CleanupResult,
)


class FakeTerminal:
    def __init__(self, *, returncode: int = 0) -> None:
        self.returncode = returncode
        self.commands: list[tuple[str, ...]] = []
        self.environments: list[dict[str, str]] = []
        self.lines: list[str] = []

    def run(
        self,
        command: Sequence[str],
        *,
        env: dict[str, str] | None = None,
        **kwargs: object,
    ) -> int:
        self.commands.append(tuple(command))
        if env is not None:
            self.environments.append(env)
        return self.returncode

    def writeline(self, line: str, *, style: str | None = None) -> None:
        self.lines.append(line)


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


def _write_desktop(directory: Path, name: str, exec_line: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.desktop").write_text(
        f"[Desktop Entry]\nType=Application\nExec={exec_line}\n",
        encoding="utf-8",
    )


def _package_item(name: str) -> CleanupItem:
    return CleanupItem(CleanupCategory.PACKAGE, name, name)


def _webapp_item(name: str) -> CleanupItem:
    return CleanupItem(CleanupCategory.WEBAPP, name, name)


def _tui_item(name: str) -> CleanupItem:
    return CleanupItem(CleanupCategory.TUI, name, name)


def _mise_item(name: str, path: Path) -> CleanupItem:
    return CleanupItem(CleanupCategory.MISE, name, str(path))


def test_get_installed_packages_returns_pacman_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        assert command == ["pacman", "-Qq"]
        return subprocess.CompletedProcess(command, 0, stdout="aether\npamac\n", stderr="")

    monkeypatch.setattr(shutil, "which", lambda _: "pacman")
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert cleanup_module.get_installed_packages() == frozenset({"aether", "pamac"})


def test_get_installed_packages_returns_empty_when_pacman_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)

    assert cleanup_module.get_installed_packages() == frozenset()


def test_get_installed_packages_returns_empty_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="failed")

    monkeypatch.setattr(shutil, "which", lambda _: "pacman")
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert cleanup_module.get_installed_packages() == frozenset()


def test_discover_mise_wrappers_finds_only_regular_mise_files(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    wrapper = bin_dir / "codex"
    wrapper.write_text(
        "#!/usr/bin/env bash\nmise use -g --quiet codex\n",
        encoding="utf-8",
    )
    non_wrapper = bin_dir / "tool"
    non_wrapper.write_text("#!/usr/bin/env bash\necho tool\n", encoding="utf-8")
    alias = bin_dir / "alias"
    alias.symlink_to(wrapper)

    assert cleanup_module.discover_mise_wrappers(bin_dir) == (wrapper,)


def test_available_cleanup_items_returns_only_installed_candidates(
    tmp_path: Path,
) -> None:
    applications = tmp_path / "applications"
    _write_desktop(applications, "Docker", "xdg-terminal-exec -e lazydocker")
    _write_desktop(applications, "YouTube", "omarchy-launch-webapp https://youtube.com")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    wrapper = bin_dir / "codex"
    wrapper.write_text(
        "#!/usr/bin/env bash\nmise use -g --quiet codex\n",
        encoding="utf-8",
    )

    items = cleanup_module.available_cleanup_items(
        applications_dir=applications,
        bin_dir=bin_dir,
        installed_packages={"aether", "lazydocker", "not-a-candidate"},
    )

    assert _package_item("aether") in items
    assert _package_item("lazydocker") in items
    assert _package_item("cliamp") not in items
    assert _webapp_item("YouTube") in items
    assert _tui_item("Docker") in items
    assert _mise_item("codex", wrapper) in items


def test_remove_selected_items_with_terminal_streams_packages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = FakeTerminal()
    item = _package_item("aether")

    def fail(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("subprocess should not be used when a terminal is supplied")

    monkeypatch.setattr(subprocess, "run", fail)

    report = cleanup_module.remove_selected_items(
        (item,),
        terminal=cast(ui.VirtualTerminal, terminal),
    )

    assert report == CleanupReport(removed=(item,), failed=())
    assert terminal.commands == [("omarchy", "pkg", "drop", "aether")]
    assert terminal.environments[0]["OMARCHY_REMOVE_NOTIFY"] == "false"
    assert any("Removing 1 package" in line for line in terminal.lines)


def test_remove_selected_items_without_terminal_uses_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    mise_path = tmp_path / ".local/bin/codex"
    mise_path.parent.mkdir(parents=True)
    mise_path.write_text("#!/usr/bin/env bash\nmise use -g --quiet codex\n", encoding="utf-8")

    commands: list[tuple[str, ...]] = []
    environments: list[dict[str, str]] = []

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        commands.append(tuple(command))
        environment = kwargs.get("env")
        assert isinstance(environment, dict)
        environments.append(environment)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    items = (
        _package_item("aether"),
        _webapp_item("YouTube"),
        _tui_item("Docker"),
        _mise_item("Codex", mise_path),
    )

    report = cleanup_module.remove_selected_items(items)

    assert report == CleanupReport(removed=items, failed=())
    assert commands == [
        ("omarchy", "pkg", "drop", "aether"),
        ("omarchy", "webapp", "remove", "YouTube"),
        ("omarchy", "tui", "remove", "Docker"),
    ]
    assert all(environment["OMARCHY_REMOVE_NOTIFY"] == "false" for environment in environments)
    assert not mise_path.exists()


def test_remove_selected_items_reports_package_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="failed")

    monkeypatch.setattr(subprocess, "run", fake_run)

    item = _package_item("aether")
    report = cleanup_module.remove_selected_items((item,))

    assert report == CleanupReport(removed=(), failed=(item,))


def test_remove_selected_items_rejects_mise_path_outside_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    item = _mise_item("Unsafe", Path("/usr/bin/unsafe"))

    report = cleanup_module.remove_selected_items((item,))

    assert report == CleanupReport(removed=(), failed=(item,))


def test_remove_selected_items_updates_progress_for_launchers_and_mise(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    mise_path = tmp_path / ".local/bin/codex"
    mise_path.parent.mkdir(parents=True)
    mise_path.write_text("#!/usr/bin/env bash\nmise use -g --quiet codex\n", encoding="utf-8")

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    progress = FakeProgress()

    report = cleanup_module.remove_selected_items(
        (_webapp_item("YouTube"), _mise_item("Codex", mise_path)),
        progress=cast(Progress, progress),
    )

    assert len(report.removed) == 2
    assert progress.tasks == [
        ("Removing [Webapp] YouTube", 1),
        ("Removing [Mise] Codex", 1),
    ]
    assert progress.advanced == [0, 1]


def test_run_cleanup_step_skips_without_interactive_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> list[str]:
        raise AssertionError("checkbox should not be shown")

    monkeypatch.setattr(ui, "is_interactive", lambda: False)
    monkeypatch.setattr(
        cleanup_module,
        "available_cleanup_items",
        lambda **kwargs: (_package_item("aether"),),
    )
    monkeypatch.setattr(ui, "checkbox", fail)

    assert cleanup_module.run_cleanup_step() is CleanupResult.SKIPPED


def test_run_cleanup_step_skips_without_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> list[str]:
        raise AssertionError("checkbox should not be shown")

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(cleanup_module, "available_cleanup_items", lambda **kwargs: ())
    monkeypatch.setattr(ui, "checkbox", fail)

    assert cleanup_module.run_cleanup_step() is CleanupResult.SKIPPED


def test_run_cleanup_step_removes_only_selected_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = _package_item("aether")
    webapp = _webapp_item("YouTube")
    shown_messages: list[str] = []
    removal_calls: list[tuple[list[CleanupItem], dict[str, object]]] = []

    def fake_checkbox(
        message: str,
        choices: list[str],
        **kwargs: object,
    ) -> list[str]:
        shown_messages.append(message)
        if "packages" in message:
            return [package.name]
        if "web apps" in message:
            return [webapp.name]
        return []

    def fake_remove(
        items: Sequence[CleanupItem],
        **kwargs: object,
    ) -> CleanupReport:
        removal_calls.append((list(items), kwargs))
        return CleanupReport(removed=tuple(items))

    @contextmanager
    def fake_virtual_terminal(**kwargs: object) -> Iterator[str]:
        yield "terminal"

    @contextmanager
    def fake_progress_bar(**kwargs: object) -> Iterator[str]:
        yield "progress"

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(
        cleanup_module,
        "available_cleanup_items",
        lambda **kwargs: (package, webapp),
    )
    monkeypatch.setattr(ui, "checkbox", fake_checkbox)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(ui, "virtual_terminal", fake_virtual_terminal)
    monkeypatch.setattr(ui, "progress_bar", fake_progress_bar)
    monkeypatch.setattr(cleanup_module, "remove_selected_items", fake_remove)

    assert cleanup_module.run_cleanup_step() is CleanupResult.COMPLETED
    assert shown_messages == [
        "Select packages to remove:",
        "Select web apps to remove:",
    ]
    assert removal_calls == [
        ([package], {"terminal": "terminal"}),
        ([webapp], {"progress": "progress"}),
    ]


def test_run_cleanup_step_skips_when_nothing_is_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> CleanupReport:
        raise AssertionError("removal should not run")

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(
        cleanup_module,
        "available_cleanup_items",
        lambda **kwargs: (_package_item("aether"),),
    )
    monkeypatch.setattr(ui, "checkbox", lambda *args, **kwargs: [])
    monkeypatch.setattr(cleanup_module, "remove_selected_items", fail)

    assert cleanup_module.run_cleanup_step() is CleanupResult.SKIPPED


def test_run_cleanup_step_skips_when_declined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _package_item("aether")

    def fail(*args: object, **kwargs: object) -> CleanupReport:
        raise AssertionError("removal should not run")

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(cleanup_module, "available_cleanup_items", lambda **kwargs: (item,))
    monkeypatch.setattr(ui, "checkbox", lambda *args, **kwargs: [item.name])
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)
    monkeypatch.setattr(cleanup_module, "remove_selected_items", fail)

    assert cleanup_module.run_cleanup_step() is CleanupResult.SKIPPED


def test_run_cleanup_step_reports_removal_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _package_item("aether")

    @contextmanager
    def fake_virtual_terminal(**kwargs: object) -> Iterator[str]:
        yield "terminal"

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(cleanup_module, "available_cleanup_items", lambda **kwargs: (item,))
    monkeypatch.setattr(ui, "checkbox", lambda *args, **kwargs: [item.name])
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(ui, "virtual_terminal", fake_virtual_terminal)
    monkeypatch.setattr(
        cleanup_module,
        "remove_selected_items",
        lambda items, **kwargs: CleanupReport(failed=tuple(items)),
    )

    assert cleanup_module.run_cleanup_step() is CleanupResult.FAILED
