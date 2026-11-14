"""Install selected Omarchy shell plugins."""

from __future__ import annotations

import configparser
import json
import os
import shutil
import subprocess  # nosec B404
import time
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

from rich.progress import Progress, TaskID

from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.logger import get_session

OMARCHY_COMMAND: Final = "omarchy"
PLUGIN_ADD_TIMEOUT_SECONDS: Final = 300.0
PLUGIN_ENABLE_TIMEOUT_SECONDS: Final = 60.0
PLUGIN_LIST_TIMEOUT_SECONDS: Final = 30.0
PLUGIN_PATCH_TIMEOUT_SECONDS: Final = 120.0
PATCHES_DIR_ENV_VAR: Final = "OMARCHY_TWEAKER_PATCHES_DIR"
VALID_PLUGIN_POSITIONS: Final = frozenset({"left", "center", "right"})
PATCH_CONFIRM_INPUT: Final = "y\n" * 20
SHELL_CONFIG_BACKUP_SUFFIX: Final = ".bak"


class PluginResult(StrEnum):
    """Outcome of the plugin installation step."""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class PluginSpec:
    """A selectable Omarchy shell plugin."""

    name: str
    url: str
    description: str
    patch: bool = False
    patch_file: str | None = None
    position: str | None = None


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


def get_plugin_catalog_path() -> Path:
    """Return the bundled plugin catalog path."""
    return Path(__file__).resolve().parents[1] / "config" / "plugins.ini"


