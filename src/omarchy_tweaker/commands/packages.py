"""Packages command."""

from __future__ import annotations

import typer

from omarchy_tweaker.functions.packages import PackageResult, run_packages_step


def packages() -> None:
    """Install selected Pacman and AUR packages.

    Raises:
        typer.Exit: If package installation fails.
    """
    result = run_packages_step()
    if result is PackageResult.FAILED:
        raise typer.Exit(code=1)


def register(app: typer.Typer) -> None:
    """Register the packages command.

    Args:
        app: The Typer application to register the command on.
    """
    app.command(
        name="packages",
        help="Install selected Pacman and AUR packages.",
    )(packages)
