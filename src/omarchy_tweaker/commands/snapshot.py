"""Snapshot command."""

from __future__ import annotations

from typing import Annotated

import typer

from omarchy_tweaker.functions.snapshot import SnapshotResult, run_snapshot_step


def snapshot(
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Create the snapshot without asking for confirmation.",
        ),
    ] = False,
) -> None:
    """Create a system snapshot with ``omarchy snapshot create``.

    Args:
        yes: Skip the confirmation prompt.

    Raises:
        typer.Exit: If snapshot creation fails.
    """
    result = run_snapshot_step(assume_yes=yes)
    if result is SnapshotResult.FAILED:
        raise typer.Exit(code=1)


def register(app: typer.Typer) -> None:
    """Register the snapshot command.

    Args:
        app: The Typer application to register the command on.
    """
    app.command(name="snapshot", help="Create a system snapshot.")(snapshot)
