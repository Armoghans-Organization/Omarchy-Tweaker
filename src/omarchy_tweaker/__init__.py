"""Omarchy Tweaker package."""

from omarchy_tweaker.error_handling import install_error_handling
from omarchy_tweaker.functions import ui

install_error_handling()


def main() -> None:
    """Run the Omarchy Tweaker CLI."""
    ui.clear_screen()
    print()
    print()
    ui.banner()
    ui.info("Welcome to Omarchy Tweaker!")
