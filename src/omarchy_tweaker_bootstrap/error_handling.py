"""Process-wide rich exception rendering for Omarchy Tweaker.

Importing :mod:`omarchy_tweaker` installs these handlers before any application
module is imported. Uncaught exceptions from the main thread, worker threads,
and unraisable contexts are rendered with Rich. Syntax and indentation errors
receive a dedicated code frame because their source location is not part of the
runtime traceback.
"""

from __future__ import annotations

import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Final

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.traceback import Traceback

DEFAULT_WIDTH: Final = 200
DEFAULT_CODE_WIDTH: Final = 88
DEFAULT_EXTRA_LINES: Final = 3
DEFAULT_LOCALS_MAX_LENGTH: Final = 10
DEFAULT_LOCALS_MAX_STRING: Final = 100


@dataclass(frozen=True)
class ErrorHandlingConfig:
    """Options controlling rich exception rendering."""

    width: int | None = DEFAULT_WIDTH
    code_width: int | None = DEFAULT_CODE_WIDTH
    extra_lines: int = DEFAULT_EXTRA_LINES
    theme: str | None = None
    word_wrap: bool = True
    show_locals: bool = True
    locals_max_length: int = DEFAULT_LOCALS_MAX_LENGTH
    locals_max_string: int = DEFAULT_LOCALS_MAX_STRING
    indent_guides: bool = True


def install_error_handling(
    *,
    console: Console | None = None,
    config: ErrorHandlingConfig | None = None,
) -> None:
    """Install rich handlers for uncaught exceptions across the process.

    Args:
        console: Optional console used for exception output. Defaults to a
            stderr console.
        config: Optional rendering configuration.
    """
    output = console or Console(stderr=True)
    options = config or ErrorHandlingConfig()

    def excepthook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        print_exception(
            exc_type,
            exc_value,
            exc_traceback,
            console=output,
            config=options,
        )

    def thread_excepthook(args: threading.ExceptHookArgs) -> None:
        if args.exc_type is None or args.exc_value is None:
            return
        print_exception(
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
            console=output,
            config=options,
        )

    def unraisable_hook(unraisable: Any) -> None:
        if unraisable.exc_type is None or unraisable.exc_value is None:
            return
        if unraisable.err_msg:
            output.print(Text(unraisable.err_msg, style="bold yellow"))
        print_exception(
            unraisable.exc_type,
            unraisable.exc_value,
            unraisable.exc_traceback,
            console=output,
            config=options,
        )

    sys.excepthook = excepthook
    threading.excepthook = thread_excepthook
    sys.unraisablehook = unraisable_hook


def print_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
    *,
    console: Console | None = None,
    config: ErrorHandlingConfig | None = None,
) -> None:
    """Render an exception with rich formatting.

    Args:
        exc_type: Exception type.
        exc_value: Exception instance.
        exc_traceback: Exception traceback, if available.
        console: Optional console used for output. Defaults to a stderr console.
        config: Optional rendering configuration.
    """
    output = console or Console(stderr=True)
    options = config or ErrorHandlingConfig()

    if isinstance(exc_value, SyntaxError):
        output.print(_syntax_error_panel(exc_value))
        return

    output.print(
        Traceback.from_exception(
            exc_type,
            exc_value,
            exc_traceback,
            width=options.width,
            code_width=options.code_width,
            extra_lines=options.extra_lines,
            theme=options.theme,
            word_wrap=options.word_wrap,
            show_locals=options.show_locals,
            locals_max_length=options.locals_max_length,
            locals_max_string=options.locals_max_string,
            indent_guides=options.indent_guides,
        )
    )


def _syntax_error_panel(error: SyntaxError) -> Panel:
    filename = error.filename or "<unknown>"
    lineno = error.lineno or 1
    source_lines = _read_source(filename, error.text).splitlines()
    if not source_lines:
        source_lines = [error.text or ""]

    last_line = max(len(source_lines), lineno)
    start = max(1, lineno - 3)
    end = min(last_line, lineno + 2)
    number_width = len(str(max(end, 1)))

    body = Text(no_wrap=False)
    for number in range(start, end + 1):
        line = source_lines[number - 1] if number <= len(source_lines) else ""
        marker = "❱" if number == lineno else " "
        line_style = "bold red" if number == lineno else "dim"
        body.append(f"{marker} {number:>{number_width}} │ ", style=line_style)
        body.append(line, style="red" if number == lineno else "default")
        body.append("\n")

        if number == lineno:
            caret_offset = error.offset or 0
            if isinstance(error, IndentationError):
                caret_offset = len(line) - len(line.lstrip()) + 1
            if caret_offset > 0:
                padding = 2 + number_width + 3 + caret_offset - 1
                body.append(" " * padding + "^\n", style="bold red")

    body.append(f"{type(error).__name__}: {error.msg}", style="bold red")

    title = Text()
    title.append(f"{filename}:{lineno}", style="bold red")

    return Panel(
        body,
        title=title,
        border_style="red",
        padding=(0, 1),
    )


def _read_source(filename: str, fallback: str | None) -> str:
    if filename and filename != "<unknown>":
        try:
            return Path(filename).read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    return fallback or ""
