from __future__ import annotations

import subprocess
import sys
import threading
from collections.abc import Sequence
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from InquirerPy.utils import InquirerPyQuestions, InquirerPySessionResult
from prompt_toolkit.completion import PathCompleter, WordCompleter
from pydantic import ValidationError
from rich.console import Console
from rich.text import Text

from omarchy_tweaker.app_metadata import APP_NAME, APP_VERSION
from omarchy_tweaker.functions import ui


def _make_console(width: int = 200) -> tuple[Console, StringIO]:
    stream = StringIO()
    console = Console(
        file=stream,
        width=width,
        force_terminal=False,
        color_system=None,
        highlight=False,
    )
    return console, stream


def _noop() -> None:
    return None


def _return_false() -> bool:
    return False


def _return_true() -> bool:
    return True


class FakeStream:
    def __init__(self, lines: Sequence[str]) -> None:
        self._lines = iter(lines)
        self.closed = False

    def __iter__(self) -> FakeStream:
        return self

    def __next__(self) -> str:
        return next(self._lines)

    def close(self) -> None:
        self.closed = True


class FakeProcess:
    def __init__(
        self,
        command: Sequence[str],
        lines: Sequence[str],
        *,
        returncode: int = 0,
    ) -> None:
        self.command = command
        self.stdout = FakeStream(lines)
        self.returncode = returncode
        self.terminated = False
        self.killed = False

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


class BlockingStream:
    def __init__(self) -> None:
        self.released = threading.Event()
        self.closed = False

    def __iter__(self) -> BlockingStream:
        return self

    def __next__(self) -> str:
        self.released.wait()
        raise StopIteration

    def close(self) -> None:
        self.closed = True


class BlockingProcess:
    def __init__(self) -> None:
        self.stdout = BlockingStream()
        self.returncode = -15
        self.terminated = False
        self.killed = False

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.stdout.released.set()

    def kill(self) -> None:
        self.killed = True
        self.stdout.released.set()


def test_banner_renders_art_and_metadata() -> None:
    console, stream = _make_console(width=200)

    ui.banner(console=console)

    output = stream.getvalue()
    assert ui.BANNER_ART[0] in output
    assert APP_NAME in output
    assert APP_VERSION in output
    assert "Customize. Automate. Maintain." in output


def test_banner_uses_compact_layout_on_narrow_terminals() -> None:
    console, stream = _make_console(width=60)

    ui.banner(console=console)

    output = stream.getvalue()
    assert APP_NAME in output
    assert APP_VERSION in output
    assert ui.BANNER_ART[0] not in output


def test_banner_compact_can_be_forced() -> None:
    console, stream = _make_console(width=200)

    ui.banner(console=console, compact=True, subtitle="Hello", version="9.9.9")

    output = stream.getvalue()
    assert ui.BANNER_ART[0] not in output
    assert "Hello" in output
    assert "9.9.9" in output


def test_gradient_text_preserves_plain_text() -> None:
    assert ui._gradient_text("Omarchy").plain == "Omarchy"


def test_message_helpers_render_icons_and_text() -> None:
    console, stream = _make_console()

    ui.success("saved", console=console)
    ui.error("failed", console=console)
    ui.warning("careful", console=console)
    ui.info("ready", console=console)
    ui.debug("trace", console=console)
    ui.note("hint", console=console)

    output = stream.getvalue()
    for icon in (
        ui.ICONS.success,
        ui.ICONS.error,
        ui.ICONS.warning,
        ui.ICONS.info,
        ui.ICONS.debug,
        ui.ICONS.note,
    ):
        assert icon in output

    for message in ("saved", "failed", "careful", "ready", "trace", "hint"):
        assert message in output


def test_section_and_rule_render_titles() -> None:
    console, stream = _make_console()

    ui.section("Setup", subtitle="Configure things", console=console)
    ui.rule("Done", console=console)

    output = stream.getvalue()
    assert "SETUP" in output
    assert "Configure things" in output
    assert "Done" in output


def test_panel_renders_body_title_subtitle_and_icon() -> None:
    console, stream = _make_console()

    ui.panel(
        "Body text",
        title="Title",
        subtitle="Subtitle",
        icon=ui.ICONS.info,
        console=console,
    )

    output = stream.getvalue()
    assert "Body text" in output
    assert "Title" in output
    assert "Subtitle" in output
    assert ui.ICONS.info in output


