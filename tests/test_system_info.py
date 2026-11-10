from __future__ import annotations

import pytest

from omarchy_tweaker.functions.system_info import (
    format_bytes,
    format_duration,
    format_usage,
    get_system_info,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (0, "0.0 B"),
        (1023, "1023.0 B"),
        (1024, "1.0 KiB"),
        (1024**2, "1.0 MiB"),
        (1024**3, "1.0 GiB"),
        (1024**4, "1.0 TiB"),
    ),
)
def test_format_bytes(value: int, expected: str) -> None:
    assert format_bytes(value) == expected


@pytest.mark.parametrize(
    ("seconds", "expected"),
    (
        (0, "<1m"),
        (59, "<1m"),
        (60, "1m"),
        (3600, "1h"),
        (3660, "1h 1m"),
        (90000, "1d 1h"),
    ),
)
def test_format_duration(seconds: float, expected: str) -> None:
    assert format_duration(seconds) == expected


def test_format_usage_returns_unknown_for_zero_total() -> None:
    assert format_usage(0, 0) == "Unknown"


def test_format_usage_includes_percentage() -> None:
    assert format_usage(512, 1024) == "512.0 B / 1.0 KiB (50%)"


def test_get_system_info_returns_system_values() -> None:
    info = get_system_info()

    assert info.os_name
    assert info.kernel
    assert info.desktop
    assert info.architecture
    assert info.cpu_model
    assert info.cpu_threads > 0
    assert info.memory_total > 0
    assert info.disk_total > 0
    assert info.hostname
