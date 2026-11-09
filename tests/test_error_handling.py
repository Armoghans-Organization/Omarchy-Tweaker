from __future__ import annotations

import sys
import threading
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from rich.console import Console

from omarchy_tweaker import error_handling


def _make_console() -> tuple[Console, StringIO]:
    stream = StringIO()
    console = Console(
        file=stream,
        width=100,
        force_terminal=False,
        color_system=None,
        highlight=False,
    )
    return console, stream


def test_print_exception_renders_regular_traceback() -> None:
    console, stream = _make_console()

    def fail() -> None:
        raise ValueError("boom")

    try:
        fail()
    except ValueError as error:
        error_handling.print_exception(
            type(error),
            error,
            error.__traceback__,
            console=console,
        )

    output = stream.getvalue()
    assert "Traceback" in output
    assert "ValueError: boom" in output


def test_print_exception_renders_indentation_error_with_source(tmp_path: Path) -> None:
    console, stream = _make_console()
    source_path = tmp_path / "bad_module.py"
    source_path.write_text(
        "def broken() -> None:\n    if True:\n        pass\n      pass\n",
        encoding="utf-8",
    )

    try:
        compile(source_path.read_text(encoding="utf-8"), str(source_path), "exec")
    except IndentationError as error:
        error_handling.print_exception(
            type(error),
            error,
            error.__traceback__,
            console=console,
        )

    output = stream.getvalue()
    assert f"{source_path}:4" in output
    assert "IndentationError" in output
    assert "pass" in output
    assert "^" in output


def test_print_exception_renders_syntax_error_without_traceback() -> None:
    console, stream = _make_console()

    try:
        compile("def broken(:\n    pass\n", "broken.py", "exec")
    except SyntaxError as error:
        error_handling.print_exception(
            type(error),
            error,
            None,
            console=console,
        )

    output = stream.getvalue()
    assert "broken.py:1" in output
    assert "SyntaxError" in output


def test_install_error_handling_sets_process_hooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    monkeypatch.setattr(threading, "excepthook", threading.excepthook)
    monkeypatch.setattr(sys, "unraisablehook", sys.unraisablehook)

    original_excepthook = sys.excepthook
    original_thread_hook = threading.excepthook
    original_unraisable_hook = sys.unraisablehook

    error_handling.install_error_handling()

    assert sys.excepthook is not original_excepthook
    assert threading.excepthook is not original_thread_hook
    assert sys.unraisablehook is not original_unraisable_hook


def test_installed_excepthook_uses_custom_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console, stream = _make_console()
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)

    error_handling.install_error_handling(console=console)

    try:
        raise RuntimeError("main thread boom")
    except RuntimeError as error:
        sys.excepthook(type(error), error, error.__traceback__)

    assert "RuntimeError: main thread boom" in stream.getvalue()


def test_installed_thread_hook_uses_custom_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console, stream = _make_console()
    monkeypatch.setattr(threading, "excepthook", threading.excepthook)

    error_handling.install_error_handling(console=console)

    try:
        raise RuntimeError("thread boom")
    except RuntimeError as error:
        args = threading.ExceptHookArgs((type(error), error, error.__traceback__, None))
        threading.excepthook(args)

    assert "RuntimeError: thread boom" in stream.getvalue()


def test_installed_unraisable_hook_uses_custom_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console, stream = _make_console()
    monkeypatch.setattr(sys, "unraisablehook", sys.unraisablehook)

    error_handling.install_error_handling(console=console)

    class FakeUnraisable:
        exc_type = RuntimeError
        exc_value = RuntimeError("unraisable boom")
        exc_traceback = None
        err_msg = "Exception ignored in test"
        object: Any = None

    sys.unraisablehook(FakeUnraisable())  # type: ignore[arg-type]

    output = stream.getvalue()
    assert "Exception ignored in test" in output
    assert "RuntimeError: unraisable boom" in output
