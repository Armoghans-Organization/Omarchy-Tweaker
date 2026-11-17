"""Link bundled Omarchy helper scripts into the user's PATH."""

from __future__ import annotations

import os
import stat
from enum import StrEnum
from pathlib import Path
from typing import Final

from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.logger import get_session

SCRIPT_DIRECTORY_ENV_VAR: Final = "OMARCHY_TWEAKER_SCRIPTS_DIR"
EXECUTE_BITS: Final = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH


class ScriptResult(StrEnum):
    """Outcome of the bundled script linking step."""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


def _log_error(message: str, *args: object) -> None:
    logger = get_session()
    if logger is not None:
        logger.error(message, *args)


def _log_info(message: str, *args: object) -> None:
    logger = get_session()
    if logger is not None:
        logger.info(message, *args)


def _log_warning(message: str, *args: object) -> None:
    logger = get_session()
    if logger is not None:
        logger.warning(message, *args)


def get_script_source_directory() -> Path:
    """Return the directory containing the bundled helper scripts.

    ``OMARCHY_TWEAKER_SCRIPTS_DIR`` takes precedence. When it is unset, the
    ``script`` directory bundled next to the package modules is used.
    """
    override = os.environ.get(SCRIPT_DIRECTORY_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[1] / "script"


def get_bin_directory(home: Path | None = None) -> Path:
    """Return the per-user binary directory beneath the selected home directory.

    Args:
        home: Optional home directory override, primarily for tests.

    Returns:
        The path to ``~/.local/bin`` for the selected home directory.
    """
    base = home if home is not None else Path.home()
    return base / ".local" / "bin"


def discover_scripts(source: Path) -> tuple[Path, ...]:
    """Return the bundled scripts that should be linked into the bin directory.

    Args:
        source: Directory containing the bundled scripts.

    Returns:
        Regular, non-hidden files in name order, or an empty tuple when the
        source directory is missing.
    """
    if not source.is_dir():
        return ()
    return tuple(
        path
        for path in sorted(source.iterdir())
        if path.is_file() and not path.is_symlink() and not path.name.startswith(".")
    )


def make_script_executable(path: Path) -> bool:
    """Add execute bits to a bundled script when they are missing.

    Args:
        path: Script file to update.

    Returns:
        True if permissions changed, False if the script was already executable.

    Raises:
        OSError: If the script's mode cannot be read or changed.
    """
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & EXECUTE_BITS == EXECUTE_BITS:
        return False
    path.chmod(mode | EXECUTE_BITS)
    return True


def link_script(source: Path, destination: Path) -> bool:
    """Link a bundled script into the user's bin directory.

    An existing symlink that already points at the bundled script is left alone.
    Any other entry at the destination is replaced with a symlink.

    Args:
        source: Bundled script file.
        destination: Target path inside ``~/.local/bin``.

    Returns:
        True if a link was created or replaced, False if it was already correct.

    Raises:
        OSError: If the existing target cannot be removed or the link fails.
    """
    resolved_source = source.resolve()
    if destination.is_symlink() and destination.resolve() == resolved_source:
        return False

    if destination.exists() or destination.is_symlink():
        destination.unlink()

    destination.symlink_to(resolved_source)
    return True


def _has_conflict(source: Path, destination: Path) -> bool:
    """Return whether a destination contains something other than the correct link."""
    if not (destination.exists() or destination.is_symlink()):
        return False
    return not (destination.is_symlink() and destination.resolve() == source.resolve())


def run_scripts_step(
    *,
    home: Path | None = None,
    source: Path | None = None,
) -> ScriptResult:
    """Link bundled scripts into ``~/.local/bin`` and make them executable.

    Args:
        home: Optional home directory override, primarily for tests.
        source: Optional bundled script directory override, primarily for tests.

    Returns:
        The outcome of the script linking step.
    """
    _log_info("Bundled script step started.")

    ui.section(
        "Bundled Scripts",
        subtitle="Link the bundled helper scripts into ~/.local/bin.",
        icon=ui.ICONS.terminal,
    )

    source_directory = source if source is not None else get_script_source_directory()
    bin_directory = get_bin_directory(home)
    scripts = discover_scripts(source_directory)

    if not scripts:
        _log_warning("Bundled script step skipped: no scripts found at %s", source_directory)
        ui.warning("Script linking skipped: no bundled scripts were found.")
        return ScriptResult.SKIPPED

    if not ui.is_interactive():
        _log_info("Bundled script step skipped: no interactive terminal.")
        ui.warning("Script linking skipped: linking scripts requires an interactive terminal.")
        return ScriptResult.SKIPPED

    ui.info(f"Found {len(scripts)} bundled script(s):")
    ui.bullet_list(script.name for script in scripts)

    conflicts = [
        script.name for script in scripts if _has_conflict(script, bin_directory / script.name)
    ]
    if conflicts:
        ui.warning(f"Existing entries will be replaced: {', '.join(conflicts)}")

    if not ui.confirm(
        f"Link {len(scripts)} bundled script(s) into ~/.local/bin?",
        default=False,
        instruction="Existing files are replaced without a backup.",
    ):
        _log_info("Bundled script step skipped by the user.")
        ui.info("Script linking skipped.")
        return ScriptResult.SKIPPED

    try:
        bin_directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _log_error("Could not create bin directory %s: %s", bin_directory, exc)
        ui.error(f"Could not create {bin_directory}: {exc}")
        return ScriptResult.FAILED

    linked: list[str] = []
    unchanged: list[str] = []
    failed: list[str] = []

    for script in scripts:
        destination = bin_directory / script.name
        try:
            permissions_changed = make_script_executable(script)
            link_changed = link_script(script, destination)
        except OSError as exc:
            failed.append(script.name)
            _log_error("Could not link script %s to %s: %s", script, destination, exc)
            ui.error(f"Could not link {script.name}: {exc}")
            continue

        if permissions_changed or link_changed:
            linked.append(script.name)
            _log_info("Linked bundled script: %s", destination)
            ui.success(f"Linked {script.name}.")
        else:
            unchanged.append(script.name)
            _log_info("Bundled script already linked: %s", destination)
            ui.info(f"{script.name} is already linked.")

    if failed:
        noun = "script" if len(failed) == 1 else "scripts"
        _log_error("Bundled script step failed for %d %s.", len(failed), noun)
        ui.error(f"Script linking failed for {len(failed)} {noun}: {', '.join(failed)}")
        return ScriptResult.FAILED

    if not linked:
        _log_info("Bundled script step completed: all scripts are already linked.")
        ui.success("Bundled scripts are already up to date.")
        return ScriptResult.COMPLETED

    _log_info(
        "Bundled script step completed: %d linked, %d already linked.",
        len(linked),
        len(unchanged),
    )
    ui.success(
        f"Script linking complete: {len(linked)} linked, {len(unchanged)} already linked.",
    )
    return ScriptResult.COMPLETED
