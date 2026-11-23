from __future__ import annotations

import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

import omarchy_tweaker.functions.dotfiles as dotfiles_module
from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.dotfiles import (
    DotfileResult,
    create_from_template,
    discover_dotfile_bundles,
    ensure_gpg_key,
    ensure_ssh_key,
    get_dotfiles_source_directory,
    link_dotfile,
    load_dotfile_bundle,
)

FINGERPRINT = "1234567890ABCDEF1234567890ABCDEF12345678"


def make_bundle(tmp_path: Path, *, with_keys: bool = True) -> Path:
    root = tmp_path / "dotfiles"
    bundle = root / "git"
    bundle.mkdir(parents=True)
    (bundle / "config").write_text("[user]\n", encoding="utf-8")

    key_section = ""
    if with_keys:
        key_section = """
[keys]
ssh_private = "~/.ssh/id_ed25519"
ssh_public = "~/.ssh/id_ed25519.pub"
gpg_home = "~/.gnupg"
gpg_public = "~/.config/git/gpg-public-key.asc"
ssh_type = "ed25519"
ssh_rounds = 100
gpg_algorithm = "ed25519"
gpg_usage = "sign"
gpg_expiration = "never"
"""

    (bundle / "config.toml").write_text(
        """
[symlink]
config = "~/.config/git/config"

[ask]
Name = "What is your name?"
Email = "What is your email?"

[create]
user = "~/.config/git/user"
"""
        + key_section,
        encoding="utf-8",
    )
    (bundle / "user").write_text(
        "[user]\n    name = {name}\n    email = {email}\n    signingkey = {signing_key}\n",
        encoding="utf-8",
    )
    return root


def fake_key_commands(
    calls: list[list[str]],
    generated: list[bool],
) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)

        if command[0] == "ssh-keygen" and "-y" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                "ssh-ed25519 AAAA existing@example.com\n",
                "",
            )
        if command[0] == "ssh-keygen":
            private = Path(command[command.index("-f") + 1])
            private.write_text("PRIVATE KEY\n", encoding="utf-8")
            Path(f"{private}.pub").write_text(
                "ssh-ed25519 AAAA test@example.com\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, "", "")
        if "--list-secret-keys" in command:
            stdout = f"fpr:::::::::{FINGERPRINT}:\n" if generated[0] else ""
            return subprocess.CompletedProcess(command, 0, stdout, "")
        if "--quick-generate-key" in command:
            assert kwargs["input"] == "secret\n"
            generated[0] = True
            return subprocess.CompletedProcess(command, 0, "", "")
        if "--export" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                "-----BEGIN PGP PUBLIC KEY BLOCK-----\nKEY\n-----END PGP PUBLIC KEY BLOCK-----\n",
                "",
            )
        raise AssertionError(f"Unexpected command: {command}")

    return run


def test_get_dotfiles_source_directory_honors_environment_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OMARCHY_TWEAKER_DOTFILES_DIR", str(tmp_path))
    assert get_dotfiles_source_directory() == tmp_path


def test_discover_dotfile_bundles_returns_only_directories_with_config(
    tmp_path: Path,
) -> None:
    root = make_bundle(tmp_path)
    (root / "empty").mkdir()
    (root / "plain.txt").write_text("ignored", encoding="utf-8")

    assert [path.name for path in discover_dotfile_bundles(root)] == ["git"]


def test_discover_bundled_dotfile_catalogs_includes_expected_catalogs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OMARCHY_TWEAKER_DOTFILES_DIR", raising=False)
    source = get_dotfiles_source_directory()
    bundles = discover_dotfile_bundles(source)

    names = {path.name for path in bundles}
    assert {
        "Bat",
        "Foot",
        "Superfile",
        "Tig",
        "Tmux",
        "Zellij",
        "git",
        "lazygit",
        "starship",
    } <= names

    for path in bundles:
        bundle = load_dotfile_bundle(path, Path("/home/test"))
        assert bundle.symlinks
        assert all((path / name).exists() for name, _ in bundle.symlinks)


