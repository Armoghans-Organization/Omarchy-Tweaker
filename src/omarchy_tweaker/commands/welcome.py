"""Welcome command."""

from __future__ import annotations

import typer

from omarchy_tweaker.screens.welcome import show_welcome


def welcome() -> None:
    """Show the welcome message and system overview."""
    show_welcome()


def register(app: typer.Typer) -> None:
    """Register the welcome command.

    Args:
        app: The Typer application to register the command on.
    """
    app.command(name="welcome", help="Show the welcome screen.")(welcome)
