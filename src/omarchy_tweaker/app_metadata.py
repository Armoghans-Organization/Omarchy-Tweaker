"""Application metadata derived from the packaged project definition.

The distribution name and version are read from the installed package metadata,
which is generated from ``pyproject.toml``. When the package is not installed
(for example, when running directly from a source checkout), the nearest
matching ``pyproject.toml`` is used as a fallback.

This keeps ``pyproject.toml`` as the single source of truth: changing the name
or version there is enough, no other module needs to be updated.
"""

from __future__ import annotations

import tomllib
from importlib import metadata
from pathlib import Path
from typing import Final

DISTRIBUTION_NAME: Final = "omarchy-tweaker"


def _humanize(name: str) -> str:
    """Convert a distribution name into a display-friendly name."""
    return name.replace("-", " ").replace("_", " ").title()


def _distribution_field(field: str) -> str | None:
    """Read a field from the installed distribution metadata."""
    try:
        value = metadata.metadata(DISTRIBUTION_NAME).get(field)
    except metadata.PackageNotFoundError:
        return None
    return str(value) if value else None


def _load_project_table() -> dict[str, object]:
    """Return the ``[project]`` table from the nearest matching pyproject."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "pyproject.toml"
        if not candidate.is_file():
            continue

        try:
            with candidate.open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError):
            continue

        project = data.get("project")
        if isinstance(project, dict) and project.get("name") == DISTRIBUTION_NAME:
            return project

    return {}


def _resolve_name() -> str:
    """Resolve the display name from metadata, falling back to pyproject."""
    name = _distribution_field("Name")

    if name is None:
        project_name = _load_project_table().get("name")
        if isinstance(project_name, str) and project_name:
            name = project_name

    return _humanize(name or DISTRIBUTION_NAME)


def _resolve_version() -> str:
    """Resolve the version from metadata, falling back to pyproject."""
    try:
        return metadata.version(DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        pass

    project_version = _load_project_table().get("version")
    if isinstance(project_version, str) and project_version:
        return project_version

    return "unknown"


APP_NAME: Final = _resolve_name()
APP_SLUG: Final = DISTRIBUTION_NAME.replace("-", "_")
APP_VERSION: Final = _resolve_version()
