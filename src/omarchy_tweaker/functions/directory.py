"""Create the required personal directories for an Omarchy setup."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.logger import get_session


@dataclass(frozen=True)
class DirectoryTarget:
    """A directory that the setup step can create."""

    relative_path: Path
    description: str

    @property
    def display_path(self) -> str:
        """Return the target path in home-relative display form."""
        return f"~/{self.relative_path.as_posix()}"

    def path_for(self, home: Path | None = None) -> Path:
        """Return the absolute path for this target.

        Args:
            home: Optional home directory override.

        Returns:
            The target path beneath the selected home directory.
        """
        base = home if home is not None else Path.home()
        return base / self.relative_path


class DirectoryResult(StrEnum):
    """Outcome of the directory setup step."""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


REQUIRED_DIRECTORIES: Final[tuple[DirectoryTarget, ...]] = (
    DirectoryTarget(Path("Github"), "Git repositories"),
    DirectoryTarget(Path("Github/Clone"), "Cloned repositories"),
    DirectoryTarget(Path("Projects"), "Personal projects"),
    DirectoryTarget(Path("Projects/Containers"), "Container projects"),
    DirectoryTarget(Path(".ISO"), "ISO images"),
    DirectoryTarget(Path(".VM"), "Virtual machines"),
    DirectoryTarget(Path(".Cloud"), "Cloud storage"),
)


def create_directory(path: Path) -> None:
    """Create one directory without creating missing parents.

    Args:
        path: Directory path to create.

    Raises:
        FileExistsError: If the path already exists.
        FileNotFoundError: If the parent directory does not exist.
        OSError: If the directory cannot be created.
    """
    path.mkdir(mode=0o755)


def run_directory_step(*, home: Path | None = None) -> DirectoryResult:
    """Create required directories after asking about each missing path.

    Args:
        home: Optional home directory override, primarily for tests.

    Returns:
        The outcome of the directory setup step.
    """
    logger = get_session()
    if logger is not None:
        logger.info("Directory step started.")

    ui.section(
        "Required Directories",
        subtitle="Create the standard workspace folders used by this setup.",
        icon=ui.ICONS.folder,
    )

    base = home if home is not None else Path.home()
    targets = tuple((target, target.path_for(base)) for target in REQUIRED_DIRECTORIES)

    if all(path.is_dir() for _, path in targets):
        if logger is not None:
            logger.info("Directory step completed: all required directories exist.")
        ui.success("All required directories already exist.")
        return DirectoryResult.COMPLETED

    if not ui.is_interactive():
        if logger is not None:
            logger.info("Directory step skipped: no interactive terminal.")
        ui.warning(
            "Directory setup skipped: creating directories requires an interactive terminal.",
        )
        return DirectoryResult.SKIPPED

    created: list[DirectoryTarget] = []
    existing: list[DirectoryTarget] = []
    skipped: list[DirectoryTarget] = []
    failed: list[DirectoryTarget] = []

    for target, path in targets:
        if path.is_dir():
            existing.append(target)
            if logger is not None:
                logger.info("Directory already exists: %s", path)
            ui.info(f"{target.display_path} already exists.")
            continue

        if path.exists() or path.is_symlink():
            failed.append(target)
            if logger is not None:
                logger.error(
                    "Cannot create directory because the path is not a directory: %s",
                    path,
                )
            ui.error(f"{target.display_path} exists but is not a directory.")
            continue

        if not ui.confirm(
            f"Create {target.display_path}?",
            default=True,
            instruction=target.description,
        ):
            skipped.append(target)
            if logger is not None:
                logger.info("Directory creation skipped by the user: %s", path)
            ui.info(f"Skipped {target.display_path}.")
            continue

        if not path.parent.is_dir():
            skipped.append(target)
            if logger is not None:
                logger.info(
                    "Directory creation skipped because the parent is unavailable: %s",
                    path,
                )
            ui.warning(
                f"Skipped {target.display_path}: its parent directory is not available.",
            )
            continue

        try:
            create_directory(path)
        except OSError as exc:
            failed.append(target)
            if logger is not None:
                logger.error("Could not create directory %s: %s", path, exc)
            ui.error(f"Could not create {target.display_path}: {exc}")
            continue

        created.append(target)
        if logger is not None:
            logger.info("Created directory: %s", path)
        ui.success(f"Created {target.display_path}.")

    if failed:
        noun = "directory" if len(failed) == 1 else "directories"
        if logger is not None:
            logger.error("Directory step failed for %d %s.", len(failed), noun)
        ui.error(f"Directory setup failed for {len(failed)} {noun}.")
        return DirectoryResult.FAILED

    if created:
        if logger is not None:
            logger.info(
                "Directory step completed: %d created, %d existing, %d skipped.",
                len(created),
                len(existing),
                len(skipped),
            )
        ui.success(
            f"Directory setup complete: {len(created)} created, "
            f"{len(existing)} already present, {len(skipped)} skipped.",
        )
        return DirectoryResult.COMPLETED

    if logger is not None:
        logger.info("Directory step skipped: no directories were created.")
    ui.info("Directory setup skipped. No directories were created.")
    return DirectoryResult.SKIPPED
