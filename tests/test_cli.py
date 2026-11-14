from __future__ import annotations

import pytest
from typer.testing import CliRunner

import omarchy_tweaker.cli as cli_module
import omarchy_tweaker.commands.cleanup as cleanup_command
import omarchy_tweaker.commands.directory as directory_command
import omarchy_tweaker.commands.packages as packages_command
import omarchy_tweaker.commands.plugins as plugins_command
import omarchy_tweaker.commands.snapshot as snapshot_command
import omarchy_tweaker.functions.cleanup as cleanup_module
import omarchy_tweaker.startup as startup_module
from omarchy_tweaker.cli import app
from omarchy_tweaker.functions.cleanup import CleanupResult, run_cleanup_step
from omarchy_tweaker.functions.directory import DirectoryResult, run_directory_step
from omarchy_tweaker.functions.packages import PackageResult
from omarchy_tweaker.functions.plugins import PluginResult
from omarchy_tweaker.functions.snapshot import SnapshotResult, run_snapshot_step
from omarchy_tweaker.screens.banner import show_banner

runner = CliRunner()


def test_cli_without_arguments_shows_banner_and_snapshot_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cleanup_module, "available_cleanup_items", lambda **kwargs: ())

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "Omarchy Tweaker" in result.output
    assert "SYSTEM SNAPSHOT" in result.output
    assert "Snapshot skipped" in result.output
    assert "CLEANUP" in result.output
    assert "No installed cleanup items were found." in result.output
    assert "REQUIRED DIRECTORIES" in result.output
    assert "Directory setup skipped" in result.output


def test_cli_without_arguments_runs_default_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(cli_module, "run_default", lambda: calls.append(True))

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert calls == [True]


def test_subcommand_shows_banner_before_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(cli_module, "show_banner", lambda: calls.append("banner"))
    monkeypatch.setattr(
        cleanup_command,
        "run_cleanup_step",
        lambda: CleanupResult.SKIPPED,
    )

    result = runner.invoke(app, ["cleanup"])

    assert result.exit_code == 0
    assert calls == ["banner"]


def test_no_argument_invocation_does_not_show_extra_banner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail() -> None:
        raise AssertionError("default sequence owns the banner")

    monkeypatch.setattr(cli_module, "show_banner", fail)
    monkeypatch.setattr(cli_module, "run_default", lambda: None)

    result = runner.invoke(app, [])

    assert result.exit_code == 0


def test_subcommand_output_contains_banner_before_section() -> None:
    result = runner.invoke(app, ["snapshot"])

    assert result.exit_code == 0
    assert "Omarchy Tweaker" in result.output
    assert result.output.index("Omarchy Tweaker") < result.output.index("SYSTEM SNAPSHOT")


def test_default_sequence_starts_with_banner() -> None:
    assert startup_module.DEFAULT_SEQUENCE[0] is show_banner


def test_default_sequence_includes_snapshot_step() -> None:
    assert run_snapshot_step in startup_module.DEFAULT_SEQUENCE


def test_default_sequence_includes_cleanup_step() -> None:
    assert run_cleanup_step in startup_module.DEFAULT_SEQUENCE


def test_default_sequence_includes_directory_step() -> None:
    assert run_directory_step in startup_module.DEFAULT_SEQUENCE


def test_default_sequence_runs_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        startup_module,
        "DEFAULT_SEQUENCE",
        (
            lambda: calls.append("first"),
            lambda: calls.append("second"),
        ),
    )

    startup_module.run_default()

    assert calls == ["first", "second"]


def test_snapshot_command_passes_yes_to_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    def fake_run(*, assume_yes: bool) -> SnapshotResult:
        calls.append(assume_yes)
        return SnapshotResult.CREATED

    monkeypatch.setattr(snapshot_command, "run_snapshot_step", fake_run)

    result = runner.invoke(app, ["snapshot", "--yes"])

    assert result.exit_code == 0
    assert calls == [True]


def test_snapshot_command_exits_nonzero_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        snapshot_command,
        "run_snapshot_step",
        lambda *, assume_yes: SnapshotResult.FAILED,
    )

    result = runner.invoke(app, ["snapshot"])

    assert result.exit_code == 1


def test_cleanup_command_exits_nonzero_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cleanup_command,
        "run_cleanup_step",
        lambda: CleanupResult.FAILED,
    )

    result = runner.invoke(app, ["cleanup"])

    assert result.exit_code == 1


def test_cleanup_command_exits_zero_when_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cleanup_command,
        "run_cleanup_step",
        lambda: CleanupResult.SKIPPED,
    )

    result = runner.invoke(app, ["cleanup"])

    assert result.exit_code == 0


def test_directory_command_exits_nonzero_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        directory_command,
        "run_directory_step",
        lambda: DirectoryResult.FAILED,
    )

    result = runner.invoke(app, ["directories"])

    assert result.exit_code == 1


def test_directory_command_exits_zero_when_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        directory_command,
        "run_directory_step",
        lambda: DirectoryResult.SKIPPED,
    )

    result = runner.invoke(app, ["directories"])

    assert result.exit_code == 0


def test_packages_command_exits_nonzero_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        packages_command,
        "run_packages_step",
        lambda: PackageResult.FAILED,
    )

    result = runner.invoke(app, ["packages"])

    assert result.exit_code == 1


def test_packages_command_exits_zero_when_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        packages_command,
        "run_packages_step",
        lambda: PackageResult.SKIPPED,
    )

    result = runner.invoke(app, ["packages"])

    assert result.exit_code == 0


def test_plugins_command_exits_nonzero_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        plugins_command,
        "run_plugins_step",
        lambda: PluginResult.FAILED,
    )

    result = runner.invoke(app, ["plugins"])

    assert result.exit_code == 1


def test_plugins_command_exits_zero_when_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        plugins_command,
        "run_plugins_step",
        lambda: PluginResult.SKIPPED,
    )

    result = runner.invoke(app, ["plugins"])

    assert result.exit_code == 0


def test_welcome_command_shows_welcome() -> None:
    result = runner.invoke(app, ["welcome"])

    assert result.exit_code == 0
    assert "Omarchy Tweaker" in result.output
    assert "Welcome to Omarchy Tweaker!" in result.output


def test_welcome_command_shows_banner_once() -> None:
    result = runner.invoke(app, ["welcome"])

    assert result.exit_code == 0
    assert result.output.count("Customize. Automate. Maintain.") == 1


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "cleanup" in result.output
    assert "directories" in result.output
    assert "packages" in result.output
    assert "snapshot" in result.output
    assert "welcome" in result.output