def test_bundled_bat_catalog_exposes_expected_symlink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OMARCHY_TWEAKER_DOTFILES_DIR", raising=False)
    source = get_dotfiles_source_directory()
    home = Path("/home/test")

    bundle = load_dotfile_bundle(source / "Bat", home)

    assert bundle.symlinks == (("config", home / ".config" / "bat" / "config"),)

    config_text = (source / "Bat" / "config").read_text(encoding="utf-8")
    assert '--theme="Catppuccin Macchiato"' in config_text
    assert '--style="numbers,changes,header,grid"' in config_text
    assert '--map-syntax "*.md:Markdown"' in config_text
    assert '--map-syntax "*.sh:Bourne Again Shell (bash)"' in config_text
    assert '--map-syntax "*.bat:Batch File"' in config_text
    assert '--map-syntax "*.cmd:Batch File"' in config_text
    assert '--map-syntax "*.tf:Terraform"' in config_text


def test_bundled_foot_catalog_exposes_expected_symlink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OMARCHY_TWEAKER_DOTFILES_DIR", raising=False)
    source = get_dotfiles_source_directory()
    home = Path("/home/test")

    bundle = load_dotfile_bundle(source / "Foot", home)

    assert bundle.symlinks == (("config", home / ".config" / "foot" / "foot.ini"),)

    config_text = (source / "Foot" / "config").read_text(encoding="utf-8")
    assert "include=~/.local/state/omarchy/current/theme/foot.ini" in config_text
    assert "term=xterm-256color" in config_text
    assert "font=Hack Nerd Font:size=11.5, Noto Color Emoji:size=9" in config_text
    assert "clipboard-copy=Control+Insert Control+Shift+c XF86Copy" in config_text
    assert "clipboard-paste=Control+v Control+Shift+v XF86Paste" in config_text
    assert "\\x1b[13;2u=Shift+Return" in config_text
    assert "urgent=yes" in config_text
    assert "notify=yes" in config_text
    assert "command=yes" not in config_text


def test_bundled_superfile_catalog_exposes_expected_symlinks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OMARCHY_TWEAKER_DOTFILES_DIR", raising=False)
    source = get_dotfiles_source_directory()
    home = Path("/home/test")

    bundle = load_dotfile_bundle(source / "Superfile", home)

    assert bundle.symlinks == (
        ("config", home / ".config" / "superfile" / "config.toml"),
        ("hotkeys", home / ".config" / "superfile" / "hotkeys.toml"),
        (
            "catppuccin",
            home / ".config" / "superfile" / "theme" / "catppuccin-frappe.toml",
        ),
    )


def test_bundled_zellij_catalog_exposes_expected_symlinks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OMARCHY_TWEAKER_DOTFILES_DIR", raising=False)
    source = get_dotfiles_source_directory()
    home = Path("/home/test")

    bundle = load_dotfile_bundle(source / "Zellij", home)

    assert bundle.symlinks == (
        ("config", home / ".config" / "zellij" / "config.kdl"),
        ("zextract", home / ".config" / "zellij" / "zextract.kdl"),
        (
            "layouts/custom.kdl",
            home / ".config" / "zellij" / "layouts" / "custom.kdl",
        ),
        (
            "layouts/default.kdl",
            home / ".config" / "zellij" / "layouts" / "default.kdl",
        ),
        (
            "layouts/strider.kdl",
            home / ".config" / "zellij" / "layouts" / "strider.kdl",
        ),
        (
            "layouts/compact.kdl",
            home / ".config" / "zellij" / "layouts" / "compact.kdl",
        ),
    )
    assert (source / "Zellij" / "layouts").is_dir()


def test_bundled_tmux_catalog_exposes_expected_symlinks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OMARCHY_TWEAKER_DOTFILES_DIR", raising=False)
    source = get_dotfiles_source_directory()
    home = Path("/home/test")

    bundle = load_dotfile_bundle(source / "Tmux", home)

    assert bundle.symlinks == (
        ("config", home / ".config" / "tmux" / "tmux.conf"),
        ("script/extract", home / ".config" / "tmux" / "script" / "extract"),
        ("script/float", home / ".config" / "tmux" / "script" / "float"),
        ("script/notify", home / ".config" / "tmux" / "script" / "notify"),
        ("script/scrollback", home / ".config" / "tmux" / "script" / "scrollback"),
        ("script/switch", home / ".config" / "tmux" / "script" / "switch"),
    )

    config_text = (source / "Tmux" / "config").read_text(encoding="utf-8")
    assert "~/.config/tmux/scripts/" not in config_text
    for script_name in ("extract", "float", "notify", "scrollback", "switch"):
        script = source / "Tmux" / "script" / script_name
        assert script.is_file()
        assert script.stat().st_mode & stat.S_IXUSR
        assert f"~/.config/tmux/script/{script_name}" in config_text


