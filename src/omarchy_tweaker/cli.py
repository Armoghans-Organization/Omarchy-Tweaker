"""Typer CLI application."""

from __future__ import annotations

import typer

from omarchy_tweaker.commands import register_commands
from omarchy_tweaker.startup import run_default

app = typer.Typer(
    name="omarchy-tweaker",
    help="Customize, automate, and maintain your Omarchy installation.",
    no_args_is_help=False,
    add_completion=False,
    rich_markup_mode="rich",
    rich_help_panel="rich",
)


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context) -> None:
    """Run the Omarchy Tweaker CLI.

    Args:
        ctx: The Typer context for the current invocation.
    """
    if ctx.invoked_subcommand is None:
        run_default()


register_commands(app)


def main(args: list[str] | None = None) -> None:
    """Run the Typer application.

    Args:
        args: Optional command-line arguments. When omitted, Typer reads
            ``sys.argv``.
    """
    from omarchy_tweaker.functions.logger import application_session

    with application_session():
        app(args=args)
