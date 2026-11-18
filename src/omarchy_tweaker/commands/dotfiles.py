"""Dotfiles command."""

from __future__ import annotations

import typer

from omarchy_tweaker.functions.dotfiles import DotfileResult, run_dotfiles_step


def dotfiles() -> None:
    """Apply bundled dotfiles and prepare configured keys.

    Raises:
        typer.Exit: If a dotfile bundle could not be applied.
    """
    result = run_dotfiles_step()
    if result is DotfileResult.FAILED:
        raise typer.Exit(code=1)


def register(app: typer.Typer) -> None:
    """Register the dotfiles command.

    Args:
        app: The Typer application to register the command on.
    """
    app.command(
        name="dotfiles",
        help="Link bundled dotfiles and prepare SSH and GPG keys.",
    )(dotfiles)