def get_patches_directory() -> Path:
    """Return the directory containing optional plugin patch scripts.

    ``OMARCHY_TWEAKER_PATCHES_DIR`` takes precedence. When it is unset, the
    repository-level ``patches`` directory next to the source tree is used.
    """
    override = os.environ.get(PATCHES_DIR_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[3] / "patches"


def _optional_value(value: str) -> str | None:
    """Normalize an optional INI value."""
    normalized = value.strip()
    if not normalized or normalized.lower() == "none":
        return None
    return normalized


def load_plugin_catalog(path: Path | None = None) -> tuple[PluginSpec, ...]:
    """Load the fixed plugin catalog from an INI file.

    Args:
        path: Optional catalog path override, primarily for tests.

    Returns:
        Plugin definitions in file order.

    Raises:
        OSError: If the catalog cannot be read.
        configparser.Error: If the catalog is malformed.
    """
    catalog_path = path or get_plugin_catalog_path()
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(catalog_path, encoding="utf-8")

    plugins: list[PluginSpec] = []
    for section in parser.sections():
        name = parser.get(section, "name", fallback=section).strip() or section
        url = parser.get(section, "url", fallback="").strip()
        description = parser.get(section, "description", fallback="").strip()
        if not url:
            _log_warning("Skipping plugin %s: missing url.", name)
            continue

        try:
            patch = parser.getboolean(section, "patch", fallback=False)
        except ValueError:
            _log_warning("Plugin %s has an invalid patch value; assuming false.", name)
            patch = False

        patch_file = _optional_value(parser.get(section, "patch-file", fallback=""))
        if patch_file is not None and Path(patch_file).name != patch_file:
            _log_warning("Plugin %s has an unsafe patch file name; ignoring it.", name)
            patch_file = None
        if patch and patch_file is None:
            _log_warning("Plugin %s enables a patch but does not name a patch file.", name)
            patch = False

        position = _optional_value(parser.get(section, "position", fallback=""))
        if position is not None and position not in VALID_PLUGIN_POSITIONS:
            _log_warning(
                "Plugin %s has invalid position %r; using the plugin default.",
                name,
                position,
            )
            position = None

        plugins.append(
            PluginSpec(
                name=name,
                url=url,
                description=description,
                patch=patch,
                patch_file=patch_file,
                position=position,
            )
        )

    return tuple(plugins)


def _select_plugins(plugins: Sequence[PluginSpec]) -> tuple[PluginSpec, ...]:
    """Show the catalog and return selected plugins in catalog order."""
    selected_names = ui.checkbox(
        "Select Omarchy Plugins to install:",
        [plugin.name for plugin in plugins],
        instruction=(
            "Space selects, Enter confirms. Leave all unselected to skip plugin installation."
        ),
    )
    selected_set = set(selected_names)
    return tuple(plugin for plugin in plugins if plugin.name in selected_set)


def _confirm_install(plugins: Sequence[PluginSpec]) -> bool:
    """Ask for final confirmation before installing plugins."""
    return ui.confirm(
        f"Install {len(plugins)} selected plugin(s)?",
        default=False,
        instruction=(
            "Plugins run as unsandboxed code inside omarchy-shell. "
            "Only install repositories you trust."
        ),
    )


def _parse_plugin_ids(payload: str) -> frozenset[str] | None:
    """Parse ``omarchy plugin list --json`` output into plugin IDs."""
    try:
        data: object = json.loads(payload)
    except json.JSONDecodeError:
        _log_error("Could not parse the installed plugin list.")
        return None

    if not isinstance(data, list):
        _log_error("The installed plugin list has an unexpected shape.")
        return None

    ids: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        plugin_id = item.get("id")
        if isinstance(plugin_id, str) and plugin_id:
            ids.add(plugin_id)
    return frozenset(ids)


def _list_plugin_ids() -> frozenset[str] | None:
    """Return installed plugin IDs, or ``None`` when discovery fails."""
    omarchy = shutil.which(OMARCHY_COMMAND)
    if omarchy is None:
        _log_error("Could not list plugins: omarchy was not found.")
        return None

    try:
        result = subprocess.run(  # nosec B603
            [omarchy, "plugin", "list", "--json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=PLUGIN_LIST_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        _log_error("Could not list plugins: omarchy was not found.")
        return None
    except subprocess.TimeoutExpired:
        _log_error("Plugin discovery timed out after %s seconds.", PLUGIN_LIST_TIMEOUT_SECONDS)
        return None
    except OSError as exc:
        _log_error("Could not list plugins: %s", exc)
        return None

    if result.returncode != 0:
        _log_error("Plugin discovery exited with status %s.", result.returncode)
        return None

    return _parse_plugin_ids(result.stdout)


def _new_plugin_id(
    before: frozenset[str] | None,
    after: frozenset[str] | None,
) -> str | None:
    """Return the single plugin ID added between two discovery snapshots."""
    if before is None or after is None:
        return None
    added = after - before
    if len(added) == 1:
        return next(iter(added))
    return None


def _normalize_plugin_url(url: str) -> str:
    """Normalize a plugin repository URL for comparison."""
    normalized = url.strip().rstrip("/").casefold()
    if normalized.startswith("git@github.com:"):
        normalized = f"https://github.com/{normalized.removeprefix('git@github.com:')}"
    if normalized.endswith(".git"):
        normalized = normalized.removesuffix(".git")
    return normalized


def _installed_plugin_id(
    plugin: PluginSpec,
    installed_ids: frozenset[str] | None,
) -> str | None:
    """Return the installed plugin ID matching the catalog repository URL."""
    if installed_ids is None:
        return None

    expected_url = _normalize_plugin_url(plugin.url)
    plugins_directory = Path.home() / ".config" / "omarchy" / "plugins"
    for plugin_id in installed_ids:
        config_path = plugins_directory / plugin_id / ".git" / "config"
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        try:
            parser.read(config_path, encoding="utf-8")
            remote_url = parser.get('remote "origin"', "url", fallback=None)
        except (OSError, UnicodeError, configparser.Error):
            continue
        if remote_url is not None and _normalize_plugin_url(remote_url) == expected_url:
            return plugin_id
    return None


def _enable_plugin(
    plugin: PluginSpec,
    plugin_id: str,
    *,
    terminal: ui.VirtualTerminal,
    progress: Progress,
    task_id: TaskID,
) -> bool:
    """Apply the configured bar placement to an installed plugin."""
    if plugin.position is None:
        return True

    enable_command = [
        OMARCHY_COMMAND,
        "plugin",
        "enable",
        plugin_id,
        "--section",
        plugin.position,
    ]
    return _run_terminal_command(
        terminal,
        enable_command,
        timeout=PLUGIN_ENABLE_TIMEOUT_SECONDS,
        progress=progress,
        task_id=task_id,
        failure_label=f"{plugin.name} placement",
    )


def _run_terminal_command(
    terminal: ui.VirtualTerminal,
    command: Sequence[str],
    *,
    timeout: float,
    progress: Progress,
    task_id: TaskID,
    failure_label: str,
) -> bool:
    """Run one command in the virtual terminal and report failures."""
    _log_info("Running plugin command: %s", " ".join(command))
    try:
        returncode = terminal.run(command, timeout=timeout, echo=False)
    except FileNotFoundError:
        _log_error("%s failed: command was not found.", failure_label)
        terminal.writeline("The required command was not found on PATH.", style=ui.THEME.error)
        progress.update(task_id, description=f"Failed {failure_label}")
        progress.advance(task_id)
        return False
    except subprocess.TimeoutExpired:
        _log_error("%s timed out after %s seconds.", failure_label, timeout)
        terminal.writeline(
            f"{failure_label} timed out after {timeout:g}s.",
            style=ui.THEME.error,
        )
        progress.update(task_id, description=f"Failed {failure_label}")
        progress.advance(task_id)
        return False
    except OSError as exc:
        _log_error("Could not start %s: %s", failure_label, exc)
        terminal.writeline(f"Could not start {failure_label}: {exc}", style=ui.THEME.error)
        progress.update(task_id, description=f"Failed {failure_label}")
        progress.advance(task_id)
        return False

    if returncode != 0:
        _log_error("%s exited with status %s.", failure_label, returncode)
        progress.update(task_id, description=f"Failed {failure_label}")
        progress.advance(task_id)
        return False

    return True


def _apply_patch(
    plugin: PluginSpec,
    *,
    patches_directory: Path,
    terminal: ui.VirtualTerminal,
) -> bool:
    """Apply an optional plugin patch non-interactively."""
    if not plugin.patch or plugin.patch_file is None:
        return True

    patch_path = patches_directory / plugin.patch_file
    if not patch_path.is_file():
        _log_error("Plugin patch was not found: %s", patch_path)
        terminal.writeline(
            f"Plugin patch was not found: {patch_path}",
            style=ui.THEME.error,
        )
        return False

    bash = shutil.which("bash")
    if bash is None:
        _log_error("Could not apply plugin patch: bash was not found.")
        terminal.writeline(
            "Could not apply plugin patch: bash was not found.", style=ui.THEME.error
        )
        return False

    terminal.writeline(f"Applying patch {plugin.patch_file}...", style=ui.THEME.info)
    try:
        result = subprocess.run(  # nosec B603
            [bash, str(patch_path)],
            check=False,
            capture_output=True,
            text=True,
            input=PATCH_CONFIRM_INPUT,
            timeout=PLUGIN_PATCH_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        _log_error(
            "Plugin patch timed out after %s seconds.",
            PLUGIN_PATCH_TIMEOUT_SECONDS,
        )
        terminal.writeline(
            f"Plugin patch timed out after {PLUGIN_PATCH_TIMEOUT_SECONDS:g}s.",
            style=ui.THEME.error,
        )
        return False
    except OSError as exc:
        _log_error("Could not run plugin patch %s: %s", patch_path, exc)
        terminal.writeline(f"Could not run plugin patch: {exc}", style=ui.THEME.error)
        return False

    output = f"{result.stdout}{result.stderr}"
    if output:
        terminal.write(output)

    if result.returncode != 0:
        _log_error("Plugin patch exited with status %s.", result.returncode)
        return False

    _log_info("Applied plugin patch: %s", patch_path)
    return True


def _install_plugin(
    plugin: PluginSpec,
    *,
    terminal: ui.VirtualTerminal,
    progress: Progress,
    patches_directory: Path,
) -> bool:
    """Install, enable, and optionally patch one plugin."""
    task_id = progress.add_task(f"Installing {plugin.name}", total=None)
    installed_ids = _list_plugin_ids()
    installed_id = _installed_plugin_id(plugin, installed_ids)

    if installed_id is not None:
        terminal.writeline(
            f"{plugin.name} is already installed; skipping installation.",
            style=ui.THEME.info,
        )
        if not _enable_plugin(
            plugin,
            installed_id,
            terminal=terminal,
            progress=progress,
            task_id=task_id,
        ):
            return False
        if not _apply_patch(plugin, patches_directory=patches_directory, terminal=terminal):
            progress.update(task_id, description=f"Failed {plugin.name}")
            progress.advance(task_id)
            return False

        _log_info("Plugin already installed: %s", plugin.name)
        progress.update(task_id, description=f"Already installed {plugin.name}")
        progress.advance(task_id)
        return True

    before_ids = installed_ids if plugin.position is not None else None
    terminal.writeline(f"Installing {plugin.name}...", style=ui.THEME.info)

    add_command = [OMARCHY_COMMAND, "plugin", "add", plugin.url, "--yes", "--enable"]
    if not _run_terminal_command(
        terminal,
        add_command,
        timeout=PLUGIN_ADD_TIMEOUT_SECONDS,
        progress=progress,
        task_id=task_id,
        failure_label=f"{plugin.name} installation",
    ):
        return False

    if plugin.position is not None:
        plugin_id = _new_plugin_id(before_ids, _list_plugin_ids())
        if plugin_id is None:
            _log_warning(
                "Could not determine the installed id for %s; keeping the default placement.",
                plugin.name,
            )
            terminal.writeline(
                "Could not determine the installed plugin id; keeping the default placement.",
                style=ui.THEME.warning,
            )
        elif not _enable_plugin(
            plugin,
            plugin_id,
            terminal=terminal,
            progress=progress,
            task_id=task_id,
        ):
            return False

    if not _apply_patch(plugin, patches_directory=patches_directory, terminal=terminal):
        progress.update(task_id, description=f"Failed {plugin.name}")
        progress.advance(task_id)
        return False

    _log_info("Plugin installation completed: %s", plugin.name)
    progress.update(task_id, description=f"Installed {plugin.name}")
    progress.advance(task_id)
    return True


def _get_shell_config_source() -> Path:
    """Return the path to the bundled shell.json configuration file."""
    return Path(__file__).resolve().parent.parent / "config" / "shell.json"


def _get_shell_config_destination() -> Path:
    """Return the path to the omarchy shell.json configuration file."""
    return Path.home() / ".config" / "omarchy" / "shell.json"


def _install_shell_config(
    *,
    terminal: ui.VirtualTerminal,
    progress: Progress,
) -> bool:
    """Back up and replace the omarchy shell.json configuration.

    Copies the bundled shell.json to ~/.config/omarchy/shell.json,
    backs up any existing file, and makes the new file read-only.

    Args:
        terminal: Virtual terminal for user-visible output.
        progress: Progress display for task updates.

    Returns:
        True if the shell config was installed or already up to date,
        False if installation failed.
    """
    source = _get_shell_config_source()
    destination = _get_shell_config_destination()

    if not source.exists():
        _log_error("Bundled shell.json not found at %s", source)
        terminal.writeline(
            f"Shell config source not found: {source}",
            style=ui.THEME.error,
        )
        return False

    task_id = progress.add_task("Installing shell config", total=None)

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _log_error("Could not create omarchy config directory: %s", exc)
        terminal.writeline(
            f"Could not create config directory: {exc}",
            style=ui.THEME.error,
        )
        progress.update(task_id, description="Failed shell config")
        progress.advance(task_id)
        return False

    if destination.exists():
        if destination.is_symlink():
            _log_info(
                "Shell config is already a symlink; replacing with bundled config.",
            )
        else:
            backup_path = _backup_shell_config(destination)
            if backup_path is not None:
                _log_info("Backed up shell config to %s", backup_path)
                terminal.writeline(
                    f"Backed up existing shell config to {backup_path.name}",
                    style=ui.THEME.info,
                )
            else:
                _log_warning("Could not back up existing shell config.")
                terminal.writeline(
                    "Could not back up existing shell config.",
                    style=ui.THEME.warning,
                )

    try:
        shutil.copy2(source, destination)
    except OSError as exc:
        _log_error("Could not copy shell config: %s", exc)
        terminal.writeline(
            f"Could not copy shell config: {exc}",
            style=ui.THEME.error,
        )
        progress.update(task_id, description="Failed shell config")
        progress.advance(task_id)
        return False

    if not _set_shell_config_permissions(destination, terminal=terminal):
        terminal.writeline(
            "Shell config permissions could not be set.",
            style=ui.THEME.error,
        )
        progress.update(task_id, description="Failed shell config permissions")
        progress.advance(task_id)
        return False

    _log_info("Shell config installed at %s", destination)
    progress.update(task_id, description="Installed shell config")
    progress.advance(task_id)
    return True


def _backup_shell_config(destination: Path) -> Path | None:
    """Back up an existing shell config file.

    Args:
        destination: Path to the existing shell config.

    Returns:
        Path to the backup file, or None if backup failed.
    """
    timestamp = time.strftime("%Y%m%d%H%M%S")
    backup_path = destination.with_name(
        f"{destination.name}{SHELL_CONFIG_BACKUP_SUFFIX}.{timestamp}",
    )
    try:
        shutil.copy2(destination, backup_path)
    except OSError as exc:
        _log_error("Could not back up shell config: %s", exc)
        return None
    return backup_path


def _set_shell_config_permissions(
    destination: Path,
    *,
    terminal: ui.VirtualTerminal,
) -> bool:
    """Set restrictive permissions on the shell config file.

    Uses sudo to change ownership to root and set read-only permissions,
    so the file can only be edited with elevated privileges.

    Args:
        destination: Path to the shell config file.
        terminal: Virtual terminal for user-visible output.

    Returns:
        True if permissions were set successfully, False otherwise.
    """
    try:
        result = subprocess.run(  # nosec B603 B607
            ["sudo", "chown", "root:root", str(destination)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        _log_error("sudo command not found; cannot set shell config permissions.")
        terminal.writeline(
            "sudo not found; shell config permissions not set.",
            style=ui.THEME.warning,
        )
        return False
    except subprocess.TimeoutExpired:
        _log_error("Timed out setting shell config ownership.")
        terminal.writeline(
            "Timed out setting shell config ownership.",
            style=ui.THEME.error,
        )
        return False

    if result.returncode != 0:
        _log_error(
            "Could not change shell config ownership: %s",
            result.stderr.strip(),
        )
        terminal.writeline(
            "Could not change shell config ownership (sudo required).",
            style=ui.THEME.error,
        )
        return False

    try:
        result = subprocess.run(  # nosec B603 B607
            ["sudo", "chmod", "444", str(destination)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        _log_error("sudo command not found; cannot set shell config permissions.")
        terminal.writeline(
            "sudo not found; shell config permissions not set.",
            style=ui.THEME.warning,
        )
        return False
    except subprocess.TimeoutExpired:
        _log_error("Timed out setting shell config permissions.")
        terminal.writeline(
            "Timed out setting shell config permissions.",
            style=ui.THEME.error,
        )
        return False

    if result.returncode != 0:
        _log_error(
            "Could not change shell config permissions: %s",
            result.stderr.strip(),
        )
        terminal.writeline(
            "Could not change shell config permissions (sudo required).",
            style=ui.THEME.error,
        )
        return False

    _log_info("Set shell config ownership to root and permissions to read-only.")
    terminal.writeline(
        "Shell config is now read-only (edit with sudo).",
        style=ui.THEME.info,
    )
    return True


def run_plugins_step(
    *,
    plugins: Sequence[PluginSpec] | None = None,
    patches_directory: Path | None = None,
    install_shell_config: bool = True,
) -> PluginResult:
    """Install selected Omarchy shell plugins.

    After successful plugin installation, replaces ~/.config/omarchy/shell.json
    with the bundled configuration and sets read-only permissions.

    Args:
        plugins: Optional catalog override, primarily for tests.
        patches_directory: Optional patch directory override, primarily for tests.
        install_shell_config: Whether to install the shell config after plugins.
            Defaults to True. Primarily for tests.

    Returns:
        The outcome of the plugin installation step.
    """
    logger = get_session()
    if logger is not None:
        logger.info("Plugin installation step started.")

    ui.section(
        "Omarchy Plugins",
        subtitle="Install selected Omarchy shell plugins.",
        icon=ui.ICONS.gear,
    )

    if not ui.is_interactive():
        if logger is not None:
            logger.info("Plugin installation skipped: no interactive terminal.")
        ui.warning(
            "Plugin installation skipped: selecting plugins requires an interactive terminal.",
        )
        return PluginResult.SKIPPED

    try:
        catalog = tuple(plugins) if plugins is not None else load_plugin_catalog()
    except (OSError, configparser.Error) as exc:
        _log_error("Could not load the plugin catalog: %s", exc)
        ui.error(f"Could not load the plugin catalog: {exc}")
        return PluginResult.FAILED

    if not catalog:
        _log_warning("Plugin installation skipped: the plugin catalog is empty.")
        ui.warning("No plugins are configured.")
        return PluginResult.SKIPPED

    selected = _select_plugins(catalog)
    if not selected:
        if logger is not None:
            logger.info("Plugin installation skipped: no plugins were selected.")
        ui.info("No plugins were selected.")
        return PluginResult.SKIPPED

    if not _confirm_install(selected):
        if logger is not None:
            logger.info("Plugin installation skipped by the user.")
        ui.info("Plugin installation skipped.")
        return PluginResult.SKIPPED

    patch_directory = patches_directory or get_patches_directory()
    installed_any = False
    failed_any = False

    with ui.terminal_with_progress(
        height=14,
        max_lines=300,
        title="Omarchy Plugin Installation",
    ) as (terminal, progress):
        for plugin in selected:
            if _install_plugin(
                plugin,
                terminal=terminal,
                progress=progress,
                patches_directory=patch_directory,
            ):
                installed_any = True
            else:
                failed_any = True

        if (
            install_shell_config
            and not failed_any
            and not _install_shell_config(
                terminal=terminal,
                progress=progress,
            )
        ):
            if logger is not None:
                logger.error("Shell config installation failed.")
            ui.error("Plugin installation succeeded, but shell config installation failed.")
            return PluginResult.FAILED

    if failed_any:
        if logger is not None:
            logger.error("Plugin installation failed for one or more plugins.")
        ui.error("Plugin installation failed for one or more plugins.")
        return PluginResult.FAILED

    if not installed_any:
        if logger is not None:
            logger.info("Plugin installation skipped: no plugins were installed.")
        ui.info("No plugins were installed.")
        return PluginResult.SKIPPED

    if logger is not None:
        logger.info("Plugin installation step completed.")
    ui.success("Plugin installation completed.")
    return PluginResult.COMPLETED
