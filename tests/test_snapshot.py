from __future__ import annotations

import subprocess
from collections.abc import Iterator, Sequence
from contextlib import contextmanager

import pytest

import omarchy_tweaker.functions.snapshot as snapshot_module
from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.snapshot import SnapshotResult


class FakeTerminal:
    def __init__(self, *, returncode: int = 0, error: Exception | None = None) -> None:
        self.returncode = returncode
        self.error = error
        self.command: tuple[str, ...] | None = None
        self.timeout: float | None = None
        self.lines: list[str] = []

    def run(
        self,
        command: Sequence[str],
        *,
        timeout: float | None = None,
        **kwargs: object,
    ) -> int:
        self.command = tuple(command)
        self.timeout = timeout
        if self.error is not None:
            raise self.error
        return self.returncode

    def writeline(self, line: str, *, style: str | None = None) -> None:
        self.lines.append(line)


def _install_fake_terminal(
    monkeypatch: pytest.MonkeyPatch,
    terminal: FakeTerminal,
) -> None:
    @contextmanager
    def fake_virtual_terminal(**kwargs: object) -> Iterator[FakeTerminal]:
        yield terminal

    monkeypatch.setattr(ui, "virtual_terminal", fake_virtual_terminal)


def test_create_snapshot_runs_omarchy_snapshot_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = FakeTerminal()
    _install_fake_terminal(monkeypatch, terminal)

    assert snapshot_module.create_snapshot() is True
    assert terminal.command == snapshot_module.SNAPSHOT_COMMAND
    assert terminal.timeout == snapshot_module.SNAPSHOT_TIMEOUT_SECONDS


def test_create_snapshot_handles_missing_omarchy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = FakeTerminal(error=FileNotFoundError())
    _install_fake_terminal(monkeypatch, terminal)

    assert snapshot_module.create_snapshot() is False
    assert any("not found" in line for line in terminal.lines)


def test_create_snapshot_handles_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = FakeTerminal(returncode=1)
    _install_fake_terminal(monkeypatch, terminal)

    assert snapshot_module.create_snapshot() is False


def test_create_snapshot_handles_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = FakeTerminal(
        error=subprocess.TimeoutExpired(cmd=["omarchy"], timeout=1.0),
    )
    _install_fake_terminal(monkeypatch, terminal)

    assert snapshot_module.create_snapshot() is False


def test_create_snapshot_handles_os_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = FakeTerminal(error=OSError("permission denied"))
    _install_fake_terminal(monkeypatch, terminal)

    assert snapshot_module.create_snapshot() is False
    assert any("Could not start" in line for line in terminal.lines)


def test_run_snapshot_step_skips_without_interactive_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail() -> bool:
        raise AssertionError("snapshot command should not run")

    monkeypatch.setattr(ui, "is_interactive", lambda: False)
    monkeypatch.setattr(snapshot_module, "create_snapshot", fail)

    assert snapshot_module.run_snapshot_step() is SnapshotResult.SKIPPED


def test_run_snapshot_step_skips_when_declined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail() -> bool:
        raise AssertionError("snapshot command should not run")

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)
    monkeypatch.setattr(snapshot_module, "create_snapshot", fail)

    assert snapshot_module.run_snapshot_step() is SnapshotResult.SKIPPED


def test_run_snapshot_step_creates_when_confirmed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(snapshot_module, "create_snapshot", lambda: True)

    assert snapshot_module.run_snapshot_step() is SnapshotResult.CREATED


def test_run_snapshot_step_assume_yes_skips_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> bool:
        raise AssertionError("confirmation should not be requested")

    monkeypatch.setattr(ui, "confirm", fail)
    monkeypatch.setattr(snapshot_module, "create_snapshot", lambda: True)

    assert snapshot_module.run_snapshot_step(assume_yes=True) is SnapshotResult.CREATED


def test_run_snapshot_step_reports_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(snapshot_module, "create_snapshot", lambda: False)

    assert snapshot_module.run_snapshot_step() is SnapshotResult.FAILED
