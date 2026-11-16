"""Create the required Docker containers for Omarchy Tweaker.

Each container lives in its own directory below ``containers/``. A container
directory contains a ``docker-compose.yml``, a ``.env.example`` template, an
optional ``Caddyfile``, optional configuration files, and an optional
``container.toml`` manifest.

The manifest has three optional sections::

    [container]
    name = "Atuin AI Server"
    description = "AI chat server with an OpenAI-compatible API."
    directories = ["data"]

    [symlinks]
    "config.toml" = "~/.config/atuin-ai-server/config.toml"

    [env]
    generate = ["AUTH_TOKEN"]

``[symlinks]`` maps a file inside the container directory to a host path. The
host path becomes a symlink to the container file, so edits on the host are
visible to the container without copying. ``[env]`` lists environment
variables that should offer an automatically generated secret.

Container files are prepared below ``~/Projects/Containers/<container>``.
Docker Compose runs from that directory. Caddy receives one managed snippet
per container plus a global snippet from the catalog-level ``Caddyfile``, and a
managed block in the host Caddyfile imports them.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess  # nosec B404
import time
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Final

from rich.progress import Progress, TaskID

from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.logger import get_session

CONTAINERS_DIRECTORY_ENV_VAR: Final = "OMARCHY_TWEAKER_CONTAINERS_DIR"
CONTAINERS_ROOT_ENV_VAR: Final = "OMARCHY_TWEAKER_CONTAINERS_ROOT"
CADDY_CONFIG_ENV_VAR: Final = "OMARCHY_TWEAKER_CADDY_CONFIG"
CADDY_DIRECTORY_ENV_VAR: Final = "OMARCHY_TWEAKER_CADDY_DIR"
CADDY_DEFAULT_CONFIG_PATH: Final = Path("/etc/caddy/Caddyfile")
CADDY_DEFAULT_DIRECTORY: Final = Path("/etc/caddy/omarchy-tweaker")
COMPOSE_FILE_NAME: Final = "docker-compose.yml"
ENV_EXAMPLE_FILE_NAME: Final = ".env.example"
ENV_FILE_NAME: Final = ".env"
MANIFEST_FILE_NAME: Final = "container.toml"
CADDYFILE_NAME: Final = "Caddyfile"
GLOBAL_CADDYFILE_SNIPPET_NAME: Final = "global.caddy"
AGENTS_COMPOSE_FILE_NAME: Final = "compose.agents.yaml"
AGENTS_DISCOVER_SCRIPT_NAME: Final = "discover.sh"

OMNIROUTE_SLUG: Final = "omniroute"
OMNIROUTE_NPM_PACKAGE: Final = "omniroute"
OMNIROUTE_BASE_URL_ENV: Final = "OMNIROUTE_BASE_URL"
OMNIROUTE_CLI_API_KEY_ENV: Final = "OMNIROUTE_API_KEY"
OMNIROUTE_REQUIRE_API_KEY_ENV: Final = "REQUIRE_API_KEY"
OMNIROUTE_CONTAINER_NAME: Final = "omniroute"
HOST_NODE_BIN_ENV_VAR: Final = "HOST_NODE_BIN"
BOOTSTRAP_TOKEN_MIN_LENGTH: Final = 16
BOOTSTRAP_TOKEN_CHARS: Final = re.compile(r"[A-Za-z0-9_-]+")
ZSH_PROFILE_NAME: Final = ".zshrc"
OMNIROUTE_RC_BEGIN: Final = "# >>> omarchy-tweaker omniroute >>>"
OMNIROUTE_RC_END: Final = "# <<< omarchy-tweaker omniroute <<<"

COMPOSE_TIMEOUT_SECONDS: Final = 900.0
COMPOSE_CONFIG_TIMEOUT_SECONDS: Final = 60.0
SUDO_TIMEOUT_SECONDS: Final = 120.0
CADDY_TIMEOUT_SECONDS: Final = 60.0
NPM_INSTALL_TIMEOUT_SECONDS: Final = 600.0
DISCOVER_TIMEOUT_SECONDS: Final = 60.0
DOCKER_LOG_TIMEOUT_SECONDS: Final = 30.0
BOOTSTRAP_TOKEN_TIMEOUT_SECONDS: Final = 300.0
BOOTSTRAP_TOKEN_POLL_INTERVAL_SECONDS: Final = 2.0
BACKUP_TIMESTAMP_FORMAT: Final = "%Y%m%d%H%M%S"

CONTAINER_NAME_PATTERN: Final = re.compile(
    r"^\s*container_name:\s*[\"']?([A-Za-z0-9][A-Za-z0-9_.-]*)"
)
COMPOSE_PROJECT_NAME_PATTERN: Final = re.compile(r"^name:\s*[\"']?([A-Za-z0-9][A-Za-z0-9_.-]*)")

CADDY_INCLUDE_BEGIN: Final = "# BEGIN omarchy-tweaker"
CADDY_INCLUDE_END: Final = "# END omarchy-tweaker"
SECRET_KEY_MARKERS: Final = ("TOKEN", "SECRET", "PASSWORD")
PLACEHOLDER_MARKERS: Final = ("replace", "changeme", "your_")
ENV_REFERENCE_PATTERN: Final = re.compile(
    r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))"
)
PREFERRED_CONTAINERS_ROOT: Final = Path("Projects") / "Containers"


class ContainerResult(StrEnum):
    """Outcome of the container creation step."""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class EnvVariable:
    """One variable declared in a container's ``.env.example``."""

    key: str
    default: str


@dataclass(frozen=True)
class ContainerSpec:
    """A discoverable container definition."""

    name: str
    slug: str
    directory: Path
    description: str
    directories: tuple[str, ...] = ()
    symlinks: tuple[tuple[str, str], ...] = ()
    generated_env: tuple[str, ...] = ()

    @property
    def compose_file(self) -> Path:
        """Return the compose file path."""
        return self.directory / COMPOSE_FILE_NAME

    @property
    def env_example_file(self) -> Path:
        """Return the environment template path."""
        return self.directory / ENV_EXAMPLE_FILE_NAME

    @property
    def caddyfile(self) -> Path:
        """Return the container Caddyfile path."""
        return self.directory / CADDYFILE_NAME

    @property
    def snippet_path(self) -> Path:
        """Return the managed Caddy snippet path for this container."""
        return get_managed_caddy_directory() / f"{self.slug}.caddy"


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


