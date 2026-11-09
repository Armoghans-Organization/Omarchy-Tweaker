"""Structured file logging for Omarchy Tweaker.

Log files are written to the application's state directory by default::

    $XDG_STATE_HOME/omarchy_tweaker/logs/omarchy_tweaker_<timestamp>.log

If ``XDG_STATE_HOME`` is unset, ``~/.local/state`` is used. The directory can
be overridden with the ``OMARCHY_TWEAKER_LOG_DIR`` environment variable, which
is useful during development and testing.

Each session writes a startup header, structured log records, and a shutdown
report containing per-level message statistics.
"""

from __future__ import annotations

import logging
import os
import platform
import socket
import sys
import textwrap
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from types import TracebackType
from typing import Any, Final

from omarchy_tweaker.app_metadata import APP_NAME, APP_SLUG, APP_VERSION

LOG_DATE_FORMAT: Final = "%Y-%m-%d %H:%M:%S %Z"
LOG_FILE_DATE_FORMAT: Final = "%Y-%m-%d_%H-%M-%S"
LOG_FORMAT: Final = "%(asctime)s | %(levelname)-8s | %(message)s"

LOG_DIR_ENV_VAR: Final = "OMARCHY_TWEAKER_LOG_DIR"
LOGGER_NAME: Final = "omarchy_tweaker"

LOG_LEVELS: Final[dict[str, int]] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

DEFAULT_LOG_LEVEL: Final = logging.INFO

HEADER_WIDTH: Final = 100
FIELD_LABEL_WIDTH: Final = 21
SESSION_ID_LENGTH: Final = 12


def resolve_log_level(level: int | str) -> int:
    """Resolve a log level name or numeric value to a logging level.

    Args:
        level: Numeric logging level or a case-insensitive level name.

    Returns:
        The numeric logging level.

    Raises:
        ValueError: If a string level name is not recognised.
    """
    if isinstance(level, int):
        return level

    try:
        return LOG_LEVELS[level.upper()]
    except KeyError as exc:
        supported = ", ".join(LOG_LEVELS)
        raise ValueError(
            f"Unsupported log level {level!r}. Supported levels: {supported}."
        ) from exc


def get_log_directory() -> Path:
    """Return the directory used to store log files.

    Returns:
        The configured log directory. ``OMARCHY_TWEAKER_LOG_DIR`` takes
        precedence, followed by ``XDG_STATE_HOME`` and then
        ``~/.local/state``.
    """
    override = os.environ.get(LOG_DIR_ENV_VAR)
    if override:
        return Path(override).expanduser()

    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
    return base / APP_SLUG / "logs"


class LogStatistics(logging.Filter):
    """Count log records by level for the duration of a session."""

    def __init__(self) -> None:
        super().__init__()
        self.counts: dict[str, int] = dict.fromkeys(LOG_LEVELS, 0)

    def filter(self, record: logging.LogRecord) -> bool:
        """Count the record and allow it to pass through."""
        if record.levelname in self.counts:
            self.counts[record.levelname] += 1
        return True


