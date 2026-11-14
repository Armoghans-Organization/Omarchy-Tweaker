"""Plugins command."""

from __future__ import annotations

import typer

from omarchy_tweaker.functions.plugins import PluginResult, run_plugins_step


def plugins() -> None:
    """Install selected Omarchy shell plugins.

    Raises:
        typer.Exit: If plugin installation fails.
    """
    result = run_plugins_step()
    if result is PluginResult.FAILED:
        raise typer.Exit(code=1)


def register(app: typer.Typer) -> None:
    """Register the plugins command.

    Args:
        app: The Typer application to register the command on.
    """
    app.command(
        name="plugins",
        help="Install selected Omarchy shell plugins.",
    )(plugins)
