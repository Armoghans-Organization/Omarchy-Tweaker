from __future__ import annotations

import os
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


def _completed(
    returncode: int = 0,
    *,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


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
directories = ["data"]

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
    assert specs[0].directories == ("data",)
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


def test_bundled_atuin_caddyfile_is_statically_valid() -> None:
    atuin = next(spec for spec in load_container_specs() if spec.slug == "atuin")
    caddyfile = atuin.caddyfile.read_text(encoding="utf-8")

    assert "http://atuin-ai.localhost" in caddyfile
    assert "reverse_proxy 127.0.0.1:6900" in caddyfile
    assert "http://chat.atuin-ai.localhost" in caddyfile
    assert "http://models.atuin-ai.localhost" in caddyfile
    assert "rewrite /api/cli/chat" in caddyfile
    assert "rewrite /api/cli/models" in caddyfile


def test_bundled_open_webui_manifest_exposes_expected_assets() -> None:
    specs = load_container_specs()
    webui = next(spec for spec in specs if spec.slug == "open-webui")

    assert webui.name == "Open WebUI"
    assert webui.symlinks == ()
    assert webui.generated_env == ("WEBUI_SECRET_KEY",)
    assert webui.compose_file.is_file()
    assert webui.env_example_file.is_file()
    assert webui.caddyfile.is_file()


def test_bundled_open_webui_compose_is_statically_valid() -> None:
    webui = next(spec for spec in load_container_specs() if spec.slug == "open-webui")
    compose = webui.compose_file.read_text(encoding="utf-8")

    assert "container_name: OpenWebUi" in compose
    assert "network_mode: host" in compose
    assert "PORT=${PORT:?set PORT in .env}" in compose
    assert "WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY:?set WEBUI_SECRET_KEY in .env}" in compose
    assert "OLLAMA_BASE_URLS=${OLLAMA_BASE_URL:-http://ollama.localhost}" in compose
    assert "OPENAI_API_BASE_URL=${OMNIROUTE_URL:-http://omniroute.localhost}" in compose
    assert "${HOME}/Projects/Containers/open-webui/data:/app/backend/data" in compose

    caddyfile = webui.caddyfile.read_text(encoding="utf-8")
    assert "http://open-webui.localhost" in caddyfile
    assert "reverse_proxy 127.0.0.1:6901" in caddyfile


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
    assert (runtime / "data").is_dir()

    env_text = (runtime / ".env").read_text(encoding="utf-8")
    assert "AUTH_TOKEN=" in env_text
    assert "AUTH_TOKEN=replace_with_a_long_random_secret" not in env_text
    assert "DEMO_API_KEY=real-api-key" in env_text
    assert stat.S_IMODE((runtime / ".env").stat().st_mode) == 0o600

    assert destination.is_symlink()
    assert destination.resolve() == (runtime / "config.toml").resolve()
    backups = list(destination.parent.glob("config.toml.bak.*"))
    assert len(backups) == 1


def test_prepare_container_fixes_unwritable_runtime_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    runtime = tmp_path / "root" / "demo-service"
    (runtime / "data").mkdir(parents=True)
    commands: list[Sequence[str]] = []

    def fake_run(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(list(command))
        return _completed()

    monkeypatch.setattr(containers_module, "_directory_is_writable", lambda path: False)
    monkeypatch.setattr(containers_module, "_run_process", fake_run)
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(ui, "prompt_text", lambda *args, **kwargs: "real-api-key")

    assert prepare_container(spec, home=home, containers_root=tmp_path / "root") is True
    assert commands == [
        [
            "sudo",
            "chown",
            "-R",
            f"{os.getuid()}:{os.getgid()}",
            str(runtime / "data"),
        ]
    ]


def test_prepare_container_keeps_unwritable_runtime_directory_when_declined(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    runtime = tmp_path / "root" / "demo-service"
    (runtime / "data").mkdir(parents=True)

    monkeypatch.setattr(containers_module, "_directory_is_writable", lambda path: False)
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)

    assert prepare_container(spec, home=home, containers_root=tmp_path / "root") is False


def test_load_container_specs_rejects_unsafe_directory_entry(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    _write(
        catalog / "demo-service" / "container.toml",
        """
[container]
name = "Demo Service"
directories = ["../escape"]
""",
    )

    assert load_container_specs(catalog) == ()


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


def test_install_global_caddy_snippet_copies_catalog_file(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    global_caddyfile = catalog / "Caddyfile"
    _write(global_caddyfile, "http://omarchy.localhost {\n    reverse_proxy 127.0.0.1:1313\n}\n")
    caddy_directory = tmp_path / "caddy"

    snippet = containers_module.install_global_caddy_snippet(
        caddy_directory=caddy_directory,
        global_caddyfile=global_caddyfile,
    )

    assert snippet is not None
    assert snippet == caddy_directory / containers_module.GLOBAL_CADDYFILE_SNIPPET_NAME
    assert snippet.is_file()
    assert snippet.read_text(encoding="utf-8") == global_caddyfile.read_text(encoding="utf-8")


def test_install_global_caddy_snippet_returns_none_when_missing(tmp_path: Path) -> None:
    assert (
        containers_module.install_global_caddy_snippet(
            caddy_directory=tmp_path / "caddy",
            global_caddyfile=tmp_path / "missing",
        )
        is None
    )


def test_install_caddy_config_preserves_existing_snippet_imports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(containers_module, "_validate_caddy_config", lambda content: True)
    caddy_directory = tmp_path / "snippets"
    caddy_directory.mkdir()
    existing_snippet = caddy_directory / "snapotter.caddy"
    _write(existing_snippet, "snapotter.localhost {}\n")
    new_snippet = caddy_directory / "atuin.caddy"
    _write(new_snippet, "atuin-ai.localhost {}\n")
    config = tmp_path / "Caddyfile"
    _write(
        config,
        "# Existing\n\n"
        + containers_module.CADDY_INCLUDE_BEGIN
        + "\n"
        + "# Managed by Omarchy Tweaker. Do not edit this block by hand.\n"
        + f'import "{existing_snippet}"\n'
        + containers_module.CADDY_INCLUDE_END
        + "\n",
    )

    assert containers_module.install_caddy_config([new_snippet], config_path=config) is True

    content = config.read_text(encoding="utf-8")
    assert str(existing_snippet) in content
    assert str(new_snippet) in content
    assert content.count("import ") == 2


def test_install_caddy_config_deduplicates_snippet_imports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(containers_module, "_validate_caddy_config", lambda content: True)
    snippet = tmp_path / "snippets" / "demo.caddy"
    _write(snippet, "demo.localhost {}\n")
    config = tmp_path / "Caddyfile"
    _write(config, "# Existing\n")

    assert containers_module.install_caddy_config([snippet], config_path=config) is True
    assert containers_module.install_caddy_config([snippet], config_path=config) is True

    content = config.read_text(encoding="utf-8")
    assert content.count("import ") == 1
    assert len(list(tmp_path.glob("Caddyfile.bak.*"))) == 1


def test_spec_snippet_path_uses_slug(tmp_path: Path) -> None:
    spec = _spec(tmp_path)

    assert spec.snippet_path.name == f"{spec.slug}.caddy"


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


def test_bundled_omniroute_manifest_exposes_expected_assets() -> None:
    specs = load_container_specs()
    omniroute = next(spec for spec in specs if spec.slug == "omniroute")

    assert omniroute.name == "OmniRoute"
    assert omniroute.generated_env == ("OMNIROUTE_WS_BRIDGE_SECRET",)
    assert omniroute.directories == ("data",)
    assert omniroute.compose_file.is_file()
    assert omniroute.env_example_file.is_file()
    assert omniroute.caddyfile.is_file()
    assert (omniroute.directory / "discover.sh").is_file()
    assert not (omniroute.directory / "compose.agents.yaml").exists()


def test_bundled_snapotter_manifest_exposes_expected_assets() -> None:
    specs = load_container_specs()
    snapotter = next(spec for spec in specs if spec.slug == "snapotter")

    assert snapotter.name == "SnapOtter"
    assert snapotter.generated_env == ("SNAPOTTER_PASSWORD", "POSTGRES_PASSWORD")
    assert snapotter.directories == ("data", "pgdata", "redisdata")
    assert snapotter.compose_file.is_file()
    assert snapotter.env_example_file.is_file()
    assert snapotter.caddyfile.is_file()


def test_bundled_snapotter_compose_is_statically_valid() -> None:
    snapotter = next(spec for spec in load_container_specs() if spec.slug == "snapotter")
    compose = snapotter.compose_file.read_text(encoding="utf-8")

    assert "container_name: snapotter" in compose
    assert "network_mode: host" not in compose
    assert "snapotter-internal" in compose
    assert '"127.0.0.1:6907:1349"' in compose
    assert "DATABASE_URL" in compose
    assert "DATABASE_MIGRATION_URL" in compose
    assert "REDIS_URL" in compose
    assert "redis://redis:6379" in compose
    assert "@postgres:5432" in compose
    assert "ports:" not in compose.split("postgres:")[1].split("redis:")[0]


def test_bundled_omniroute_compose_is_statically_valid() -> None:
    omniroute = next(spec for spec in load_container_specs() if spec.slug == "omniroute")
    compose = omniroute.compose_file.read_text(encoding="utf-8")

    assert "container_name: omniroute" in compose
    assert "network_mode: host" in compose
    assert "CLI_MOUNTS_FILE" not in compose
    assert "compose.agents.yaml:/app" not in compose
    assert "/host-mise/installs" not in compose
    assert 'CLI_EXTRA_PATHS: "/host-node/bin:/usr/local/bin:/host-local/bin"' in compose
    assert "CLI_MODE: auto" in compose
    assert "CLI_CONFIG_HOME: /home/node" in compose
    assert "${HOME}/Projects/Containers/omniroute/data:/app/data" in compose
    assert "${HOME}/Projects/Containers/omniroute/redis:/data" in compose
    assert "/home/armoghan" not in compose


def test_bundled_omniroute_env_example_has_no_machine_specific_paths() -> None:
    omniroute = next(spec for spec in load_container_specs() if spec.slug == "omniroute")
    template = omniroute.env_example_file.read_text(encoding="utf-8")

    assert "/home/" not in template
    assert "HOST_NODE_BIN=\n" in template


def test_detect_host_node_bin_prefers_environment_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOST_NODE_BIN", "/custom/node/bin")

    assert containers_module._detect_host_node_bin() == "/custom/node/bin"


def test_detect_host_node_bin_falls_back_to_path_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HOST_NODE_BIN", raising=False)
    monkeypatch.setattr(
        "omarchy_tweaker.functions.containers.shutil.which",
        lambda name: "/opt/node/bin/node" if name == "node" else None,
    )

    assert containers_module._detect_host_node_bin() == "/opt/node/bin"


def test_detect_host_node_bin_returns_none_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HOST_NODE_BIN", raising=False)
    monkeypatch.setattr(
        "omarchy_tweaker.functions.containers.shutil.which",
        lambda name: None,
    )

    assert containers_module._detect_host_node_bin() is None


def test_auto_detect_env_default_maps_host_node_bin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        containers_module,
        "_detect_host_node_bin",
        lambda: "/detected/node/bin",
    )

    assert containers_module._auto_detect_env_default("HOST_NODE_BIN") == "/detected/node/bin"
    assert containers_module._auto_detect_env_default("API_PORT") is None


def test_ensure_omniroute_cli_returns_true_when_already_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(containers_module, "_installed_npm_version", lambda: "3.8.52")
    monkeypatch.setattr(containers_module, "_npm_package_outdated", lambda package: False)

    assert containers_module.ensure_omniroute_cli() is True


def test_ensure_omniroute_cli_updates_when_outdated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[Sequence[str]] = []

    def fake_run(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(list(command))
        return _completed()

    monkeypatch.setattr(containers_module, "_installed_npm_version", lambda: "3.8.0")
    monkeypatch.setattr(containers_module, "_npm_package_outdated", lambda package: True)
    monkeypatch.setattr(
        "omarchy_tweaker.functions.containers.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(containers_module, "_run_process", fake_run)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    assert containers_module.ensure_omniroute_cli() is True
    assert ["/usr/bin/npm", "install", "-g", "omniroute"] in commands


def test_ensure_omniroute_cli_keeps_installed_when_update_declined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[Sequence[str]] = []

    def fake_run(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(list(command))
        return _completed()

    monkeypatch.setattr(containers_module, "_installed_npm_version", lambda: "3.8.0")
    monkeypatch.setattr(containers_module, "_npm_package_outdated", lambda package: True)
    monkeypatch.setattr(containers_module, "_run_process", fake_run)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)

    assert containers_module.ensure_omniroute_cli() is True
    assert commands == []


def test_ensure_omniroute_cli_installs_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[Sequence[str]] = []

    def fake_run(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(list(command))
        return _completed()

    monkeypatch.setattr(containers_module, "_installed_npm_version", lambda: None)
    monkeypatch.setattr(
        "omarchy_tweaker.functions.containers.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(containers_module, "_run_process", fake_run)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    assert containers_module.ensure_omniroute_cli() is True
    assert ["/usr/bin/npm", "install", "-g", "omniroute"] in commands


def test_ensure_omniroute_cli_returns_false_when_declined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(containers_module, "_installed_npm_version", lambda: None)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)

    assert containers_module.ensure_omniroute_cli() is False


def test_ensure_omniroute_cli_returns_false_when_npm_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(containers_module, "_installed_npm_version", lambda: None)
    monkeypatch.setattr(
        "omarchy_tweaker.functions.containers.shutil.which",
        lambda name: None,
    )
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)

    assert containers_module.ensure_omniroute_cli() is False


def test_discover_agent_mounts_runs_discover_script(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[Sequence[str]] = []

    def fake_run(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(list(command))
        return _completed()

    _write(tmp_path / "discover.sh", "#!/usr/bin/env bash\nset -euo pipefail\n")
    _write(
        tmp_path / "compose.agents.yaml",
        'services:\n  omniroute:\n    volumes:\n      - "/home/agent/.claude:/host-home/.claude:rw"\n',
    )
    monkeypatch.setattr(containers_module, "_run_process", fake_run)

    mounts = containers_module.discover_agent_mounts(tmp_path)

    assert mounts == ('- "/home/agent/.claude:/host-home/.claude:rw"',)
    assert commands[0][:2] == ["bash", str(tmp_path / "discover.sh")]


def test_discover_agent_mounts_returns_empty_when_no_agents(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(containers_module, "_run_process", lambda command, **kwargs: _completed())
    _write(tmp_path / "discover.sh", "#!/usr/bin/env bash\nset -euo pipefail\n")
    _write(tmp_path / "compose.agents.yaml", "services:\n  omniroute:\n    volumes:\n")

    assert containers_module.discover_agent_mounts(tmp_path) == ()


def test_discover_agent_mounts_returns_none_when_script_missing(tmp_path: Path) -> None:
    assert containers_module.discover_agent_mounts(tmp_path) is None


def test_discover_agent_mounts_returns_none_when_script_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        containers_module,
        "_run_process",
        lambda command, **kwargs: _completed(1),
    )
    _write(tmp_path / "discover.sh", "#!/usr/bin/env bash\nset -euo pipefail\n")

    assert containers_module.discover_agent_mounts(tmp_path) is None


def test_discover_script_emits_real_cli_paths(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    mise_root = tmp_path / "mise"
    fake_bin = tmp_path / "bin"
    node_bin = home / "node" / "bin"

    for directory in (
        home / ".claude",
        home / ".config" / "opencode",
        home / ".pi" / "agent",
        home / ".hermes",
        home / ".omp" / "agent",
        home / ".grok",
        home / ".local" / "bin",
        home / ".local" / "share" / "mise" / "installs",
        node_bin,
        mise_root / "claude" / "latest",
        mise_root / "codex" / "latest" / "bin",
        fake_bin,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    claude = mise_root / "claude" / "latest" / "claude"
    codex = mise_root / "codex" / "latest" / "bin" / "codex"
    for binary in (claude, codex):
        _write(binary, "#!/usr/bin/env bash\n")
        binary.chmod(0o755)

    shim = home / ".local" / "bin" / "claude"
    _write(shim, '#!/usr/bin/env bash\nmise x claude -- claude "$@"\n')
    shim.chmod(0o755)

    mise = fake_bin / "mise"
    _write(
        mise,
        "#!/usr/bin/env bash\n"
        'case "$2" in\n'
        f'  claude) printf "%s\\n" "{claude}" ;;\n'
        f'  codex) printf "%s\\n" "{codex}" ;;\n'
        "  *) exit 1 ;;\n"
        "esac\n",
    )
    mise.chmod(0o755)

    _write(tmp_path / ".env", f"HOST_NODE_BIN={node_bin}\n")
    script = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "omarchy_tweaker"
        / "containers"
        / "omniroute"
        / "discover.sh"
    )
    environment = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "OMNIROUTE_ENV_FILE": ".env",
    }
    subprocess.run(
        ["bash", str(script)],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    compose = (tmp_path / "compose.agents.yaml").read_text(encoding="utf-8")
    assert f'CLI_CLAUDE_BIN: "{claude}"' in compose
    assert f'CLI_CODEX_BIN: "{codex}"' in compose
    assert "/host-local/bin/claude" not in compose
    assert "mise x claude" not in compose
    assert 'PI_CODING_AGENT_DIR: "/home/node/.pi/agent"' in compose
    assert 'HERMES_HOME: "/home/node/.hermes"' in compose
    assert f'"{home}/.config/opencode:/home/node/.config/opencode:rw"' in compose
    assert f'"{home}/.omp:/home/node/.omp:rw"' in compose
    assert f'"{home}/.grok:/home/node/.grok:rw"' in compose
    assert "/host-home" not in compose

    extra = next(line for line in compose.splitlines() if "CLI_EXTRA_PATHS:" in line)
    assert extra.startswith('      CLI_EXTRA_PATHS: "/host-node/bin:')
    assert extra.endswith(':/host-local/bin"')

    path = next(line for line in compose.splitlines() if line.startswith("      PATH:"))
    assert "/usr/local/bin" in path
    assert "/usr/bin" in path


class _RecordingConsole:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def print(self, *args: object, **kwargs: object) -> None:
        self.lines.extend(str(arg) for arg in args)


def test_connect_omniroute_cli_prints_base_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    console = _RecordingConsole()
    monkeypatch.setattr(ui, "get_console", lambda: console)
    _write(tmp_path / ".env", "BASE_URL=http://127.0.0.1:6905\nREQUIRE_API_KEY=false\n")

    assert containers_module.connect_omniroute_cli(tmp_path) is True
    assert "export OMNIROUTE_BASE_URL=http://127.0.0.1:6905" in console.lines


def test_connect_omniroute_cli_derives_url_from_api_port(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    console = _RecordingConsole()
    monkeypatch.setattr(ui, "get_console", lambda: console)
    _write(tmp_path / ".env", "API_PORT=7000\n")

    assert containers_module.connect_omniroute_cli(tmp_path) is True
    assert "export OMNIROUTE_BASE_URL=http://127.0.0.1:7000" in console.lines


def test_connect_omniroute_cli_mentions_api_key_when_required(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    console = _RecordingConsole()
    monkeypatch.setattr(ui, "get_console", lambda: console)
    monkeypatch.delenv("OMNIROUTE_API_KEY", raising=False)
    _write(tmp_path / ".env", "BASE_URL=http://127.0.0.1:6905\nREQUIRE_API_KEY=true\n")

    assert containers_module.connect_omniroute_cli(tmp_path) is True
    assert any("OMNIROUTE_API_KEY" in line for line in console.lines)


def test_connect_omniroute_cli_returns_false_without_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ui, "get_console", lambda: _RecordingConsole())

    assert containers_module.connect_omniroute_cli(tmp_path) is False


def test_connect_omniroute_cli_offers_shell_profile_update(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    profile = tmp_path / ".zshrc"
    monkeypatch.setattr(ui, "get_console", lambda: _RecordingConsole())
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    _write(
        tmp_path / ".env",
        "BASE_URL=http://127.0.0.1:6905\nREQUIRE_API_KEY=false\n",
    )

    assert containers_module.connect_omniroute_cli(tmp_path, profile_path=profile) is True
    content = profile.read_text(encoding="utf-8")
    assert "# >>> omarchy-tweaker omniroute >>>" in content
    assert "# <<< omarchy-tweaker omniroute <<<" in content
    assert "export OMNIROUTE_BASE_URL=http://127.0.0.1:6905" in content


def test_connect_omniroute_cli_prints_manual_instructions_when_declined(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    console = _RecordingConsole()
    profile = tmp_path / ".zshrc"
    monkeypatch.setattr(ui, "get_console", lambda: console)
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)
    _write(tmp_path / ".env", "BASE_URL=http://127.0.0.1:6905\n")

    assert containers_module.connect_omniroute_cli(tmp_path, profile_path=profile) is True
    assert not profile.exists()
    assert any("Add these lines" in line for line in console.lines)
    assert any("export OMNIROUTE_BASE_URL=http://127.0.0.1:6905" in line for line in console.lines)


def test_update_shell_profile_is_idempotent(tmp_path: Path) -> None:
    profile = tmp_path / ".zshrc"
    _write(profile, "export PATH=$PATH:/existing\n")
    lines = ["export OMNIROUTE_BASE_URL=http://127.0.0.1:6905"]

    assert containers_module._update_shell_profile(profile, lines)
    assert containers_module._update_shell_profile(profile, lines)

    content = profile.read_text(encoding="utf-8")
    assert content.count(containers_module.OMNIROUTE_RC_BEGIN) == 1
    assert "export PATH=$PATH:/existing" in content


def test_update_shell_profile_preserves_user_api_key(tmp_path: Path) -> None:
    profile = tmp_path / ".zshrc"
    lines = [
        "export OMNIROUTE_BASE_URL=http://127.0.0.1:6905",
        "# Create an API key in the dashboard, then uncomment and set it:",
        '# export OMNIROUTE_API_KEY="<dashboard-api-key>"',
    ]

    assert containers_module._update_shell_profile(profile, lines)
    content = profile.read_text(encoding="utf-8")
    content = content.replace(
        '# export OMNIROUTE_API_KEY="<dashboard-api-key>"',
        'export OMNIROUTE_API_KEY="real-key"',
    )
    profile.write_text(content, encoding="utf-8")

    assert containers_module._update_shell_profile(profile, lines)
    updated = profile.read_text(encoding="utf-8")
    assert updated.count('export OMNIROUTE_API_KEY="real-key"') == 1
    assert updated.count('OMNIROUTE_API_KEY="<dashboard-api-key>"') == 0


def test_update_shell_profile_backs_up_existing_profile(tmp_path: Path) -> None:
    profile = tmp_path / ".zshrc"
    _write(profile, "export PATH=$PATH:/existing\n")

    assert containers_module._update_shell_profile(
        profile, ["export OMNIROUTE_BASE_URL=http://127.0.0.1:6905"]
    )

    backups = list(tmp_path.glob(".zshrc.*.bak"))
    assert len(backups) == 1
    assert "export PATH=$PATH:/existing" in backups[0].read_text(encoding="utf-8")


BOOTSTRAP_LOG_LINE = (
    "2026-11-15T01:13:52.907676177Z [omniroute] [BOOTSTRAP] Fresh install detected "
    "from a non-loopback peer (e.g. a Docker port-forwarded connection) with no "
    "password configured yet. Paste this ONE-TIME bootstrap token into the onboarding "
    "wizard to continue: S8Dll5Lmy4MobPxaLSaW38Ma73zD45Jm"
)


def test_find_bootstrap_token_parses_log_line() -> None:
    assert (
        containers_module._find_bootstrap_token(BOOTSTRAP_LOG_LINE)
        == "S8Dll5Lmy4MobPxaLSaW38Ma73zD45Jm"
    )


def test_find_bootstrap_token_returns_none_for_unrelated_logs() -> None:
    assert containers_module._find_bootstrap_token("server listening on 6905\n") is None


def test_find_bootstrap_token_ignores_initial_password_message() -> None:
    log = (
        "[bootstrap] INFO  INITIAL_PASSWORD is unset here. Unless a .env file that "
        "Next.js loads sets it, a fresh install asks you to create the dashboard "
        "password in the onboarding wizard.\n"
    )

    assert containers_module._find_bootstrap_token(log) is None


def test_find_bootstrap_token_skips_to_real_token_after_noise() -> None:
    log = "\n".join(
        (
            "[bootstrap] INITIAL_PASSWORD is unset here. Unless a .env file sets it.",
            "[bootstrap] JWT_SECRET auto-generated (first run)",
            "[sqljsAdapter] save failed: EACCES",
            "[BOOTSTRAP] Fresh install detected from a non-loopback peer with no "
            "password configured yet. Paste this ONE-TIME bootstrap token into the "
            "onboarding wizard to continue: i3smeVvGDNun04I2N_tmTwblpoBCtOLg",
            "[sqljsAdapter] save failed: EACCES",
        )
    )

    assert containers_module._find_bootstrap_token(log) == "i3smeVvGDNun04I2N_tmTwblpoBCtOLg"


def test_find_bootstrap_token_returns_none_when_token_is_missing() -> None:
    log = (
        "[BOOTSTRAP] Paste this ONE-TIME bootstrap token into the onboarding wizard to continue:\n"
    )

    assert containers_module._find_bootstrap_token(log) is None


def test_onboarding_url_prefers_public_base_url(tmp_path: Path) -> None:
    _write(
        tmp_path / ".env",
        "NEXT_PUBLIC_BASE_URL=http://omniroute.localhost/\nDASHBOARD_PORT=6904\n",
    )

    assert containers_module._onboarding_url(tmp_path) == (
        "http://omniroute.localhost/dashboard/onboarding"
    )


def test_onboarding_url_falls_back_to_dashboard_port(tmp_path: Path) -> None:
    _write(tmp_path / ".env", "DASHBOARD_PORT=7001\n")

    assert containers_module._onboarding_url(tmp_path) == (
        "http://127.0.0.1:7001/dashboard/onboarding"
    )


def test_docker_log_text_reads_since_window(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[Sequence[str]] = []

    def fake_run(command: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(list(command))
        return _completed(stdout=BOOTSTRAP_LOG_LINE)

    monkeypatch.setattr(
        "omarchy_tweaker.functions.containers.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(containers_module, "_run_process", fake_run)

    text = containers_module._docker_log_text("omniroute", since="2026-11-15T01:00:00+00:00")

    assert "BOOTSTRAP" in text
    assert commands[0] == [
        "/usr/bin/docker",
        "logs",
        "--since",
        "2026-11-15T01:00:00+00:00",
        "omniroute",
    ]


def test_show_bootstrap_token_returns_existing_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ui, "get_console", lambda: _RecordingConsole())
    monkeypatch.setattr(ui, "is_interactive", lambda: False)
    monkeypatch.setattr(
        containers_module,
        "_docker_log_text",
        lambda *args, **kwargs: BOOTSTRAP_LOG_LINE,
    )

    assert containers_module.show_bootstrap_token(tmp_path) == "S8Dll5Lmy4MobPxaLSaW38Ma73zD45Jm"


def test_show_bootstrap_token_prints_hint_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    console = _RecordingConsole()
    monkeypatch.setattr(ui, "get_console", lambda: console)
    monkeypatch.setattr(ui, "is_interactive", lambda: False)
    monkeypatch.setattr(containers_module, "_docker_log_text", lambda *args, **kwargs: "")
    _write(tmp_path / ".env", "NEXT_PUBLIC_BASE_URL=http://omniroute.localhost\n")

    assert containers_module.show_bootstrap_token(tmp_path) is None
    assert any("grep BOOTSTRAP" in line for line in console.lines)


def test_show_bootstrap_token_waits_when_confirmed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ui, "get_console", lambda: _RecordingConsole())
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(containers_module, "_docker_log_text", lambda *args, **kwargs: "")
    monkeypatch.setattr(
        containers_module,
        "_wait_for_bootstrap_token",
        lambda *args, **kwargs: "W4itedT0kenAbcdefghijklmnop123456",
    )

    assert containers_module.show_bootstrap_token(tmp_path) == "W4itedT0kenAbcdefghijklmnop123456"


def test_show_bootstrap_token_skips_wait_when_declined(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ui, "get_console", lambda: _RecordingConsole())
    monkeypatch.setattr(ui, "is_interactive", lambda: True)
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)
    monkeypatch.setattr(containers_module, "_docker_log_text", lambda *args, **kwargs: "")
    monkeypatch.setattr(
        containers_module,
        "_wait_for_bootstrap_token",
        lambda *args, **kwargs: pytest.fail("should not wait"),
    )

    assert containers_module.show_bootstrap_token(tmp_path) is None


def test_wait_for_bootstrap_token_returns_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Status:
        def update(self, message: str) -> None:
            pass

    class Spinner:
        def __enter__(self) -> Status:
            return Status()

        def __exit__(self, *args: object) -> None:
            pass

    responses = iter(["", BOOTSTRAP_LOG_LINE])
    monkeypatch.setattr(
        containers_module,
        "_docker_log_text",
        lambda *args, **kwargs: next(responses),
    )
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    monkeypatch.setattr(ui, "spinner", lambda *args, **kwargs: Spinner())

    assert (
        containers_module._wait_for_bootstrap_token(
            "omniroute", since="2026-11-15T01:00:00+00:00", timeout=30.0
        )
        == "S8Dll5Lmy4MobPxaLSaW38Ma73zD45Jm"
    )


def test_read_env_value_reads_rendered_values(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    _write(env_path, "# comment\nOMNIROUTE_BASE_URL=http://127.0.0.1:6905\nOTHER=value\n")

    assert containers_module._read_env_value(env_path, "OMNIROUTE_BASE_URL") == (
        "http://127.0.0.1:6905"
    )
    assert containers_module._read_env_value(env_path, "MISSING") is None


def test_create_env_file_prefills_detected_host_node_bin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalog"
    container = catalog / "node-service"
    _write(container / "docker-compose.yml", "services:\n  svc:\n    image: svc:latest\n")
    _write(container / ".env.example", "HOST_NODE_BIN=\nOTHER=value\n")
    spec = load_container_specs(catalog)[0]
    runtime = tmp_path / "root" / "node-service"
    runtime.mkdir(parents=True)
    monkeypatch.setattr(
        containers_module,
        "_detect_host_node_bin",
        lambda: "/detected/node/bin",
    )
    monkeypatch.setattr(ui, "confirm", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        ui,
        "prompt_text",
        lambda *args, **kwargs: kwargs.get("default", "value"),
    )

    assert containers_module._create_env_file(spec, runtime) is True
    env_text = (runtime / ".env").read_text(encoding="utf-8")
    assert "HOST_NODE_BIN=/detected/node/bin" in env_text


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
    assert list(commands[0]) == [
        "/usr/bin/docker",
        "compose",
        "-f",
        "docker-compose.yml",
        "up",
        "-d",
        "--remove-orphans",
    ]


def test_start_container_merges_generated_agents_file(
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

    _write(tmp_path / "compose.agents.yaml", "services:\n  demo-service:\n    volumes:\n")
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
    assert list(commands[0]) == [
        "/usr/bin/docker",
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "compose.agents.yaml",
        "up",
        "-d",
        "--remove-orphans",
    ]


def test_compose_file_arguments_include_agents_file_when_present(tmp_path: Path) -> None:
    assert containers_module._compose_file_arguments(tmp_path) == ["-f", "docker-compose.yml"]

    _write(tmp_path / "compose.agents.yaml", "services:\n  demo-service:\n    volumes:\n")

    assert containers_module._compose_file_arguments(tmp_path) == [
        "-f",
        "docker-compose.yml",
        "-f",
        "compose.agents.yaml",
    ]
