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
    from omarchy_tweaker.functions.logger import application_session

    cli_args = sys.argv[1:] if args is None else args

    with application_session() as logger:
        logger.info("CLI invocation started with arguments: %s", cli_args or "<none>")

        if not cli_args:
            from omarchy_tweaker.startup import run_default

            run_default()
            return

        from omarchy_tweaker.cli import main as run_typer

        logger.info("Dispatching to the Typer CLI.")
        run_typer(cli_args)
        logger.info("Typer CLI completed.")


__all__ = ["main"]
