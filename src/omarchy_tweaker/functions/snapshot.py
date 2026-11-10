"""Create a system snapshot before applying system changes."""

from __future__ import annotations

import subprocess  # nosec B404
from enum import Enum
from typing import Final

from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.logger import get_session

SNAPSHOT_COMMAND: Final[tuple[str, ...]] = ("omarchy", "snapshot", "create")
SNAPSHOT_TIMEOUT_SECONDS: Final = 600.0


class SnapshotResult(Enum):
    """Outcome of the snapshot step."""

    CREATED = "created"
    SKIPPED = "skipped"
    FAILED = "failed"


def _run_snapshot_command(terminal: ui.VirtualTerminal) -> bool:
    """Run the snapshot command in a virtual terminal.

    Args:
        terminal: Terminal that streams the command output.

    Returns:
        ``True`` when the command exits successfully, otherwise ``False``.
    """
    logger = get_session()
    if logger is not None:
        logger.info("Running snapshot command: %s", " ".join(SNAPSHOT_COMMAND))

    try:
        returncode = terminal.run(
            SNAPSHOT_COMMAND,
            timeout=SNAPSHOT_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        if logger is not None:
            logger.error("Snapshot command was not found on PATH.")
        terminal.writeline(
            "The omarchy command was not found on PATH.",
            style=ui.THEME.error,
        )
        return False
    except subprocess.TimeoutExpired:
        if logger is not None:
            logger.error(
                "Snapshot command timed out after %s seconds.",
                SNAPSHOT_TIMEOUT_SECONDS,
            )
        return False
    except OSError as exc:
        if logger is not None:
            logger.error("Could not start the snapshot command: %s", exc)
        terminal.writeline(
            f"Could not start the snapshot command: {exc}",
            style=ui.THEME.error,
        )
        return False

    if logger is not None:
        if returncode == 0:
            logger.info("Snapshot command completed successfully.")
        else:
            logger.error("Snapshot command exited with status %s.", returncode)

    return returncode == 0


def create_snapshot() -> bool:
    """Create a system snapshot with ``omarchy snapshot create``.

    Returns:
        ``True`` when the command exits successfully, otherwise ``False``.
    """
    with ui.virtual_terminal(
        height=10,
        max_lines=20,
        title="Snapshot",
        show_line_numbers=True,
    ) as terminal:
        return _run_snapshot_command(terminal)


def run_snapshot_step(*, assume_yes: bool = False) -> SnapshotResult:
    """Run the snapshot step, asking for permission before executing it.

    Args:
        assume_yes: Skip the confirmation prompt and run the command.

    Returns:
        The outcome of the step.
    """
    logger = get_session()
    if logger is not None:
        logger.info("Snapshot step started (assume_yes=%s).", assume_yes)

    ui.section(
        "System Snapshot",
        subtitle="Create a restore point before changing system configuration.",
        icon=ui.ICONS.gear,
    )

    if not assume_yes:
        if not ui.is_interactive():
            if logger is not None:
                logger.info("Snapshot step skipped: no interactive terminal.")
            ui.warning(
                "Snapshot skipped: confirmation requires an interactive terminal.",
            )
            return SnapshotResult.SKIPPED

        if not ui.confirm(
            "Create a system snapshot now?",
            default=True,
            instruction="Recommended before applying system changes.",
        ):
            if logger is not None:
                logger.info("Snapshot step skipped by the user.")
            ui.info("Snapshot skipped.")
            return SnapshotResult.SKIPPED

    ui.info("Creating a system snapshot with snapper...")
    if not create_snapshot():
        if logger is not None:
            logger.error("Snapshot step failed.")
        ui.error("Snapshot creation failed. Review the terminal output above.")
        return SnapshotResult.FAILED

    if logger is not None:
        logger.info("Snapshot step completed successfully.")
    ui.success("System snapshot created.")
    return SnapshotResult.CREATED
