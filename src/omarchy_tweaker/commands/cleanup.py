"""Cleanup command."""

from __future__ import annotations

import typer

from omarchy_tweaker.functions.cleanup import CleanupResult, run_cleanup_step


def cleanup() -> None:
    """Remove selected installed Omarchy applications and wrappers.

    Raises:
        typer.Exit: If any selected item could not be removed.
    """
    result = run_cleanup_step()
    if result is CleanupResult.FAILED:
        raise typer.Exit(code=1)


def register(app: typer.Typer) -> None:
    """Register the cleanup command.

    Args:
        app: The Typer application to register the command on.
    """
    app.command(
        name="cleanup", help="Remove selected installed Omarchy applications and wrappers."
    )(cleanup)