def get_containers_directory() -> Path:
    """Return the bundled container catalog directory."""
    override = os.environ.get(CONTAINERS_DIRECTORY_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[1] / "containers"


def get_containers_root(home: Path | None = None) -> Path:
    """Return the directory where containers are prepared on the host."""
    override = os.environ.get(CONTAINERS_ROOT_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return (home if home is not None else Path.home()) / PREFERRED_CONTAINERS_ROOT


def get_caddy_config_path() -> Path:
    """Return the host Caddyfile path."""
    override = os.environ.get(CADDY_CONFIG_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return CADDY_DEFAULT_CONFIG_PATH


def get_managed_caddy_directory() -> Path:
    """Return the system directory containing managed Caddy snippets."""
    override = os.environ.get(CADDY_DIRECTORY_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return CADDY_DEFAULT_DIRECTORY


def get_global_caddyfile() -> Path:
    """Return the catalog-level global Caddyfile path."""
    return get_containers_directory() / CADDYFILE_NAME


def _snippet_name(path: Path) -> str:
    """Return the import token Caddy uses for a snippet path."""
    return json.dumps(str(path))


def _existing_snippet_paths(config_path: Path) -> tuple[str, ...]:
    """Return import tokens already present in the host Caddyfile's managed block."""
    try:
        existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    except (OSError, UnicodeError):
        return ()
    start = existing.find(CADDY_INCLUDE_BEGIN)
    if start == -1:
        return ()
    end = existing.find(CADDY_INCLUDE_END, start)
    if end == -1:
        return ()
    block = existing[start:end]
    imports: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("import "):
            continue
        token = stripped[len("import ") :].strip()
        if token:
            imports.append(token)
    return tuple(imports)


def _display_name(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.replace("_", "-").split("-") if part)


def _manifest_text(section: Mapping[str, object], key: str) -> str | None:
    value = section.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"manifest value {key!r} must be a string")
    return value.strip() or None


def _load_symlinks(raw: object, directory: Path) -> tuple[tuple[str, str], ...]:
    if raw is None:
        return ()
    if not isinstance(raw, dict):
        raise ValueError("the symlinks section must be a table")

    links: list[tuple[str, str]] = []
    for source, destination in raw.items():
        if not isinstance(source, str) or not isinstance(destination, str):
            raise ValueError("symlink entries must map strings to strings")
        if Path(source).name != source or source in {"", ".", ".."}:
            raise ValueError(f"symlink source must be a file name: {source!r}")
        if not (directory / source).is_file():
            raise ValueError(f"symlink source does not exist: {source!r}")
        if not destination.strip():
            raise ValueError(f"symlink destination is empty for {source!r}")
        links.append((source, destination.strip()))
    return tuple(links)


def _load_directories(raw: object) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(isinstance(value, str) for value in raw):
        raise ValueError("container.directories must be a list of strings")

    directories: list[str] = []
    for value in raw:
        name = value.strip()
        if not name:
            continue
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("container.directories entries must be relative paths")
        directories.append(name)
    return tuple(directories)


def _load_generated_env(raw: object) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, dict):
        raise ValueError("the env section must be a table")

    values = raw.get("generate", [])
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError("env.generate must be a list of strings")
    return tuple(value.strip() for value in values if value.strip())


def _load_container_spec(directory: Path) -> ContainerSpec:
    name = _display_name(directory.name) or directory.name
    description = ""
    directories: tuple[str, ...] = ()
    symlinks: tuple[tuple[str, str], ...] = ()
    generated_env: tuple[str, ...] = ()

    manifest = directory / MANIFEST_FILE_NAME
    if manifest.is_file():
        raw = tomllib.loads(manifest.read_text(encoding="utf-8"))
        container_section = raw.get("container")
        if container_section is not None and not isinstance(container_section, dict):
            raise ValueError("the container section must be a table")
        if isinstance(container_section, dict):
            name = _manifest_text(container_section, "name") or name
            description = _manifest_text(container_section, "description") or description
            directories = _load_directories(container_section.get("directories"))
        symlinks = _load_symlinks(raw.get("symlinks"), directory)
        generated_env = _load_generated_env(raw.get("env"))

    return ContainerSpec(
        name=name,
        slug=directory.name,
        directory=directory,
        description=description,
        directories=directories,
        symlinks=symlinks,
        generated_env=generated_env,
    )


def load_container_specs(directory: Path | None = None) -> tuple[ContainerSpec, ...]:
    """Load container definitions from the catalog.

    Args:
        directory: Optional catalog override, primarily for tests.

    Returns:
        Container definitions in directory-name order.

    Raises:
        OSError: If the catalog directory cannot be read.
    """
    base = directory if directory is not None else get_containers_directory()
    if not base.is_dir():
        _log_error("Container catalog directory was not found: %s", base)
        return ()

    specs: list[ContainerSpec] = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if not (entry / COMPOSE_FILE_NAME).is_file():
            _log_warning("Skipping container without a compose file: %s", entry)
            continue
        try:
            specs.append(_load_container_spec(entry))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError, ValueError) as exc:
            _log_error("Could not load container %s: %s", entry.name, exc)
    return tuple(specs)


def _parse_env_variables(content: str) -> tuple[EnvVariable, ...]:
    """Parse environment variable declarations from template text."""
    variables: list[EnvVariable] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()
        if key:
            variables.append(EnvVariable(key=key, default=value.strip()))
    return tuple(variables)


def load_env_template(path: Path) -> tuple[EnvVariable, ...]:
    """Read environment variables from a ``.env.example`` file."""
    return _parse_env_variables(path.read_text(encoding="utf-8"))


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().casefold()
    if not normalized:
        return True
    return any(marker in normalized for marker in PLACEHOLDER_MARKERS)


def _looks_secret(key: str) -> bool:
    normalized = key.upper()
    return any(marker in normalized for marker in SECRET_KEY_MARKERS)


def _detect_host_node_bin() -> str | None:
    """Return the host Node binary directory used for the container mount.

    The path is discovered at runtime so the catalog never hardcodes a
    machine-specific location. An explicit ``HOST_NODE_BIN`` environment
    variable takes precedence.
    """
    override = os.environ.get(HOST_NODE_BIN_ENV_VAR)
    if override and override.strip():
        return override.strip()

    node = shutil.which("node")
    if node is not None:
        return str(Path(node).resolve().parent)

    mise = shutil.which("mise")
    if mise is not None:
        result = _run_process([mise, "which", "node"], timeout=DISCOVER_TIMEOUT_SECONDS)
        if result is not None and result.returncode == 0:
            located = result.stdout.strip()
            if located:
                return str(Path(located).parent)
    return None


def _auto_detect_env_default(key: str) -> str | None:
    """Return a runtime-detected default for a host-path environment variable."""
    if key == HOST_NODE_BIN_ENV_VAR:
        return _detect_host_node_bin()
    return None


def _read_env_value(env_path: Path, key: str) -> str | None:
    """Read a single variable value from a rendered .env file."""
    try:
        content = env_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _log_warning("Could not read %s: %s", env_path, exc)
        return None
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, _, value = stripped.partition("=")
        if name.strip() == key:
            return value.strip()
    return None


def _installed_npm_version() -> str | None:
    """Return the globally installed OmniRoute CLI version, or ``None``."""
    npm = shutil.which("npm")
    if npm is None:
        return None
    result = _run_process(
        [npm, "ls", "-g", OMNIROUTE_NPM_PACKAGE, "--depth=0"],
        timeout=NPM_INSTALL_TIMEOUT_SECONDS,
    )
    if result is None:
        return None
    for line in result.stdout.splitlines():
        if "omniroute@" in line:
            return line.split("omniroute@", 1)[1].strip()
    return None


def _npm_package_outdated(package: str) -> bool:
    """Return whether a globally installed npm package has a newer release."""
    npm = shutil.which("npm")
    if npm is None:
        return False
    result = _run_process(
        [npm, "outdated", "-g", package],
        timeout=DISCOVER_TIMEOUT_SECONDS,
    )
    return result is not None and result.returncode == 1


def _npm_install_global(package: str) -> bool:
    npm = shutil.which("npm")
    if npm is None:
        _log_error("npm was not found; cannot install %s.", package)
        ui.error("npm was not found on PATH. Install Node.js first.")
        return False

    result = _run_process(
        [npm, "install", "-g", package],
        timeout=NPM_INSTALL_TIMEOUT_SECONDS,
    )
    if result is None or result.returncode != 0:
        detail = ""
        if result is not None and result.stderr.strip():
            detail = result.stderr.strip().splitlines()[-1]
        _log_error("Could not install %s globally. %s", package, detail)
        ui.error(f"Could not install {package}: {detail or 'npm failed'}.")
        return False
    return True


def ensure_omniroute_cli() -> bool:
    """Install the OmniRoute CLI globally when it is missing or outdated.

    Returns:
        ``True`` when the CLI is available, otherwise ``False``.
    """
    installed = _installed_npm_version()
    if installed is not None:
        _log_info("OmniRoute CLI is installed (%s).", installed)
        ui.info(f"OmniRoute CLI is installed (v{installed}).")
        if not _npm_package_outdated(OMNIROUTE_NPM_PACKAGE):
            return True
        if not ui.confirm(
            "A newer OmniRoute CLI is available. Update it now?",
            default=True,
            instruction="Runs npm install -g omniroute on the host.",
        ):
            _log_warning("OmniRoute CLI update was declined.")
            ui.warning("OmniRoute CLI update was declined.")
            return True
    elif not ui.confirm(
        "The OmniRoute CLI is not installed. Install it globally with npm?",
        default=True,
        instruction="Runs npm install -g omniroute on the host.",
    ):
        _log_warning("OmniRoute CLI installation was declined.")
        ui.warning("OmniRoute CLI installation was declined.")
        return False

    if not _npm_install_global(OMNIROUTE_NPM_PACKAGE):
        return False

    _log_info("Installed the OmniRoute CLI with npm.")
    ui.success("Installed the OmniRoute CLI with npm.")
    return True


def discover_agent_mounts(runtime_directory: Path) -> tuple[str, ...] | None:
    """Run discover.sh to find installed agent configuration directories.

    Args:
        runtime_directory: The prepared container directory containing discover.sh.

    Returns:
        The discovered agent mount lines (possibly empty), or ``None`` when
        discovery could not be performed.
    """
    script = runtime_directory / AGENTS_DISCOVER_SCRIPT_NAME
    if not script.is_file():
        _log_error("discover.sh was not found in %s.", runtime_directory)
        ui.error(f"OmniRoute: discover.sh was not found in {runtime_directory}.")
        return None

    result = _run_process(
        ["bash", str(script)],
        timeout=DISCOVER_TIMEOUT_SECONDS,
        cwd=runtime_directory,
    )
    if result is None or result.returncode != 0:
        detail = ""
        if result is not None and result.stderr.strip():
            detail = result.stderr.strip().splitlines()[-1]
        _log_error("discover.sh failed for OmniRoute. %s", detail)
        ui.error(f"OmniRoute: agent discovery failed: {detail or 'discover.sh failed'}.")
        return None

    output = runtime_directory / AGENTS_COMPOSE_FILE_NAME
    try:
        content = output.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _log_error("Could not read %s: %s", output, exc)
        ui.error(f"OmniRoute: could not read {output.name}: {exc}")
        return None

    mounts = tuple(line.strip() for line in content.splitlines() if line.strip().startswith("- "))
    if not mounts:
        _log_warning("discover.sh found no agent configuration directories.")
        ui.warning("OmniRoute: no installed agents were found to mount.")
        return ()

    _log_info("discover.sh wrote %d agent mount(s) to %s.", len(mounts), output)
    ui.success(f"OmniRoute: discovered {len(mounts)} agent configuration(s).")
    return mounts


def _shell_profile_block(lines: Sequence[str]) -> str:
    """Build the managed shell-profile block for the OmniRoute exports."""
    return "\n".join((OMNIROUTE_RC_BEGIN, *lines, OMNIROUTE_RC_END))


def _existing_export(block: str, key: str) -> str | None:
    """Return an active ``export KEY=...`` line from a managed block."""
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"export {key}=") and not stripped.startswith("#"):
            return stripped
    return None


