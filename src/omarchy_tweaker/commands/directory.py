"""Directories command."""

from __future__ import annotations

import typer

from omarchy_tweaker.functions.directory import DirectoryResult, run_directory_step


def directories() -> None:
    """Create the required personal directories.

    Raises:
        typer.Exit: If a directory could not be created.
    """
    result = run_directory_step()
    if result is DirectoryResult.FAILED:
        raise typer.Exit(code=1)


def register(app: typer.Typer) -> None:
    """Register the directories command.

    Args:
        app: The Typer application to register the command on.
    """
    app.command(
        name="directories",
        help="Create the required personal directories.",
    )(directories)