def test_table_renders_headers_rows_and_title() -> None:
    console, stream = _make_console()

    ui.table(
        [["alpha", 1], ["beta", 2]],
        headers=["Name", "Value"],
        title="Items",
        console=console,
    )

    output = stream.getvalue()
    for value in ("Name", "Value", "alpha", "1", "beta", "2", "Items"):
        assert value in output


def test_table_without_headers_renders_rows() -> None:
    console, stream = _make_console()

    ui.table([["alpha", "beta"]], console=console)

    output = stream.getvalue()
    assert "alpha" in output
    assert "beta" in output


def test_table_rejects_rows_that_do_not_match_headers() -> None:
    with pytest.raises(ValueError, match="number of headers"):
        ui.table([["only one"]], headers=["One", "Two"])


def test_key_value_table_renders_mapping() -> None:
    console, stream = _make_console()

    ui.key_value_table({"name": "Omarchy", "version": "1"}, console=console)

    output = stream.getvalue()
    for value in ("name", "Omarchy", "version", "1"):
        assert value in output


def test_bullet_and_numbered_lists_render_items() -> None:
    console, stream = _make_console()

    ui.bullet_list(["one", "two"], console=console)
    ui.numbered_list(["three"], start=3, console=console)

    output = stream.getvalue()
    for value in ("one", "two", "three", "3."):
        assert value in output


def test_clear_screen_is_noop_for_non_terminal() -> None:
    console, stream = _make_console()

    ui.clear_screen(console=console)

    assert stream.getvalue() == ""


def test_set_console_controls_default_console() -> None:
    console, stream = _make_console()

    ui.set_console(console)
    try:
        ui.info("hello")
    finally:
        ui.set_console(None)

    assert "hello" in stream.getvalue()


def test_spinner_context_manager_yields_status() -> None:
    console, _ = _make_console()

    with ui.spinner("Working", console=console) as status:
        assert status is not None


def test_progress_bar_advances_task() -> None:
    console, _ = _make_console()

    with ui.progress_bar(console=console) as progress:
        task = progress.add_task("Working", total=2)
        progress.advance(task)
        progress.advance(task)
        assert progress.tasks[0].completed == 2


def test_track_yields_all_items() -> None:
    console, _ = _make_console()

    assert list(ui.track([1, 2, 3], "Working", console=console)) == [1, 2, 3]


def test_prompt_helpers_forward_question_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers: dict[str, Any] = {
        "input": "hello",
        "confirm": True,
        "password": "secret",
        "list": "beta",
        "checkbox": ["a", "c"],
    }
    seen: list[dict[str, Any]] = []
    styles: list[object] = []

    def fake_prompt(
        questions: InquirerPyQuestions,
        **kwargs: object,
    ) -> InquirerPySessionResult:
        question = questions[0] if isinstance(questions, list) else questions
        seen.append(question)
        styles.append(kwargs["style"])
        return {question["name"]: answers[question["type"]]}

    monkeypatch.setattr(ui, "_require_interactive", _noop)
    monkeypatch.setattr(ui, "_inquirer_prompt", fake_prompt)

    assert ui.prompt_text("Name?") == "hello"
    assert ui.confirm("Continue?") is True
    assert ui.password("Secret?") == "secret"
    assert ui.select("Pick", ["alpha", "beta"]) == "beta"
    assert ui.checkbox("Choose", ["a", "b", "c"]) == ["a", "c"]

    assert [question["type"] for question in seen] == [
        "input",
        "confirm",
        "password",
        "list",
        "checkbox",
    ]
    assert all(style is ui.PROMPT_STYLE for style in styles)
    assert all("style" not in question for question in seen)


def test_prompt_text_returns_default_when_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_prompt(
        questions: InquirerPyQuestions,
        **kwargs: object,
    ) -> InquirerPySessionResult:
        return {"value": None}

    monkeypatch.setattr(ui, "_require_interactive", _noop)
    monkeypatch.setattr(ui, "_inquirer_prompt", fake_prompt)

    assert ui.prompt_text("Name?", default="fallback") == "fallback"


