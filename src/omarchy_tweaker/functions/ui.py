"""Reusable terminal UI helpers for Omarchy Tweaker.

This module is the project's single place for terminal presentation: banners,
messages, panels, tables, lists, trees, syntax highlighting, markdown, JSON,
virtual terminals, spinners, progress bars, and interactive prompts. It uses
Rich for rendering, InquirerPy and Prompt Toolkit for prompts, and Pydantic for
validated UI data.

Display helpers accept an optional ``console`` argument, which makes them easy
to test with a recording console. When omitted, the shared console returned by
:func:`get_console` is used.
"""

from __future__ import annotations

import queue
import shlex

# Required to execute argument-list commands without invoking a shell.
import subprocess  # nosec B404
import sys
import threading
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence, Sized
from contextlib import contextmanager
from pathlib import Path
from time import monotonic
from types import TracebackType
from typing import Any, Final, Self

from InquirerPy.resolver import prompt as _inquirer_prompt
from InquirerPy.utils import InquirerPySessionResult
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, PathCompleter, WordCompleter
from prompt_toolkit.styles import Style as PromptToolkitStyle
from pydantic import BaseModel, ConfigDict, Field, model_validator
from rich import box
from rich.color import Color
from rich.columns import Columns
from rich.console import Console
from rich.json import JSON
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.rule import Rule
from rich.status import Status
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from omarchy_tweaker.app_metadata import APP_NAME, APP_VERSION

# ===========================================================================
# THEME AND ICONS
# ===========================================================================


class Icons(BaseModel):
    """Nerd Font glyphs used by the UI helpers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    success: str = "\uf00c"
    error: str = "\uf00d"
    warning: str = "\uf071"
    info: str = "\uf05a"
    debug: str = "\uf188"
    note: str = "\uf0eb"
    bullet: str = "\uf111"
    chevron: str = "\uf054"
    arrow: str = "\uf061"
    prompt: str = "\uf105"
    pointer: str = "\uf0da"
    checkbox: str = "\uf14a"
    gear: str = "\uf013"
    clock: str = "\uf017"
    tag: str = "\uf02b"
    sparkles: str = "\uf890"
    rocket: str = "\uf135"
    package: str = "\uf1b2"
    folder: str = "\uf07b"
    file: str = "\uf15b"
    terminal: str = "\uf120"
    linux: str = "\uf17c"
    star: str = "\uf005"


class Theme(BaseModel):
    """Rich style names and colours used by the UI helpers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    primary: str = "bold cyan"
    accent: str = "bold magenta"
    success: str = "green"
    error: str = "red"
    warning: str = "yellow"
    info: str = "blue"
    debug: str = "dim"
    note: str = "cyan"
    text: str = "default"
    muted: str = "dim"
    border: str = "cyan"
    badge: str = "bold white on #7c3aed"
    banner_gradient: tuple[str, ...] = Field(
        default=(
            "#7c3aed",
            "#a855f7",
            "#d946ef",
            "#f472b6",
            "#fb7185",
            "#fbbf24",
        ),
        min_length=2,
    )


