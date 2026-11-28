# ╭──────────────────────────────────────────────────────────────────────────╮
# │                                                                          │
# │                     P Y T H O N   /   S T A R T U P                    │
# │                                                                          │
# │  File: ~/.local/bin/startup.py                                           │
# │  Purpose: Premium interactive Python environment                       │
# │  Features: Rich UI, Tracebacks, Pretty Printing, REPL Commands           │
# │                                                                          │
# ╰──────────────────────────────────────────────────────────────────────────╯


# ───────────────────────────────────────────────────────────────────────────
# 1. STANDARD LIBRARY
# ───────────────────────────────────────────────────────────────────────────

import os
import platform
import sys
import traceback
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

# ───────────────────────────────────────────────────────────────────────────
# 2. OPTIONAL DEPENDENCIES
# ───────────────────────────────────────────────────────────────────────────

# Rich is optional.
# Python must remain usable even if Rich is missing or broken.


class ConsoleLike(Protocol):
    """Minimal Rich console surface used by this module."""

    def print(self, *objects: object) -> None: ...

    def clear(self) -> None: ...


class _PlainConsole:
    """Fallback console used when Rich is unavailable."""

    def print(self, *objects: object) -> None:
        print(*objects)

    def clear(self) -> None:
        print("\033[2J\033[H", end="")


rprint: Callable[..., None]

try:
    from rich import box
    from rich import print as rich_print
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.pretty import install as install_pretty
    from rich.table import Table
    from rich.text import Text
    from rich.traceback import install as install_traceback

    rprint = rich_print
    RICH_AVAILABLE = True

except ImportError:
    RICH_AVAILABLE = False
    rprint = print


# ───────────────────────────────────────────────────────────────────────────
# 3. CONSOLE INITIALIZATION
# ───────────────────────────────────────────────────────────────────────────

console: ConsoleLike = _PlainConsole()

if RICH_AVAILABLE:
    console = Console(
        highlight=True,
        soft_wrap=True,
        tab_size=4,
    )

    # Beautiful exception formatting.
    install_traceback(
        console=console,
        extra_lines=3,
        word_wrap=True,
        show_locals=False,
    )

    # Pretty-print Python objects.
    install_pretty(
        console=console,
        expand_all=False,
    )


# ───────────────────────────────────────────────────────────────────────────
# 4. COLOR PALETTE
# ───────────────────────────────────────────────────────────────────────────

COLORS = {
    "primary": "bright_magenta",
    "secondary": "bright_cyan",
    "success": "bright_green",
    "warning": "bright_yellow",
    "error": "bright_red",
    "muted": "grey70",
    "white": "bright_white",
}


# ───────────────────────────────────────────────────────────────────────────
# 5. STARTUP DASHBOARD
# ───────────────────────────────────────────────────────────────────────────


def startup_banner() -> None:
    """Display the Python welcome dashboard."""

    version = platform.python_version()
    implementation = platform.python_implementation()
    executable = sys.executable
    current_time = datetime.now().strftime("%H:%M:%S")
    current_date = datetime.now().strftime("%A, %d %B %Y")

    # Standard Python fallback.
    if not RICH_AVAILABLE:
        print()
        print("╭──────────────────────────────────────────────╮")
        print("│                                              │")
        print("│          PYTHON INTERACTIVE ENV              │")
        print("│                                              │")
        print("│          ✦  ENVIRONMENT READY  ✦             │")
        print("│                                              │")
        print("╰──────────────────────────────────────────────╯")
        print()
        print(f"  Python          : {version}")
        print(f"  Implementation  : {implementation}")
        print(f"  Platform        : {platform.system()}")
        print(f"  Session         : {current_time}")
        print()
        print("  Welcome back. Happy coding!")
        print()

        return

    # Main heading.
    heading = Text()

    heading.append("P Y T H O N", style="bold bright_white")
    heading.append("  /  ", style="grey50")
    heading.append("INTERACTIVE", style="bold bright_cyan")

    subtitle = Text(
        "✦  YOUR ENVIRONMENT IS READY  ✦",
        style="bold bright_green",
        justify="center",
    )

    # Environment information.
    details = Table.grid(padding=(0, 2))

    details.add_column(
        style="bold bright_cyan",
        justify="right",
    )

    details.add_column(
        style="bright_white",
    )

    details.add_row("VERSION", version)
    details.add_row("ENGINE", implementation)
    details.add_row("PLATFORM", platform.system())
    details.add_row("EXECUTABLE", executable)
    details.add_row("DATE", current_date)
    details.add_row("SESSION", current_time)

    # Dependency status.
    status = Text()

    status.append("● ", style="bright_green")
    status.append("RICH ENABLED", style="bold bright_white")
    status.append("     ", style="grey50")
    status.append("● ", style="bright_green")
    status.append("TRACEBACKS READY", style="bold bright_white")

    # Compose the dashboard.
    content = Table.grid(padding=(1, 0))
    content.add_column(justify="center")

    content.add_row(Align.center(heading))
    content.add_row(Align.center(subtitle))
    content.add_row("")
    content.add_row(details)
    content.add_row("")
    content.add_row(Align.center(status))

    console.print()

    console.print(
        Align.center(
            Panel(
                content,
                title="[bold bright_magenta]✦  PYTHON ENVIRONMENT  ✦[/bold bright_magenta]",
                subtitle="[dim]ARMOGHAN'S INTERACTIVE SHELL[/dim]",
                border_style="bright_magenta",
                box=box.DOUBLE,
                padding=(1, 4),
                expand=False,
            )
        )
    )

    console.print()

    console.print(
        Align.center(
            Text.from_markup(
                "[bold bright_green]❯[/bold bright_green] "
                "[bold white]Let's build something extraordinary.[/bold white]"
            )
        )
    )

    console.print()