def _update_shell_profile(profile_path: Path, lines: Sequence[str]) -> bool:
    """Write the OmniRoute exports into a managed shell-profile block.

    An existing managed block is replaced while preserving a key the user filled
    in. A timestamped backup is written before the profile is modified.

    Args:
        profile_path: Shell profile to update, typically ``~/.zshrc``.
        lines: Export lines to place inside the managed block.

    Returns:
        ``True`` when the profile was updated, otherwise ``False``.
    """
    try:
        existing = profile_path.read_text(encoding="utf-8") if profile_path.is_file() else ""
    except (OSError, UnicodeError) as exc:
        _log_warning("Could not read %s: %s", profile_path, exc)
        ui.warning(f"Could not read {profile_path}: {exc}")
        return False

    managed = lines
    if OMNIROUTE_RC_BEGIN in existing and OMNIROUTE_RC_END in existing:
        start = existing.index(OMNIROUTE_RC_BEGIN)
        end = existing.index(OMNIROUTE_RC_END, start) + len(OMNIROUTE_RC_END)
        preserved = _existing_export(existing[start:end], OMNIROUTE_CLI_API_KEY_ENV)
        if preserved is not None:
            managed = [line for line in lines if OMNIROUTE_CLI_API_KEY_ENV not in line]
            managed = [*managed, preserved]
        block = _shell_profile_block(managed)
        updated = f"{existing[:start]}{block}{existing[end:]}"
    else:
        block = _shell_profile_block(managed)
        prefix = existing
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        if prefix and not prefix.endswith("\n\n"):
            prefix += "\n"
        updated = f"{prefix}{block}\n"

    if not profile_path.is_file():
        try:
            profile_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            _log_warning("Could not create %s: %s", profile_path.parent, exc)
            ui.warning(f"Could not create {profile_path.parent}: {exc}")
            return False

    if profile_path.is_file() and updated != existing:
        backup = profile_path.with_name(
            f"{profile_path.name}.{time.strftime(BACKUP_TIMESTAMP_FORMAT)}.bak"
        )
        try:
            shutil.copy2(profile_path, backup)
        except OSError as exc:
            _log_warning("Could not back up %s: %s", profile_path, exc)

    try:
        profile_path.write_text(updated, encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _log_error("Could not update %s: %s", profile_path, exc)
        ui.error(f"Could not update {profile_path}: {exc}")
        return False

    return True


def _print_connection_instructions(profile_path: Path, lines: Sequence[str]) -> None:
    """Print the export lines so the user can add them manually."""
    ui.info(f"Add these lines to {profile_path}:")
    console = ui.get_console()
    if console is not None:
        for line in lines:
            console.print(f"  {line}", style=ui.THEME.info)


def connect_omniroute_cli(
    runtime_directory: Path,
    *,
    profile_path: Path | None = None,
) -> bool:
    """Connect the host CLI to the OmniRoute container.

    Prints the export lines, then offers to persist them in ``~/.zshrc``. When
    the update is declined or the session is non-interactive, the lines are
    printed for manual entry.

    Args:
        runtime_directory: The prepared container directory containing .env.
        profile_path: Shell profile to update; defaults to ``~/.zshrc``.

    Returns:
        ``True`` when the connection details were produced, otherwise ``False``.
    """
    env_path = runtime_directory / ENV_FILE_NAME
    if not env_path.is_file():
        _log_error("No environment file exists for OmniRoute at %s.", env_path)
        ui.error(f"OmniRoute: no .env file found at {env_path}.")
        return False

    base_url = _read_env_value(env_path, "BASE_URL")
    if not base_url:
        port = _read_env_value(env_path, "API_PORT") or "6905"
        base_url = f"http://127.0.0.1:{port}"

    require_api_key = (
        _read_env_value(env_path, OMNIROUTE_REQUIRE_API_KEY_ENV) or ""
    ).strip().casefold() == "true"
    existing_key = os.environ.get(OMNIROUTE_CLI_API_KEY_ENV)

    ui.section(
        "OmniRoute CLI Connection",
        subtitle="Point the host CLI at the container API.",
        icon=ui.ICONS.chevron,
    )
    ui.info(f"OmniRoute API: {base_url}")

    lines = [f"export {OMNIROUTE_BASE_URL_ENV}={base_url}"]
    if require_api_key and not existing_key:
        lines.append("# Create an API key in the dashboard, then uncomment and set it:")
        lines.append(f'# export {OMNIROUTE_CLI_API_KEY_ENV}="<dashboard-api-key>"')

    console = ui.get_console()
    if console is not None:
        for line in lines:
            console.print(line, style=ui.THEME.info)

    target_profile = profile_path if profile_path is not None else Path.home() / ZSH_PROFILE_NAME
    if ui.is_interactive() and ui.confirm(
        f"Add these exports to {target_profile}?",
        default=True,
        instruction="Adds a managed block to your shell profile.",
    ):
        if _update_shell_profile(target_profile, lines):
            _log_info("Updated the OmniRoute exports in %s.", target_profile)
            ui.success(
                f'Updated {target_profile}. Restart your shell or run "source {target_profile}".'
            )
        else:
            _print_connection_instructions(target_profile, lines)
    else:
        _print_connection_instructions(target_profile, lines)

    _log_info("OmniRoute CLI connection details were printed for %s.", base_url)
    return True


def _docker_log_text(container_name: str, *, since: str | None = None) -> str:
    """Return the combined stdout/stderr logs for a container."""
    docker = shutil.which("docker")
    if docker is None:
        return ""

    command = [docker, "logs"]
    if since is not None:
        command.extend(["--since", since])
    command.append(container_name)

    result = _run_process(command, timeout=DOCKER_LOG_TIMEOUT_SECONDS)
    if result is None:
        return ""
    return f"{result.stdout}\n{result.stderr}"


def _find_bootstrap_token(log_text: str) -> str | None:
    """Extract the one-time OmniRoute bootstrap token from container logs.

    Only ``[BOOTSTRAP]`` lines that mention the one-time token are considered,
    and the token is taken from the final word of the line. This avoids matching
    unrelated bootstrap messages such as ``INITIAL_PASSWORD``.
    """
    for line in reversed(log_text.splitlines()):
        if "[BOOTSTRAP]" not in line.upper() or "TOKEN" not in line.upper():
            continue
        for candidate in reversed(line.split()):
            cleaned = candidate.strip("\"'[](){}.,;:")
            if (
                len(cleaned) >= BOOTSTRAP_TOKEN_MIN_LENGTH
                and BOOTSTRAP_TOKEN_CHARS.fullmatch(cleaned) is not None
            ):
                return cleaned
    return None


def _onboarding_url(runtime_directory: Path) -> str:
    """Return the dashboard onboarding URL for the OmniRoute container."""
    env_path = runtime_directory / ENV_FILE_NAME
    base_url = _read_env_value(env_path, "NEXT_PUBLIC_BASE_URL") if env_path.is_file() else None
    if not base_url:
        port = _read_env_value(env_path, "DASHBOARD_PORT") if env_path.is_file() else None
        base_url = f"http://127.0.0.1:{port or '6904'}"
    return f"{base_url.rstrip('/')}/dashboard/onboarding"


def _print_log_hint(container_name: str) -> None:
    """Tell the user how to read the bootstrap token from the logs."""
    ui.info(f"Get the token later with: docker logs {container_name} | grep BOOTSTRAP")


def _wait_for_bootstrap_token(
    container_name: str,
    *,
    since: str,
    timeout: float,
) -> str | None:
    """Poll container logs until the bootstrap token appears or time runs out."""
    deadline = time.monotonic() + timeout
    try:
        with ui.spinner("Waiting for the OmniRoute bootstrap token...") as status:
            while True:
                token = _find_bootstrap_token(_docker_log_text(container_name, since=since))
                if token is not None:
                    return token
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                status.update(
                    f"Waiting for the OmniRoute bootstrap token ({remaining:.0f}s remaining)..."
                )
                time.sleep(min(BOOTSTRAP_TOKEN_POLL_INTERVAL_SECONDS, remaining))
    except KeyboardInterrupt:
        ui.warning("Stopped waiting for the bootstrap token.")
        return None


def show_bootstrap_token(
    runtime_directory: Path,
    *,
    container_name: str = OMNIROUTE_CONTAINER_NAME,
) -> str | None:
    """Show the one-time OmniRoute bootstrap token from the container logs.

    The token is only logged after the onboarding wizard is opened, so an
    interactive session is offered the chance to wait for it. Non-interactive
    sessions and declined prompts receive the log command instead.

    Args:
        runtime_directory: The prepared container directory containing .env.
        container_name: Docker container name to read logs from.

    Returns:
        The bootstrap token when found, otherwise ``None``.
    """
    onboarding_url = _onboarding_url(runtime_directory)
    ui.section(
        "OmniRoute Bootstrap Token",
        subtitle="One-time token required by the onboarding wizard.",
        icon=ui.ICONS.tag,
    )
    ui.info(f"Onboarding wizard: {onboarding_url}")

    since = datetime.now(UTC).isoformat(timespec="seconds")
    token = _find_bootstrap_token(_docker_log_text(container_name, since=since))
    if token is None:
        ui.info(
            "The token is logged after onboarding starts. Open the URL above, "
            "begin the wizard, and keep this running."
        )
        _print_log_hint(container_name)

    if token is not None:
        ui.panel(token, title="One-time bootstrap token", icon=ui.ICONS.tag)
        _log_info("OmniRoute bootstrap token was found in the container logs.")
        return token

    if not ui.is_interactive() or not ui.confirm(
        "Wait for the onboarding bootstrap token now?",
        default=True,
        instruction="Open the onboarding page and start the wizard.",
    ):
        return None

    token = _wait_for_bootstrap_token(
        container_name,
        since=since,
        timeout=BOOTSTRAP_TOKEN_TIMEOUT_SECONDS,
    )
    if token is None:
        ui.warning("The bootstrap token did not appear in the container logs.")
        _print_log_hint(container_name)
        return None

    ui.panel(token, title="One-time bootstrap token", icon=ui.ICONS.tag)
    _log_info("OmniRoute bootstrap token was found in the container logs.")
    return token


def _unresolved_env_references(env_path: Path) -> tuple[str, ...]:
    try:
        content = env_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _log_warning("Could not inspect the existing .env file: %s", exc)
        return ()

    defined = set(os.environ)
    values: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()
        if key:
            defined.add(key)
        values.append(value)

    unresolved: set[str] = set()
    for value in values:
        for match in ENV_REFERENCE_PATTERN.finditer(value):
            name = match.group(1) or match.group(2)
            if name and name not in defined:
                unresolved.add(name)
    return tuple(sorted(unresolved))


def generate_secret() -> str:
    """Return a URL-safe random secret."""
    return secrets.token_urlsafe(48)


def _resolve_env_value(variable: EnvVariable, *, generate: bool) -> str | None:
    if generate and ui.confirm(
        f"Generate a random value for {variable.key}?",
        default=True,
        instruction="The generated value is written only to the local .env file.",
    ):
        return generate_secret()

    default = "" if _is_placeholder(variable.default) else variable.default
    value = ui.prompt_text(
        f"Value for {variable.key}",
        default=default,
        instruction=(
            f"Current template value: {variable.default}"
            if variable.default
            else "This value is required."
        ),
    ).strip()
    if not value or _is_placeholder(value):
        return None
    return value


def _render_env(template: str, values: Mapping[str, str]) -> str:
    lines: list[str] = []
    for line in template.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            token = stripped.partition("=")[0].strip()
            exported = token.startswith("export ")
            key = token.removeprefix("export ").strip()
            if key in values:
                prefix = "export " if exported else ""
                lines.append(f"{prefix}{key}={values[key]}")
                continue
        lines.append(line)
    return "\n".join(lines).rstrip("\n") + "\n"


def _backup_path(path: Path) -> Path | None:
    timestamp = time.strftime(BACKUP_TIMESTAMP_FORMAT)
    backup = path.with_name(f"{path.name}.bak.{timestamp}")
    if backup.exists():
        backup = path.with_name(f"{path.name}.bak.{timestamp}.{os.getpid()}")
    try:
        shutil.move(str(path), str(backup))
    except OSError as exc:
        _log_error("Could not back up %s: %s", path, exc)
        return None
    return backup


def _create_symlink(source: Path, destination: Path) -> bool:
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink():
            try:
                if destination.resolve() == source.resolve():
                    return True
            except OSError:
                pass
            destination.unlink()
        elif destination.exists():
            backup = _backup_path(destination)
            if backup is None:
                return False
            _log_info("Backed up %s to %s", destination, backup)
        os.symlink(source, destination)
    except OSError as exc:
        _log_error("Could not link %s to %s: %s", source, destination, exc)
        return False
    return True


def _install_compose_file(source: Path, destination: Path) -> bool:
    try:
        if destination.is_symlink():
            destination.unlink()
        if destination.exists():
            if destination.is_file() and destination.read_bytes() == source.read_bytes():
                return True
            backup = _backup_path(destination)
            if backup is None:
                return False
            _log_info("Backed up %s to %s", destination, backup)
        shutil.copy2(source, destination)
    except OSError as exc:
        _log_error("Could not install compose file %s: %s", destination, exc)
        return False
    return True


def _link_container_assets(spec: ContainerSpec, runtime_directory: Path) -> bool:
    skip_names = {
        COMPOSE_FILE_NAME,
        ENV_EXAMPLE_FILE_NAME,
        ENV_FILE_NAME,
        MANIFEST_FILE_NAME,
    }
    for source in sorted(spec.directory.iterdir()):
        if not source.is_file() or source.is_symlink() or source.name in skip_names:
            continue
        if not _create_symlink(source, runtime_directory / source.name):
            return False
    return True


def _create_env_file(spec: ContainerSpec, runtime_directory: Path) -> bool:
    example = spec.env_example_file
    if not example.is_file():
        _log_info("No environment template for %s.", spec.name)
        return True

    env_path = runtime_directory / ENV_FILE_NAME
    if env_path.exists():
        unresolved = _unresolved_env_references(env_path)
        if unresolved:
            names = ", ".join(unresolved)
            _log_error(
                "The existing .env file for %s references unset variables: %s",
                spec.name,
                names,
            )
            ui.error(
                f"{spec.name}: .env references unset variable(s): {names}. "
                "Define them in the environment or in .env before starting the container.",
            )
            return False
        _log_info("Keeping the existing environment file for %s.", spec.name)
        ui.info(f"{spec.name}: keeping the existing .env file.")
        return True

    try:
        template = example.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _log_error("Could not read environment template for %s: %s", spec.name, exc)
        ui.error(f"{spec.name}: could not read .env.example: {exc}")
        return False

    variables: list[EnvVariable] = []
    for variable in _parse_env_variables(template):
        default = variable.default or (_auto_detect_env_default(variable.key) or "")
        variables.append(EnvVariable(key=variable.key, default=default))

    values: dict[str, str] = {}
    for variable in variables:
        generate = variable.key in spec.generated_env or _looks_secret(variable.key)
        value = _resolve_env_value(variable, generate=generate)
        if value is None:
            _log_error("No usable value was provided for %s.", variable.key)
            ui.error(f"{spec.name}: a value is required for {variable.key}.")
            return False
        values[variable.key] = value

    try:
        env_path.write_text(_render_env(template, values), encoding="utf-8")
        env_path.chmod(0o600)
    except OSError as exc:
        _log_error("Could not write environment file for %s: %s", spec.name, exc)
        ui.error(f"{spec.name}: could not write .env: {exc}")
        return False

    _log_info("Created environment file for %s.", spec.name)
    ui.success(f"{spec.name}: created .env.")
    return True


def _host_path(value: str, home: Path) -> Path:
    if value == "~":
        return home
    if value.startswith("~/"):
        return home / value.removeprefix("~/")
    path = Path(value).expanduser()
    if not path.is_absolute():
        return home / path
    return path


def _apply_host_symlinks(
    spec: ContainerSpec,
    runtime_directory: Path,
    home: Path,
) -> bool:
    for source_name, destination_value in spec.symlinks:
        source = runtime_directory / source_name
        if not source.exists() and not source.is_symlink():
            _log_error("Symlink source was not prepared: %s", source)
            ui.error(f"{spec.name}: missing symlink source {source_name}.")
            return False
        destination = _host_path(destination_value, home)
        if not _create_symlink(source, destination):
            ui.error(f"{spec.name}: could not link {destination_value}.")
            return False
        _log_info("Linked %s to %s", source, destination)
        ui.success(f"{spec.name}: linked {destination_value}.")
    return True


def _directory_is_writable(path: Path) -> bool:
    return os.access(path, os.W_OK)


def _prepare_runtime_directories(
    spec: ContainerSpec,
    runtime_directory: Path,
) -> bool:
    for name in spec.directories:
        path = runtime_directory / name
        if path.exists():
            if not path.is_dir():
                _log_error("Runtime path for %s is not a directory: %s", spec.name, path)
                ui.error(f"{spec.name}: {path} exists but is not a directory.")
                return False
            if _directory_is_writable(path):
                continue

            owner = f"{os.getuid()}:{os.getgid()}"
            command = ["sudo", "chown", "-R", owner, str(path)]
            _log_warning("Runtime directory for %s is not writable: %s", spec.name, path)
            ui.warning(f"{spec.name}: {path} is not writable by the current user.")
            ui.info(f"Fix with: {' '.join(command)}")
            if not ui.is_interactive() or not ui.confirm(
                f"Fix ownership of {path} now?",
                default=True,
                instruction="Runs sudo chown -R on the container runtime directory.",
            ):
                _log_error("Runtime directory ownership was not fixed for %s.", spec.name)
                return False

            result = _run_process(command, timeout=SUDO_TIMEOUT_SECONDS)
            if result is None or result.returncode != 0:
                _log_error("Could not change ownership of %s.", path)
                ui.error(f"{spec.name}: could not change ownership of {path}.")
                return False
            _log_info("Changed ownership of %s to %s.", path, owner)
            ui.success(f"{spec.name}: fixed ownership of {path}.")
            continue

        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            _log_error("Could not create runtime directory %s: %s", path, exc)
            ui.error(f"{spec.name}: could not create {path}: {exc}")
            return False
        _log_info("Created runtime directory %s.", path)
    return True


def prepare_container(
    spec: ContainerSpec,
    *,
    home: Path,
    containers_root: Path,
) -> bool:
    """Prepare one container's runtime directory without starting it.

    Args:
        spec: Container definition to prepare.
        home: Home directory used for host symlink expansion.
        containers_root: Directory that holds prepared containers.

    Returns:
        ``True`` when every required file was prepared.
    """
    runtime_directory = containers_root / spec.slug
    try:
        runtime_directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _log_error("Could not create container directory %s: %s", runtime_directory, exc)
        ui.error(f"{spec.name}: could not create {runtime_directory}: {exc}")
        return False

    if not _install_compose_file(
        spec.compose_file,
        runtime_directory / COMPOSE_FILE_NAME,
    ):
        ui.error(f"{spec.name}: could not install the compose file.")
        return False

    if not _link_container_assets(spec, runtime_directory):
        ui.error(f"{spec.name}: could not link container files.")
        return False

    if not _prepare_runtime_directories(spec, runtime_directory):
        ui.error(f"{spec.name}: could not prepare runtime directories.")
        return False

    if not _create_env_file(spec, runtime_directory):
        return False

    if not _apply_host_symlinks(spec, runtime_directory, home):
        return False

    _log_info("Prepared container %s in %s.", spec.name, runtime_directory)
    ui.success(f"{spec.name}: prepared in {runtime_directory}.")
    return True


def install_caddy_snippet(
    spec: ContainerSpec,
    *,
    caddy_directory: Path | None = None,
) -> Path | None:
    """Copy a container Caddyfile into the managed Caddy snippet directory."""
    if not spec.caddyfile.is_file():
        _log_warning("No Caddyfile configured for %s.", spec.name)
        return None

    directory = caddy_directory if caddy_directory is not None else get_managed_caddy_directory()
    if not _ensure_system_directory(directory):
        return None

    try:
        content = spec.caddyfile.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _log_error("Could not read the Caddyfile for %s: %s", spec.name, exc)
        return None

    snippet_path = directory / f"{spec.slug}.caddy"
    if not _write_system_file(snippet_path, content):
        return None
    return snippet_path


def install_global_caddy_snippet(
    *,
    caddy_directory: Path | None = None,
    global_caddyfile: Path | None = None,
) -> Path | None:
    """Copy the catalog-level global Caddyfile into the managed snippet directory.

    Returns:
        The snippet path when the global Caddyfile exists, otherwise ``None``.
    """
    source = global_caddyfile if global_caddyfile is not None else get_global_caddyfile()
    if not source.is_file():
        _log_info("No global Caddyfile configured.")
        return None

    directory = caddy_directory if caddy_directory is not None else get_managed_caddy_directory()
    if not _ensure_system_directory(directory):
        return None

    try:
        content = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _log_error("Could not read the global Caddyfile: %s", exc)
        return None

    snippet_path = directory / GLOBAL_CADDYFILE_SNIPPET_NAME
    if not _write_system_file(snippet_path, content):
        return None
    return snippet_path


def _render_import_block(snippets: Sequence[Path]) -> str:
    lines = [
        CADDY_INCLUDE_BEGIN,
        "# Managed by Omarchy Tweaker. Do not edit this block by hand.",
    ]
    lines.extend(f"import {json.dumps(str(snippet))}" for snippet in snippets)
    lines.append(CADDY_INCLUDE_END)
    return "\n".join(lines)


def _replace_managed_block(existing: str, block: str) -> str:
    start = existing.find(CADDY_INCLUDE_BEGIN)
    if start != -1:
        end = existing.find(CADDY_INCLUDE_END, start)
        if end != -1:
            prefix = existing[:start].rstrip("\n")
            suffix = existing[end + len(CADDY_INCLUDE_END) :].lstrip("\n")
            parts = [part for part in (prefix, block, suffix) if part]
            return "\n\n".join(parts) + "\n"
        prefix = existing[:start].rstrip("\n")
        return f"{prefix}\n\n{block}\n" if prefix else f"{block}\n"

    if not existing.strip():
        return f"{block}\n"
    return existing.rstrip("\n") + "\n\n" + block + "\n"


def _run_process(
    command: Sequence[str],
    *,
    timeout: float,
    input_text: str | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(  # nosec B603
            list(command),
            check=False,
            capture_output=True,
            text=True,
            input=input_text,
            timeout=timeout,
            cwd=cwd,
        )
    except FileNotFoundError:
        _log_error("Command was not found: %s", command[0])
    except subprocess.TimeoutExpired:
        _log_error("Command timed out after %s seconds: %s", timeout, command[0])
    except OSError as exc:
        _log_error("Could not run command %s: %s", command[0], exc)
    return None


def _is_writable(path: Path) -> bool:
    if path.exists():
        return os.access(path, os.W_OK)
    return path.parent.is_dir() and os.access(path.parent, os.W_OK)


def _validate_caddy_config(content: str) -> bool:
    caddy = shutil.which("caddy")
    if caddy is None:
        _log_warning("Caddy was not found; skipping Caddyfile validation.")
        return True

    temporary_path: Path | None = None
    result: subprocess.CompletedProcess[str] | None = None
    try:
        with NamedTemporaryFile(
            "w",
            suffix=".caddy",
            encoding="utf-8",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        result = _run_process(
            [caddy, "adapt", "--config", str(temporary_path)],
            timeout=CADDY_TIMEOUT_SECONDS,
        )
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    if result is None or result.returncode != 0:
        detail = ""
        if result is not None and result.stderr.strip():
            detail = result.stderr.strip().splitlines()[-1]
        _log_error("The generated Caddy configuration is invalid. %s", detail)
        return False
    return True


def _backup_system_file(path: Path) -> bool:
    timestamp = time.strftime(BACKUP_TIMESTAMP_FORMAT)
    backup = path.with_name(f"{path.name}.bak.{timestamp}")
    if _is_writable(path.parent):
        try:
            shutil.copy2(path, backup)
        except OSError as exc:
            _log_error("Could not back up %s: %s", path, exc)
            return False
        return True

    sudo = shutil.which("sudo")
    if sudo is None:
        _log_error("sudo was not found; cannot back up %s.", path)
        return False
    result = _run_process(
        [sudo, "cp", "--preserve=mode,timestamps", str(path), str(backup)],
        timeout=SUDO_TIMEOUT_SECONDS,
    )
    return result is not None and result.returncode == 0


def _ensure_system_directory(path: Path) -> bool:
    if path.is_dir():
        return True

    if path.parent.is_dir() and os.access(path.parent, os.W_OK):
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            _log_error("Could not create directory %s: %s", path, exc)
            return False
        return True

    sudo = shutil.which("sudo")
    if sudo is None:
        _log_error("sudo was not found; cannot create %s.", path)
        return False
    result = _run_process(
        [sudo, "mkdir", "-p", str(path)],
        timeout=SUDO_TIMEOUT_SECONDS,
    )
    return result is not None and result.returncode == 0


def _write_system_file(path: Path, content: str) -> bool:
    if _is_writable(path):
        try:
            path.write_text(content, encoding="utf-8")
            path.chmod(0o644)
        except OSError as exc:
            _log_error("Could not write %s: %s", path, exc)
            return False
        return True

    sudo = shutil.which("sudo")
    if sudo is None:
        _log_error("sudo was not found; cannot write %s.", path)
        return False
    result = _run_process(
        [sudo, "tee", str(path)],
        timeout=SUDO_TIMEOUT_SECONDS,
        input_text=content,
    )
    if result is None or result.returncode != 0:
        _log_error("Could not write %s with sudo.", path)
        return False
    chmod_result = _run_process(
        [sudo, "chmod", "644", str(path)],
        timeout=SUDO_TIMEOUT_SECONDS,
    )
    return chmod_result is not None and chmod_result.returncode == 0


def _merge_snippet_imports(
    existing_imports: Sequence[str],
    snippets: Sequence[Path],
) -> list[Path]:
    """Combine existing managed imports with new snippet paths, preserving order.

    Import tokens already present in the managed block are kept so snippets for
    containers that were not selected in the current run stay installed. New
    snippets are appended in the order they are provided, and duplicates are
    removed.
    """
    snippet_tokens = [_snippet_name(snippet) for snippet in snippets]
    merged_tokens: list[str] = []
    seen: set[str] = set()
    for token in (*existing_imports, *snippet_tokens):
        if token in seen:
            continue
        seen.add(token)
        merged_tokens.append(token)
    return [Path(token.strip('"')) for token in merged_tokens]


def install_caddy_config(
    snippets: Sequence[Path],
    *,
    config_path: Path,
) -> bool:
    """Add the managed import block to the host Caddyfile.

    The existing file is read, the managed block is replaced in place, and the
    result is validated before it is written. Import lines already present in
    the managed block are preserved so previously installed container snippets
    remain active even when only a subset of containers is selected in the
    current run. Existing content is backed up when the managed block changes.
    """
    existing_snippets = tuple(snippet for snippet in snippets if snippet.is_file())
    if not existing_snippets:
        _log_warning("No Caddy snippets were available; leaving Caddy unchanged.")
        return True

    try:
        existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    except (OSError, UnicodeError) as exc:
        _log_error("Could not read the Caddyfile at %s: %s", config_path, exc)
        ui.error(f"Could not read the host Caddyfile: {exc}")
        return False

    existing_imports = _existing_snippet_paths(config_path)
    merged = _merge_snippet_imports(existing_imports, existing_snippets)
    updated = _replace_managed_block(existing, _render_import_block(merged))
    if updated == existing:
        _log_info("The host Caddyfile is already up to date.")
        return True

    if not _validate_caddy_config(updated):
        ui.error("The generated Caddy configuration is invalid.")
        return False

    if config_path.exists() and not _backup_system_file(config_path):
        ui.error("Could not back up the host Caddyfile.")
        return False

    if not _write_system_file(config_path, updated):
        ui.error("Could not update the host Caddyfile.")
        return False

    _log_info("Updated the managed Caddy block in %s.", config_path)
    return True


def ensure_sudo() -> bool:
    """Prompt for and cache sudo credentials."""
    sudo = shutil.which("sudo")
    if sudo is None:
        _log_error("Sudo authentication failed: sudo was not found.")
        return False

    authenticated = _run_process([sudo, "-v"], timeout=SUDO_TIMEOUT_SECONDS)
    if authenticated is None or authenticated.returncode != 0:
        return False

    noninteractive = _run_process([sudo, "-n", "-v"], timeout=SUDO_TIMEOUT_SECONDS)
    return noninteractive is not None and noninteractive.returncode == 0


def ensure_caddy_running() -> bool:
    """Start the Caddy service when it is not already running.

    Returns:
        ``True`` when Caddy is active or was started, otherwise ``False``.
    """
    systemctl = shutil.which("systemctl")
    sudo = shutil.which("sudo")
    if systemctl is None or sudo is None:
        _log_error("Cannot manage the Caddy service without systemctl and sudo.")
        return False

    active = _run_process(
        [systemctl, "is-active", "--quiet", "caddy"],
        timeout=CADDY_TIMEOUT_SECONDS,
    )
    if active is not None and active.returncode == 0:
        return True

    if not ui.confirm(
        "The Caddy service is not running. Start and enable it now?",
        default=True,
        instruction="Caddy must be running to serve the container reverse-proxy routes.",
    ):
        _log_warning("Caddy was not started; reverse-proxy routes will not be served.")
        return False

    result = _run_process(
        [sudo, "systemctl", "enable", "--now", "caddy"],
        timeout=CADDY_TIMEOUT_SECONDS,
    )
    if result is None or result.returncode != 0:
        detail = ""
        if result is not None and result.stderr.strip():
            detail = result.stderr.strip().splitlines()[-1]
        _log_error("Could not start the Caddy service. %s", detail)
        return False

    _log_info("Started and enabled the Caddy service.")
    return True


def reload_caddy(config_path: Path) -> bool:
    """Reload the host Caddy service after its configuration changed."""
    sudo = shutil.which("sudo")
    systemctl = shutil.which("systemctl")
    if sudo is not None and systemctl is not None:
        result = _run_process(
            [sudo, "systemctl", "reload", "caddy"],
            timeout=CADDY_TIMEOUT_SECONDS,
        )
        if result is not None and result.returncode == 0:
            _log_info("Reloaded Caddy through systemd.")
            return True

    caddy = shutil.which("caddy")
    if caddy is not None and sudo is not None:
        result = _run_process(
            [sudo, caddy, "reload", "--config", str(config_path)],
            timeout=CADDY_TIMEOUT_SECONDS,
        )
        if result is not None and result.returncode == 0:
            _log_info("Reloaded Caddy through the CLI.")
            return True

    _log_error("Could not reload Caddy.")
    return False


def _select_containers(containers: Sequence[ContainerSpec]) -> tuple[ContainerSpec, ...]:
    selected_names = ui.checkbox(
        "Select containers to create:",
        [container.name for container in containers],
        instruction=(
            "Space selects, Enter confirms. Leave all unselected to skip container setup."
        ),
    )
    selected_set = set(selected_names)
    return tuple(container for container in containers if container.name in selected_set)


def _confirm_create(containers: Sequence[ContainerSpec]) -> bool:
    return ui.confirm(
        f"Create {len(containers)} selected container(s)?",
        default=False,
        instruction=(
            "Files are prepared below ~/Projects/Containers and started with Docker Compose."
        ),
    )


def _compose_metadata_from_file(
    runtime_directory: Path,
) -> tuple[str, tuple[str, ...]] | None:
    compose_path = runtime_directory / COMPOSE_FILE_NAME
    try:
        content = compose_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _log_warning("Could not inspect %s: %s", compose_path, exc)
        return None

    project_name: str | None = None
    container_names: list[str] = []
    for line in content.splitlines():
        if project_name is None:
            project_match = COMPOSE_PROJECT_NAME_PATTERN.match(line)
            if project_match is not None:
                project_name = project_match.group(1)
        container_match = CONTAINER_NAME_PATTERN.match(line)
        if container_match is not None:
            container_names.append(container_match.group(1).lower())

    return project_name or runtime_directory.name, tuple(container_names)


def _compose_file_arguments(runtime_directory: Path) -> list[str]:
    """Return the ``-f`` arguments for a container's Compose invocation.

    The generated ``compose.agents.yaml`` is merged when present so the
    discovered host mounts are included in validation and startup.
    """
    arguments = ["-f", COMPOSE_FILE_NAME]
    if (runtime_directory / AGENTS_COMPOSE_FILE_NAME).is_file():
        arguments.extend(["-f", AGENTS_COMPOSE_FILE_NAME])
    return arguments


def _compose_metadata(runtime_directory: Path) -> tuple[str, tuple[str, ...]] | None:
    docker = shutil.which("docker")
    if docker is not None:
        result = _run_process(
            [
                docker,
                "compose",
                *_compose_file_arguments(runtime_directory),
                "config",
                "--format",
                "json",
            ],
            timeout=COMPOSE_CONFIG_TIMEOUT_SECONDS,
            cwd=runtime_directory,
        )
        if result is not None and result.returncode == 0:
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                data = None
            if isinstance(data, dict):
                project = data.get("name")
                services = data.get("services")
                names: list[str] = []
                if isinstance(services, dict):
                    for service in services.values():
                        if not isinstance(service, dict):
                            continue
                        container_name = service.get("container_name")
                        if isinstance(container_name, str) and container_name:
                            names.append(container_name.lower())
                if isinstance(project, str) and project:
                    return project, tuple(names)

    return _compose_metadata_from_file(runtime_directory)


def _existing_container_project(name: str) -> tuple[bool, str | None]:
    docker = shutil.which("docker")
    if docker is None:
        return False, None
    result = _run_process(
        [
            docker,
            "inspect",
            "--format",
            '{{ index .Config.Labels "com.docker.compose.project" }}',
            name,
        ],
        timeout=COMPOSE_CONFIG_TIMEOUT_SECONDS,
    )
    if result is None or result.returncode != 0:
        return False, None
    project = result.stdout.strip()
    return True, project or None


def _resolve_container_name_conflicts(runtime_directory: Path) -> bool:
    """Stop and rename containers that block the Compose project name."""
    metadata = _compose_metadata(runtime_directory)
    if metadata is None:
        return True

    project, container_names = metadata
    if not container_names:
        return True

    docker = shutil.which("docker")
    if docker is None:
        return True

    for name in container_names:
        exists, owner = _existing_container_project(name)
        if not exists or owner == project:
            continue

        owner_text = f' by Compose project "{owner}"' if owner is not None else " outside Compose"
        replacement = f"{name}-backup-{time.strftime(BACKUP_TIMESTAMP_FORMAT)}"
        ui.warning(f'Container name "{name}" is already in use{owner_text}.')
        if not ui.confirm(
            f'Stop and rename the existing container "{name}" to "{replacement}"?',
            default=True,
            instruction=(
                "The old container is preserved but stopped so Docker Compose can "
                "create a container with the configured name."
            ),
        ):
            _log_error("Container name conflict was not resolved for %s.", name)
            return False

        rename_result = _run_process(
            [docker, "rename", name, replacement],
            timeout=COMPOSE_TIMEOUT_SECONDS,
        )
        if rename_result is None or rename_result.returncode != 0:
            _log_error("Could not rename the existing container %s.", name)
            return False

        stop_result = _run_process(
            [docker, "stop", replacement],
            timeout=COMPOSE_TIMEOUT_SECONDS,
        )
        if stop_result is None or stop_result.returncode != 0:
            _log_error("Could not stop the renamed container %s.", replacement)
            return False

        _log_info("Renamed and stopped the existing container %s.", name)
        ui.success(f'Renamed the existing container to "{replacement}" and stopped it.')

    return True


def _start_container(
    spec: ContainerSpec,
    runtime_directory: Path,
    *,
    terminal: ui.VirtualTerminal,
    progress: Progress,
) -> bool:
    task_id: TaskID = progress.add_task(f"Starting {spec.name}", total=None)
    docker = shutil.which("docker")
    if docker is None:
        _log_error("Docker was not found; cannot start %s.", spec.name)
        terminal.writeline("The docker command was not found on PATH.", style=ui.THEME.error)
        progress.update(task_id, description=f"Failed {spec.name}")
        progress.advance(task_id)
        return False

    command = [
        docker,
        "compose",
        *_compose_file_arguments(runtime_directory),
        "up",
        "-d",
        "--remove-orphans",
    ]
    _log_info("Starting container: %s", " ".join(command))
    terminal.writeline(f"Starting {spec.name}...", style=ui.THEME.info)

    try:
        returncode = terminal.run(
            command,
            cwd=runtime_directory,
            timeout=COMPOSE_TIMEOUT_SECONDS,
            echo=False,
        )
    except FileNotFoundError:
        _log_error("Docker was not found while starting %s.", spec.name)
        terminal.writeline("The docker command was not found.", style=ui.THEME.error)
        progress.update(task_id, description=f"Failed {spec.name}")
        progress.advance(task_id)
        return False
    except subprocess.TimeoutExpired:
        _log_error("Starting %s timed out after %s seconds.", spec.name, COMPOSE_TIMEOUT_SECONDS)
        terminal.writeline(
            f"Starting {spec.name} timed out after {COMPOSE_TIMEOUT_SECONDS:g}s.",
            style=ui.THEME.error,
        )
        progress.update(task_id, description=f"Failed {spec.name}")
        progress.advance(task_id)
        return False
    except OSError as exc:
        _log_error("Could not start %s: %s", spec.name, exc)
        terminal.writeline(f"Could not start {spec.name}: {exc}", style=ui.THEME.error)
        progress.update(task_id, description=f"Failed {spec.name}")
        progress.advance(task_id)
        return False

    if returncode != 0:
        _log_error("Docker Compose exited with status %s for %s.", returncode, spec.name)
        progress.update(task_id, description=f"Failed {spec.name}")
        progress.advance(task_id)
        return False

    _log_info("Container started: %s", spec.name)
    progress.update(task_id, description=f"Started {spec.name}")
    progress.advance(task_id)
    return True


def run_containers_step(
    *,
    containers: Sequence[ContainerSpec] | None = None,
    home: Path | None = None,
    containers_root: Path | None = None,
    caddy_config_path: Path | None = None,
    caddy_directory: Path | None = None,
) -> ContainerResult:
    """Prepare and start the selected Docker containers.

    Args:
        containers: Optional catalog override, primarily for tests.
        home: Optional home directory override, primarily for tests.
        containers_root: Optional prepared-container root override.
        caddy_config_path: Optional host Caddyfile override.
        caddy_directory: Optional managed Caddy snippet directory override.

    Returns:
        The outcome of the container setup step.
    """
    logger = get_session()
    if logger is not None:
        logger.info("Container setup step started.")

    ui.section(
        "Docker Containers",
        subtitle="Prepare Docker Compose projects and Caddy reverse proxies.",
        icon=ui.ICONS.package,
    )

    if not ui.is_interactive():
        if logger is not None:
            logger.info("Container setup skipped: no interactive terminal.")
        ui.warning(
            "Container setup skipped: selecting containers requires an interactive terminal.",
        )
        return ContainerResult.SKIPPED

    try:
        catalog = tuple(containers) if containers is not None else load_container_specs()
    except OSError as exc:
        _log_error("Could not load the container catalog: %s", exc)
        ui.error(f"Could not load the container catalog: {exc}")
        return ContainerResult.FAILED

    if not catalog:
        _log_warning("Container setup skipped: the container catalog is empty.")
        ui.warning("No containers are configured.")
        return ContainerResult.SKIPPED

    selected = _select_containers(catalog)
    if not selected:
        if logger is not None:
            logger.info("Container setup skipped: no containers were selected.")
        ui.info("No containers were selected.")
        return ContainerResult.SKIPPED

    omniroute_selected = any(container.slug == OMNIROUTE_SLUG for container in selected)
    if omniroute_selected and not ensure_omniroute_cli():
        _log_warning("OmniRoute CLI is unavailable; continuing without it.")
        ui.warning("OmniRoute CLI is unavailable; continuing without it.")

    if not _confirm_create(selected):
        if logger is not None:
            logger.info("Container setup skipped by the user.")
        ui.info("Container setup skipped.")
        return ContainerResult.SKIPPED

    base_home = home if home is not None else Path.home()
    root = containers_root if containers_root is not None else get_containers_root(base_home)
    caddyfile = caddy_config_path if caddy_config_path is not None else get_caddy_config_path()

    prepared: list[ContainerSpec] = []
    failed_any = False
    for container in selected:
        if prepare_container(container, home=base_home, containers_root=root):
            prepared.append(container)
        else:
            failed_any = True

    omniroute_runtime = root / OMNIROUTE_SLUG
    omniroute_prepared = any(container.slug == OMNIROUTE_SLUG for container in prepared)
    startable: list[ContainerSpec] = []
    if omniroute_prepared and discover_agent_mounts(omniroute_runtime) is None:
        _log_error("OmniRoute agent discovery failed; skipping OmniRoute startup.")
        ui.error("OmniRoute agent discovery failed; skipping OmniRoute startup.")
        failed_any = True
        startable = [container for container in prepared if container.slug != OMNIROUTE_SLUG]
    else:
        for container in prepared:
            if _resolve_container_name_conflicts(root / container.slug):
                startable.append(container)
            else:
                failed_any = True

    has_caddyfile = any(container.caddyfile.is_file() for container in startable)
    has_global_caddyfile = get_global_caddyfile().is_file()
    configure_caddy = (has_caddyfile or has_global_caddyfile) and ui.confirm(
        "Configure Caddy reverse proxy routes for the selected containers?",
        default=True,
        instruction="Adds a managed import block to the host Caddyfile.",
    )
    if configure_caddy:
        snippets: list[Path] = []
        if not ensure_sudo():
            _log_error("Caddy configuration failed: sudo authentication failed.")
            ui.error("Caddy configuration failed: sudo authentication failed.")
            failed_any = True
        else:
            global_snippet = install_global_caddy_snippet(caddy_directory=caddy_directory)
            if global_snippet is not None:
                snippets.append(global_snippet)

            for container in startable:
                snippet = install_caddy_snippet(
                    container,
                    caddy_directory=caddy_directory,
                )
                if snippet is None:
                    if container.caddyfile.is_file():
                        failed_any = True
                    continue
                snippets.append(snippet)

            if snippets:
                if not install_caddy_config(snippets, config_path=caddyfile):
                    failed_any = True
                elif not ensure_caddy_running():
                    ui.warning("Caddy configuration was written but Caddy is not running.")
                    failed_any = True
                elif not reload_caddy(caddyfile):
                    ui.warning("Caddy configuration was written but could not be reloaded.")
                    failed_any = True

    started_any = False
    omniroute_started = False
    if startable:
        with ui.terminal_with_progress(
            height=12,
            max_lines=200,
            title="Docker Container Setup",
        ) as (terminal, progress):
            for container in startable:
                if _start_container(
                    container,
                    root / container.slug,
                    terminal=terminal,
                    progress=progress,
                ):
                    started_any = True
                    if container.slug == OMNIROUTE_SLUG:
                        omniroute_started = True
                else:
                    failed_any = True

    if omniroute_started:
        show_bootstrap_token(omniroute_runtime)

    if omniroute_started and not connect_omniroute_cli(omniroute_runtime):
        _log_error("OmniRoute CLI connection details could not be printed.")
        ui.error("OmniRoute CLI connection details could not be printed.")
        failed_any = True

    if failed_any:
        if logger is not None:
            logger.error("Container setup failed for one or more containers.")
        ui.error("Container setup failed for one or more containers.")
        return ContainerResult.FAILED

    if not started_any:
        if logger is not None:
            logger.info("Container setup skipped: no containers were started.")
        ui.info("No containers were started.")
        return ContainerResult.SKIPPED

    if logger is not None:
        logger.info("Container setup step completed.")
    ui.success("Container setup completed.")
    return ContainerResult.COMPLETED