class OmarchyTweakerLogger:
    """File logger that writes a session header, records, and a report."""

    def __init__(
        self,
        log_level: int | str = DEFAULT_LOG_LEVEL,
        log_directory: Path | None = None,
    ) -> None:
        """Create a logger for a new application session.

        Args:
            log_level: Numeric logging level or level name. Defaults to INFO.
            log_directory: Directory for log files. Defaults to
                :func:`get_log_directory`.
        """
        resolved_level = resolve_log_level(log_level)

        self.start_time = datetime.now().astimezone()
        self.start_timestamp = self.start_time.strftime(LOG_FILE_DATE_FORMAT)
        self.session_id = uuid.uuid4().hex[:SESSION_ID_LENGTH].upper()

        self.log_directory = (log_directory or get_log_directory()).expanduser()
        self.log_file = self.log_directory / f"{APP_SLUG}_{self.start_timestamp}.log"

        self.statistics = LogStatistics()
        self.closed = False

        self.logger = logging.getLogger(LOGGER_NAME)
        self.logger.setLevel(resolved_level)
        self.logger.propagate = False

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            handler.close()

        self.log_directory.mkdir(parents=True, exist_ok=True)

        self.file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        self.file_handler.setLevel(resolved_level)
        self.file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))

        self.logger.addHandler(self.file_handler)
        self.logger.addFilter(self.statistics)

        self._write_block(self._generate_header())
        self.info("Application startup initiated.")

    def __enter__(self) -> OmarchyTweakerLogger:
        """Return the logger for use as a context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Shut the session down, marking it failed if an error occurred."""
        self.shutdown("SUCCESS" if exc_type is None else "FAILED")

    # ===================================================================
    # FORMATTING HELPERS
    # ===================================================================

    @staticmethod
    def _separator(char: str = "=", width: int = HEADER_WIDTH) -> str:
        """Return a horizontal separator line."""
        return char * width

    @staticmethod
    def _center(text: str, width: int = HEADER_WIDTH) -> str:
        """Center text within the header width."""
        return text.center(width)

    @staticmethod
    def _field(label: str, value: object) -> str:
        """Format a metadata field with consistent alignment and wrapping."""
        value_width = HEADER_WIDTH - FIELD_LABEL_WIDTH - 6
        wrapped = textwrap.wrap(
            str(value),
            width=value_width,
            break_long_words=True,
            break_on_hyphens=False,
        ) or [""]

        lines = [f"  {label:<{FIELD_LABEL_WIDTH}} : {wrapped[0]}"]
        lines.extend(f"  {'':<{FIELD_LABEL_WIDTH}}   {line}" for line in wrapped[1:])

        return "\n".join(lines)

    @staticmethod
    def _format_runtime(seconds: float) -> str:
        """Format a runtime duration into a readable string."""
        return str(timedelta(seconds=round(seconds, 3)))

    def _write_block(self, content: str) -> None:
        """Write a formatted block without log-level prefixes."""
        stream = self.file_handler.stream
        if stream is None:
            raise RuntimeError("Cannot write to a closed log file stream.")

        stream.write(content.rstrip() + "\n\n")
        stream.flush()

    # ===================================================================
    # HEADER
    # ===================================================================

    def _generate_header(self) -> str:
        """Generate the application startup banner."""
        entry_file = Path(sys.argv[0]).resolve()

        logo = [
            "██╗      ██████╗  ██████╗  ██████╗ ██╗███╗   ██╗ ██████╗",
            "██║     ██╔═══██╗██╔════╝ ██╔════╝ ██║████╗  ██║██╔════╝",
            "██║     ██║   ██║██║  ███╗██║  ███╗██║██╔██╗ ██║██║  ███╗",
            "██║     ██║   ██║██║   ██║██║   ██║██║██║╚██╗██║██║   ██║",
            "███████╗╚██████╔╝╚██████╔╝╚██████╔╝██║██║ ╚████║╚██████╔╝",
            "╚══════╝ ╚═════╝  ╚═════╝  ╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝",
        ]

        lines = [
            self._separator(),
            "",
            *[self._center(line) for line in logo],
            "",
            self._separator(),
            "",
            self._center(f"{APP_NAME.upper()} | APPLICATION LOGGER"),
            self._center(f"VERSION {APP_VERSION}"),
            "",
            self._separator("-"),
            "",
            "  APPLICATION",
            self._separator("-"),
            self._field("Application", APP_NAME),
            self._field("Version", APP_VERSION),
            self._field("Session ID", self.session_id),
            self._field("Process ID", os.getpid()),
            self._field("Process Parent ID", os.getppid()),
            "",
            "  EXECUTION",
            self._separator("-"),
            self._field("Started At", self.start_time.strftime(LOG_DATE_FORMAT)),
            self._field("Entry Point", entry_file.name),
            self._field("Entry Path", entry_file),
            self._field("Working Directory", Path.cwd()),
            self._field("Command Arguments", " ".join(sys.argv[1:]) or "None"),
            "",
            "  SYSTEM",
            self._separator("-"),
            self._field(
                "Operating System",
                f"{platform.system()} {platform.release()}",
            ),
            self._field("Distribution", platform.platform()),
            self._field("Architecture", platform.machine()),
            self._field("Python Version", platform.python_version()),
            self._field("Python Executable", sys.executable),
            self._field("Hostname", socket.gethostname()),
            self._field("CPU Count", os.cpu_count() or "Unknown"),
            "",
            "  LOGGING",
            self._separator("-"),
            self._field("Log Level", logging.getLevelName(self.logger.level)),
            self._field("Log File", self.log_file),
            self._field("Log Directory", self.log_directory),
            self._field("Encoding", "UTF-8"),
            self._field("Session Status", "INITIALIZING"),
            "",
            self._separator(),
            "",
            self._center("STARTUP SEQUENCE"),
            "",
            "  [  OK  ] Runtime environment detected",
            "  [  OK  ] Application configuration loaded",
            "  [  OK  ] Logging system initialized",
            "  [  OK  ] Session created",
            "",
            self._separator(),
        ]

        return "\n".join(lines)

    # ===================================================================
    # LOGGING METHODS
    # ===================================================================

    def debug(self, message: str, *args: object, **kwargs: Any) -> None:
        """Log a debug message."""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args: object, **kwargs: Any) -> None:
        """Log an informational message."""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args: object, **kwargs: Any) -> None:
        """Log a warning message."""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args: object, **kwargs: Any) -> None:
        """Log an error message."""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args: object, **kwargs: Any) -> None:
        """Log a critical message."""
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args: object, **kwargs: Any) -> None:
        """Log an exception with traceback information."""
        self.logger.exception(message, *args, **kwargs)

    # ===================================================================
    # FOOTER
    # ===================================================================

    def _generate_footer(self, status: str = "SUCCESS") -> str:
        """Generate the application shutdown report."""
        end_time = datetime.now().astimezone()
        runtime_seconds = (end_time - self.start_time).total_seconds()
        total = sum(self.statistics.counts.values())
        status = status.upper()

        if status == "SUCCESS":
            status_label = "[  SUCCESS  ]"
        elif status in {"FAILED", "ERROR"}:
            status_label = "[   FAILED  ]"
        elif status in {"INTERRUPTED", "CANCELLED"}:
            status_label = "[INTERRUPTED]"
        else:
            status_label = f"[ {status[:12]:^10} ]"

        lines = [
            "",
            self._separator(),
            "",
            self._center("APPLICATION SHUTDOWN REPORT"),
            "",
            self._separator("-"),
            "",
            "  SESSION INFORMATION",
            self._separator("-"),
            self._field("Session ID", self.session_id),
            self._field("Session Status", status_label),
            self._field("Exit Timestamp", end_time.strftime(LOG_DATE_FORMAT)),
            self._field("Start Timestamp", self.start_time.strftime(LOG_DATE_FORMAT)),
            self._field("Total Runtime", self._format_runtime(runtime_seconds)),
            "",
            "  LOGGING STATISTICS",
            self._separator("-"),
            self._field("Total Log Messages", total),
            self._field("DEBUG Messages", self.statistics.counts["DEBUG"]),
            self._field("INFO Messages", self.statistics.counts["INFO"]),
            self._field("WARNING Messages", self.statistics.counts["WARNING"]),
            self._field("ERROR Messages", self.statistics.counts["ERROR"]),
            self._field("CRITICAL Messages", self.statistics.counts["CRITICAL"]),
            "",
            self._separator("-"),
            "",
            self._center(
                "SESSION COMPLETED SUCCESSFULLY" if status == "SUCCESS" else "SESSION TERMINATED"
            ),
            self._center(f"{APP_NAME.upper()} | SESSION {self.session_id}"),
            "",
            self._separator(),
        ]

        return "\n".join(lines)

    # ===================================================================
    # SHUTDOWN
    # ===================================================================

    def shutdown(self, status: str = "SUCCESS") -> None:
        """Write the shutdown report and release logging resources.

        Calling this method more than once has no effect.

        Args:
            status: Final session status, such as ``"SUCCESS"`` or ``"FAILED"``.
        """
        if self.closed:
            return

        self.info("Application shutdown initiated.")
        self._write_block(self._generate_footer(status))

        self.closed = True

        self.logger.removeFilter(self.statistics)
        self.logger.removeHandler(self.file_handler)
        self.file_handler.close()
