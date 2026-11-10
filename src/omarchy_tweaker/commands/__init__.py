"""CLI command modules."""

from __future__ import annotations

import typer

from omarchy_tweaker.commands import snapshot, welcome


def register_commands(app: typer.Typer) -> None:
    """Register all application commands on the Typer application.

    Args:
        app: The Typer application to register commands on.
    """
    snapshot.register(app)
    welcome.register(app)
