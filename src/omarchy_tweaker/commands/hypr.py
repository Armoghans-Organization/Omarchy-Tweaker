"""Hyprland command."""

from __future__ import annotations

import typer

from omarchy_tweaker.functions.hypr import HyprResult, run_hypr_step


def hypr() -> None:
    """Apply the bundled Hyprland configuration.

    Raises:
        typer.Exit: If the Hyprland configuration could not be applied.
    """
    result = run_hypr_step()
    if result is HyprResult.FAILED:
        raise typer.Exit(code=1)


def register(app: typer.Typer) -> None:
    """Register the hypr command.

    Args:
        app: The Typer application to register the command on.
    """
    app.command(
        name="hypr",
        help="Apply the bundled Hyprland configuration.",
    )(hypr)
