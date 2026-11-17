"""Bundled scripts command."""

from __future__ import annotations

import typer

from omarchy_tweaker.functions.scripts import ScriptResult, run_scripts_step


def scripts() -> None:
    """Link the bundled helper scripts into ~/.local/bin.

    Raises:
        typer.Exit: If a script could not be linked.
    """
    result = run_scripts_step()
    if result is ScriptResult.FAILED:
        raise typer.Exit(code=1)


def register(app: typer.Typer) -> None:
    """Register the scripts command.

    Args:
        app: The Typer application to register the command on.
    """
    app.command(
        name="scripts",
        help="Link the bundled helper scripts into ~/.local/bin.",
    )(scripts)
