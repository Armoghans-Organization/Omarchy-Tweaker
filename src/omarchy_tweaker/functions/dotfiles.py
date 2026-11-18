"""Configure bundled dotfiles and generate Git signing keys."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess  # nosec B404
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Final

from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.logger import get_session

DOTFILES_DIRECTORY_ENV_VAR: Final = "OMARCHY_TWEAKER_DOTFILES_DIR"
BACKUP_TIMESTAMP_FORMAT: Final = "%Y%m%d-%H%M%S"
COMMAND_TIMEOUT_SECONDS: Final = 120


class DotfileResult(StrEnum):
    """Outcome of the dotfiles setup step."""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class DotfileBundle:
    """A bundled dotfile catalog loaded from one config.toml file."""

    name: str
    source: Path
    symlinks: tuple[tuple[str, Path], ...]
    questions: tuple[tuple[str, str], ...]
    create: tuple[tuple[str, Path], ...]
    keys: KeyConfig | None


@dataclass(frozen=True)
class KeyConfig:
    """Key locations and options loaded from a dotfile config.toml file."""

    ssh_private: Path
    ssh_public: Path
    gpg_home: Path
    gpg_public: Path
    ssh_type: str
    ssh_rounds: int
    gpg_algorithm: str
    gpg_usage: str
    gpg_expiration: str


@dataclass(frozen=True)
class LinkOutcome:
    """Result of creating one dotfile symlink."""

    changed: bool
    backup: Path | None


@dataclass(frozen=True)
class SshKeyInfo:
    """Generated or existing SSH key paths."""

    private_key: Path
    public_key: Path
    created: bool


@dataclass(frozen=True)
class GpgKeyInfo:
    """Generated or existing GPG signing key details."""

    fingerprint: str
    public_key: Path
    created: bool


@dataclass(frozen=True)
class KeySetup:
    """SSH and GPG key details for one dotfile bundle."""

    ssh: SshKeyInfo
    gpg: GpgKeyInfo


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


def get_dotfiles_source_directory() -> Path:
    """Return the directory containing bundled dotfile catalogs."""
    override = os.environ.get(DOTFILES_DIRECTORY_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[1] / "dotfiles"


def discover_dotfile_bundles(source: Path) -> tuple[Path, ...]:
    """Return bundled directories that contain a config.toml file.

    Args:
        source: Root directory containing dotfile catalogs.

    Returns:
        Matching directories in name order.
    """
    if not source.is_dir():
        return ()
    return tuple(
        path
        for path in sorted(source.iterdir())
        if path.is_dir() and not path.is_symlink() and (path / "config.toml").is_file()
    )


def _expand_home_path(value: object, home: Path) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("Dotfile paths must be non-empty strings.")
    if value == "~":
        return home.resolve()
    if not value.startswith("~/"):
        raise ValueError(f"Dotfile paths must start with '~/': {value}")

    base = home.resolve()
    candidate = (home / value[2:]).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"Dotfile path escapes the home directory: {value}")
    return candidate


def _string_table(data: dict[str, object], name: str) -> dict[str, str]:
    table = data.get(name, {})
    if not isinstance(table, dict):
        raise ValueError(f"[{name}] must be a table.")

    result: dict[str, str] = {}
    for key, value in table.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError(f"[{name}] values must be strings.")
        result[key] = value
    return result


def _require_string(table: dict[str, object], key: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"[keys].{key} must be a non-empty string.")
    return value


def _require_positive_int(table: dict[str, object], key: str) -> int:
    value = table.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"[keys].{key} must be a positive integer.")
    return value


def _load_key_config(data: dict[str, object], home: Path) -> KeyConfig | None:
    raw = data.get("keys")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("[keys] must be a table.")

    return KeyConfig(
        ssh_private=_expand_home_path(_require_string(raw, "ssh_private"), home),
        ssh_public=_expand_home_path(_require_string(raw, "ssh_public"), home),
        gpg_home=_expand_home_path(_require_string(raw, "gpg_home"), home),
        gpg_public=_expand_home_path(_require_string(raw, "gpg_public"), home),
        ssh_type=_require_string(raw, "ssh_type"),
        ssh_rounds=_require_positive_int(raw, "ssh_rounds"),
        gpg_algorithm=_require_string(raw, "gpg_algorithm"),
        gpg_usage=_require_string(raw, "gpg_usage"),
        gpg_expiration=_require_string(raw, "gpg_expiration"),
    )


def load_dotfile_bundle(bundle_directory: Path, home: Path) -> DotfileBundle:
    """Load one dotfile catalog from its config.toml file.

    Args:
        bundle_directory: Directory containing config.toml and bundled files.
        home: Home directory used to resolve configured paths.

    Returns:
        The validated dotfile bundle.

    Raises:
        OSError: If config.toml cannot be read.
        ValueError: If config.toml contains invalid values.
    """
    config_path = bundle_directory / "config.toml"
    with config_path.open("rb") as config_file:
        data: dict[str, object] = tomllib.load(config_file)

    symlinks = tuple(
        (key, _expand_home_path(path, home)) for key, path in _string_table(data, "symlink").items()
    )
    questions = tuple(
        (key.strip().lower(), message) for key, message in _string_table(data, "ask").items()
    )
    create = tuple(
        (key.strip().lower(), _expand_home_path(path, home))
        for key, path in _string_table(data, "create").items()
    )

    return DotfileBundle(
        name=bundle_directory.name,
        source=bundle_directory,
        symlinks=symlinks,
        questions=questions,
        create=create,
        keys=_load_key_config(data, home),
    )


def load_dotfile_bundles(source: Path, home: Path) -> tuple[DotfileBundle, ...]:
    """Load every bundled dotfile catalog.

    Args:
        source: Root directory containing dotfile catalogs.
        home: Home directory used to resolve configured paths.

    Returns:
        Validated bundles in name order.

    Raises:
        OSError: If a config.toml cannot be read.
        ValueError: If a config.toml contains invalid values.
    """
    return tuple(load_dotfile_bundle(path, home) for path in discover_dotfile_bundles(source))


def _backup_path(path: Path) -> Path:
    timestamp = datetime.now().strftime(BACKUP_TIMESTAMP_FORMAT)
    candidate = path.with_name(f"{path.name}.bak.{timestamp}")
    counter = 1
    while candidate.exists() or candidate.is_symlink():
        candidate = path.with_name(f"{path.name}.bak.{timestamp}.{os.getpid()}.{counter}")
        counter += 1
    shutil.move(str(path), str(candidate))
    return candidate


def link_dotfile(source: Path, destination: Path) -> LinkOutcome:
    """Replace a destination with a symlink after backing up any existing entry.

    Args:
        source: Bundled file or directory to link.
        destination: Destination path configured in config.toml.

    Returns:
        Whether the link changed and the backup path when one was made.

    Raises:
        FileNotFoundError: If the bundled source does not exist.
        OSError: If the parent, backup, restoration, or symlink operation fails.
    """
    if not source.exists():
        raise FileNotFoundError(f"Bundled dotfile is missing: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    target = source.resolve()
    if destination.is_symlink() and destination.resolve() == target:
        return LinkOutcome(changed=False, backup=None)

    backup = _backup_path(destination) if destination.exists() or destination.is_symlink() else None
    try:
        destination.symlink_to(target)
    except OSError:
        if backup is not None:
            shutil.move(str(backup), str(destination))
        raise
    return LinkOutcome(changed=True, backup=backup)


def create_from_template(template: Path, destination: Path, values: dict[str, str]) -> bool:
    """Render a bundled template into a destination with backup protection.

    Args:
        template: Bundled template file.
        destination: Destination path configured in config.toml.
        values: Values used to render the template.

    Returns:
        True if the destination changed, False if it already matched.

    Raises:
        OSError: If the template or destination cannot be read or written.
        KeyError: If the template references a missing value.
        ValueError: If the template cannot be formatted.
    """
    content = template.read_text(encoding="utf-8").format(**values)
    if (
        destination.is_file()
        and not destination.is_symlink()
        and destination.read_text(encoding="utf-8") == content
    ):
        return False

    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = _backup_path(destination) if destination.exists() or destination.is_symlink() else None
    try:
        destination.write_text(content, encoding="utf-8")
    except OSError:
        if backup is not None:
            shutil.move(str(backup), str(destination))
        raise
    return True


def _run_command(
    command: list[str],
    *,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # nosec B603
            command,
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required command is not installed: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command timed out: {command[0]}") from exc


def _gpg_fingerprint(keys: KeyConfig, email: str) -> str | None:
    result = _run_command(
        [
            "gpg",
            "--homedir",
            str(keys.gpg_home),
            "--batch",
            "--list-secret-keys",
            "--with-colons",
            email,
        ],
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        fields = line.split(":")
        if len(fields) > 9 and fields[0] == "fpr" and fields[9]:
            return fields[9]
    return None


def ensure_ssh_key(
    keys: KeyConfig,
    email: str,
    passphrase_provider: Callable[[], str],
) -> SshKeyInfo:
    """Create an SSH key when missing and keep existing keys untouched.

    Args:
        keys: Key locations and options from config.toml.
        email: Comment stored on the SSH key.
        passphrase_provider: Callback that returns the shared key passphrase.

    Returns:
        SSH key paths and whether a key was created.

    Raises:
        OSError: If key directories or files cannot be written.
        RuntimeError: If ssh-keygen is unavailable or fails.
    """
    keys.ssh_private.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _set_mode(keys.ssh_private.parent, 0o700)

    if keys.ssh_private.is_file():
        if not keys.ssh_public.exists():
            result = _run_command(
                [
                    "ssh-keygen",
                    "-y",
                    "-P",
                    passphrase_provider(),
                    "-f",
                    str(keys.ssh_private),
                ],
            )
            if result.returncode != 0:
                raise RuntimeError("Could not derive the existing SSH public key.")
            keys.ssh_public.parent.mkdir(parents=True, exist_ok=True)
            keys.ssh_public.write_text(f"{result.stdout.strip()}\n", encoding="utf-8")
            keys.ssh_public.chmod(0o644)
        return SshKeyInfo(private_key=keys.ssh_private, public_key=keys.ssh_public, created=False)

    if keys.ssh_public.exists() or keys.ssh_public.is_symlink():
        raise RuntimeError("SSH public key exists without its private key.")

    result = _run_command(
        [
            "ssh-keygen",
            "-q",
            "-t",
            keys.ssh_type,
            "-a",
            str(keys.ssh_rounds),
            "-f",
            str(keys.ssh_private),
            "-C",
            email,
            "-N",
            passphrase_provider(),
        ],
    )
    if result.returncode != 0:
        raise RuntimeError("SSH key generation failed.")

    keys.ssh_private.chmod(0o600)
    generated_public = Path(f"{keys.ssh_private}.pub")
    if not generated_public.is_file():
        raise RuntimeError("SSH key generation did not create a public key.")

    keys.ssh_public.parent.mkdir(parents=True, exist_ok=True)
    if generated_public != keys.ssh_public:
        shutil.move(str(generated_public), str(keys.ssh_public))
    keys.ssh_public.chmod(0o644)
    return SshKeyInfo(private_key=keys.ssh_private, public_key=keys.ssh_public, created=True)


def _set_mode(path: Path, mode: int) -> None:
    current_mode = stat.S_IMODE(path.stat().st_mode)
    if current_mode != mode:
        path.chmod(mode)


def ensure_gpg_key(
    keys: KeyConfig,
    name: str,
    email: str,
    passphrase_provider: Callable[[], str],
) -> GpgKeyInfo:
    """Create a GPG signing key when missing and export its public key.

    Args:
        keys: Key locations and options from config.toml.
        name: Real name used for the key identity.
        email: Email address used for the key identity.
        passphrase_provider: Callback that returns the shared key passphrase.

    Returns:
        GPG fingerprint, export path, and whether a key was created.

    Raises:
        OSError: If key directories or export files cannot be written.
        RuntimeError: If gpg is unavailable or fails.
    """
    keys.gpg_home.mkdir(mode=0o700, parents=True, exist_ok=True)
    _set_mode(keys.gpg_home, 0o700)

    fingerprint = _gpg_fingerprint(keys, email)
    created = False
    if fingerprint is None:
        result = _run_command(
            [
                "gpg",
                "--homedir",
                str(keys.gpg_home),
                "--batch",
                "--yes",
                "--pinentry-mode",
                "loopback",
                "--passphrase-fd",
                "0",
                "--quick-generate-key",
                f"{name} <{email}>",
                keys.gpg_algorithm,
                keys.gpg_usage,
                keys.gpg_expiration,
            ],
            input_text=f"{passphrase_provider()}\n",
        )
        if result.returncode != 0:
            raise RuntimeError("GPG key generation failed.")
        created = True
        fingerprint = _gpg_fingerprint(keys, email)
        if fingerprint is None:
            raise RuntimeError("The GPG fingerprint could not be read after key generation.")

    result = _run_command(
        [
            "gpg",
            "--homedir",
            str(keys.gpg_home),
            "--batch",
            "--armor",
            "--export",
            fingerprint,
        ],
    )
    if result.returncode != 0:
        raise RuntimeError("GPG public key export failed.")

    keys.gpg_public.parent.mkdir(parents=True, exist_ok=True)
    keys.gpg_public.write_text(result.stdout, encoding="utf-8")
    keys.gpg_public.chmod(0o644)
    return GpgKeyInfo(fingerprint=fingerprint, public_key=keys.gpg_public, created=created)


def setup_keys(
    keys: KeyConfig,
    answers: dict[str, str],
    passphrase_provider: Callable[[], str],
) -> KeySetup:
    """Generate configured SSH and GPG keys for one dotfile bundle.

    Args:
        keys: Key locations and options from config.toml.
        answers: Answers collected from the [ask] section.
        passphrase_provider: Callback that returns the shared key passphrase.

    Returns:
        The prepared SSH and GPG key details.

    Raises:
        KeyError: If the bundle does not collect name and email answers.
        OSError: If key files cannot be written.
        RuntimeError: If key commands fail.
    """
    name = answers["name"].strip()
    email = answers["email"].strip()
    if not name or not email:
        raise ValueError("Name and email are required to generate keys.")

    ssh = ensure_ssh_key(keys, email, passphrase_provider)
    gpg = ensure_gpg_key(keys, name, email, passphrase_provider)
    return KeySetup(ssh=ssh, gpg=gpg)


def _validate_required(value: str, message: str) -> bool | str:
    return True if value.strip() else message


def _validate_email(value: str) -> bool | str:
    candidate = value.strip()
    if "@" not in candidate or "." not in candidate.rsplit("@", 1)[-1]:
        return "Enter a valid email address."
    return True


def _ask_questions(questions: tuple[tuple[str, str], ...]) -> dict[str, str]:
    validators: dict[str, Callable[[str], bool | str]] = {
        "name": lambda value: _validate_required(value, "Name is required."),
        "email": _validate_email,
    }
    answers: dict[str, str] = {}
    for key, message in questions:
        answers[key] = ui.prompt_text(message, validator=validators.get(key))
    return answers


def _ask_passphrase() -> str:
    passphrase = ui.password(
        "Passphrase for new SSH and GPG keys",
        instruction="Leave empty to create keys without a passphrase.",
    )
    confirmation = ui.password("Confirm key passphrase")
    if passphrase != confirmation:
        raise ValueError("Key passphrases do not match.")
    if not passphrase:
        ui.warning("Keys will be created without a passphrase.")
    return passphrase


def _cached_passphrase_provider() -> Callable[[], str]:
    cached: str | None = None

    def provider() -> str:
        nonlocal cached
        if cached is None:
            cached = _ask_passphrase()
        return cached

    return provider


def _show_key_setup(setup: KeySetup) -> None:
    ui.info(f"SSH private key: {setup.ssh.private_key}")
    ui.info(f"SSH public key: {setup.ssh.public_key}")
    try:
        public_key = setup.ssh.public_key.read_text(encoding="utf-8").strip()
    except OSError:
        public_key = ""
    if public_key:
        ui.info(public_key)
    ui.info(f"GPG fingerprint: {setup.gpg.fingerprint}")
    ui.info(f"GPG public key: {setup.gpg.public_key}")
    ui.bullet_list(
        (
            "Copy the SSH public key above into GitHub under SSH and GPG keys.",
            f"Upload {setup.gpg.public_key} under GitHub SSH and GPG keys.",
            "The private keys stay in your home directory and are never uploaded.",
        )
    )


def run_dotfiles_step(
    *,
    home: Path | None = None,
    source: Path | None = None,
) -> DotfileResult:
    """Apply bundled dotfiles and prepare configured keys.

    Args:
        home: Optional home directory override, primarily for tests.
        source: Optional dotfiles root override, primarily for tests.

    Returns:
        The outcome of the dotfiles setup step.
    """
    _log_info("Dotfiles step started.")

    ui.section(
        "Dotfiles",
        subtitle="Symlink bundled configuration and prepare signing keys.",
        icon=ui.ICONS.folder,
    )

    base = home if home is not None else Path.home()
    root = source if source is not None else get_dotfiles_source_directory()

    try:
        bundles = load_dotfile_bundles(root, base)
    except (OSError, ValueError) as exc:
        _log_error("Could not load dotfile bundles: %s", exc)
        ui.error(f"Dotfiles setup failed: {exc}")
        return DotfileResult.FAILED

    if not bundles:
        _log_warning("Dotfiles step skipped: no bundles found at %s", root)
        ui.warning("Dotfiles setup skipped: no bundled dotfiles were found.")
        return DotfileResult.SKIPPED

    if not ui.is_interactive():
        _log_info("Dotfiles step skipped: no interactive terminal.")
        ui.warning("Dotfiles setup skipped: an interactive terminal is required.")
        return DotfileResult.SKIPPED

    completed: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    for bundle in bundles:
        ui.info(f"Dotfile bundle: {bundle.name}")
        ui.bullet_list(str(destination) for _, destination in bundle.symlinks)
        if bundle.keys is not None:
            ui.info("SSH and GPG keys will be created when missing.")
        if not ui.confirm(
            f"Apply the {bundle.name} dotfiles?",
            default=False,
            instruction="Existing files are backed up before replacement.",
        ):
            skipped.append(bundle.name)
            _log_info("Dotfiles bundle skipped by the user: %s", bundle.name)
            ui.info(f"Skipped {bundle.name} dotfiles.")
            continue

        try:
            answers = _ask_questions(bundle.questions)
            key_setup: KeySetup | None = None
            if bundle.keys is not None:
                key_setup = setup_keys(bundle.keys, answers, _cached_passphrase_provider())
                _show_key_setup(key_setup)

            for name, destination in bundle.symlinks:
                outcome = link_dotfile(bundle.source / name, destination)
                if outcome.changed:
                    _log_info("Linked dotfile %s to %s", name, destination)
                    ui.success(f"Linked {destination}")
                    if outcome.backup is not None:
                        _log_info("Backed up %s to %s", destination, outcome.backup)
                        ui.info(f"Backup saved at {outcome.backup}")
                else:
                    ui.info(f"{destination} is already linked.")

            values = dict(answers)
            if key_setup is not None:
                values["signing_key"] = key_setup.gpg.fingerprint
            for name, destination in bundle.create:
                changed = create_from_template(bundle.source / name, destination, values)
                if changed:
                    _log_info("Created dotfile %s", destination)
                    ui.success(f"Created {destination}")
                else:
                    ui.info(f"{destination} is already up to date.")
        except (KeyError, OSError, RuntimeError, ValueError) as exc:
            failed.append(bundle.name)
            _log_error("Dotfiles bundle failed: %s: %s", bundle.name, exc)
            ui.error(f"Failed to apply {bundle.name} dotfiles: {exc}")
            continue

        completed.append(bundle.name)
        _log_info("Dotfiles bundle completed: %s", bundle.name)
        ui.success(f"Applied {bundle.name} dotfiles.")

    if failed:
        noun = "bundle" if len(failed) == 1 else "bundles"
        _log_error("Dotfiles step failed for %d %s.", len(failed), noun)
        ui.error(f"Dotfiles setup failed for {len(failed)} {noun}: {', '.join(failed)}")
        return DotfileResult.FAILED

    if completed:
        _log_info(
            "Dotfiles step completed: %d applied, %d skipped.",
            len(completed),
            len(skipped),
        )
        ui.success(
            f"Dotfiles setup complete: {len(completed)} applied, {len(skipped)} skipped.",
        )
        return DotfileResult.COMPLETED

    _log_info("Dotfiles step skipped: no bundles were applied.")
    ui.info("Dotfiles setup skipped. No dotfiles were applied.")
    return DotfileResult.SKIPPED
