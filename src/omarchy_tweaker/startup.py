"""Default startup workflow for invocations without CLI arguments."""

from __future__ import annotations

from collections.abc import Callable

from omarchy_tweaker.functions.cleanup import run_cleanup_step
from omarchy_tweaker.functions.containers import run_containers_step
from omarchy_tweaker.functions.directory import run_directory_step
from omarchy_tweaker.functions.logger import get_session
from omarchy_tweaker.functions.packages import run_packages_step
from omarchy_tweaker.functions.plugins import run_plugins_step
from omarchy_tweaker.functions.snapshot import run_snapshot_step
from omarchy_tweaker.screens.banner import show_banner

DEFAULT_SEQUENCE: tuple[Callable[[], object], ...] = (
    show_banner,
    run_snapshot_step,
    run_cleanup_step,
    run_directory_step,
    run_packages_step,
    run_containers_step,
    run_plugins_step,
)


def run_default() -> None:
    """Run the default startup functions in order."""
    logger = get_session()
    if logger is not None:
        logger.info("Starting the default startup sequence.")

    for step in DEFAULT_SEQUENCE:
        if logger is not None:
            logger.info("Running startup step: %s", step.__name__)
        step()

    if logger is not None:
        logger.info("Default startup sequence completed.")
