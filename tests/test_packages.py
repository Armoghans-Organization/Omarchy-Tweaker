from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import cast

import pytest
from rich.progress import Progress

import omarchy_tweaker.functions.packages as packages_module
from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.packages import (
    AUR_PACKAGES,
    PACKAGE_GROUPS,
    PACMAN_PACKAGES,
    PackageGroup,
    PackageGroupSpec,
    PackageResult,
)


class FakeTerminal:
    def __init__(
        self,
        *,
        returncode: int = 0,
        error: BaseException | None = None,
    ) -> None:
        self.returncode = returncode
        self.error = error
        self.commands: list[tuple[str, ...]] = []
        self.lines: list[str] = []

    def run(
        self,
        command: Sequence[str],
        **kwargs: object,
    ) -> int:
        self.commands.append(tuple(command))
        if self.error is not None:
            raise self.error
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


def _group(group: PackageGroup) -> PackageGroupSpec:
    return next(spec for spec in PACKAGE_GROUPS if spec.group is group)


def test_package_catalog_uses_expected_groups_and_commands() -> None:
    assert [spec.group for spec in PACKAGE_GROUPS] == [
        PackageGroup.PACMAN,
        PackageGroup.AUR,
    ]
    assert [spec.title for spec in PACKAGE_GROUPS] == [
        "Pacman Packages",
        "AUR Packages",
    ]
    assert [spec.command for spec in PACKAGE_GROUPS] == [
        ("sudo", "pacman", "-S", "--noconfirm", "--needed", "--noprogressbar"),
        ("yay", "-S", "--noconfirm", "--needed", "--noprogressbar"),
    ]
    assert PACMAN_PACKAGES[0] == "atuin"
    assert PACMAN_PACKAGES[-1] == "rclone"
    assert AUR_PACKAGES == ("powershell-bin", "cyberchef-web", "anydesk-bin")


def test_select_packages_returns_selected_catalog_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = PackageGroupSpec(
        PackageGroup.PACMAN,
        ("atuin", "fnm", "go"),
        ("pkg", "add"),
    )
    shown_choices: list[str] = []

    def fake_checkbox(
        message: str,
        choices: Sequence[str],
        **kwargs: object,
    ) -> list[str]:
        assert message == "Select Pacman Packages to install:"
        shown_choices.extend(choices)
        return ["go", "atuin"]

    monkeypatch.setattr(ui, "checkbox", fake_checkbox)

    assert packages_module._select_packages(group) == ("atuin", "go")
    assert shown_choices == ["atuin", "fnm", "go"]


def test_install_group_runs_single_pacman_command() -> None:
    terminal = FakeTerminal()
    progress = FakeProgress()

    assert packages_module._install_group(
        _group(PackageGroup.PACMAN),
        ("atuin", "fnm"),
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
    )

    assert terminal.commands == [
        ("sudo", "pacman", "-S", "--noconfirm", "--needed", "--noprogressbar", "atuin", "fnm")
    ]
    assert progress.tasks == [("Installing 2 Pacman package(s)", None)]
    assert progress.updated == [(0, "Installed 2 Pacman package(s)")]
    assert progress.advanced == [0]
    assert any("Installing 2 Pacman package(s)" in line for line in terminal.lines)


def test_install_group_runs_single_aur_command() -> None:
    terminal = FakeTerminal()
    progress = FakeProgress()

    assert packages_module._install_group(
        _group(PackageGroup.AUR),
        ("powershell-bin",),
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
    )

    assert terminal.commands == [
        ("yay", "-S", "--noconfirm", "--needed", "--noprogressbar", "powershell-bin")
    ]
    assert progress.tasks == [("Installing 1 AUR package(s)", None)]


def test_install_group_reports_missing_package_manager() -> None:
    terminal = FakeTerminal(error=FileNotFoundError("pacman"))
    progress = FakeProgress()

    assert not packages_module._install_group(
        _group(PackageGroup.PACMAN),
        ("atuin",),
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
    )

    assert progress.updated == [(0, "Failed Pacman installation")]
    assert any("pacman command was not found" in line for line in terminal.lines)


def test_install_group_reports_timeout() -> None:
    terminal = FakeTerminal(error=subprocess.TimeoutExpired("omarchy", 1))
    progress = FakeProgress()

    assert not packages_module._install_group(
        _group(PackageGroup.PACMAN),
        ("atuin",),
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
    )

    assert progress.updated == [(0, "Failed Pacman installation")]
    assert any("timed out" in line for line in terminal.lines)


def test_install_group_reports_os_error() -> None:
    terminal = FakeTerminal(error=OSError("permission denied"))
    progress = FakeProgress()

    assert not packages_module._install_group(
        _group(PackageGroup.PACMAN),
        ("atuin",),
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
    )

    assert progress.updated == [(0, "Failed Pacman installation")]
    assert any("Could not start package installation" in line for line in terminal.lines)


def test_install_group_reports_nonzero_exit() -> None:
    terminal = FakeTerminal(returncode=1)
    progress = FakeProgress()

    assert not packages_module._install_group(
        _group(PackageGroup.PACMAN),
        ("atuin",),
        terminal=cast(ui.VirtualTerminal, terminal),
        progress=cast(Progress, progress),
    )

    assert progress.updated == [(0, "Failed Pacman installation")]
    assert progress.advanced == [0]


