"""Application banner screen."""

from __future__ import annotations

from omarchy_tweaker.functions import ui


def show_banner() -> None:
    """Clear the screen and display the application banner."""
    ui.clear_screen()
    ui.banner()