class MenuOption(BaseModel):
    """A validated label/value pair for an interactive menu."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str = Field(min_length=1)
    value: str = Field(min_length=1)


class Menu(BaseModel):
    """A validated menu definition for InquirerPy prompts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(min_length=1)
    options: tuple[MenuOption, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_unique_options(self) -> Self:
        labels = [option.label for option in self.options]
        values = [option.value for option in self.options]

        if len(labels) != len(set(labels)):
            raise ValueError("Menu option labels must be unique.")
        if len(values) != len(set(values)):
            raise ValueError("Menu option values must be unique.")

        return self

    @property
    def labels(self) -> list[str]:
        """Return option labels in display order."""
        return [option.label for option in self.options]

    def value_for(self, label: str) -> str:
        """Return the value associated with a label.

        Raises:
            KeyError: If the label is not part of the menu.
        """
        for option in self.options:
            if option.label == label:
                return option.value
        raise KeyError(f"Unknown menu label: {label}")

    def label_for(self, value: str) -> str:
        """Return the label associated with a value.

        Raises:
            KeyError: If the value is not part of the menu.
        """
        for option in self.options:
            if option.value == value:
                return option.label
        raise KeyError(f"Unknown menu value: {value}")


class TreeNode(BaseModel):
    """A validated node for :func:`tree`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str = Field(min_length=1)
    children: tuple[TreeNode, ...] = ()
    style: str | None = None


ICONS: Final = Icons()
THEME: Final = Theme()


class VirtualTerminalConfig(BaseModel):
    """Validated settings for :class:`VirtualTerminal`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    height: int = Field(default=10, ge=1)
    max_lines: int = Field(default=1000, ge=1)
    title: str = Field(default="Terminal", min_length=1)
    show_line_numbers: bool = False
    border_style: str = THEME.border

    @model_validator(mode="after")
    def _validate_max_lines(self) -> Self:
        if self.max_lines < self.height:
            raise ValueError("max_lines must be greater than or equal to height.")
        return self


PROMPT_STYLE: Final[dict[str, str]] = {
    "questionmark": "bold #22d3ee",
    "answermark": "bold #22c55e",
    "answer": "#a78bfa",
    "input": "#e5e7eb",
    "question": "bold #e5e7eb",
    "instruction": "#94a3b8",
    "pointer": "bold #f472b6",
    "checkbox": "bold #22c55e",
    "marker": "bold #fbbf24",
    "validator": "#f87171",
    "fuzzy_border": "#22d3ee",
    "fuzzy_match": "#f472b6",
}

PROMPT_TOOLKIT_STYLE: Final = PromptToolkitStyle.from_dict(
    {
        "prompt": "bold #22d3ee",
        "": "#e5e7eb",
        "bottom-toolbar": "#94a3b8",
        "bottom-toolbar.text": "#94a3b8",
        "completion-menu.completion": "#e5e7eb bg:#111827",
        "completion-menu.completion.current": "#0f172a bg:#22d3ee",
        "completion-menu.meta.completion": "#94a3b8 bg:#111827",
        "completion-menu.meta.completion.current": "#0f172a bg:#22d3ee",
    }
)

BANNER_ART: Final[tuple[str, ...]] = (
    "██████╗ ███╗   ███╗ █████╗ ██████╗  ██████╗██╗  ██╗██╗   ██╗    "
    "████████╗██╗    ██╗███████╗ █████╗ ██╗  ██╗███████╗██████╗",
    "██╔═══██╗████╗ ████║██╔══██╗██╔══██╗██╔════╝██║  ██║╚██╗ ██╔╝    "
    "╚══██╔══╝██║    ██║██╔════╝██╔══██╗██║ ██╔╝██╔════╝██╔══██╗",
    "██║   ██║██╔████╔██║███████║██████╔╝██║     ███████║ ╚████╔╝        "
    "██║   ██║ █╗ ██║█████╗  ███████║█████╔╝ █████╗  ██████╔╝",
    "██║   ██║██║╚██╔╝██║██╔══██║██╔══██╗██║     ██╔══██║  ╚██╔╝         "
    "██║   ██║███╗██║██╔══╝  ██╔══██║██╔═██╗ ██╔══╝  ██╔══██╗",
    "╚██████╔╝██║ ╚═╝ ██║██║  ██║██║  ██║╚██████╗██║  ██║   ██║          "
    "██║   ╚███╔███╔╝███████╗██║  ██║██║  ██╗███████╗██║  ██║",
    " ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝   ╚═╝          "
    "╚═╝    ╚══╝╚══╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝",
)

BANNER_WIDTH: Final = max(len(line) for line in BANNER_ART)


# ===========================================================================
# CONSOLE
# ===========================================================================

_console: Console | None = None


def get_console() -> Console:
    """Return the shared Rich console, creating it on first use."""
    global _console
    if _console is None:
        _console = Console(highlight=False)
    return _console


def set_console(console: Console | None) -> None:
    """Replace the shared Rich console.

    Args:
        console: Console to use globally, or ``None`` to reset to the default.
    """
    global _console
    _console = console


def _resolve_console(console: Console | None) -> Console:
    return console if console is not None else get_console()


# ===========================================================================
# BANNER
# ===========================================================================


def _gradient_text(text: str, colors: Sequence[str] = THEME.banner_gradient) -> Text:
    """Render text with a smooth horizontal colour gradient."""
    if not text:
        return Text()

    stops = [Color.parse(color).get_truecolor() for color in colors]
    if len(stops) == 1:
        return Text(text, style=f"bold {colors[0]}")

    result = Text()
    last_index = max(len(text) - 1, 1)

    for index, char in enumerate(text):
        position = index / last_index * (len(stops) - 1)
        lower = min(int(position), len(stops) - 2)
        fraction = position - lower

        start = stops[lower]
        end = stops[lower + 1]
        red = round(start.red + (end.red - start.red) * fraction)
        green = round(start.green + (end.green - start.green) * fraction)
        blue = round(start.blue + (end.blue - start.blue) * fraction)

        result.append(char, style=f"bold #{red:02x}{green:02x}{blue:02x}")

    return result


def _compact_banner(
    console: Console,
    subtitle: str,
    version: str,
) -> None:
    """Print a narrow-terminal fallback banner."""
    title = Text()
    title.append(f"{ICONS.rocket} ", style=THEME.accent)
    title.append(APP_NAME, style=THEME.primary)

    body = Text()
    body.append(subtitle, style=THEME.muted)
    body.append("\n")
    body.append(f"{ICONS.tag} v{version}", style=THEME.muted)

    console.print(
        Panel(
            body,
            title=title,
            border_style=THEME.border,
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )


def banner(
    *,
    subtitle: str = "Customize. Automate. Maintain.",
    version: str | None = None,
    console: Console | None = None,
    compact: bool | None = None,
) -> None:
    """Print the Omarchy Tweaker banner.

    The full ASCII art is used when the terminal is wide enough. Narrow
    terminals receive a compact panel instead so the artwork is never mangled.

    Args:
        subtitle: Tagline printed below the banner.
        version: Version label. Defaults to the package version.
        console: Optional console to render with.
        compact: Force or disable the compact banner. ``None`` selects
            automatically based on terminal width.
    """
    output = _resolve_console(console)
    version = version or APP_VERSION
    use_compact = compact if compact is not None else output.width < BANNER_WIDTH

    if use_compact:
        _compact_banner(output, subtitle, version)
        return

    padded_art = [line.ljust(BANNER_WIDTH) for line in BANNER_ART]
    left_margin = " " * max((output.width - BANNER_WIDTH) // 2, 0)

    output.print()
    for line in padded_art:
        rendered = Text(left_margin)
        rendered.append_text(_gradient_text(line))
        output.print(
            rendered,
            no_wrap=True,
            overflow="crop",
        )
    output.print()

    tagline = Text()
    tagline.append(f"{ICONS.sparkles} ", style=THEME.accent)
    tagline.append(subtitle, style=THEME.primary)
    output.print(tagline, justify="center")

    meta = Text()
    meta.append(f"{ICONS.tag} {APP_NAME} v{version}", style=THEME.muted)
    output.print(meta, justify="center")
    output.print()


# ===========================================================================
# MESSAGES
# ===========================================================================


def _emit(
    message: str,
    *,
    icon: str,
    style: str,
    console: Console | None = None,
) -> None:
    text = Text()
    text.append(f"{icon} ", style=f"bold {style}")
    text.append(message, style=style)
    _resolve_console(console).print(text)


def success(message: str, *, console: Console | None = None) -> None:
    """Print a success message."""
    _emit(message, icon=ICONS.success, style=THEME.success, console=console)


def error(message: str, *, console: Console | None = None) -> None:
    """Print an error message."""
    _emit(message, icon=ICONS.error, style=THEME.error, console=console)


def warning(message: str, *, console: Console | None = None) -> None:
    """Print a warning message."""
    _emit(message, icon=ICONS.warning, style=THEME.warning, console=console)


def info(message: str, *, console: Console | None = None) -> None:
    """Print an informational message."""
    _emit(message, icon=ICONS.info, style=THEME.info, console=console)


def debug(message: str, *, console: Console | None = None) -> None:
    """Print a debug message."""
    _emit(message, icon=ICONS.debug, style=THEME.debug, console=console)


def note(message: str, *, console: Console | None = None) -> None:
    """Print a note or hint."""
    _emit(message, icon=ICONS.note, style=THEME.note, console=console)


# ===========================================================================
# LAYOUT
# ===========================================================================


def rule(title: str | None = None, *, console: Console | None = None) -> None:
    """Print a horizontal rule, optionally with a title."""
    _resolve_console(console).rule(title or "", style=THEME.border, align="left")


def section(
    title: str,
    *,
    subtitle: str | None = None,
    icon: str = ICONS.chevron,
    console: Console | None = None,
) -> None:
    """Print a section heading with an optional subtitle."""
    output = _resolve_console(console)

    heading = Text()
    heading.append(f"{icon} ", style=THEME.accent)
    heading.append(title.upper(), style=THEME.primary)

    output.print()
    output.print(Rule(heading, style=THEME.border, align="left"))
    if subtitle is not None:
        output.print(Text(f"  {subtitle}", style=THEME.muted))


def panel(
    body: str | Text,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    icon: str | None = None,
    border_style: str = THEME.border,
    console: Console | None = None,
) -> None:
    """Print a rounded panel containing text or Rich text."""
    title_text: Text | None = None
    if title is not None:
        title_text = Text()
        if icon is not None:
            title_text.append(f"{icon} ", style=THEME.accent)
        title_text.append(title, style=THEME.primary)

    _resolve_console(console).print(
        Panel(
            body if isinstance(body, Text) else Text(body),
            title=title_text,
            subtitle=subtitle,
            border_style=border_style,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def table(
    rows: Iterable[Sequence[object]],
    *,
    headers: Sequence[str] | None = None,
    title: str | None = None,
    console: Console | None = None,
) -> None:
    """Print rows as a table.

    Args:
        rows: Row values. Each row must match the number of headers when
            headers are provided.
        headers: Optional column headers.
        title: Optional table title.
        console: Optional console to render with.

    Raises:
        ValueError: If a row does not match the number of headers.
    """
    row_values: list[list[str | Text]] = [
        [value if isinstance(value, Text) else str(value) for value in row] for row in rows
    ]

    if headers is not None and any(len(row) != len(headers) for row in row_values):
        raise ValueError("Every row must match the number of headers.")

    column_count = (
        len(headers) if headers is not None else max((len(row) for row in row_values), default=0)
    )

    rich_table = Table(
        title=title,
        box=box.SIMPLE_HEAVY,
        border_style=THEME.border,
        header_style=THEME.primary,
        title_style=THEME.accent,
        show_header=headers is not None,
        expand=False,
    )

    for column in range(column_count):
        header = headers[column] if headers is not None else ""
        rich_table.add_column(header, overflow="fold")

    for row in row_values:
        padded = row + [""] * (column_count - len(row))
        rich_table.add_row(*padded)

    _resolve_console(console).print(rich_table)


def key_value_table(
    data: Mapping[str, object],
    *,
    title: str | None = None,
    console: Console | None = None,
) -> None:
    """Print a mapping as a two-column key/value table."""
    rows = ((key, value) for key, value in data.items())
    table(rows, headers=("Key", "Value"), title=title, console=console)


def bullet_list(
    items: Iterable[object],
    *,
    icon: str = ICONS.bullet,
    console: Console | None = None,
) -> None:
    """Print items as an icon-prefixed list."""
    output = _resolve_console(console)

    for item in items:
        text = Text()
        text.append(f"{icon} ", style=THEME.accent)
        text.append(str(item), style=THEME.text)
        output.print(text)


def numbered_list(
    items: Iterable[object],
    *,
    start: int = 1,
    console: Console | None = None,
) -> None:
    """Print items as a numbered list."""
    output = _resolve_console(console)

    for index, item in enumerate(items, start=start):
        text = Text()
        text.append(f"{ICONS.chevron} ", style=THEME.accent)
        text.append(f"{index}. ", style=THEME.primary)
        text.append(str(item), style=THEME.text)
        output.print(text)


def clear_screen(*, console: Console | None = None) -> None:
    """Clear the terminal when it is attached to a real TTY."""
    output = _resolve_console(console)
    if output.is_terminal:
        output.clear()


# ===========================================================================
# RICH CONTENT
# ===========================================================================


def badge(label: str, *, style: str | None = None) -> Text:
    """Return a compact styled badge for tables, panels, and inline text."""
    return Text(f" {label} ", style=style or THEME.badge)


def columns(
    items: Iterable[object],
    *,
    title: str | None = None,
    equal: bool = False,
    console: Console | None = None,
) -> None:
    """Print items as Rich columns."""
    values = [Text(str(item), style=THEME.text) for item in items]
    title_text = Text(title, style=THEME.accent) if title is not None else None
    _resolve_console(console).print(
        Columns(
            values,
            title=title_text,
            equal=equal,
            expand=False,
            padding=(0, 2),
        )
    )


def markdown(
    text: str,
    *,
    title: str | None = None,
    console: Console | None = None,
) -> None:
    """Print Markdown content with Rich rendering."""
    output = _resolve_console(console)
    if title is not None:
        output.print(Text(title, style=THEME.primary))
    output.print(Markdown(text))


def syntax(
    code: str,
    language: str = "text",
    *,
    title: str | None = None,
    line_numbers: bool = False,
    console: Console | None = None,
) -> None:
    """Print syntax-highlighted source code."""
    output = _resolve_console(console)
    if title is not None:
        output.print(Text(title, style=THEME.primary))
    output.print(
        Syntax(
            code,
            language,
            line_numbers=line_numbers,
            theme="monokai",
            word_wrap=True,
        )
    )


def json_view(
    data: object,
    *,
    title: str | None = None,
    indent: int = 2,
    console: Console | None = None,
) -> None:
    """Print data as syntax-highlighted JSON."""
    output = _resolve_console(console)
    if title is not None:
        output.print(Text(title, style=THEME.primary))
    output.print(JSON.from_data(data, indent=indent))


def _build_tree(node: TreeNode) -> Tree:
    branch = Tree(
        Text(node.label, style=node.style or THEME.text),
        guide_style=THEME.muted,
    )
    for child in node.children:
        branch.add(_build_tree(child))
    return branch


def tree(
    root: TreeNode,
    *,
    title: str | None = None,
    console: Console | None = None,
) -> None:
    """Print a validated tree structure."""
    output = _resolve_console(console)
    if title is not None:
        output.print(Text(title, style=THEME.primary))
    output.print(_build_tree(root))


# ===========================================================================
# SPINNERS AND PROGRESS
# ===========================================================================


@contextmanager
def spinner(
    message: str,
    *,
    spinner_name: str = "dots",
    console: Console | None = None,
) -> Iterator[Status]:
    """Show a spinner while a block of work runs.

    Args:
        message: Text shown next to the spinner.
        spinner_name: Rich spinner style name.
        console: Optional console to render with.

    Yields:
        The Rich status object, which can be updated with ``status.update()``.
    """
    output = _resolve_console(console)
    with output.status(
        f"{ICONS.gear} {message}",
        spinner=spinner_name,
        spinner_style=THEME.accent,
    ) as status:
        yield status


@contextmanager
def progress_bar(
    *,
    console: Console | None = None,
    transient: bool = False,
) -> Iterator[Progress]:
    """Create a Rich progress display for one or more tasks.

    Args:
        console: Optional console to render with.
        transient: Remove the progress display when it finishes.

    Yields:
        A Rich ``Progress`` instance. Add tasks with ``progress.add_task``.
    """
    output = _resolve_console(console)
    progress = Progress(
        SpinnerColumn(style=THEME.accent),
        TextColumn("[progress.description]{task.description}", style=THEME.text),
        BarColumn(bar_width=None, style=THEME.muted, complete_style=THEME.success),
        TaskProgressColumn(style=THEME.primary),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=output,
        transient=transient,
    )

    with progress:
        yield progress


def track[T](
    iterable: Iterable[T],
    description: str,
    *,
    total: int | None = None,
    console: Console | None = None,
) -> Iterator[T]:
    """Yield items while displaying progress for the iteration.

    Args:
        iterable: Items to iterate over.
        description: Task description shown in the progress display.
        total: Total number of items. Inferred for sized iterables.
        console: Optional console to render with.

    Yields:
        Each item from ``iterable``.
    """
    if total is None and isinstance(iterable, Sized):
        total = len(iterable)

    with progress_bar(console=console) as progress:
        task_id = progress.add_task(description, total=total)
        for item in iterable:
            yield item
            progress.advance(task_id)


# ===========================================================================
# VIRTUAL TERMINAL
# ===========================================================================


class VirtualTerminal:
    """A fixed-height terminal buffer that redraws in place.

    The terminal keeps a bounded scrollback buffer and only renders the most
    recent ``height`` lines. Use it as a context manager so the live display is
    started and stopped cleanly::

        with VirtualTerminal(height=8, title="Build") as terminal:
            terminal.run(["uv", "run", "poe", "check"])

    Commands are executed without a shell. Use an explicit shell invocation
    when shell features are required::

        terminal.run(["bash", "-lc", "echo hello | wc -l"])

    Writes made before the context manager starts are buffered and rendered as
    soon as the display starts.
    """

    def __init__(
        self,
        *,
        height: int = 10,
        max_lines: int = 1000,
        title: str = "Terminal",
        show_line_numbers: bool = False,
        border_style: str = THEME.border,
        console: Console | None = None,
    ) -> None:
        """Create a virtual terminal.

        Args:
            height: Number of lines visible at once.
            max_lines: Maximum number of lines kept in scrollback.
            title: Panel title.
            show_line_numbers: Prefix each visible line with its line number.
            border_style: Rich style for the panel border.
            console: Optional console to render with.

        Raises:
            pydantic.ValidationError: If the configuration is invalid.
        """
        self.config = VirtualTerminalConfig(
            height=height,
            max_lines=max_lines,
            title=title,
            show_line_numbers=show_line_numbers,
            border_style=border_style,
        )
        self._console = _resolve_console(console)
        self._buffer: deque[Text] = deque(maxlen=self.config.max_lines)
        self._line_count = 0
        self._live: Live | None = None

    @property
    def height(self) -> int:
        """Number of lines visible at once."""
        return self.config.height

    @property
    def line_count(self) -> int:
        """Total number of lines written since the last clear."""
        return self._line_count

    @property
    def lines(self) -> tuple[str, ...]:
        """Return all buffered lines as plain text, oldest first."""
        return tuple(line.plain for line in self._buffer)

    @property
    def visible_lines(self) -> tuple[str, ...]:
        """Return the lines currently visible in the terminal."""
        return tuple(line.plain for line in list(self._buffer)[-self.config.height :])

    @property
    def is_started(self) -> bool:
        """Return whether the live display is running."""
        return self._live is not None

    def write(
        self,
        text: str,
        *,
        style: str | None = None,
        refresh: bool = True,
    ) -> None:
        """Write text to the terminal, splitting it into lines.

        Carriage-return updates within a single write are collapsed to their
        final segment so progress output does not flood the buffer.

        Args:
            text: Text to append.
            style: Optional Rich style for plain-text lines.
            refresh: Whether to redraw immediately.
        """
        if not text:
            return

        normalized = text.replace("\r\n", "\n")
        lines = normalized.split("\n")
        if lines and lines[-1] == "":
            lines.pop()

        for line in lines:
            line = line.rstrip("\r")
            if "\r" in line:
                line = line.rsplit("\r", 1)[-1]
            self._append(line, style)

        if refresh:
            self.refresh()

    def write_lines(
        self,
        lines: Iterable[str],
        *,
        style: str | None = None,
        refresh: bool = True,
    ) -> None:
        """Write an iterable of lines to the terminal.

        Args:
            lines: Lines to append. Trailing newlines are accepted.
            style: Optional Rich style for plain-text lines.
            refresh: Whether to redraw immediately.
        """
        for line in lines:
            self.write(line, style=style, refresh=False)
        if refresh:
            self.refresh()

    def writeline(
        self,
        line: str | Text = "",
        *,
        style: str | None = None,
        refresh: bool = True,
    ) -> None:
        """Append one line to the terminal.

        Args:
            line: Plain text or Rich text to append.
            style: Optional Rich style when ``line`` is plain text.
            refresh: Whether to redraw immediately.
        """
        self._append(line, style)
        if refresh:
            self.refresh()

    def run(
        self,
        command: Sequence[str] | str,
        *,
        cwd: Path | str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check: bool = False,
        echo: bool = True,
    ) -> int:
        """Run a command and stream its combined output into the terminal.

        The command is executed without a shell. When shell features are
        required, pass an explicit shell invocation such as
        ``["bash", "-lc", "command"]``. Standard output and standard error are
        merged in arrival order.

        Args:
            command: Command and arguments, or a command string split with
                :func:`shlex.split`.
            cwd: Working directory for the command.
            env: Optional environment overrides for the command.
            timeout: Maximum number of seconds to wait for output and exit.
            check: Raise :class:`subprocess.CalledProcessError` on a non-zero
                exit status.
            echo: Write the command line to the terminal before running it.

        Returns:
            The process exit code.

        Raises:
            ValueError: If the command is empty.
            subprocess.TimeoutExpired: If the command exceeds ``timeout``.
            subprocess.CalledProcessError: If ``check`` is set and the command
                exits with a non-zero status.
        """
        args = self._normalize_command(command)
        if not args:
            raise ValueError("run() requires a non-empty command.")

        if echo:
            prompt = Text()
            prompt.append("$ ", style=THEME.accent)
            prompt.append(shlex.join(args), style=THEME.primary)
            self.writeline(prompt)

        # Commands are argument lists; shell execution is never used.
        process = subprocess.Popen(  # nosec B603
            args,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        stdout = process.stdout
        if stdout is None:
            raise RuntimeError("Command process did not provide stdout.")

        output: queue.Queue[str | None] = queue.Queue()

        def _read_output() -> None:
            try:
                for line in stdout:
                    output.put(line)
            finally:
                output.put(None)

        reader = threading.Thread(target=_read_output, daemon=True)
        reader.start()

        deadline = monotonic() + timeout if timeout is not None else None
        timeout_seconds = timeout if timeout is not None else 0.0
        try:
            while True:
                if deadline is None:
                    line = output.get()
                else:
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(args, timeout_seconds)
                    try:
                        line = output.get(timeout=remaining)
                    except queue.Empty:
                        raise subprocess.TimeoutExpired(args, timeout_seconds) from None

                if line is None:
                    break
                self.write(line, refresh=True)

            wait_timeout = None if deadline is None else max(deadline - monotonic(), 0.0)
            returncode = process.wait(timeout=wait_timeout)
        except subprocess.TimeoutExpired:
            self.writeline(
                f"Command timed out after {timeout}s",
                style=THEME.error,
            )
            self._stop_process(process)
            raise
        finally:
            reader.join(timeout=1)
            stdout.close()

        if returncode != 0:
            self.writeline(
                f"Process exited with code {returncode}",
                style=THEME.error,
            )

        if check and returncode != 0:
            raise subprocess.CalledProcessError(returncode, args)

        return returncode

    @staticmethod
    def _normalize_command(command: Sequence[str] | str) -> list[str]:
        if isinstance(command, str):
            return shlex.split(command)
        return [str(part) for part in command]

    @staticmethod
    def _stop_process(process: subprocess.Popen[str]) -> None:
        try:
            process.terminate()
        except ProcessLookupError:
            return

        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except ProcessLookupError:
                return
            process.wait()

    def clear(self, *, refresh: bool = True) -> None:
        """Remove all buffered lines and reset the line counter."""
        self._buffer.clear()
        self._line_count = 0
        if refresh:
            self.refresh()

    def render(self) -> Panel:
        """Build the fixed-height Rich panel for the current buffer."""
        visible = list(self._buffer)[-self.config.height :]
        padding = self.config.height - len(visible)
        first_line_number = self._line_count - len(visible) + 1

        body = Text(no_wrap=True, overflow="ellipsis")
        for index in range(self.config.height):
            if index:
                body.append("\n")

            if index < padding:
                if self.config.show_line_numbers:
                    body.append("     ", style=THEME.muted)
                continue

            line = visible[index - padding]
            if self.config.show_line_numbers:
                line_number = first_line_number + (index - padding)
                body.append(f"{line_number:>4} ", style=THEME.muted)
            body.append_text(line)

        title = Text()
        title.append(f"{ICONS.terminal} ", style=THEME.accent)
        title.append(self.config.title, style=THEME.primary)

        return Panel(
            body,
            title=title,
            subtitle=Text(f"{self._line_count} lines", style=THEME.muted),
            border_style=self.config.border_style,
            box=box.ROUNDED,
            padding=(0, 1),
        )

    def start(self) -> None:
        """Start the in-place live display."""
        if self._live is not None:
            return

        self._live = Live(
            self.render(),
            console=self._console,
            auto_refresh=False,
            transient=False,
        )
        self._live.start()
        self._live.update(self.render(), refresh=True)

    def stop(self) -> None:
        """Stop the live display, leaving the final frame visible."""
        if self._live is None:
            return

        self._live.stop()
        self._live = None
        if not self._console.is_terminal:
            self._console.print()

    def refresh(self) -> None:
        """Redraw the terminal when the live display is running."""
        if self._live is not None:
            self._live.update(self.render(), refresh=True)

    def _append(self, line: str | Text, style: str | None = None) -> None:
        if isinstance(line, Text):
            self._buffer.append(line)
        else:
            self._buffer.append(Text.from_ansi(line, style=style or THEME.text))
        self._line_count += 1

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()


@contextmanager
def virtual_terminal(
    *,
    height: int = 10,
    max_lines: int = 1000,
    title: str = "Terminal",
    show_line_numbers: bool = False,
    border_style: str = THEME.border,
    console: Console | None = None,
) -> Iterator[VirtualTerminal]:
    """Run a fixed-height virtual terminal as a context manager.

    Args:
        height: Number of lines visible at once.
        max_lines: Maximum number of lines kept in scrollback.
        title: Panel title.
        show_line_numbers: Prefix each visible line with its line number.
        border_style: Rich style for the panel border.
        console: Optional console to render with.

    Yields:
        The running virtual terminal.
    """
    terminal = VirtualTerminal(
        height=height,
        max_lines=max_lines,
        title=title,
        show_line_numbers=show_line_numbers,
        border_style=border_style,
        console=console,
    )
    with terminal:
        yield terminal


# ===========================================================================
# PROMPTS
# ===========================================================================


def is_interactive() -> bool:
    """Return whether both stdin and stdout are attached to a TTY."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _require_interactive() -> None:
    if not is_interactive():
        raise RuntimeError("Interactive prompts require a TTY.")


def _ask(question: dict[str, Any]) -> object:
    _require_interactive()
    result: InquirerPySessionResult = _inquirer_prompt(
        [question],
        style=PROMPT_STYLE,
        style_override=False,
    )
    return result[question["name"]]


def prompt_text(
    message: str,
    *,
    default: str = "",
    placeholder: str | None = None,
    instruction: str | None = None,
    validator: Callable[[str], bool | str] | None = None,
) -> str:
    """Prompt for a line of text.

    Args:
        message: Question shown to the user.
        default: Value returned when the user submits an empty answer.
        placeholder: Placeholder text shown while typing.
        instruction: Short instruction shown next to the prompt.
        validator: Optional validator returning ``True`` or an error message.

    Returns:
        The entered text.
    """
    question: dict[str, Any] = {
        "type": "input",
        "name": "value",
        "message": message,
        "default": default,
        "qmark": ICONS.prompt,
        "amark": ICONS.success,
    }

    if placeholder is not None:
        question["long_instruction"] = placeholder
    if instruction is not None:
        question["instruction"] = instruction
    if validator is not None:
        question["validate"] = validator

    value = _ask(question)
    return default if value is None else str(value)


def confirm(
    message: str,
    *,
    default: bool = False,
    instruction: str | None = None,
) -> bool:
    """Prompt for a yes/no confirmation.

    Args:
        message: Question shown to the user.
        default: Answer used when the user presses Enter.
        instruction: Short instruction shown next to the prompt.

    Returns:
        ``True`` for yes, otherwise ``False``.
    """
    question: dict[str, Any] = {
        "type": "confirm",
        "name": "confirmed",
        "message": message,
        "default": default,
        "qmark": ICONS.prompt,
        "amark": ICONS.success,
    }

    if instruction is not None:
        question["instruction"] = instruction

    return bool(_ask(question))


def password(
    message: str,
    *,
    instruction: str | None = None,
) -> str:
    """Prompt for a secret value without echoing it.

    Args:
        message: Question shown to the user.
        instruction: Short instruction shown next to the prompt.

    Returns:
        The entered secret.
    """
    question: dict[str, Any] = {
        "type": "password",
        "name": "password",
        "message": message,
        "qmark": ICONS.prompt,
        "amark": ICONS.success,
    }

    if instruction is not None:
        question["instruction"] = instruction

    value = _ask(question)
    return "" if value is None else str(value)


def select(
    message: str,
    choices: Sequence[str],
    *,
    default: str | None = None,
    instruction: str | None = None,
) -> str:
    """Prompt the user to select one option.

    Args:
        message: Question shown to the user.
        choices: Available options.
        default: Option selected initially.
        instruction: Short instruction shown next to the prompt.

    Returns:
        The selected option.

    Raises:
        ValueError: If no choices are provided.
        RuntimeError: If the prompt returns no selection.
    """
    if not choices:
        raise ValueError("select() requires at least one choice.")

    question: dict[str, Any] = {
        "type": "list",
        "name": "selected",
        "message": message,
        "choices": list(choices),
        "pointer": ICONS.pointer,
        "qmark": ICONS.prompt,
        "amark": ICONS.success,
    }

    if default is not None:
        question["default"] = default
    if instruction is not None:
        question["instruction"] = instruction

    value = _ask(question)
    if value is None:
        raise RuntimeError("No selection was made.")

    return str(value)


def checkbox(
    message: str,
    choices: Sequence[str],
    *,
    default: Sequence[str] = (),
    instruction: str | None = None,
) -> list[str]:
    """Prompt the user to select zero or more options.

    Args:
        message: Question shown to the user.
        choices: Available options.
        default: Options selected initially.
        instruction: Short instruction shown next to the prompt.

    Returns:
        The selected options.

    Raises:
        ValueError: If no choices are provided.
    """
    if not choices:
        raise ValueError("checkbox() requires at least one choice.")

    question: dict[str, Any] = {
        "type": "checkbox",
        "name": "selected",
        "message": message,
        "choices": list(choices),
        "default": list(default),
        "pointer": ICONS.pointer,
        "qmark": ICONS.prompt,
        "amark": ICONS.success,
    }

    if instruction is not None:
        question["instruction"] = instruction

    value = _ask(question)
    if isinstance(value, list):
        return [str(item) for item in value]

    return []


# ===========================================================================
# PROMPT TOOLKIT PROMPTS
# ===========================================================================


def _make_prompt_session(
    *,
    completer: Completer | None = None,
    complete_while_typing: bool = False,
) -> PromptSession[str]:
    return PromptSession(
        style=PROMPT_TOOLKIT_STYLE,
        completer=completer,
        complete_while_typing=complete_while_typing,
    )


def prompt_multiline(
    message: str,
    *,
    default: str = "",
    instruction: str | None = None,
) -> str:
    """Prompt for multi-line text using Prompt Toolkit.

    Args:
        message: Question shown to the user.
        default: Initial buffer contents.
        instruction: Text shown in the bottom toolbar.

    Returns:
        The entered text.
    """
    _require_interactive()
    session = _make_prompt_session()
    return session.prompt(
        f"{message} ",
        default=default,
        multiline=True,
        prompt_continuation="... ",
        bottom_toolbar=instruction or "Press Esc+Enter or Alt+Enter to submit.",
    )


def prompt_autocomplete(
    message: str,
    suggestions: Sequence[str],
    *,
    default: str = "",
    case_sensitive: bool = False,
    instruction: str | None = None,
) -> str:
    """Prompt for text with word completion using Prompt Toolkit.

    Args:
        message: Question shown to the user.
        suggestions: Words offered by the completer.
        default: Initial buffer contents.
        case_sensitive: Whether completions should match case.
        instruction: Text shown in the bottom toolbar.

    Returns:
        The entered text.

    Raises:
        ValueError: If no suggestions are provided.
    """
    if not suggestions:
        raise ValueError("prompt_autocomplete() requires at least one suggestion.")

    _require_interactive()
    completer = WordCompleter(list(suggestions), ignore_case=not case_sensitive)
    session = _make_prompt_session(
        completer=completer,
        complete_while_typing=True,
    )
    return session.prompt(
        f"{message} ",
        default=default,
        bottom_toolbar=instruction or "Tab to complete, Enter to submit.",
    )


def prompt_path(
    message: str,
    *,
    default: Path | None = None,
    must_exist: bool = False,
    only_directories: bool = False,
    instruction: str | None = None,
) -> Path:
    """Prompt for a filesystem path with completion using Prompt Toolkit.

    Args:
        message: Question shown to the user.
        default: Initial path.
        must_exist: Require the resulting path to exist.
        only_directories: Restrict completion and validation to directories.
        instruction: Text shown in the bottom toolbar.

    Returns:
        The expanded path entered by the user.

    Raises:
        ValueError: If the user submits an empty path.
        FileNotFoundError: If ``must_exist`` is set and the path is missing.
        NotADirectoryError: If ``only_directories`` is set and the path is not
            a directory.
    """
    _require_interactive()
    completer = PathCompleter(expanduser=True, only_directories=only_directories)
    session = _make_prompt_session(
        completer=completer,
        complete_while_typing=True,
    )
    raw = session.prompt(
        f"{message} ",
        default=str(default) if default is not None else "",
        bottom_toolbar=instruction or "Tab to complete paths, Enter to submit.",
    ).strip()

    if not raw:
        raise ValueError("prompt_path() requires a non-empty path.")

    path = Path(raw).expanduser()

    if must_exist and not path.exists():
        raise FileNotFoundError(path)
    if only_directories and path.exists() and not path.is_dir():
        raise NotADirectoryError(path)

    return path


# ===========================================================================
# VALIDATED MENUS
# ===========================================================================


def menu_select(
    menu: Menu,
    *,
    default: str | None = None,
    instruction: str | None = None,
) -> str:
    """Prompt with a validated menu and return the selected value.

    Args:
        menu: Menu definition.
        default: Value selected initially.
        instruction: Short instruction shown next to the prompt.

    Returns:
        The value associated with the selected label.
    """
    default_label = menu.label_for(default) if default is not None else None
    selected = select(
        menu.title,
        menu.labels,
        default=default_label,
        instruction=instruction,
    )
    return menu.value_for(selected)


def menu_checkbox(
    menu: Menu,
    *,
    default: Sequence[str] = (),
    instruction: str | None = None,
) -> list[str]:
    """Prompt with a validated menu and return selected values.

    Args:
        menu: Menu definition.
        default: Values selected initially.
        instruction: Short instruction shown next to the prompt.

    Returns:
        Values associated with the selected labels.
    """
    default_labels = [menu.label_for(value) for value in default]
    selected = checkbox(
        menu.title,
        menu.labels,
        default=default_labels,
        instruction=instruction,
    )
    return [menu.value_for(label) for label in selected]
