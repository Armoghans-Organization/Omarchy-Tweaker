"""Omarchy Tweaker package."""

import sys

from omarchy_tweaker.error_handling import install_error_handling

install_error_handling()


def main(args: list[str] | None = None) -> None:
    """Run the default workflow or the Typer CLI.

    Args:
        args: Optional command-line arguments. When omitted, ``sys.argv`` is
            used. With no arguments, the default startup sequence runs without
            invoking Typer.
    """
    cli_args = sys.argv[1:] if args is None else args
    if not cli_args:
        from omarchy_tweaker.startup import run_default

        run_default()
        return

    from omarchy_tweaker.cli import main as run_typer

    run_typer(cli_args)


__all__ = ["main"]
