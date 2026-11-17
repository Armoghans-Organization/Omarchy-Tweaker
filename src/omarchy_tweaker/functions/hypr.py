"""Install the bundled Hyprland configuration for an Omarchy setup."""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from typing import Final

from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.logger import get_session

HYPR_DIRECTORY_ENV_VAR: Final = "OMARCHY_TWEAKER_HYPR_DIR"
HYPRLAND_CONFIG_FILE: Final = "hyprland.lua"
WORKSPACES_REQUIRE: Final = 'require("hypr.workspaces")'


class HyprResult(StrEnum):
    """Outcome of the Hyprland configuration step."""

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


def get_hypr_source_directory() -> Path:
    """Return the directory containing the bundled Hyprland configuration.

    ``OMARCHY_TWEAKER_HYPR_DIR`` takes precedence. When it is unset, the
    ``hypr`` directory bundled next to the package modules is used.
    """
    override = os.environ.get(HYPR_DIRECTORY_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[1] / "hypr"


def get_hypr_config_directory(home: Path | None = None) -> Path:
    """Return the Hyprland configuration directory beneath the home directory.

    Args:
        home: Optional home directory override, primarily for tests.

    Returns:
        The path to ``~/.config/hypr`` for the selected home directory.
    """
    base = home if home is not None else Path.home()
    return base / ".config" / "hypr"


def discover_hypr_files(source: Path) -> tuple[Path, ...]:
    """Return the bundled files that should be linked into the config directory.

    Args:
        source: Directory containing the bundled configuration files.

    Returns:
        Regular files in name order, or an empty tuple if the source is missing.
    """
    if not source.is_dir():
        return ()
    return tuple(path for path in sorted(source.iterdir()) if path.is_file())


def link_hypr_file(source: Path, destination: Path) -> bool:
    """Replace a Hyprland config file with a symlink to the bundled file.

    An existing symlink that already points at the bundled file is left alone.
    Any other file at the destination is replaced without a backup, as the
    bundled configuration is the intended source of truth.

    Args:
        source: Bundled configuration file.
        destination: Target path inside ``~/.config/hypr``.

    Returns:
        True if a link was created or replaced, False if it was already correct.

    Raises:
        OSError: If the existing target cannot be removed or the link fails.
    """
    if destination.is_symlink() and destination.resolve() == source.resolve():
        return False

    if destination.exists() or destination.is_symlink():
        destination.unlink()

    destination.symlink_to(source)
    return True


def append_workspaces_require(hyprland_lua: Path) -> bool:
    """Append the workspaces require line to ``hyprland.lua`` when missing.

    The check is idempotent: a line that already matches is never duplicated,
    regardless of surrounding whitespace.

    Args:
        hyprland_lua: Path to the Hyprland Lua entrypoint.

    Returns:
        True if the line was appended, False if it was already present.

    Raises:
        OSError: If the entrypoint cannot be read or written.
    """
    existing = hyprland_lua.read_text(encoding="utf-8")
    if any(line.strip() == WORKSPACES_REQUIRE for line in existing.splitlines()):
        return False

    with hyprland_lua.open("a", encoding="utf-8") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(f"{WORKSPACES_REQUIRE}\n")
    return True


def run_hypr_step(
    *,
    home: Path | None = None,
    source: Path | None = None,
) -> HyprResult:
    """Link bundled Hyprland configuration files and enable workspaces.

    Args:
        home: Optional home directory override, primarily for tests.
        source: Optional bundled configuration directory override, primarily
            for tests.

    Returns:
        The outcome of the Hyprland configuration step.
    """
    logger = get_session()
    if logger is not None:
        logger.info("Hyprland configuration step started.")

    ui.section(
        "Hyprland Configuration",
        subtitle="Apply the bundled Hyprland configuration.",
        icon=ui.ICONS.gear,
    )

    source_directory = source if source is not None else get_hypr_source_directory()
    config_directory = get_hypr_config_directory(home)
    files = discover_hypr_files(source_directory)

    if not files:
        _log_warning(
            "Hyprland configuration step skipped: no bundled files found at %s",
            source_directory,
        )
        ui.warning("Hyprland configuration skipped: no bundled files were found.")
        return HyprResult.SKIPPED

    if not ui.is_interactive():
        if logger is not None:
            logger.info("Hyprland configuration step skipped: no interactive terminal.")
        ui.warning(
            "Hyprland configuration skipped: replacing config files requires "
            "an interactive terminal.",
        )
        return HyprResult.SKIPPED

    ui.info(f"Found {len(files)} bundled Hyprland configuration file(s):")
    ui.bullet_list(file.name for file in files)

    if not ui.confirm(
        f"Replace {len(files)} Hyprland config file(s) with symlinks and load workspaces?",
        default=False,
        instruction="Existing files in ~/.config/hypr/ are replaced without a backup.",
    ):
        if logger is not None:
            logger.info("Hyprland configuration step skipped by the user.")
        ui.info("Hyprland configuration skipped.")
        return HyprResult.SKIPPED

    try:
        config_directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _log_error("Could not create Hyprland config directory %s: %s", config_directory, exc)
        ui.error(f"Could not create {config_directory}: {exc}")
        return HyprResult.FAILED

    linked: list[str] = []
    unchanged: list[str] = []
    failed: list[str] = []

    for file in files:
        destination = config_directory / file.name
        try:
            changed = link_hypr_file(file, destination)
        except OSError as exc:
            failed.append(file.name)
            _log_error("Could not link %s to %s: %s", file, destination, exc)
            ui.error(f"Could not link {file.name}: {exc}")
            continue

        if changed:
            linked.append(file.name)
            if logger is not None:
                logger.info("Linked Hyprland config: %s", destination)
            ui.success(f"Linked {file.name}.")
        else:
            unchanged.append(file.name)
            if logger is not None:
                logger.info("Hyprland config already linked: %s", destination)
            ui.info(f"{file.name} is already linked.")

    if failed:
        noun = "file" if len(failed) == 1 else "files"
        _log_error("Hyprland configuration failed for %d %s.", len(failed), noun)
        ui.error(f"Hyprland configuration failed for {len(failed)} {noun}: {', '.join(failed)}")
        return HyprResult.FAILED

    hyprland_lua = config_directory / HYPRLAND_CONFIG_FILE
    try:
        require_added = append_workspaces_require(hyprland_lua)
    except OSError as exc:
        _log_error("Could not update %s: %s", hyprland_lua, exc)
        ui.error(f"Could not update {HYPRLAND_CONFIG_FILE}: {exc}")
        return HyprResult.FAILED

    if require_added:
        if logger is not None:
            logger.info("Added workspaces require to %s", hyprland_lua)
        ui.success(f"Added {WORKSPACES_REQUIRE} to {HYPRLAND_CONFIG_FILE}.")
    else:
        if logger is not None:
            logger.info("Workspaces require is already present in %s", hyprland_lua)
        ui.info(f"{HYPRLAND_CONFIG_FILE} already loads hypr.workspaces.")

    if not linked and not require_added:
        if logger is not None:
            logger.info(
                "Hyprland configuration step completed: configuration is already up to date.",
            )
        ui.success("Hyprland configuration is already up to date.")
        return HyprResult.COMPLETED

    if logger is not None:
        logger.info(
            "Hyprland configuration step completed: %d linked, %d already linked.",
            len(linked),
            len(unchanged),
        )
    ui.success(
        f"Hyprland configuration complete: {len(linked)} linked, {len(unchanged)} already linked.",
    )
    return HyprResult.COMPLETED
