"""Welcome screen and system overview."""

from __future__ import annotations

from rich.text import Text

from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.system_info import (
    format_duration,
    format_usage,
    get_system_info,
)


def _system_text() -> Text:
    """Build the operating system and hardware summary."""
    info = get_system_info()
    rows = (
        ("OS", info.os_name),
        ("Kernel", info.kernel),
        ("Desktop", info.desktop),
        ("CPU", f"{info.cpu_model} · {info.cpu_threads} threads · {info.architecture}"),
        ("GPU", info.gpu),
        ("Memory", format_usage(info.memory_used, info.memory_total)),
        ("Disk", format_usage(info.disk_used, info.disk_total)),
        ("Uptime", format_duration(info.uptime_seconds)),
        ("Hostname", info.hostname),
    )
    label_width = max(len(label) for label, _ in rows)

    text = Text()
    for index, (label, value) in enumerate(rows):
        if index:
            text.append("\n")
        text.append(f"{label:<{label_width}}  ", style=ui.THEME.muted)
        text.append(value, style=ui.THEME.text)
    return text


def show_welcome() -> None:
    """Display the welcome message and system overview."""
    body = Text()
    body.append("Welcome to Omarchy Tweaker!\n", style=ui.THEME.primary)
    body.append("Your Omarchy desktop, under your control.", style=ui.THEME.text)

    ui.panel(
        body,
        title="Welcome",
        subtitle="Your control center",
        icon=ui.ICONS.sparkles,
    )
    ui.panel(
        _system_text(),
        title="System",
        subtitle="Operating system and hardware",
        icon=ui.ICONS.linux,
    )
    ui.info("Run omarchy-tweaker --help to explore commands.")
