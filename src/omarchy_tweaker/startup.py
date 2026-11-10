"""Default startup workflow for invocations without CLI arguments."""

from __future__ import annotations

from collections.abc import Callable

from omarchy_tweaker.screens.banner import show_banner
from omarchy_tweaker.screens.welcome import show_welcome

DEFAULT_SEQUENCE: tuple[Callable[[], None], ...] = (
    show_banner,
    show_welcome,
)


def run_default() -> None:
    """Run the default startup functions in order."""
    for step in DEFAULT_SEQUENCE:
        step()