def test_ensure_sudo_returns_true_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Sequence[str], dict[str, object]]] = []

    def fake_run(
        command: Sequence[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/sudo")
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert packages_module._ensure_sudo()
    assert calls == [
        (
            ["/usr/bin/sudo", "-v"],
            {"check": False, "timeout": packages_module.SUDO_AUTH_TIMEOUT_SECONDS},
        ),
        (
            ["/usr/bin/sudo", "-n", "-v"],
            {"check": False, "timeout": packages_module.SUDO_AUTH_TIMEOUT_SECONDS},
        ),
    ]


def test_ensure_sudo_returns_false_when_sudo_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("sudo should not run when it is missing")

    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setattr(subprocess, "run", fail)

    assert not packages_module._ensure_sudo()


def test_ensure_sudo_returns_false_on_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        command: Sequence[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/sudo")
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert not packages_module._ensure_sudo()


def test_ensure_sudo_returns_false_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(["sudo", "-v"], 1)

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/sudo")
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert not packages_module._ensure_sudo()


def test_ensure_sudo_returns_false_when_password_is_required_each_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses = iter((0, 1))

    def fake_run(
        command: Sequence[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, next(statuses))

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/sudo")
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert not packages_module._ensure_sudo()


def test_run_packages_step_skips_without_interactive_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> list[str]:
        raise AssertionError("checkbox should not be shown")

    monkeypatch.setattr(ui, "is_interactive", lambda: False)
    monkeypatch.setattr(ui, "checkbox", fail)

    assert packages_module.run_packages_step() is PackageResult.SKIPPED


def test_run_packages_step_skips_when_nothing_is_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> bool:
        raise AssertionError("install should not run")

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(packages_module, "_select_packages", lambda group: ())
    monkeypatch.setattr(packages_module, "_install_group", fail)

    assert packages_module.run_packages_step() is PackageResult.SKIPPED


def test_run_packages_step_installs_selected_groups_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selections = {
        PackageGroup.PACMAN: ("atuin", "fnm"),
        PackageGroup.AUR: ("powershell-bin",),
    }
    install_calls: list[tuple[PackageGroupSpec, tuple[str, ...]]] = []
    terminal_titles: list[str] = []

    def fake_select(group: PackageGroupSpec) -> tuple[str, ...]:
        return selections[group.group]

    def fake_install(
        group: PackageGroupSpec,
        packages: Sequence[str],
        **kwargs: object,
    ) -> bool:
        install_calls.append((group, tuple(packages)))
        return True

    @contextmanager
    def fake_terminal_with_progress(
        **kwargs: object,
    ) -> Iterator[tuple[FakeTerminal, FakeProgress]]:
        terminal_titles.append(str(kwargs["title"]))
        yield FakeTerminal(), FakeProgress()

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(packages_module, "_select_packages", fake_select)
    monkeypatch.setattr(packages_module, "_confirm_install", lambda *args: True)
    monkeypatch.setattr(packages_module, "_ensure_sudo", lambda: True)
    monkeypatch.setattr(packages_module, "_install_group", fake_install)
    monkeypatch.setattr(ui, "terminal_with_progress", fake_terminal_with_progress)

    assert packages_module.run_packages_step() is PackageResult.COMPLETED
    assert install_calls == [
        (_group(PackageGroup.PACMAN), ("atuin", "fnm")),
        (_group(PackageGroup.AUR), ("powershell-bin",)),
    ]
    assert terminal_titles == [
        "Pacman Packages Installation",
        "AUR Packages Installation",
    ]


def test_run_packages_step_skips_declined_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> bool:
        raise AssertionError("install should not run")

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(
        packages_module,
        "_select_packages",
        lambda group: ("atuin",) if group.group is PackageGroup.PACMAN else (),
    )
    monkeypatch.setattr(packages_module, "_confirm_install", lambda *args: False)
    monkeypatch.setattr(packages_module, "_install_group", fail)

    assert packages_module.run_packages_step() is PackageResult.SKIPPED


def test_run_packages_step_reports_installation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def fake_terminal_with_progress(
        **kwargs: object,
    ) -> Iterator[tuple[FakeTerminal, FakeProgress]]:
        yield FakeTerminal(), FakeProgress()

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(
        packages_module,
        "_select_packages",
        lambda group: ("atuin",) if group.group is PackageGroup.PACMAN else (),
    )
    monkeypatch.setattr(packages_module, "_confirm_install", lambda *args: True)
    monkeypatch.setattr(packages_module, "_ensure_sudo", lambda: True)
    monkeypatch.setattr(packages_module, "_install_group", lambda *args, **kwargs: False)
    monkeypatch.setattr(ui, "terminal_with_progress", fake_terminal_with_progress)

    assert packages_module.run_packages_step() is PackageResult.FAILED


def test_run_packages_step_reports_sudo_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> bool:
        raise AssertionError("install should not run")

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(
        packages_module,
        "_select_packages",
        lambda group: ("atuin",) if group.group is PackageGroup.PACMAN else (),
    )
    monkeypatch.setattr(packages_module, "_confirm_install", lambda *args: True)
    monkeypatch.setattr(packages_module, "_ensure_sudo", lambda: False)
    monkeypatch.setattr(packages_module, "_install_group", fail)

    assert packages_module.run_packages_step() is PackageResult.FAILED