def test_load_dotfile_bundle_reads_config_sections(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    home = tmp_path / "home"

    bundle = load_dotfile_bundle(root / "git", home)

    assert bundle.name == "git"
    assert bundle.symlinks[0][0] == "config"
    assert bundle.symlinks[0][1] == home / ".config" / "git" / "config"
    assert bundle.questions == (
        ("name", "What is your name?"),
        ("email", "What is your email?"),
    )
    assert bundle.create == (("user", home / ".config" / "git" / "user"),)
    assert bundle.keys is not None
    assert bundle.keys.ssh_private == home / ".ssh" / "id_ed25519"
    assert bundle.keys.gpg_public == home / ".config" / "git" / "gpg-public-key.asc"


def test_load_dotfile_bundle_rejects_paths_outside_home(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "config.toml").write_text(
        '[symlink]\nconfig = "~/.config/../../../outside"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="escapes the home directory"):
        load_dotfile_bundle(bundle, tmp_path / "home")


def test_link_dotfile_creates_symlink_and_backup(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("new", encoding="utf-8")
    destination = tmp_path / "destination"
    destination.write_text("old", encoding="utf-8")

    outcome = link_dotfile(source, destination)

    assert outcome.changed is True
    assert outcome.backup is not None
    assert destination.is_symlink()
    assert destination.resolve() == source
    assert outcome.backup.read_text(encoding="utf-8") == "old"


def test_link_dotfile_leaves_correct_symlink_unchanged(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("new", encoding="utf-8")
    destination = tmp_path / "destination"
    destination.symlink_to(source)

    outcome = link_dotfile(source, destination)

    assert outcome.changed is False
    assert outcome.backup is None
    assert destination.resolve() == source


def test_link_dotfile_restores_backup_when_symlink_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.write_text("new", encoding="utf-8")
    destination = tmp_path / "destination"
    destination.write_text("old", encoding="utf-8")

    original_backup = dotfiles_module._backup_path
    backups: list[Path] = []

    def record_backup(path: Path) -> Path:
        backup = original_backup(path)
        backups.append(backup)
        return backup

    def fail_symlink(self: Path, target: str | Path) -> Path:
        raise OSError("symlink blocked")

    monkeypatch.setattr(dotfiles_module, "_backup_path", record_backup)
    monkeypatch.setattr(Path, "symlink_to", fail_symlink)

    with pytest.raises(OSError, match="symlink blocked"):
        link_dotfile(source, destination)

    assert destination.read_text(encoding="utf-8") == "old"
    assert len(backups) == 1
    assert not backups[0].exists()


def test_create_from_template_renders_and_is_idempotent(tmp_path: Path) -> None:
    template = tmp_path / "template"
    template.write_text("{name} <{email}> {signing_key}\n", encoding="utf-8")
    destination = tmp_path / "user"
    values = {"name": "Armoghan", "email": "a@example.com", "signing_key": FINGERPRINT}

    assert create_from_template(template, destination, values) is True
    assert destination.read_text(encoding="utf-8") == f"Armoghan <a@example.com> {FINGERPRINT}\n"
    assert create_from_template(template, destination, values) is False


def test_ensure_ssh_key_creates_key_and_public_export(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = make_bundle(tmp_path)
    home = tmp_path / "home"
    keys = load_dotfile_bundle(root / "git", home).keys
    assert keys is not None
    calls: list[list[str]] = []
    monkeypatch.setattr(
        subprocess,
        "run",
        fake_key_commands(calls, [False]),
    )

    info = ensure_ssh_key(keys, "test@example.com", lambda: "secret")

    assert info.created is True
    assert info.private_key == home / ".ssh" / "id_ed25519"
    assert info.public_key == home / ".ssh" / "id_ed25519.pub"
    assert stat.S_IMODE(info.private_key.stat().st_mode) == 0o600
    assert any("ssh-keygen" in command and "-t" in command for command in calls)


def test_ensure_ssh_key_skips_existing_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = make_bundle(tmp_path)
    home = tmp_path / "home"
    keys = load_dotfile_bundle(root / "git", home).keys
    assert keys is not None
    keys.ssh_private.parent.mkdir(parents=True)
    keys.ssh_private.write_text("existing private key\n", encoding="utf-8")
    keys.ssh_public.write_text("existing public key\n", encoding="utf-8")

    def fail_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("ssh-keygen should not run")

    def fail_passphrase() -> str:
        raise AssertionError("passphrase should not be requested")

    monkeypatch.setattr(subprocess, "run", fail_run)

    info = ensure_ssh_key(keys, "test@example.com", fail_passphrase)

    assert info.created is False
    assert info.public_key.read_text(encoding="utf-8") == "existing public key\n"


def test_ensure_gpg_key_creates_exports_and_uses_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = make_bundle(tmp_path)
    home = tmp_path / "home"
    keys = load_dotfile_bundle(root / "git", home).keys
    assert keys is not None
    calls: list[list[str]] = []
    monkeypatch.setattr(
        subprocess,
        "run",
        fake_key_commands(calls, [False]),
    )

    info = ensure_gpg_key(keys, "Armoghan", "a@example.com", lambda: "secret")

    assert info.created is True
    assert info.fingerprint == FINGERPRINT
    assert info.public_key == home / ".config" / "git" / "gpg-public-key.asc"
    assert "-----BEGIN PGP PUBLIC KEY BLOCK-----" in info.public_key.read_text(encoding="utf-8")
    assert any("--quick-generate-key" in command for command in calls)


def test_ensure_gpg_key_reuses_existing_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = make_bundle(tmp_path)
    home = tmp_path / "home"
    keys = load_dotfile_bundle(root / "git", home).keys
    assert keys is not None

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "--list-secret-keys" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                f"fpr:::::::::{FINGERPRINT}:\n",
                "",
            )
        if "--export" in command:
            return subprocess.CompletedProcess(command, 0, "PUBLIC KEY\n", "")
        raise AssertionError("generation should not run")

    def fail_passphrase() -> str:
        raise AssertionError("passphrase should not be requested")

    monkeypatch.setattr(subprocess, "run", fake_run)

    info = ensure_gpg_key(keys, "Armoghan", "a@example.com", fail_passphrase)

    assert info.created is False
    assert info.fingerprint == FINGERPRINT


def test_run_dotfiles_step_skips_when_no_bundles_are_found(tmp_path: Path) -> None:
    result = dotfiles_module.run_dotfiles_step(home=tmp_path, source=tmp_path / "missing")
    assert result is DotfileResult.SKIPPED


def test_run_dotfiles_step_skips_without_interactive_terminal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ui, "is_interactive", lambda: False)
    root = make_bundle(tmp_path)

    result = dotfiles_module.run_dotfiles_step(home=tmp_path / "home", source=root)

    assert result is DotfileResult.SKIPPED


def test_run_dotfiles_step_skips_when_declined(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)
    root = make_bundle(tmp_path)

    result = dotfiles_module.run_dotfiles_step(home=tmp_path / "home", source=root)

    assert result is DotfileResult.SKIPPED


def test_run_dotfiles_step_applies_bundle_and_generates_keys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = make_bundle(tmp_path)
    home = tmp_path / "home"
    calls: list[list[str]] = []
    generated = [False]

    def fake_prompt(message: str, **kwargs: object) -> str:
        answers = {
            "What is your name?": "Armoghan",
            "What is your email?": "a@example.com",
        }
        return answers[message]

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(ui, "prompt_text", fake_prompt)
    monkeypatch.setattr(ui, "password", lambda *args, **kwargs: "secret")
    monkeypatch.setattr(
        subprocess,
        "run",
        fake_key_commands(calls, generated),
    )

    result = dotfiles_module.run_dotfiles_step(home=home, source=root)

    assert result is DotfileResult.COMPLETED
    assert (home / ".config" / "git" / "config").is_symlink()
    user_config = (home / ".config" / "git" / "user").read_text(encoding="utf-8")
    assert "name = Armoghan" in user_config
    assert "email = a@example.com" in user_config
    assert f"signingkey = {FINGERPRINT}" in user_config
    assert (home / ".ssh" / "id_ed25519.pub").is_file()
    assert (home / ".config" / "git" / "gpg-public-key.asc").is_file()
    assert any("--quick-generate-key" in command for command in calls)


def test_run_dotfiles_step_reports_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = make_bundle(tmp_path)

    def fail_keys(*args: object, **kwargs: object) -> None:
        raise RuntimeError("key generation failed")

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(ui, "prompt_text", lambda *args, **kwargs: "Armoghan")
    monkeypatch.setattr(ui, "password", lambda *args, **kwargs: "secret")
    monkeypatch.setattr(dotfiles_module, "ensure_ssh_key", fail_keys)

    result = dotfiles_module.run_dotfiles_step(home=tmp_path / "home", source=root)

    assert result is DotfileResult.FAILED
