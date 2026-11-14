"""Install selected Pacman and AUR packages."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from rich.progress import Progress, TaskID

from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.logger import get_session

PACKAGE_INSTALL_TIMEOUT_SECONDS: Final = 900.0
SUDO_AUTH_TIMEOUT_SECONDS: Final = 120.0

PACMAN_PACKAGES: Final = (
    "atuin",
    "brave-origin-bin",
    "fnm",
    "git-delta",
    "gitleaks",
    "go",
    "hugo",
    "kdeconnect",
    "omarchy-zsh",
    "onefetch",
    "onionshare",
    "openvpn",
    "python-pip",
    "python-pipx",
    "python-pytest",
    "qemu-full",
    "qemu-user-static-binfmt",
    "qrencode",
    "ripgrep",
    "sqlitebrowser",
    "superfile",
    "tig",
    "tldr",
    "ttf-hack-nerd",
    "uv",
    "virt-manager",
    "virt-viewer",
    "visual-studio-code-bin",
    "zellij",
    "zen-browser-bin",
    "zram-generator",
    "rclone",
    "caddy",
    "docker",
    "docker-compose",
    "docker-buildx",
)

AUR_PACKAGES: Final = (
    "powershell-bin",
    "cyberchef-web",
    "anydesk-bin",
)


class PackageGroup(StrEnum):
    """Package source used during installation."""

    PACMAN = "Pacman"
    AUR = "AUR"


class PackageResult(StrEnum):
    """Outcome of the package installation step."""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class PackageGroupSpec:
    """A selectable group of packages and its install command."""

    group: PackageGroup
    packages: tuple[str, ...]
    command: tuple[str, ...]

    @property
    def label(self) -> str:
        """Return the short display label for this package group."""
        return self.group.value

    @property
    def title(self) -> str:
        """Return the display title for this package group."""
        return f"{self.label} Packages"


PACKAGE_GROUPS: Final = (
    PackageGroupSpec(
        PackageGroup.PACMAN,
        PACMAN_PACKAGES,
        ("sudo", "pacman", "-S", "--noconfirm", "--needed", "--noprogressbar"),
    ),
    PackageGroupSpec(
        PackageGroup.AUR,
        AUR_PACKAGES,
        ("yay", "-S", "--noconfirm", "--needed", "--noprogressbar"),
    ),
)


def _log_error(message: str, *args: object) -> None:
    logger = get_session()
    if logger is not None:
        logger.error(message, *args)


def _log_info(message: str, *args: object) -> None:
    logger = get_session()
    if logger is not None:
        logger.info(message, *args)


def _command_name(group: PackageGroupSpec) -> str:
    """Return the package-manager executable for a group."""
    command = group.command
    if command[0] == "sudo" and len(command) > 1:
        return command[1]
    return command[0]


def _run_sudo(args: list[str]) -> int | None:
    """Run a sudo authentication command and return its exit status."""
    try:
        result = subprocess.run(  # nosec B603
            args,
            check=False,
            timeout=SUDO_AUTH_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        _log_error("Sudo authentication failed: sudo was not found.")
        return None
    except subprocess.TimeoutExpired:
        _log_error("Sudo authentication timed out after %s seconds.", SUDO_AUTH_TIMEOUT_SECONDS)
        return None
    except OSError as exc:
        _log_error("Could not start sudo authentication: %s", exc)
        return None

    return result.returncode


def _ensure_sudo() -> bool:
    """Prompt for and cache sudo credentials before starting a live display."""
    sudo = shutil.which("sudo")
    if sudo is None:
        _log_error("Sudo authentication failed: sudo was not found.")
        return False

    authenticated = _run_sudo([sudo, "-v"])
    if authenticated != 0:
        if authenticated is not None:
            _log_error("Sudo authentication exited with status %s.", authenticated)
        return False

    noninteractive = _run_sudo([sudo, "-n", "-v"])
    if noninteractive != 0:
        if noninteractive is not None:
            _log_error("Sudo requires a password for every command.")
        return False

    return True


def _select_packages(group: PackageGroupSpec) -> tuple[str, ...]:
    """Show a package group and return the selected packages in catalog order."""
    selected_names = ui.checkbox(
        f"Select {group.title} to install:",
        list(group.packages),
        instruction=(
            "Space selects, Enter confirms. Leave all unselected to skip this package group."
        ),
    )
    selected_set = set(selected_names)
    return tuple(package for package in group.packages if package in selected_set)


def _confirm_install(group: PackageGroupSpec, packages: Sequence[str]) -> bool:
    """Ask for final confirmation before installing a package group."""
    return ui.confirm(
        f"Install {len(packages)} selected {group.label} package(s)?",
        default=False,
        instruction="Package installation may use sudo and cannot be undone easily.",
    )


def _install_group(
    group: PackageGroupSpec,
    packages: Sequence[str],
    *,
    terminal: ui.VirtualTerminal,
    progress: Progress,
) -> bool:
    """Install one package group with a single command.

    Args:
        group: Package group being installed.
        packages: Selected package names.
        terminal: Virtual terminal that streams command output.
        progress: Progress display shown outside the virtual terminal.

    Returns:
        ``True`` when the command exits successfully, otherwise ``False``.
    """
    if not packages:
        return True

    task_id: TaskID = progress.add_task(
        f"Installing {len(packages)} {group.label} package(s)",
        total=None,
    )
    command = [*group.command, *packages]
    _log_info("Installing packages: %s", " ".join(command))
    terminal.writeline(
        f"Installing {len(packages)} {group.label} package(s)...",
        style=ui.THEME.info,
    )

    try:
        returncode = terminal.run(
            command,
            timeout=PACKAGE_INSTALL_TIMEOUT_SECONDS,
            echo=False,
        )
    except FileNotFoundError:
        executable = _command_name(group)
        _log_error("Package installation failed: the %s command was not found.", executable)
        terminal.writeline(
            f"The {executable} command was not found on PATH.",
            style=ui.THEME.error,
        )
        progress.update(task_id, description=f"Failed {group.label} installation")
        progress.advance(task_id)
        return False
    except subprocess.TimeoutExpired:
        _log_error(
            "Package installation timed out after %s seconds.",
            PACKAGE_INSTALL_TIMEOUT_SECONDS,
        )
        terminal.writeline(
            f"Package installation timed out after {PACKAGE_INSTALL_TIMEOUT_SECONDS:g}s.",
            style=ui.THEME.error,
        )
        progress.update(task_id, description=f"Failed {group.label} installation")
        progress.advance(task_id)
        return False
    except OSError as exc:
        _log_error("Could not start package installation: %s", exc)
        terminal.writeline(
            f"Could not start package installation: {exc}",
            style=ui.THEME.error,
        )
        progress.update(task_id, description=f"Failed {group.label} installation")
        progress.advance(task_id)
        return False

    if returncode != 0:
        _log_error("Package installation exited with status %s.", returncode)
        progress.update(task_id, description=f"Failed {group.label} installation")
        progress.advance(task_id)
        return False

    _log_info("Package installation completed for %s.", group.title)
    progress.update(task_id, description=f"Installed {len(packages)} {group.label} package(s)")
    progress.advance(task_id)
    return True


def run_packages_step(*, groups: Sequence[PackageGroupSpec] = PACKAGE_GROUPS) -> PackageResult:
    """Install selected Pacman and AUR packages.

    Args:
        groups: Package groups to present, in display order.

    Returns:
        The outcome of the package installation step.
    """
    logger = get_session()
    if logger is not None:
        logger.info("Package installation step started.")

    ui.section(
        "Package Installation",
        subtitle="Install selected Pacman and AUR packages.",
        icon=ui.ICONS.package,
    )

    if not ui.is_interactive():
        if logger is not None:
            logger.info("Package installation skipped: no interactive terminal.")
        ui.warning(
            "Package installation skipped: selecting packages requires an interactive terminal.",
        )
        return PackageResult.SKIPPED

    installed_any = False
    failed_any = False

    for group in groups:
        selected = _select_packages(group)
        if not selected:
            ui.info(f"No {group.title} selected.")
            continue

        if not _confirm_install(group, selected):
            if logger is not None:
                logger.info("%s installation skipped by the user.", group.label)
            ui.info(f"{group.label} installation skipped.")
            continue

        if not _ensure_sudo():
            if logger is not None:
                logger.error("%s installation failed: sudo authentication failed.", group.label)
            ui.error(f"{group.label} installation failed: sudo authentication failed.")
            failed_any = True
            continue

        with ui.terminal_with_progress(
            height=12,
            max_lines=200,
            title=f"{group.title} Installation",
        ) as (terminal, progress):
            succeeded = _install_group(
                group,
                selected,
                terminal=terminal,
                progress=progress,
            )

        if succeeded:
            installed_any = True
        else:
            failed_any = True

    if failed_any:
        if logger is not None:
            logger.error("Package installation failed for one or more package groups.")
        ui.error("Package installation failed for one or more package groups.")
        return PackageResult.FAILED

    if not installed_any:
        if logger is not None:
            logger.info("Package installation skipped: no packages were selected.")
        ui.info("No packages were installed.")
        return PackageResult.SKIPPED

    if logger is not None:
        logger.info("Package installation step completed.")
    ui.success("Package installation completed.")
    return PackageResult.COMPLETED