def test_checkbox_returns_empty_list_when_no_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_prompt(
        questions: InquirerPyQuestions,
        **kwargs: object,
    ) -> InquirerPySessionResult:
        return {"selected": None}

    monkeypatch.setattr(ui, "_require_interactive", _noop)
    monkeypatch.setattr(ui, "_inquirer_prompt", fake_prompt)

    assert ui.checkbox("Choose", ["a"]) == []


def test_select_rejects_empty_choices() -> None:
    with pytest.raises(ValueError, match="at least one choice"):
        ui.select("Pick", [])


def test_checkbox_rejects_empty_choices() -> None:
    with pytest.raises(ValueError, match="at least one choice"):
        ui.checkbox("Choose", [])


def test_require_interactive_rejects_non_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", _return_false)
    monkeypatch.setattr(sys.stdout, "isatty", _return_false)

    with pytest.raises(RuntimeError, match="TTY"):
        ui._require_interactive()


def test_require_interactive_accepts_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", _return_true)
    monkeypatch.setattr(sys.stdout, "isatty", _return_true)

    ui._require_interactive()


def test_is_interactive_returns_true_when_both_streams_are_ttys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", _return_true)
    monkeypatch.setattr(sys.stdout, "isatty", _return_true)

    assert ui.is_interactive() is True


def test_is_interactive_returns_false_when_stdin_is_not_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", _return_false)
    monkeypatch.setattr(sys.stdout, "isatty", _return_true)

    assert ui.is_interactive() is False


def test_is_interactive_returns_false_when_stdout_is_not_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", _return_true)
    monkeypatch.setattr(sys.stdout, "isatty", _return_false)

    assert ui.is_interactive() is False


class _FakePromptSession:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.completer: object | None = None
        self.complete_while_typing = False

    def prompt(self, message: str, **kwargs: object) -> str:
        self.calls.append((message, kwargs))
        return self._responses.pop(0)


def _install_fake_prompt_session(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[str],
) -> _FakePromptSession:
    session = _FakePromptSession(responses)

    def fake_make_prompt_session(
        *,
        completer: object | None = None,
        complete_while_typing: bool = False,
    ) -> _FakePromptSession:
        session.completer = completer
        session.complete_while_typing = complete_while_typing
        return session

    monkeypatch.setattr(ui, "_make_prompt_session", fake_make_prompt_session)
    monkeypatch.setattr(ui, "_require_interactive", _noop)
    return session


def test_theme_rejects_short_gradient() -> None:
    with pytest.raises(ValidationError, match="at least 2"):
        ui.Theme(banner_gradient=("#000000",))


def test_menu_rejects_duplicate_labels() -> None:
    with pytest.raises(ValidationError, match="labels must be unique"):
        ui.Menu(
            title="Pick",
            options=(
                ui.MenuOption(label="Alpha", value="alpha"),
                ui.MenuOption(label="Alpha", value="beta"),
            ),
        )


def test_menu_rejects_duplicate_values() -> None:
    with pytest.raises(ValidationError, match="values must be unique"):
        ui.Menu(
            title="Pick",
            options=(
                ui.MenuOption(label="Alpha", value="same"),
                ui.MenuOption(label="Beta", value="same"),
            ),
        )


def test_menu_select_maps_label_to_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    menu = ui.Menu(
        title="Pick",
        options=(
            ui.MenuOption(label="Alpha", value="alpha"),
            ui.MenuOption(label="Beta", value="beta"),
        ),
    )

    def fake_select(
        message: str,
        choices: Sequence[str],
        **kwargs: object,
    ) -> str:
        assert message == "Pick"
        assert choices == ["Alpha", "Beta"]
        assert kwargs["default"] == "Alpha"
        return "Beta"

    monkeypatch.setattr(ui, "select", fake_select)

    assert ui.menu_select(menu, default="alpha") == "beta"


def test_menu_checkbox_maps_labels_to_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    menu = ui.Menu(
        title="Pick",
        options=(
            ui.MenuOption(label="Alpha", value="alpha"),
            ui.MenuOption(label="Beta", value="beta"),
        ),
    )

    def fake_checkbox(
        message: str,
        choices: Sequence[str],
        **kwargs: object,
    ) -> list[str]:
        assert message == "Pick"
        assert choices == ["Alpha", "Beta"]
        assert kwargs["default"] == ["Alpha"]
        return ["Beta", "Alpha"]

    monkeypatch.setattr(ui, "checkbox", fake_checkbox)

    assert ui.menu_checkbox(menu, default=("alpha",)) == ["beta", "alpha"]


