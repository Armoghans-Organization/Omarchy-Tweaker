from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from omarchy_tweaker.app_metadata import APP_NAME, APP_SLUG, APP_VERSION
from omarchy_tweaker.functions.logger import (
    LOG_DIR_ENV_VAR,
    OmarchyTweakerLogger,
    get_log_directory,
    resolve_log_level,
)


@pytest.fixture
def session(tmp_path: Path) -> Iterator[OmarchyTweakerLogger]:
    instance = OmarchyTweakerLogger(log_directory=tmp_path)
    try:
        yield instance
    finally:
        instance.shutdown()


def test_creates_log_file(session: OmarchyTweakerLogger) -> None:
    assert session.log_file.exists()
    assert session.log_file.parent == session.log_directory
    assert session.log_file.name.startswith(f"{APP_SLUG}_")
    assert session.log_file.suffix == ".log"


def test_header_contains_application_metadata(
    session: OmarchyTweakerLogger,
) -> None:
    session.shutdown()

    content = session.log_file.read_text(encoding="utf-8")

    assert APP_NAME in content
    assert APP_VERSION in content
    assert session.session_id in content
    assert "APPLICATION LOGGER" in content
    assert "STARTUP SEQUENCE" in content


def test_writes_messages_at_each_level(session: OmarchyTweakerLogger) -> None:
    baseline = dict(session.statistics.counts)

    session.debug("debug message")
    session.info("info message")
    session.warning("warning message")
    session.error("error message")
    session.critical("critical message")

    assert session.statistics.counts == {
        "DEBUG": baseline["DEBUG"],
        "INFO": baseline["INFO"] + 1,
        "WARNING": baseline["WARNING"] + 1,
        "ERROR": baseline["ERROR"] + 1,
        "CRITICAL": baseline["CRITICAL"] + 1,
    }

    session.shutdown()

    content = session.log_file.read_text(encoding="utf-8")

    assert "debug message" not in content
    assert "info message" in content
    assert "warning message" in content
    assert "error message" in content
    assert "critical message" in content


def test_debug_messages_written_when_enabled(tmp_path: Path) -> None:
    instance = OmarchyTweakerLogger(log_level="DEBUG", log_directory=tmp_path)
    try:
        instance.debug("debug visible")
    finally:
        instance.shutdown()

    content = instance.log_file.read_text(encoding="utf-8")

    assert "debug visible" in content


def test_messages_below_level_are_ignored(tmp_path: Path) -> None:
    instance = OmarchyTweakerLogger(
        log_level=logging.ERROR,
        log_directory=tmp_path,
    )
    try:
        instance.info("hidden message")
        instance.error("visible message")
    finally:
        instance.shutdown()

    content = instance.log_file.read_text(encoding="utf-8")

    assert "hidden message" not in content
    assert "visible message" in content


def test_shutdown_writes_report_and_closes_handlers(
    session: OmarchyTweakerLogger,
) -> None:
    session.info("before shutdown")
    session.shutdown()

    content = session.log_file.read_text(encoding="utf-8")

    assert "APPLICATION SHUTDOWN REPORT" in content
    assert "SESSION COMPLETED SUCCESSFULLY" in content
    assert session.closed is True
    assert session.file_handler not in session.logger.handlers
    assert session.file_handler.stream is None


def test_shutdown_is_idempotent(session: OmarchyTweakerLogger) -> None:
    session.shutdown()
    first_content = session.log_file.read_text(encoding="utf-8")

    session.shutdown()

    assert session.log_file.read_text(encoding="utf-8") == first_content


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("SUCCESS", "SESSION COMPLETED SUCCESSFULLY"),
        ("FAILED", "SESSION TERMINATED"),
        ("ERROR", "[   FAILED  ]"),
        ("INTERRUPTED", "[INTERRUPTED]"),
        ("CANCELLED", "[INTERRUPTED]"),
        ("PAUSED", "[   PAUSED   ]"),
    ],
)
def test_shutdown_status(
    tmp_path: Path,
    status: str,
    expected: str,
) -> None:
    instance = OmarchyTweakerLogger(log_directory=tmp_path)
    instance.shutdown(status)

    content = instance.log_file.read_text(encoding="utf-8")

    assert expected in content


def test_context_manager_shuts_down_on_success(tmp_path: Path) -> None:
    with OmarchyTweakerLogger(log_directory=tmp_path) as instance:
        instance.info("inside context")

    content = instance.log_file.read_text(encoding="utf-8")

    assert "inside context" in content
    assert "SESSION COMPLETED SUCCESSFULLY" in content
    assert instance.closed is True


def test_context_manager_marks_failure_on_exception(tmp_path: Path) -> None:
    with (
        pytest.raises(RuntimeError, match="boom"),
        OmarchyTweakerLogger(log_directory=tmp_path) as instance,
    ):
        raise RuntimeError("boom")

    content = instance.log_file.read_text(encoding="utf-8")

    assert "[   FAILED  ]" in content
    assert instance.closed is True


def test_exception_logs_traceback(tmp_path: Path) -> None:
    instance = OmarchyTweakerLogger(log_directory=tmp_path)
    try:
        try:
            raise ValueError("bad value")
        except ValueError:
            instance.exception("caught error")
    finally:
        instance.shutdown()

    content = instance.log_file.read_text(encoding="utf-8")

    assert "caught error" in content
    assert "Traceback (most recent call last)" in content
    assert "ValueError: bad value" in content


def test_get_log_directory_uses_env_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "custom-logs"
    monkeypatch.setenv(LOG_DIR_ENV_VAR, str(target))

    assert get_log_directory() == target


def test_get_log_directory_uses_xdg_state_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(LOG_DIR_ENV_VAR, raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    assert get_log_directory() == tmp_path / "state" / APP_SLUG / "logs"


def test_get_log_directory_falls_back_to_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_home() -> Path:
        return tmp_path

    monkeypatch.delenv(LOG_DIR_ENV_VAR, raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setattr(Path, "home", staticmethod(fake_home))

    assert get_log_directory() == tmp_path / ".local" / "state" / APP_SLUG / "logs"


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        ("info", logging.INFO),
        ("WARNING", logging.WARNING),
        (logging.ERROR, logging.ERROR),
    ],
)
def test_resolve_log_level(level: int | str, expected: int) -> None:
    assert resolve_log_level(level) == expected


def test_resolve_log_level_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unsupported log level"):
        resolve_log_level("TRACE")
