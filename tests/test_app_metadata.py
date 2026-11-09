from __future__ import annotations

import tomllib
from importlib import metadata
from pathlib import Path

import pytest

from omarchy_tweaker import app_metadata
from omarchy_tweaker.app_metadata import (
    APP_NAME,
    APP_SLUG,
    APP_VERSION,
    DISTRIBUTION_NAME,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _pyproject_project() -> dict[str, object]:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)

    project = data["project"]
    assert isinstance(project, dict)
    return project


def _raise_package_not_found(name: str) -> None:
    raise metadata.PackageNotFoundError(name)


def test_app_name_is_humanized_distribution_name() -> None:
    assert APP_NAME == "Omarchy Tweaker"


def test_app_slug_is_module_friendly() -> None:
    assert APP_SLUG == "omarchy_tweaker"


def test_app_version_matches_installed_distribution() -> None:
    assert metadata.version(DISTRIBUTION_NAME) == APP_VERSION


def test_name_falls_back_to_pyproject(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        metadata,
        "metadata",
        _raise_package_not_found,
    )

    assert app_metadata._resolve_name() == "Omarchy Tweaker"


def test_version_falls_back_to_pyproject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        metadata,
        "version",
        _raise_package_not_found,
    )

    assert app_metadata._resolve_version() == _pyproject_project()["version"]


def test_name_uses_distribution_name_when_no_source_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        metadata,
        "metadata",
        _raise_package_not_found,
    )
    monkeypatch.setattr(app_metadata, "_load_project_table", lambda: {})

    assert app_metadata._resolve_name() == "Omarchy Tweaker"


def test_version_is_unknown_when_no_source_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        metadata,
        "version",
        _raise_package_not_found,
    )
    monkeypatch.setattr(app_metadata, "_load_project_table", lambda: {})

    assert app_metadata._resolve_version() == "unknown"
