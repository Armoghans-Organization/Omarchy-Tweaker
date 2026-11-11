"""Remove installed preinstalled Omarchy applications and wrappers."""

from __future__ import annotations

import os
import re
import shutil

# Required to execute argument-list commands without invoking a shell.
import subprocess  # nosec B404
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

from rich.progress import Progress, TaskID

from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.logger import get_session

CLEANUP_TIMEOUT_SECONDS: Final = 600.0
LAUNCHER_TIMEOUT_SECONDS: Final = 60.0
PACKAGE_QUERY_TIMEOUT_SECONDS: Final = 30.0
MAX_WRAPPER_BYTES: Final = 128_000
OMARCHY_COMMAND: Final = "omarchy"

# Keep this list aligned with the removable applications in Omarchy's
# omarchy-remove-preinstalls script. Only packages that are actually installed
# are shown to the user.
OMARCHY_PREINSTALLED_PACKAGES: Final = (
    "aether",
    "cliamp",
    "kdenlive",
    "lazydocker",
    "libreoffice-fresh",
    "moonlight-qt",
    "obs-studio",
    "obsidian",
    "omacalc",
    "omacut",
    "omawrite",
    "pinta",
    "xournalpp",
)

WEBAPP_EXEC_PATTERN: Final = re.compile(
    r"^Exec=.*(?:omarchy-launch-webapp|omarchy-webapp-handler)",
    re.MULTILINE,
)
TUI_EXEC_PATTERN: Final = re.compile(
    r"^Exec=.*(?:\$TERMINAL|xdg-terminal-exec).*-e",
    re.MULTILINE,
)
MISE_WRAPPER_PATTERN: Final = re.compile(r"^\s*mise use -g\b", re.MULTILINE)


class CleanupCategory(StrEnum):
    """Category of a removable cleanup item."""

    PACKAGE = "Package"
    TUI = "TUI"
    WEBAPP = "Webapp"
    MISE = "Mise"


class CleanupResult(StrEnum):
    """Outcome of the cleanup step."""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class CleanupItem:
    """A single selectable cleanup target."""

    category: CleanupCategory
    name: str
    target: str

    @property
    def label(self) -> str:
        """Return the label used in logs and summaries."""
        return f"[{self.category.value}] {self.name}"


@dataclass(frozen=True)
class CleanupReport:
    """Result of removing a set of selected cleanup items."""

    removed: tuple[CleanupItem, ...] = ()
    failed: tuple[CleanupItem, ...] = ()


CATEGORY_DISPLAY: Final[dict[CleanupCategory, tuple[str, str, str]]] = {
    CleanupCategory.PACKAGE: ("Packages", "package", "packages"),
    CleanupCategory.WEBAPP: ("Web Apps", "web app", "web apps"),
    CleanupCategory.TUI: ("TUIs", "TUI", "TUIs"),
    CleanupCategory.MISE: ("Mise Wrappers", "Mise wrapper", "Mise wrappers"),
}


def get_applications_directory() -> Path:
    """Return the user's desktop application directory."""
    return Path.home() / ".local" / "share" / "applications"


def get_bin_directory() -> Path:
    """Return the user's local binary directory."""
    return Path.home() / ".local" / "bin"


