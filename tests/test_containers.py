from __future__ import annotations

import stat
import subprocess
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import cast

import pytest
from rich.progress import Progress

import omarchy_tweaker.functions.containers as containers_module
from omarchy_tweaker.functions import ui
from omarchy_tweaker.functions.containers import (
    ContainerResult,
    ContainerSpec,
    EnvVariable,
    generate_secret,
    install_caddy_config,
    install_caddy_snippet,
    load_container_specs,
    load_env_template,
    prepare_container,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _completed(returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr="")


def _catalog(tmp_path: Path) -> Path:
    directory = tmp_path / "catalog"
    container = directory / "demo-service"
    _write(
        container / "docker-compose.yml",
        "services:\n  demo:\n    image: demo:latest\n",
    )
    _write(
        container / ".env.example",
        "# Demo environment\n"
        "AUTH_TOKEN=replace_with_a_long_random_secret\n"
        "DEMO_API_KEY=replace_with_your_api_key\n",
    )
    _write(container / "Caddyfile", "demo.localhost {\n    reverse_proxy 127.0.0.1:8080\n}\n")
    _write(container / "config.toml", "port = 8080\n")
    _write(
        container / "container.toml",
        """
[container]
name = "Demo Service"
description = "A demo container."

[symlinks]
"config.toml" = "~/.config/demo/config.toml"

[env]
generate = ["AUTH_TOKEN"]
""",
    )
    return directory


def _spec(tmp_path: Path) -> ContainerSpec:
    specs = load_container_specs(_catalog(tmp_path))
    assert len(specs) == 1
    return specs[0]


@contextmanager
def _fake_terminal_with_progress(
    **kwargs: object,
) -> Iterator[tuple[ui.VirtualTerminal, Progress]]:
    yield (
        cast(ui.VirtualTerminal, object()),
        cast(Progress, object()),
    )


def test_load_container_specs_reads_manifest_and_defaults(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    _write(
        catalog / "plain" / "docker-compose.yml",
        "services:\n  plain:\n    image: plain:latest\n",
    )

    specs = load_container_specs(catalog)

    assert [spec.slug for spec in specs] == ["demo-service", "plain"]
    assert specs[0].name == "Demo Service"
    assert specs[0].description == "A demo container."
    assert specs[0].symlinks == (("config.toml", "~/.config/demo/config.toml"),)
    assert specs[0].generated_env == ("AUTH_TOKEN",)
    assert specs[1].name == "Plain"
    assert specs[1].symlinks == ()


def test_load_container_specs_skips_missing_compose_file(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog"
    (catalog / "empty").mkdir(parents=True)

    assert load_container_specs(catalog) == ()


def test_load_container_specs_skips_invalid_manifest(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    _write(catalog / "demo-service" / "container.toml", "not valid toml [[[")

    assert load_container_specs(catalog) == ()


def test_bundled_atuin_manifest_exposes_expected_assets() -> None:
    specs = load_container_specs()
    atuin = next(spec for spec in specs if spec.slug == "atuin")

    assert atuin.name == "Atuin AI Server"
    assert dict(atuin.symlinks) == {
        "config.toml": "~/.config/atuin-ai-server/config.toml",
        "atuin.toml": "~/.config/atuin/config.toml",
    }
    assert atuin.generated_env == ("AUTH_TOKEN",)
    assert atuin.compose_file.is_file()
    assert atuin.env_example_file.is_file()
    assert atuin.caddyfile.is_file()


def test_load_container_specs_rejects_unsafe_symlink_source(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    _write(
        catalog / "demo-service" / "container.toml",
        """
[symlinks]
"../outside" = "~/.config/outside"
""",
    )

    assert load_container_specs(catalog) == ()


def test_load_env_template_reads_keys_and_defaults(tmp_path: Path) -> None:
    template = tmp_path / ".env.example"
    _write(
        template,
        "# comment\n\nAUTH_TOKEN=abc\nexport API_KEY = def\nINVALID\nEMPTY=\n",
    )

    assert load_env_template(template) == (
        EnvVariable("AUTH_TOKEN", "abc"),
        EnvVariable("API_KEY", "def"),
        EnvVariable("EMPTY", ""),
    )


def test_generate_secret_returns_nonempty_url_safe_value() -> None:
    value = generate_secret()

    assert len(value) >= 32
    assert " " not in value


def test_host_path_expands_home_and_relative_paths(tmp_path: Path) -> None:
    assert containers_module._host_path("~/config/file", tmp_path) == tmp_path / "config/file"
    assert containers_module._host_path("~", tmp_path) == tmp_path
    assert containers_module._host_path("config/file", tmp_path) == tmp_path / "config/file"
    assert containers_module._host_path("/etc/file", tmp_path) == Path("/etc/file")


def test_render_env_replaces_values_and_preserves_comments() -> None:
    template = "# Header\nAUTH_TOKEN=old\nexport OTHER=value\n"

    rendered = containers_module._render_env(template, {"AUTH_TOKEN": "new", "OTHER": "updated"})

    assert rendered == "# Header\nAUTH_TOKEN=new\nexport OTHER=updated\n"


def test_replace_managed_block_appends_and_replaces() -> None:
    block = '# BEGIN omarchy-tweaker\nimport "a.caddy"\n# END omarchy-tweaker'

    appended = containers_module._replace_managed_block("# Existing\n", block)
    replaced = containers_module._replace_managed_block(
        "# Before\n\n# BEGIN omarchy-tweaker\nold\n# END omarchy-tweaker\n# After\n",
        block,
    )

    assert appended == "# Existing\n\n" + block + "\n"
    assert replaced == "# Before\n\n" + block + "\n\n# After\n\n"


def test_prepare_container_creates_runtime_files_and_symlinks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    destination = home / ".config" / "demo" / "config.toml"
    _write(destination, "old config\n")
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(ui, "prompt_text", lambda *args, **kwargs: "real-api-key")

    prepared = prepare_container(
        spec,
        home=home,
        containers_root=tmp_path / "root",
    )

    runtime = tmp_path / "root" / "demo-service"
    assert prepared is True
    assert (runtime / "docker-compose.yml").is_file()
    assert (runtime / "config.toml").is_symlink()
    assert (runtime / "Caddyfile").is_symlink()
    assert not (runtime / "container.toml").exists()
    assert not (runtime / ".env.example").exists()

    env_text = (runtime / ".env").read_text(encoding="utf-8")
    assert "AUTH_TOKEN=" in env_text
    assert "AUTH_TOKEN=replace_with_a_long_random_secret" not in env_text
    assert "DEMO_API_KEY=real-api-key" in env_text
    assert stat.S_IMODE((runtime / ".env").stat().st_mode) == 0o600

    assert destination.is_symlink()
    assert destination.resolve() == (runtime / "config.toml").resolve()
    backups = list(destination.parent.glob("config.toml.bak.*"))
    assert len(backups) == 1


def test_prepare_container_keeps_existing_env_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    runtime = tmp_path / "root" / "demo-service"
    _write(runtime / ".env", "AUTH_TOKEN=existing\n")
    monkeypatch.setattr(
        ui,
        "prompt_text",
        lambda *args, **kwargs: pytest.fail("env prompts should not run"),
    )

    assert prepare_container(spec, home=home, containers_root=tmp_path / "root") is True
    assert (runtime / ".env").read_text(encoding="utf-8") == "AUTH_TOKEN=existing\n"


def test_prepare_container_fails_when_required_value_is_blank(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)
    monkeypatch.setattr(ui, "prompt_text", lambda *args, **kwargs: "")

    assert prepare_container(spec, home=home, containers_root=tmp_path / "root") is False
    assert not (tmp_path / "root" / "demo-service" / ".env").exists()


def test_prepare_container_rejects_unresolved_env_references(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    runtime = tmp_path / "root" / "demo-service"
    _write(runtime / ".env", "AUTH_TOKEN=${OMARCHY_TEST_MISSING_TOKEN}\n")
    monkeypatch.delenv("OMARCHY_TEST_MISSING_TOKEN", raising=False)

    assert prepare_container(spec, home=home, containers_root=tmp_path / "root") is False


def test_unresolved_env_references_ignores_defined_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    _write(
        env_file,
        "TOKEN=${EXISTING}\nOTHER=$SECOND\nDEFINED=value\n",
    )
    monkeypatch.setenv("EXISTING", "yes")
    monkeypatch.setenv("SECOND", "yes")

    assert containers_module._unresolved_env_references(env_file) == ()


def test_unresolved_env_references_reports_missing_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    _write(env_file, "TOKEN=${MISSING_ONE}\nOTHER=$MISSING_TWO\n")

    assert containers_module._unresolved_env_references(env_file) == (
        "MISSING_ONE",
        "MISSING_TWO",
    )


def test_install_caddy_snippet_copies_caddyfile(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    caddy_directory = tmp_path / "caddy"

    snippet = install_caddy_snippet(spec, caddy_directory=caddy_directory)

    assert snippet is not None
    assert snippet.is_file()
    assert not snippet.is_symlink()
    assert snippet.read_text(encoding="utf-8") == spec.caddyfile.read_text(encoding="utf-8")


def test_install_caddy_config_writes_managed_block(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(containers_module, "_validate_caddy_config", lambda content: True)
    snippet = tmp_path / "snippets" / "demo.caddy"
    _write(snippet, "demo.localhost {}\n")
    config = tmp_path / "Caddyfile"
    _write(config, "# Existing\n")

    first = install_caddy_config([snippet], config_path=config)
    second = install_caddy_config([snippet], config_path=config)

    assert first is True
    assert second is True
    content = config.read_text(encoding="utf-8")
    assert content.startswith("# Existing")
    assert containers_module.CADDY_INCLUDE_BEGIN in content
    assert "import" in content
    assert str(snippet) in content
    assert len(list(tmp_path.glob("Caddyfile.bak.*"))) == 1


def test_install_caddy_config_rejects_invalid_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(containers_module, "_validate_caddy_config", lambda content: False)
    snippet = tmp_path / "demo.caddy"
    _write(snippet, "demo.localhost {}\n")
    config = tmp_path / "Caddyfile"
    _write(config, "# Existing\n")

    assert install_caddy_config([snippet], config_path=config) is False
    assert config.read_text(encoding="utf-8") == "# Existing\n"


def test_validate_caddy_config_uses_adapt(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(list(command))
        return _completed()

    monkeypatch.setattr(
        "omarchy_tweaker.functions.containers.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(containers_module, "_run_process", fake_run)

    assert containers_module._validate_caddy_config("demo.localhost {}\n") is True
    assert commands
    assert commands[0][1] == "adapt"


def test_compose_metadata_from_file_reads_names(tmp_path: Path) -> None:
    _write(
        tmp_path / "docker-compose.yml",
        "name: demo-project\nservices:\n  demo:\n    container_name: Demo-Service\n",
    )

    assert containers_module._compose_metadata_from_file(tmp_path) == (
        "demo-project",
        ("demo-service",),
    )


def test_resolve_container_name_conflicts_renames_existing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(list(command))
        return _completed()

    monkeypatch.setattr(
        containers_module,
        "_compose_metadata",
        lambda directory: ("demo-project", ("atuin-ai",)),
    )
    monkeypatch.setattr(
        containers_module,
        "_existing_container_project",
        lambda name: (True, None),
    )
    monkeypatch.setattr(
        "omarchy_tweaker.functions.containers.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(containers_module, "_run_process", fake_run)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    assert containers_module._resolve_container_name_conflicts(tmp_path) is True
    assert [command[:3] for command in commands] == [
        ["/usr/bin/docker", "rename", "atuin-ai"],
        ["/usr/bin/docker", "stop", commands[0][3]],
    ]


def test_resolve_container_name_conflicts_accepts_same_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        containers_module,
        "_compose_metadata",
        lambda directory: ("demo-project", ("atuin-ai",)),
    )
    monkeypatch.setattr(
        containers_module,
        "_existing_container_project",
        lambda name: (True, "demo-project"),
    )
    monkeypatch.setattr(
        ui,
        "confirm",
        lambda *args, **kwargs: pytest.fail("conflicting-project prompt should not run"),
    )

    assert containers_module._resolve_container_name_conflicts(tmp_path) is True


def test_resolve_container_name_conflicts_can_be_declined(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        containers_module,
        "_compose_metadata",
        lambda directory: ("demo-project", ("atuin-ai",)),
    )
    monkeypatch.setattr(
        containers_module,
        "_existing_container_project",
        lambda name: (True, None),
    )
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)

    assert containers_module._resolve_container_name_conflicts(tmp_path) is False


def test_ensure_caddy_running_starts_inactive_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(list(command))
        return _completed(3) if "is-active" in command else _completed()

    monkeypatch.setattr(
        "omarchy_tweaker.functions.containers.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(containers_module, "_run_process", fake_run)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    assert containers_module.ensure_caddy_running() is True
    assert commands[-1][:5] == ["/usr/bin/sudo", "systemctl", "enable", "--now", "caddy"]


def test_ensure_caddy_running_skips_active_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(list(command))
        return _completed()

    monkeypatch.setattr(
        "omarchy_tweaker.functions.containers.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(containers_module, "_run_process", fake_run)
    monkeypatch.setattr(
        ui,
        "confirm",
        lambda *args, **kwargs: pytest.fail("start prompt should not run"),
    )

    assert containers_module.ensure_caddy_running() is True
    assert commands == [["/usr/bin/systemctl", "is-active", "--quiet", "caddy"]]


def test_ensure_caddy_running_can_be_declined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "omarchy_tweaker.functions.containers.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        containers_module,
        "_run_process",
        lambda command, **kwargs: _completed(3),
    )
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)

    assert containers_module.ensure_caddy_running() is False


def test_run_containers_step_skips_without_interactive_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ui, "is_interactive", lambda: False)
    monkeypatch.setattr(
        ui,
        "checkbox",
        lambda *args, **kwargs: pytest.fail("selection should not run"),
    )

    assert containers_module.run_containers_step(containers=()) is ContainerResult.SKIPPED


def test_run_containers_step_skips_when_nothing_selected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "checkbox", lambda *args, **kwargs: [])

    assert containers_module.run_containers_step(containers=(spec,)) is ContainerResult.SKIPPED


def test_run_containers_step_skips_when_confirmation_declined(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "checkbox", lambda *args, **kwargs: [spec.name])
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)

    assert containers_module.run_containers_step(containers=(spec,)) is ContainerResult.SKIPPED


def test_run_containers_step_completes_and_starts_containers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    started: list[Path] = []

    def confirm(message: str, **kwargs: object) -> bool:
        if message.startswith("Generate"):
            return True
        if message.startswith("Create"):
            return True
        if message.startswith("Configure Caddy"):
            return False
        return False

    def start(
        container: ContainerSpec,
        runtime_directory: Path,
        **kwargs: object,
    ) -> bool:
        started.append(runtime_directory)
        return True

    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "checkbox", lambda *args, **kwargs: [spec.name])
    monkeypatch.setattr(ui, "confirm", confirm)
    monkeypatch.setattr(ui, "prompt_text", lambda *args, **kwargs: "key")
    monkeypatch.setattr(ui, "terminal_with_progress", _fake_terminal_with_progress)
    monkeypatch.setattr(containers_module, "_start_container", start)

    result = containers_module.run_containers_step(
        containers=(spec,),
        home=home,
        containers_root=tmp_path / "root",
    )

    assert result is ContainerResult.COMPLETED
    assert started == [tmp_path / "root" / "demo-service"]


def test_run_containers_step_reports_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "checkbox", lambda *args, **kwargs: [spec.name])
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(containers_module, "prepare_container", lambda *args, **kwargs: False)

    result = containers_module.run_containers_step(
        containers=(spec,),
        home=tmp_path / "home",
        containers_root=tmp_path / "root",
    )

    assert result is ContainerResult.FAILED


def test_start_container_reports_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    commands: list[Sequence[str]] = []

    class FakeTerminal:
        def run(self, command: Sequence[str], **kwargs: object) -> int:
            commands.append(command)
            return 0

        def writeline(self, line: str, **kwargs: object) -> None:
            pass

    class FakeProgress:
        def add_task(self, description: str, *, total: int | None = None) -> int:
            return 0

        def update(self, task_id: int, *, description: str) -> None:
            pass

        def advance(self, task_id: int) -> None:
            pass

    monkeypatch.setattr(
        "omarchy_tweaker.functions.containers.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )

    assert containers_module._start_container(
        spec,
        tmp_path,
        terminal=cast(ui.VirtualTerminal, FakeTerminal()),
        progress=cast(Progress, FakeProgress()),
    )
    assert commands
    assert list(commands[0])[:2] == ["/usr/bin/docker", "compose"]
