"""CLI command modules."""

from __future__ import annotations

import typer

from omarchy_tweaker.commands import cleanup, directory, packages, plugins, snapshot, welcome


def register_commands(app: typer.Typer) -> None:
    """Register all application commands on the Typer application.

    Args:
        app: The Typer application to register commands on.
    """
    cleanup.register(app)
    directory.register(app)
    packages.register(app)
    plugins.register(app)
    snapshot.register(app)
    welcome.register(app)