def test_prompt_multiline_returns_text_and_enables_multiline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _install_fake_prompt_session(monkeypatch, ["line one\nline two"])

    result = ui.prompt_multiline(
        "Notes?",
        default="draft",
        instruction="Finish with Esc+Enter",
    )

    assert result == "line one\nline two"
    message, kwargs = session.calls[0]
    assert message == "Notes? "
    assert kwargs["default"] == "draft"
    assert kwargs["multiline"] is True
    assert kwargs["bottom_toolbar"] == "Finish with Esc+Enter"


def test_prompt_autocomplete_uses_word_completer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _install_fake_prompt_session(monkeypatch, ["zsh"])

    result = ui.prompt_autocomplete(
        "Shell?",
        ["bash", "zsh"],
        default="bash",
        case_sensitive=True,
    )

    assert result == "zsh"
    assert isinstance(session.completer, WordCompleter)
    assert session.completer.words == ["bash", "zsh"]
    assert session.completer.ignore_case is False
    assert session.complete_while_typing is True


def test_prompt_autocomplete_rejects_empty_suggestions() -> None:
    with pytest.raises(ValueError, match="at least one suggestion"):
        ui.prompt_autocomplete("Shell?", [])


def test_prompt_path_returns_expanded_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    directory = tmp_path / "config"
    directory.mkdir()
    session = _install_fake_prompt_session(monkeypatch, [str(directory)])

    result = ui.prompt_path(
        "Directory?",
        default=tmp_path,
        must_exist=True,
        only_directories=True,
    )

    assert result == directory
    assert isinstance(session.completer, PathCompleter)
    assert session.completer.only_directories is True
    assert session.completer.expanduser is True
    _, kwargs = session.calls[0]
    assert kwargs["default"] == str(tmp_path)