# ───────────────────────────────────────────────────────────────────────────
# 6. TERMINAL UTILITIES
# ───────────────────────────────────────────────────────────────────────────


def cls() -> None:
    """Clear the terminal screen."""

    if RICH_AVAILABLE:
        console.clear()
    else:
        print("\033[2J\033[H", end="", flush=True)


def banner() -> None:
    """Display the welcome dashboard."""

    startup_banner()


def info() -> None:
    """Display detailed Python environment information."""

    if not RICH_AVAILABLE:
        print("\nPYTHON ENVIRONMENT")
        print("-" * 45)
        print("Version:", platform.python_version())
        print("Implementation:", platform.python_implementation())
        print("Platform:", platform.platform())
        print("Executable:", sys.executable)
        print("Directory:", os.getcwd())
        print("-" * 45)

        return

    table = Table(
        title="Python Environment",
        box=box.ROUNDED,
        border_style="bright_magenta",
        header_style="bold bright_cyan",
    )

    table.add_column("PROPERTY", style="cyan")
    table.add_column("VALUE", style="bright_white")

    table.add_row("Python", platform.python_version())
    table.add_row("Implementation", platform.python_implementation())
    table.add_row("Platform", platform.platform())
    table.add_row("Architecture", platform.machine())
    table.add_row("Executable", sys.executable)
    table.add_row("Working Directory", os.getcwd())

    console.print(table)


def deps() -> None:
    """Display optional dependency status."""

    if not RICH_AVAILABLE:
        print("Rich: Not installed")
        print("Install: python -m pip install rich")
        return

    table = Table(
        title="Environment Dependencies",
        box=box.ROUNDED,
        border_style="bright_magenta",
    )

    table.add_column("PACKAGE", style="cyan")
    table.add_column("STATUS", justify="center")

    table.add_row(
        "Rich",
        "[bold bright_green]● Available[/bold bright_green]",
    )

    table.add_row(
        "Tracebacks",
        "[bold bright_green]● Enabled[/bold bright_green]",
    )

    table.add_row(
        "Pretty Printing",
        "[bold bright_green]● Enabled[/bold bright_green]",
    )

    console.print(table)


def commands() -> None:
    """Display available interactive shortcuts."""

    shortcuts = {
        "cls": "Clear the terminal",
        "banner": "Display the welcome dashboard",
        "info": "Show Python environment information",
        "deps": "Show dependency status",
        "commands": "Show available shortcuts",
    }

    if not RICH_AVAILABLE:
        print("\nPYTHON SHORTCUTS")
        print("-" * 40)

        for name, description in shortcuts.items():
            print(f"{name:<12} {description}")

        print("-" * 40)

        return

    table = Table(
        title="Interactive Commands",
        box=box.ROUNDED,
        border_style="bright_magenta",
    )

    table.add_column("COMMAND", style="bold bright_cyan")
    table.add_column("DESCRIPTION", style="bright_white")

    for name, description in shortcuts.items():
        table.add_row(name, description)

    console.print(table)


# ───────────────────────────────────────────────────────────────────────────
# 7. COMMAND-STYLE REPL SHORTCUTS
# ───────────────────────────────────────────────────────────────────────────

# This is the interesting part.
#
# Python normally displays the representation of an object when
# you type its name in the interactive interpreter.
#
# Example:
#
#     >>> cls
#     <function cls at 0x...>
#
# We customize sys.displayhook so that registered shortcut
# functions execute when entered without parentheses.
#
# Example:
#
#     >>> cls
#     # Clears the terminal.
#
#     >>> info
#     # Displays environment information.
#
# Normal Python expressions continue working as usual.

REPL_COMMANDS = {
    "cls": cls,
    "banner": banner,
    "info": info,
    "deps": deps,
    "commands": commands,
}

# Preserve the existing display hook.
# This is important because Rich also installs its own
# pretty-printing display hook.

_original_displayhook = sys.displayhook


def custom_displayhook(value: object) -> None:
    """Execute registered commands when entered by name."""

    if value is None:
        return

    # Check whether the returned object is one of our commands.
    for command in REPL_COMMANDS.values():
        if value is command:
            try:
                result = command()

                # Preserve normal display behavior if a command
                # happens to return a value.
                if result is not None:
                    _original_displayhook(result)

            except Exception:
                sys.excepthook(*sys.exc_info())

            return

    # Delegate all normal Python expressions to the original hook.
    _original_displayhook(value)


# Activate custom REPL behavior.
sys.displayhook = custom_displayhook


# ───────────────────────────────────────────────────────────────────────────
# 8. STARTUP INITIALIZATION
# ───────────────────────────────────────────────────────────────────────────

# PYTHONSTARTUP is only executed by the interactive interpreter.
# Therefore, reaching this point means the startup configuration
# has already been loaded.

try:
    startup_banner()

    if not RICH_AVAILABLE:
        print("\033[93m⚠ Rich is not installed. Using standard Python output.\033[0m")

        print("Install Rich: python -m pip install rich\n")

except Exception:
    # A cosmetic startup error should never prevent Python
    # from being used.

    traceback.print_exc()


# ───────────────────────────────────────────────────────────────────────────
# END OF PYTHON INTERACTIVE ENVIRONMENT
# ───────────────────────────────────────────────────────────────────────────
