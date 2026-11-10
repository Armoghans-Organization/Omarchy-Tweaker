"""Operating system and hardware information helpers."""

from __future__ import annotations

import os
import platform
import shutil
import socket

# Required to query hardware details without invoking a shell.
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path

OS_RELEASE_PATH = Path("/etc/os-release")
CPUINFO_PATH = Path("/proc/cpuinfo")
MEMINFO_PATH = Path("/proc/meminfo")
UPTIME_PATH = Path("/proc/uptime")


@dataclass(frozen=True)
class SystemInfo:
    """Operating system and hardware details for the current machine."""

    os_name: str
    kernel: str
    desktop: str
    architecture: str
    cpu_model: str
    cpu_threads: int
    gpu: str
    memory_total: int
    memory_used: int
    disk_total: int
    disk_used: int
    uptime_seconds: float
    hostname: str


def get_system_info() -> SystemInfo:
    """Collect operating system and hardware information.

    Returns:
        The current system information. Unavailable values use sensible
        fallbacks such as ``"Unknown"`` or zero.
    """
    memory_total, memory_used = _read_memory()
    disk_total, disk_used = _read_disk()

    return SystemInfo(
        os_name=_read_os_name(),
        kernel=platform.release() or "Unknown",
        desktop=_read_desktop(),
        architecture=platform.machine() or "Unknown",
        cpu_model=_read_cpu_model(),
        cpu_threads=os.cpu_count() or 0,
        gpu=_read_gpu(),
        memory_total=memory_total,
        memory_used=memory_used,
        disk_total=disk_total,
        disk_used=disk_used,
        uptime_seconds=_read_uptime(),
        hostname=socket.gethostname() or "Unknown",
    )


def format_bytes(value: int) -> str:
    """Format a byte count using binary units."""
    size = float(max(value, 0))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


def format_duration(seconds: float) -> str:
    """Format a duration in seconds as days, hours, and minutes."""
    total = int(max(seconds, 0))
    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    return " ".join(parts) or "<1m"


def format_usage(used: int, total: int) -> str:
    """Format used and total capacity with a percentage."""
    if total <= 0:
        return "Unknown"
    return f"{format_bytes(used)} / {format_bytes(total)} ({used / total:.0%})"


def _read_os_release(path: Path = OS_RELEASE_PATH) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    values: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def _read_os_name() -> str:
    values = _read_os_release()
    return values.get("PRETTY_NAME") or values.get("NAME") or platform.system() or "Unknown"


def _read_desktop() -> str:
    desktop = os.environ.get("XDG_CURRENT_DESKTOP")
    if desktop:
        return desktop.split(":", 1)[0].strip()

    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "Hyprland"

    session = os.environ.get("DESKTOP_SESSION")
    return session.strip() if session else "Unknown"


def _read_cpu_model() -> str:
    try:
        lines = CPUINFO_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return platform.processor() or "Unknown"

    for line in lines:
        if line.lower().startswith("model name"):
            return line.split(":", 1)[1].strip()
    for line in lines:
        if line.lower().startswith("hardware"):
            return line.split(":", 1)[1].strip()
    return platform.processor() or "Unknown"


def _read_memory() -> tuple[int, int]:
    try:
        lines = MEMINFO_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0, 0

    values: dict[str, int] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parts = value.split()
        if parts:
            values[key] = int(parts[0])

    total = values.get("MemTotal", 0) * 1024
    available = values.get("MemAvailable", values.get("MemFree", 0)) * 1024
    return total, max(total - available, 0)


def _read_disk() -> tuple[int, int]:
    try:
        usage = shutil.disk_usage("/")
    except OSError:
        return 0, 0
    return usage.total, usage.used


def _read_uptime() -> float:
    try:
        return float(UPTIME_PATH.read_text(encoding="utf-8").split()[0])
    except (OSError, IndexError, ValueError):
        return 0.0


def _read_gpu() -> str:
    lspci = shutil.which("lspci")
    if lspci is None:
        return "Unknown"

    try:
        result = subprocess.run(  # nosec B603
            [lspci],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "Unknown"

    for line in result.stdout.splitlines():
        if "VGA compatible controller" in line or "3D controller" in line:
            _, _, description = line.partition(": ")
            return description.split("(rev", 1)[0].strip() or "Unknown"
    return "Unknown"
