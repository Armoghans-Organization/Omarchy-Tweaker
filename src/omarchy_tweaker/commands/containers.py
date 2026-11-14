"""Containers command."""

from __future__ import annotations

import typer

from omarchy_tweaker.functions.containers import ContainerResult, run_containers_step


def containers() -> None:
    """Prepare and start the selected Docker containers.

    Raises:
        typer.Exit: If container setup fails.
    """
    result = run_containers_step()
    if result is ContainerResult.FAILED:
        raise typer.Exit(code=1)


def register(app: typer.Typer) -> None:
    """Register the containers command.

    Args:
        app: The Typer application to register the command on.
    """
    app.command(
        name="containers",
        help="Prepare and start the selected Docker containers.",
    )(containers)