def get_installed_packages() -> frozenset[str]:
    """Return the names of packages installed through pacman."""
    pacman = shutil.which("pacman")
    if pacman is None:
        _log_error("Could not query installed packages: pacman was not found.")
        return frozenset()

    try:
        result = subprocess.run(  # nosec B603
            [pacman, "-Qq"],
            check=False,
            text=True,
            capture_output=True,
            timeout=PACKAGE_QUERY_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        _log_error("Could not query installed packages: pacman was not found.")
        return frozenset()
    except subprocess.TimeoutExpired:
        _log_error("Installed package query timed out.")
        return frozenset()
    except OSError as exc:
        _log_error("Could not query installed packages: %s", exc)
        return frozenset()

    if result.returncode != 0:
        _log_error("Installed package query exited with status %s.", result.returncode)
        return frozenset()

    return frozenset(line.strip() for line in result.stdout.splitlines() if line.strip())


def _desktop_names(directory: Path, pattern: re.Pattern[str]) -> tuple[str, ...]:
    """Return desktop launcher names whose ``Exec`` line matches ``pattern``."""
    if not directory.is_dir():
        return ()

    names: list[str] = []
    for desktop_file in sorted(directory.glob("*.desktop")):
        try:
            content = desktop_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if pattern.search(content):
            names.append(desktop_file.stem)

    return tuple(dict.fromkeys(names))


def discover_tuis(directory: Path | None = None) -> tuple[str, ...]:
    """Discover installed TUI desktop launchers."""
    return _desktop_names(directory or get_applications_directory(), TUI_EXEC_PATTERN)


def discover_webapps(directory: Path | None = None) -> tuple[str, ...]:
    """Discover installed web app desktop launchers."""
    return _desktop_names(directory or get_applications_directory(), WEBAPP_EXEC_PATTERN)


def discover_mise_wrappers(directory: Path | None = None) -> tuple[Path, ...]:
    """Discover installed Mise wrapper files in the user's local binary directory."""
    bin_dir = directory or get_bin_directory()
    if not bin_dir.is_dir():
        return ()

    wrappers: list[Path] = []
    for path in sorted(bin_dir.iterdir()):
        if not path.is_file() or path.is_symlink():
            continue

        try:
            if path.stat().st_size > MAX_WRAPPER_BYTES:
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if MISE_WRAPPER_PATTERN.search(content):
            wrappers.append(path)

    return tuple(wrappers)


def available_cleanup_items(
    *,
    applications_dir: Path | None = None,
    bin_dir: Path | None = None,
    installed_packages: Iterable[str] | None = None,
) -> tuple[CleanupItem, ...]:
    """Return cleanup candidates that are currently installed.

    Args:
        applications_dir: Optional desktop application directory override.
        bin_dir: Optional local binary directory override.
        installed_packages: Optional installed package names override.

    Returns:
        Installed packages, web apps, TUIs, and Mise wrappers in display order.
    """
    installed = (
        frozenset(installed_packages)
        if installed_packages is not None
        else get_installed_packages()
    )
    applications = applications_dir or get_applications_directory()
    binaries = bin_dir or get_bin_directory()

    packages = tuple(package for package in OMARCHY_PREINSTALLED_PACKAGES if package in installed)
    tuis = discover_tuis(applications)
    webapps = discover_webapps(applications)
    mise_wrappers = discover_mise_wrappers(binaries)

    items: list[CleanupItem] = []
    items.extend(CleanupItem(CleanupCategory.PACKAGE, name, name) for name in packages)
    items.extend(CleanupItem(CleanupCategory.WEBAPP, name, name) for name in webapps)
    items.extend(CleanupItem(CleanupCategory.TUI, name, name) for name in tuis)
    items.extend(CleanupItem(CleanupCategory.MISE, path.name, str(path)) for path in mise_wrappers)

    return tuple(items)


def _removal_environment() -> dict[str, str]:
    """Return an environment that suppresses Omarchy removal notifications."""
    environment = os.environ.copy()
    environment["OMARCHY_REMOVE_NOTIFY"] = "false"
    return environment


def _run_omarchy(
    arguments: Sequence[str],
    *,
    capture_output: bool,
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    """Run an Omarchy command without a shell."""
    return subprocess.run(  # nosec B603
        [OMARCHY_COMMAND, *arguments],
        check=False,
        text=True,
        capture_output=capture_output,
        timeout=timeout,
        env=_removal_environment(),
    )


def _log_error(message: str, *args: object) -> None:
    logger = get_session()
    if logger is not None:
        logger.error(message, *args)


def _log_info(message: str, *args: object) -> None:
    logger = get_session()
    if logger is not None:
        logger.info(message, *args)


def _remove_packages(
    packages: Sequence[str],
    *,
    terminal: ui.VirtualTerminal | None = None,
) -> bool:
    """Remove package names with ``omarchy pkg drop``."""
    if not packages:
        return True

    command = [OMARCHY_COMMAND, "pkg", "drop", *packages]
    _log_info("Removing packages: %s", ", ".join(packages))

    if terminal is not None:
        terminal.writeline(
            f"Removing {len(packages)} package(s)...",
            style=ui.THEME.info,
        )
        try:
            returncode = terminal.run(
                command,
                timeout=CLEANUP_TIMEOUT_SECONDS,
                env=_removal_environment(),
            )
        except FileNotFoundError:
            _log_error("Package removal failed: the omarchy command was not found.")
            terminal.writeline(
                "The omarchy command was not found on PATH.",
                style=ui.THEME.error,
            )
            return False
        except subprocess.TimeoutExpired:
            _log_error("Package removal timed out after %s seconds.", CLEANUP_TIMEOUT_SECONDS)
            return False
        except OSError as exc:
            _log_error("Could not start package removal: %s", exc)
            terminal.writeline(
                f"Could not start package removal: {exc}",
                style=ui.THEME.error,
            )
            return False

        if returncode != 0:
            _log_error("Package removal exited with status %s.", returncode)
            return False

        return True

    try:
        result = _run_omarchy(
            ["pkg", "drop", *packages],
            capture_output=False,
            timeout=CLEANUP_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        _log_error("Package removal failed: the omarchy command was not found.")
        ui.error("The omarchy command was not found on PATH.")
        return False
    except subprocess.TimeoutExpired:
        _log_error("Package removal timed out after %s seconds.", CLEANUP_TIMEOUT_SECONDS)
        ui.error("Package removal timed out.")
        return False
    except OSError as exc:
        _log_error("Could not start package removal: %s", exc)
        ui.error(f"Could not start package removal: {exc}")
        return False

    if result.returncode != 0:
        _log_error("Package removal exited with status %s.", result.returncode)
        ui.error(f"Package removal failed with exit code {result.returncode}.")
        return False

    return True


def _remove_launcher(item: CleanupItem) -> bool:
    """Remove a selected TUI or web app launcher."""
    command = (
        ["webapp", "remove", item.target]
        if item.category is CleanupCategory.WEBAPP
        else ["tui", "remove", item.target]
    )

    try:
        result = _run_omarchy(
            command,
            capture_output=True,
            timeout=LAUNCHER_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        _log_error("%s removal failed: the omarchy command was not found.", item.name)
        ui.error("The omarchy command was not found on PATH.")
        return False
    except subprocess.TimeoutExpired:
        _log_error("%s removal timed out.", item.name)
        ui.error(f"{item.label} removal timed out.")
        return False
    except OSError as exc:
        _log_error("Could not start %s removal: %s", item.name, exc)
        ui.error(f"Could not start {item.label} removal: {exc}")
        return False

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        _log_error("%s removal exited with status %s: %s", item.name, result.returncode, detail)
        ui.error(f"{item.label} removal failed with exit code {result.returncode}.")
        return False

    return True


def _remove_mise_wrapper(item: CleanupItem) -> bool:
    """Remove a selected Mise wrapper file."""
    path = Path(item.target).expanduser()
    try:
        if not path.is_absolute():
            raise ValueError("wrapper path must be absolute")
        if path.name in {"", ".", ".."}:
            raise ValueError("wrapper path must name a file")
        try:
            path.parent.resolve().relative_to(Path.home().resolve())
        except ValueError as exc:
            raise ValueError("wrapper path must stay inside the home directory") from exc
        path.unlink(missing_ok=True)
    except (OSError, ValueError) as exc:
        _log_error("Could not remove Mise wrapper %s: %s", item.name, exc)
        ui.error(f"Could not remove {item.label}: {exc}")
        return False

    return True


def _progress_task(progress: Progress | None, item: CleanupItem) -> TaskID | None:
    """Add a progress task for a single cleanup item."""
    if progress is None:
        return None
    return progress.add_task(f"Removing {item.label}", total=1)


def _finish_progress_task(
    progress: Progress | None,
    task_id: TaskID | None,
    item: CleanupItem,
    *,
    succeeded: bool,
) -> None:
    """Update and advance a cleanup item's progress task."""
    if progress is None or task_id is None:
        return

    status = "Removed" if succeeded else "Failed"
    progress.update(task_id, description=f"{status} {item.label}")
    progress.advance(task_id)


def remove_selected_items(
    items: Sequence[CleanupItem],
    *,
    terminal: ui.VirtualTerminal | None = None,
    progress: Progress | None = None,
) -> CleanupReport:
    """Remove only the supplied cleanup items.

    Packages are removed together with one Omarchy package command. TUI and web
    app launchers are removed individually. Mise entries are unlinked from their
    wrapper paths.
    """
    removed: list[CleanupItem] = []
    failed: list[CleanupItem] = []

    packages = [item for item in items if item.category is CleanupCategory.PACKAGE]
    if packages:
        if _remove_packages([item.target for item in packages], terminal=terminal):
            removed.extend(packages)
        else:
            failed.extend(packages)

    for item in items:
        if item.category not in {CleanupCategory.TUI, CleanupCategory.WEBAPP, CleanupCategory.MISE}:
            continue

        task_id = _progress_task(progress, item)
        if item.category is CleanupCategory.MISE:
            succeeded = _remove_mise_wrapper(item)
        else:
            succeeded = _remove_launcher(item)

        if succeeded:
            removed.append(item)
        else:
            failed.append(item)
        _finish_progress_task(progress, task_id, item, succeeded=succeeded)

    return CleanupReport(removed=tuple(removed), failed=tuple(failed))


def _merge_reports(*reports: CleanupReport) -> CleanupReport:
    """Combine cleanup reports into one."""
    return CleanupReport(
        removed=tuple(item for report in reports for item in report.removed),
        failed=tuple(item for report in reports for item in report.failed),
    )


def _select_category(
    category: CleanupCategory,
    items: Sequence[CleanupItem],
) -> list[CleanupItem]:
    """Show one category and return the items selected from it."""
    title, singular, plural = CATEGORY_DISPLAY[category]

    if not items:
        ui.info(f"No installed {plural} found.")
        return []

    ui.rule(f"Installed {title}")
    if category is CleanupCategory.MISE:
        ui.table(
            ((item.name, item.target) for item in items),
            headers=("Wrapper", "Path"),
        )
    else:
        ui.table((item.name,) for item in items)

    selected_names = ui.checkbox(
        f"Select {plural} to remove:",
        [item.name for item in items],
        instruction=(
            f"Space selects, Enter confirms. Leave all unselected to keep every {singular}."
        ),
    )
    selected_set = set(selected_names)
    return [item for item in items if item.name in selected_set]


def run_cleanup_step(
    *,
    applications_dir: Path | None = None,
    bin_dir: Path | None = None,
    installed_packages: Iterable[str] | None = None,
) -> CleanupResult:
    """Run the interactive cleanup step.

    Args:
        applications_dir: Optional desktop application directory override.
        bin_dir: Optional local binary directory override.
        installed_packages: Optional installed package names override.

    Returns:
        The outcome of the cleanup step.
    """
    logger = get_session()
    if logger is not None:
        logger.info("Cleanup step started.")

    ui.section(
        "Cleanup",
        subtitle="Remove installed Omarchy packages, web apps, TUIs, and Mise wrappers.",
        icon=ui.ICONS.package,
    )

    items = available_cleanup_items(
        applications_dir=applications_dir,
        bin_dir=bin_dir,
        installed_packages=installed_packages,
    )

    if not items:
        if logger is not None:
            logger.info("Cleanup step skipped: no installed cleanup items were found.")
        ui.info("No installed cleanup items were found.")
        return CleanupResult.SKIPPED

    if not ui.is_interactive():
        if logger is not None:
            logger.info("Cleanup step skipped: no interactive terminal.")
        ui.warning("Cleanup skipped: selecting items requires an interactive terminal.")
        return CleanupResult.SKIPPED

    grouped = {
        category: tuple(item for item in items if item.category is category)
        for category in CleanupCategory
    }

    selected: list[CleanupItem] = []
    for category in (
        CleanupCategory.PACKAGE,
        CleanupCategory.WEBAPP,
        CleanupCategory.TUI,
        CleanupCategory.MISE,
    ):
        selected.extend(_select_category(category, grouped[category]))

    if not selected:
        if logger is not None:
            logger.info("Cleanup step skipped: no items were selected.")
        ui.info("No items selected. Nothing was removed.")
        return CleanupResult.SKIPPED

    if logger is not None:
        logger.info("Cleanup selected items: %s", ", ".join(item.label for item in selected))

    ui.table(
        ((item.category.value, item.name) for item in selected),
        headers=("Type", "Item"),
        title="Selected for removal",
    )

    if any(item.category is CleanupCategory.PACKAGE for item in selected):
        ui.warning("Package removal uses sudo and may ask for your password.")

    if not ui.confirm(
        f"Remove {len(selected)} selected item(s)?",
        default=False,
        instruction="This cannot be undone. Make sure you have a current snapshot.",
    ):
        if logger is not None:
            logger.info("Cleanup cancelled by the user.")
        ui.info("Cleanup cancelled. Nothing was removed.")
        return CleanupResult.SKIPPED

    report = CleanupReport()
    package_items = [item for item in selected if item.category is CleanupCategory.PACKAGE]
    other_items = [item for item in selected if item.category is not CleanupCategory.PACKAGE]

    if package_items:
        with ui.virtual_terminal(
            height=12,
            max_lines=200,
            title="Package Removal",
        ) as terminal:
            report = _merge_reports(
                report,
                remove_selected_items(package_items, terminal=terminal),
            )

    if other_items:
        with ui.progress_bar() as progress:
            report = _merge_reports(
                report,
                remove_selected_items(other_items, progress=progress),
            )

    if report.failed:
        if logger is not None:
            logger.error(
                "Cleanup failed for %d item(s): %s",
                len(report.failed),
                ", ".join(item.label for item in report.failed),
            )
        ui.error(f"Cleanup failed for {len(report.failed)} item(s).")
        return CleanupResult.FAILED

    if logger is not None:
        logger.info("Cleanup completed: removed %d item(s).", len(report.removed))
    ui.success(f"Cleanup completed. Removed {len(report.removed)} item(s).")
    return CleanupResult.COMPLETED