def test_prompt_path_rejects_missing_path_when_required(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    _install_fake_prompt_session(monkeypatch, [str(missing)])

    with pytest.raises(FileNotFoundError):
        ui.prompt_path("Directory?", must_exist=True)


def test_prompt_path_rejects_file_when_only_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("content", encoding="utf-8")
    _install_fake_prompt_session(monkeypatch, [str(file_path)])

    with pytest.raises(NotADirectoryError):
        ui.prompt_path("Directory?", only_directories=True)


def test_prompt_path_rejects_empty_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_prompt_session(monkeypatch, ["   "])

    with pytest.raises(ValueError, match="non-empty path"):
        ui.prompt_path("Directory?")


def test_badge_returns_styled_text() -> None:
    badge = ui.badge("validated")

    assert badge.plain == " validated "
    assert badge.style == ui.THEME.badge


def test_columns_render_items_and_title() -> None:
    console, stream = _make_console()

    ui.columns(["one", "two"], title="Columns", console=console)

    output = stream.getvalue()
    assert "Columns" in output
    assert "one" in output
    assert "two" in output


def test_tree_renders_nested_nodes() -> None:
    console, stream = _make_console()
    root = ui.TreeNode(
        label="root",
        children=(
            ui.TreeNode(
                label="child",
                children=(ui.TreeNode(label="leaf"),),
            ),
        ),
    )

    ui.tree(root, title="Tree", console=console)

    output = stream.getvalue()
    assert "Tree" in output
    assert "root" in output
    assert "child" in output
    assert "leaf" in output


def test_markdown_renders_content() -> None:
    console, stream = _make_console()

    ui.markdown("# Heading\n\nBody text", title="Docs", console=console)

    output = stream.getvalue()
    assert "Docs" in output
    assert "Heading" in output
    assert "Body text" in output


def test_syntax_renders_code_and_title() -> None:
    console, stream = _make_console()

    ui.syntax(
        "print('hello')",
        "python",
        title="example.py",
        line_numbers=True,
        console=console,
    )

    output = stream.getvalue()
    assert "example.py" in output
    assert "print" in output
    assert "hello" in output


def test_json_view_renders_data_and_title() -> None:
    console, stream = _make_console()

    ui.json_view(
        {"name": "omarchy", "enabled": True},
        title="JSON",
        console=console,
    )

    output = stream.getvalue()
    assert "JSON" in output
    assert "name" in output
    assert "omarchy" in output
    assert "enabled" in output


def test_panel_accepts_rich_text() -> None:
    console, stream = _make_console()

    ui.panel(ui.badge("validated"), title="Panel", console=console)

    assert "validated" in stream.getvalue()


def test_table_preserves_rich_text_cells() -> None:
    console, stream = _make_console()

    ui.table([[ui.badge("ok")]], headers=["Status"], console=console)

    assert "ok" in stream.getvalue()


def test_virtual_terminal_rejects_max_lines_below_height() -> None:
    with pytest.raises(ValidationError, match="max_lines"):
        ui.VirtualTerminal(height=5, max_lines=4)


def test_virtual_terminal_keeps_fixed_height_and_latest_lines() -> None:
    console, _ = _make_console(width=100)
    terminal = ui.VirtualTerminal(
        height=3,
        max_lines=10,
        show_line_numbers=True,
        console=console,
    )

    terminal.write("alpha\nbravo\ncharlie\ndelta\n")

    assert terminal.line_count == 4
    assert terminal.lines == ("alpha", "bravo", "charlie", "delta")
    assert terminal.visible_lines == ("bravo", "charlie", "delta")

    panel = terminal.render()
    assert isinstance(panel.renderable, Text)
    body_lines = panel.renderable.plain.splitlines()
    assert len(body_lines) == 3
    assert "alpha" not in panel.renderable.plain
    for value in ("bravo", "charlie", "delta"):
        assert value in panel.renderable.plain


def test_virtual_terminal_pads_to_fixed_height() -> None:
    console, _ = _make_console()
    terminal = ui.VirtualTerminal(height=4, console=console)

    terminal.writeline("only line")

    panel = terminal.render()
    assert isinstance(panel.renderable, Text)
    assert len(panel.renderable.plain.splitlines()) == 4
    assert panel.renderable.plain.endswith("only line")


def test_virtual_terminal_does_not_wrap_long_lines() -> None:
    console, stream = _make_console(width=40)
    terminal = ui.VirtualTerminal(height=2, console=console)

    terminal.writeline("x" * 200)
    console.print(terminal.render())

    assert len(stream.getvalue().splitlines()) == 4


def test_virtual_terminal_leaves_trailing_newline() -> None:
    console, stream = _make_console()

    with ui.virtual_terminal(height=2, console=console) as terminal:
        terminal.writeline("hello")

    assert stream.getvalue().endswith("\n")


def test_virtual_terminal_write_lines_accepts_newlines() -> None:
    console, _ = _make_console()
    terminal = ui.VirtualTerminal(height=5, console=console)

    terminal.write_lines(["alpha\n", "bravo\n", "charlie"])

    assert terminal.lines == ("alpha", "bravo", "charlie")


def test_virtual_terminal_collapses_carriage_return_updates() -> None:
    console, _ = _make_console()
    terminal = ui.VirtualTerminal(console=console)

    terminal.write("progress 10%\rprogress 20%\rprogress 30%\n")

    assert terminal.lines == ("progress 30%",)


def test_virtual_terminal_clear_resets_buffer() -> None:
    console, _ = _make_console()
    terminal = ui.VirtualTerminal(console=console)
    terminal.write("alpha\nbravo\n")

    terminal.clear(refresh=False)

    assert terminal.lines == ()
    assert terminal.visible_lines == ()
    assert terminal.line_count == 0


def test_virtual_terminal_writeline_accepts_rich_text() -> None:
    console, _ = _make_console()
    terminal = ui.VirtualTerminal(console=console)

    terminal.writeline(ui.badge("ok"))

    assert terminal.lines == (" ok ",)
    panel = terminal.render()
    assert isinstance(panel.renderable, Text)
    assert "ok" in panel.renderable.plain


def test_virtual_terminal_parses_ansi_colors() -> None:
    console, _ = _make_console()
    terminal = ui.VirtualTerminal(height=2, console=console)

    terminal.write("\x1b[31mred\x1b[0m plain\n")

    assert terminal.lines == ("red plain",)
    panel = terminal.render()
    assert isinstance(panel.renderable, Text)
    assert "\x1b" not in panel.renderable.plain


def test_virtual_terminal_context_manager_starts_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeLive:
        def __init__(self, renderable: object, **kwargs: object) -> None:
            self.renderable = renderable
            self.kwargs = kwargs
            self.started = False
            self.stopped = False
            self.updates: list[object] = []

        def start(self, refresh: bool = True) -> None:
            self.started = True
            self.start_refresh = refresh

        def update(self, renderable: object, *, refresh: bool = False) -> None:
            self.updates.append(renderable)

        def stop(self) -> None:
            self.stopped = True

    created: list[FakeLive] = []

    def fake_live(renderable: object, **kwargs: object) -> FakeLive:
        live = FakeLive(renderable, **kwargs)
        created.append(live)
        return live

    monkeypatch.setattr(ui, "Live", fake_live)
    console, _ = _make_console()
    terminal = ui.VirtualTerminal(height=3, console=console)

    assert not terminal.is_started
    with terminal:
        assert terminal.is_started
        assert created[0].start_refresh is False
        assert created[0].updates == []
        terminal.writeline("alpha")
        assert created[0].updates
    assert not terminal.is_started
    assert created[0].started is True
    assert created[0].stopped is True


def test_virtual_terminal_context_manager_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeLive:
        def __init__(self, renderable: object, **kwargs: object) -> None:
            self.renderable = renderable
            self.kwargs = kwargs

        def start(self, refresh: bool = True) -> None:
            return None

        def update(self, renderable: object, *, refresh: bool = False) -> None:
            return None

        def stop(self) -> None:
            return None

    monkeypatch.setattr(ui, "Live", FakeLive)
    console, _ = _make_console()

    with ui.virtual_terminal(height=4, title="Build", console=console) as terminal:
        assert isinstance(terminal, ui.VirtualTerminal)
        assert terminal.height == 4
        terminal.writeline("hello")

    assert terminal.lines == ("hello",)


def test_virtual_terminal_run_streams_output_and_echoes_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console, _ = _make_console()
    terminal = ui.VirtualTerminal(height=6, console=console)
    process = FakeProcess(["echo", "hello"], ["hello\n", "world\n"])
    calls: list[tuple[Sequence[str], dict[str, object]]] = []

    def fake_popen(command: Sequence[str], **kwargs: object) -> FakeProcess:
        calls.append((command, kwargs))
        return process

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    result = terminal.run(["echo", "hello"])

    assert result == 0
    assert terminal.lines[0] == "$ echo hello"
    assert "hello" in terminal.lines
    assert "world" in terminal.lines
    assert calls[0][0] == ["echo", "hello"]
    assert calls[0][1]["stdout"] == subprocess.PIPE
    assert calls[0][1]["stderr"] == subprocess.STDOUT
    assert process.stdout.closed is True


def test_virtual_terminal_run_accepts_string_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console, _ = _make_console()
    terminal = ui.VirtualTerminal(console=console)
    process = FakeProcess(["echo", "hello world"], [])
    calls: list[Sequence[str]] = []

    def fake_popen(command: Sequence[str], **kwargs: object) -> FakeProcess:
        calls.append(command)
        return process

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    terminal.run("echo 'hello world'")

    assert calls[0] == ["echo", "hello world"]


def test_virtual_terminal_run_rejects_empty_command() -> None:
    console, _ = _make_console()
    terminal = ui.VirtualTerminal(console=console)

    with pytest.raises(ValueError, match="non-empty command"):
        terminal.run("   ")


def test_virtual_terminal_run_raises_on_failed_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console, _ = _make_console()
    terminal = ui.VirtualTerminal(console=console)
    process = FakeProcess(["false"], [], returncode=1)

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        terminal.run(["false"], check=True)

    assert exc_info.value.returncode == 1
    assert "Process exited with code 1" in terminal.lines


def test_virtual_terminal_run_times_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console, _ = _make_console()
    terminal = ui.VirtualTerminal(console=console)
    process = BlockingProcess()

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)

    with pytest.raises(subprocess.TimeoutExpired):
        terminal.run(["sleep", "10"], timeout=0.01)

    assert process.terminated is True
    assert "Command timed out" in terminal.lines[-1]
