---
description: Complete reference for the welcome, snapshot, cleanup, directory, dotfile, package, container, plugin, hypr, and scripts commands in Omarchy Tweaker.
icon: material/console-line
subtitle: CLI reference
mermaid: true
---

# Commands

Complete reference for the currently implemented Omarchy Tweaker commands.

| Command | Changes system | Requires TTY | Key option |
|:--|:--:|:--:|:--|
| *(none)* | Only if you confirm | For interactive steps | — |
| `welcome` | No | No | — |
| `snapshot` | Yes | Unless `--yes` | `--yes`, `-y` |
| `cleanup` | Yes | Yes | — |
| `directories` | Yes | Yes | — |
| `dotfiles` | Yes | Yes | — |
| `packages` | Yes | Yes | — |
| `containers` | Yes | Yes | — |
| `plugins` | Yes | Yes | — |
| `hypr` | Yes | Yes | — |
| `scripts` | Yes | Yes | — |

```mermaid
flowchart TD
    A[omarchy-tweaker] --> B{Subcommand?}
    B -- None --> C[Default sequence]
    B -- welcome --> D[Read-only system overview]
    B -- snapshot --> E{--yes?}
    E -- Yes --> F[Run snapshot]
    E -- No --> G{TTY?}
    G -- Yes --> H[Confirm, then run]
    G -- No --> I[Skip with warning]
    B -- cleanup --> J{TTY?}
    J -- Yes --> K[Select, confirm, remove]
    J -- No --> L[Skip with warning]
    B -- directories --> M{TTY?}
    M -- Yes --> N[Confirm each missing directory]
    M -- No --> O[Skip with warning]
    B -- dotfiles --> AE{TTY?}
    AE -- Yes --> AF[Confirm, prepare keys, link and render dotfiles]
    AE -- No --> AG[Skip with warning]
    B -- packages --> P{TTY?}
    P -- Yes --> Q[Select, confirm, install]
    P -- No --> R[Skip with warning]
    B -- containers --> S{TTY?}
    S -- Yes --> T[Select, prepare, configure Caddy, start containers]
    S -- No --> U[Skip with warning]
    B -- plugins --> V{TTY?}
    V -- Yes --> W[Select, confirm, install plugins and shell config]
    V -- No --> X[Skip with warning]
    B -- hypr --> Y{TTY?}
    Y -- Yes --> Z[Confirm, link config, load workspaces]
    Y -- No --> AA[Skip with warning]
    B -- scripts --> AB{TTY?}
    AB -- Yes --> AC[Confirm, make scripts executable, link into PATH]
    AB -- No --> AD[Skip with warning]
```

---

## Global behavior

```bash
omarchy-tweaker [OPTIONS] COMMAND [ARGS]...
```

| Behavior | Details |
|:--|:--|
| No arguments | Runs the default sequence: banner, snapshot, cleanup, directories, dotfiles, packages, containers, plugins, hypr, and scripts. |
| With a subcommand | Shows the banner, then runs the selected command. |
| `--help` | Shows global help and the available commands. |
| Completion | Disabled. |
| Shell execution | External commands use argument lists, not `shell=True`. |

!!! note "No arguments is not the same as `--help`"
    Running `omarchy-tweaker` starts the interactive default workflow. Use `omarchy-tweaker --help` to inspect commands without starting the workflow.

### Choose a command

| Goal | Command |
|:--|:--|
| Inspect the system and confirm the installation works | `omarchy-tweaker welcome` |
| Create a recovery point before making changes | `omarchy-tweaker snapshot` |
| Review and remove selected packages or launchers | `omarchy-tweaker cleanup` |
| Create the standard workspace directories | `omarchy-tweaker directories` |
| Link bundled dotfiles and prepare signing keys | `omarchy-tweaker dotfiles` |
| Install selected Pacman and AUR packages | `omarchy-tweaker packages` |
| Prepare and start selected Docker containers | `omarchy-tweaker containers` |
| Install selected Omarchy shell plugins | `omarchy-tweaker plugins` |
| Link the bundled Hyprland configuration | `omarchy-tweaker hypr` |
| Make bundled scripts executable and link them into `~/.local/bin/` | `omarchy-tweaker scripts` |
| Run the full guided workflow | `omarchy-tweaker` |
| See every command and option | `omarchy-tweaker --help` |

### Exit codes

| Code | Meaning |
|:--:|:--|
| `0` | The command completed, or the step was skipped safely. |
| `1` | A selected operation failed, such as snapshot creation, item removal, directory creation, dotfile setup, package installation, container setup, plugin installation, Hyprland configuration, or script linking. |

A skipped step is not a failure. For example, declining a snapshot, running cleanup without a TTY, declining every directory, declining dotfile setup, selecting no packages, selecting no containers, selecting no
plugins, declining the Hyprland configuration, or declining script linking exits successfully.

---

## `welcome`

Show the welcome screen and a system overview.

```bash
omarchy-tweaker welcome
```

The screen includes:

- A welcome panel.
- Operating system and kernel.
- Desktop environment.
- CPU model, thread count, and architecture.
- GPU description when `lspci` is available.
- Memory and disk usage.
- Uptime.
- Hostname.

The command does not modify the system.

---

## `snapshot`

Create a system snapshot with `omarchy snapshot create`.

```bash
omarchy-tweaker snapshot
omarchy-tweaker snapshot --yes
omarchy-tweaker snapshot -y
```

| Option | Description |
|:--|:--|
| `--yes`, `-y` | Skip the confirmation prompt. |

### Behavior

1. Prints a **System Snapshot** section.
2. Asks for confirmation unless `--yes` is supplied.
3. Runs `omarchy snapshot create` inside a virtual terminal.
4. Streams command output into a bounded terminal panel.
5. Reports success or failure.

### Confirmation

The prompt defaults to **yes**. Declining skips the snapshot without failing the command.

### Non-interactive use

| Invocation | Result |
|:--|:--|
| `omarchy-tweaker snapshot` without a TTY | Skips with a warning. |
| `omarchy-tweaker snapshot --yes` without a TTY | Runs the snapshot command. |

### Timeout

The snapshot command has a **600 second** timeout.

### Requirements

- `omarchy` must be on `PATH`.
- Omarchy's snapshot tooling must be configured and working.

If the command fails, run `omarchy snapshot create` directly to inspect the underlying error.

---

### Snapshot flow

```mermaid
sequenceDiagram
    actor User
    participant CLI as omarchy-tweaker
    participant Omarchy
    User->>CLI: snapshot --yes
    CLI->>CLI: Start virtual terminal
    CLI->>Omarchy: omarchy snapshot create
    Omarchy-->>CLI: Stream output
    CLI-->>User: Report success or failure
```

## `cleanup`

Discover installed Omarchy cleanup targets, present them as selectable lists, and remove only the items you explicitly choose.

```bash
omarchy-tweaker cleanup
```

Cleanup has no command-line options. It always uses the interactive selection workflow.

### Behavior

1. Discovers installed packages, web apps, TUIs, and Mise wrappers.
2. Prints a separate table and checkbox prompt for each non-empty category.
3. Shows a summary of selected items.
4. Asks for final confirmation.
5. Removes packages in a virtual terminal.
6. Removes launchers and Mise wrappers with a progress display.
7. Reports removed and failed items.

### Categories

| Category | Source |
|:--|:--|
| **Packages** | Omarchy preinstalled package list, filtered by `pacman -Qq`. |
| **Web Apps** | Desktop launchers using `omarchy-launch-webapp` or `omarchy-webapp-handler`. |
| **TUIs** | Desktop launchers using `$TERMINAL` or `xdg-terminal-exec` with `-e`. |
| **Mise Wrappers** | Regular, non-symlink files in `~/.local/bin` containing `mise use -g`. |

### Non-interactive use

`omarchy-tweaker cleanup` requires an interactive terminal. Without one, it prints a warning and skips without removing anything.

### Failure handling

If any selected item cannot be removed, cleanup reports the failed items and exits with code `1`.

See **[Cleanup](cleanup.md)** for discovery rules, removal commands, and safety details.

---

## `directories`

Create the standard workspace directories used by this personal Omarchy setup.

```bash
omarchy-tweaker directories
```

Directories has no command-line options. It asks about each missing target individually.

### Behavior

1. Inspects the fixed target paths beneath your home directory.
2. Leaves existing directories untouched.
3. Asks for confirmation before creating each missing directory.
4. Creates accepted directories one level at a time.
5. Skips children when their parent is unavailable.
6. Reports created, existing, skipped, and failed paths.

### Targets

| Path | Purpose |
|:--|:--|
| `~/Github` | Git repositories. |
| `~/Github/Clone` | Cloned repositories. |
| `~/Projects` | Personal projects. |
| `~/Projects/Containers` | Container projects. |
| `~/.ISO` | ISO images. |
| `~/.VM` | Virtual machines. |
| `~/.Cloud` | Cloud storage. |

### Non-interactive use

`omarchy-tweaker directories` requires an interactive terminal for missing directories.
Without one, it prints a warning and skips without creating anything. Existing directories
are recognized without prompting.

### Failure handling

An existing file, broken symlink, or creation error at a target path is reported as a
failure and exits with code `1`. Existing directories are never overwritten.

See **[Directories](directories.md)** for the full workflow and safety model.

---

## `packages`

Install selected Pacman and AUR packages from a fixed catalog.

```bash
omarchy-tweaker packages
```

Packages has no command-line options. It always uses the interactive selection workflow.
Package installation runs in the default sequence and is also available as the standalone `packages` command.

### Behavior

1. Lets you select Pacman packages.
2. Summarizes the selection and asks for confirmation.
3. Runs `sudo -v` so the password prompt appears before the live display starts, then
   verifies the cached timestamp with `sudo -n -v`.
4. Installs selected Pacman packages with
   `sudo pacman -S --noconfirm --needed --noprogressbar <packages...>`.
5. Lets you select AUR packages.
6. Summarizes the selection and asks for confirmation.
7. Installs selected AUR packages with
   `yay -S --noconfirm --needed --noprogressbar <packages...>`.
8. Reports success or failure for each group.

Each group runs inside a virtual terminal with a progress display in the same live view. A
failure in one group does not prevent the other group from being offered.

### Non-interactive use

`omarchy-tweaker packages` requires an interactive terminal. Without one, it prints a
warning and skips without installing anything.

### Failure handling

If any selected package group fails, packages reports the failure and exits with code `1`.
Each group has a **900 second** timeout.

### Requirements

- `pacman` must be on `PATH`.
- `yay` must be on `PATH` for the AUR group.
- `sudo` may be required for the Pacman group.
- Package repositories and the AUR must be reachable.

See **[Packages](packages.md)** for the full package catalog and safety details.

---

## `containers`

Prepare Docker Compose projects and start selected containers.

```bash
omarchy-tweaker containers
```

Containers has no command-line options. It always uses the interactive selection workflow.
Container setup runs in the default sequence after packages and is also available as the
standalone `containers` command.

### Behavior

1. Loads container definitions from `src/omarchy_tweaker/containers/`.
2. Lets you select containers.
3. Asks for confirmation before preparing anything.
4. Creates `~/Projects/Containers/<container>`, copies the compose file, and links the
   container's configuration files into the runtime directory.
5. Creates `.env` from `.env.example`, offering automatic generation for secrets and
   prompting for the remaining values. Existing `.env` files are kept and must not
   reference unset variables.
6. Creates configured host symlinks, backing up an existing destination first.
7. Resolves Compose `container_name` conflicts by offering to stop and rename the
   conflicting container.
8. Optionally copies the global and each container Caddyfile into `/etc/caddy/omarchy-tweaker/`
   and merges a managed import block into the host Caddyfile, preserving imports for containers
   that were not selected in the current run.
9. Starts and enables Caddy when needed, then reloads it after the configuration changes.
10. Starts each prepared container with `docker compose up -d --remove-orphans`.

Each container runs inside a virtual terminal with a progress display in the same live view.

### Non-interactive use

`omarchy-tweaker containers` requires an interactive terminal. Without one, it prints a
warning and skips without preparing or starting anything.

### Failure handling

A preparation, Caddy, or Docker Compose failure is reported and exits with code `1`. A
failure for one container does not prevent the remaining selected containers from being
processed. Compose operations have a **900 second** timeout.

### Requirements

- `docker` and the Docker Compose plugin must be on `PATH`.
- Caddy must be installed for reverse-proxy configuration.
- `sudo` is required to update the host Caddyfile and reload Caddy.

See **[Containers](containers.md)** for the catalog layout, manifest format, symlinks, and
Caddy details.

---

## `plugins`

Install selected Omarchy shell plugins from a fixed catalog.

```bash
omarchy-tweaker plugins
```

Plugins has no command-line options. It always uses the interactive selection workflow.
Plugin installation runs in the default sequence and is also available as the standalone `plugins` command.

### Behavior

1. Loads the bundled plugin catalog from `src/omarchy_tweaker/config/plugins.ini`.
2. Lets you select plugins.
3. Asks for confirmation before cloning anything.
4. Installs each selected plugin with `omarchy plugin add <url> --yes --enable`.
   Plugins that are already installed are detected by repository URL and skipped.
5. Applies a configured `position` with `omarchy plugin enable <id> --section <position>`.
6. Runs the matching patch from `patches/` when the catalog enables one.
7. Reports success or failure for each plugin.
8. Replaces `~/.config/omarchy/shell.json` with the bundled shell configuration after
   successful installation, backing up any existing file first.

Each plugin runs inside a virtual terminal with a progress display in the same live view. A
failure in one plugin does not prevent the remaining selected plugins from being processed.

### Non-interactive use

`omarchy-tweaker plugins` requires an interactive terminal. Without one, it prints a
warning and skips without installing anything. The underlying `omarchy plugin add` command
is invoked non-interactively with `--yes`.

### Failure handling

If any selected plugin fails, plugins reports the failure and exits with code `1`. An
already-installed plugin is not a failure; it is reported and skipped. Plugin add operations
have a **300 second** timeout, enable operations have a **60 second** timeout, and patch
scripts have a **120 second** timeout.

If shell config installation fails, the plugin installation is still reported, but the
command exits with code `1`. The existing shell config is backed up to
`~/.config/omarchy/shell.json.bak.<timestamp>` before replacement, and the new file is made
read-only (`root:root`, mode `444`).

### Requirements

- `omarchy` must be on `PATH`.
- `git` must be available for `omarchy plugin add`.
- `bash` and `gum` are required by the bundled patch scripts.
- `sudo` is required to install and protect the shell configuration.
- Plugin repositories must be reachable.

See **[Plugins](plugins.md)** for the full catalog, placement rules, and patch details.

---

## `hypr`

Link the bundled Hyprland Lua configuration into `~/.config/hypr/` and load the workspaces module.

```bash
omarchy-tweaker hypr
```

Hypr has no command-line options. It runs last in the default sequence and is also available as
a standalone command.

### Behavior

1. Discovers the regular files in `src/omarchy_tweaker/hypr/`.
2. Lists the files and asks for confirmation before changing anything.
3. Creates `~/.config/hypr/` when it is missing.
4. Links each bundled file to the matching name in `~/.config/hypr/`.
5. Appends `require("hypr.workspaces")` to `hyprland.lua` unless the line is already present.

Bundled files include `bindings.lua`, `input.lua`, `looknfeel.lua`, and `workspaces.lua`.
A symlink that already points at the correct bundled file is left alone; other files are
replaced without a backup.

### Non-interactive use

`omarchy-tweaker hypr` requires an interactive terminal. Without one, it prints a warning and
skips without changing anything.

### Failure handling

A link failure or an unreadable `hyprland.lua` is reported and exits with code `1`. When a link
fails, the workspaces require line is not added.

### Requirements

- `~/.config/hypr/hyprland.lua` must exist and be readable and writable.
- The bundled files in `src/omarchy_tweaker/hypr/` must be present.

See **[Hyprland](hypr.md)** for the bundled file catalog, symlink behavior, and safety details.

---

## `dotfiles`

Link bundled dotfile catalogs, prepare configured SSH and GPG keys, and render templates.

```bash
omarchy-tweaker dotfiles
```

Dotfiles has no command-line options. It runs after directory setup in the default
sequence and is also available as a standalone command.

### Behavior

1. Discovers directories containing `config.toml` under `src/omarchy_tweaker/dotfiles/`.
2. Validates every configured destination and asks for confirmation per catalog.
3. Collects answers from `[ask]`.
4. Generates SSH and GPG keys when `[keys]` is present.
5. Symlinks entries from `[symlink]` after backing up existing files.
6. Renders entries from `[create]` from bundled templates.

The bundled Git catalog links the main Git configuration, Catppuccin Delta theme,
commit template, global ignore file, secret patterns, and hooks directory. It renders
`~/.config/git/user` using the collected name, email, and GPG fingerprint. The bundled
Lazygit catalog links a Catppuccin Mocha TUI configuration to
`~/.config/lazygit/config.yml`. The bundled Tig catalog links a Catppuccin Mocha-oriented
text-mode Git interface configuration to `~/.config/tig/config`. The bundled Starship
catalog links the Catppuccin Mocha prompt configuration to `~/.config/starship.toml`. See
**[Dotfiles](dotfiles.md)** for the workflow, **[Git Dotfiles](git.md)** for Git usage and
cheat sheets, **[Lazygit Dotfiles](lazygit.md)** for TUI usage and keybindings,
**[Tig Dotfiles](tig.md)** for Tig usage and keybindings, and
**[Starship Dotfiles](starship.md)** for prompt usage and cheat sheets.

### Non-interactive use

`omarchy-tweaker dotfiles` requires an interactive terminal. Without one, it prints a
warning and skips without changing anything.

### Failure handling

Invalid configuration, missing bundled sources, key-command failures, and write errors
are reported per catalog. Other catalogs still run. The command exits with code `1` when
any catalog failed. Declining confirmation is a safe skip and exits with code `0`.

### Requirements

- `ssh-keygen` and `gpg` must be available when keys are configured.
- `lazygit`, `delta`, `nvim`, `tig`, and `xdg-open` are needed for the features used by the bundled lazygit config.
- `tig`, `delta`, `meld`, and `wl-copy` are needed for the features used by the bundled Tig config.
- The user home directory must be writable.
- The bundled files in `src/omarchy_tweaker/dotfiles/` must be present.

See **[Dotfiles](dotfiles.md)** for configuration, backups, and safety details,
**[Git Dotfiles](git.md)** for the Git-specific usage guide,
**[Lazygit Dotfiles](lazygit.md)** for the lazygit TUI guide,
**[Tig Dotfiles](tig.md)** for the Tig text-mode guide, and
**[Starship Dotfiles](starship.md)** for the Starship prompt guide.

---

## `scripts`

Make the bundled helper scripts executable and link them into `~/.local/bin/`.

```bash
omarchy-tweaker scripts
```

Scripts has no command-line options. It runs last in the default sequence and is also
available as a standalone command.

### Behavior

1. Discovers the regular files in `src/omarchy_tweaker/script/`.
2. Lists the scripts and warns about names that already exist in `~/.local/bin/`.
3. Asks for one confirmation before changing anything.
4. Creates `~/.local/bin/` when it is missing.
5. Adds execute bits to each bundled script when they are missing.
6. Links each bundled script into `~/.local/bin/` under its original name.

Bundled scripts include `create-vm`, `macos-vm`, `setup-security-fingerprint`,
`snapshot`, and `windows-vm`. A symlink that already points at the correct bundled
script is left alone; other entries are replaced without a backup.

### Non-interactive use

`omarchy-tweaker scripts` requires an interactive terminal. Without one, it prints a
warning and skips without changing anything.

### Failure handling

A failed bin directory creation, permission change, or symlink creation is reported by
name and exits with code `1`. Declining the confirmation is a safe skip and exits with
code `0`.

### Requirements

- The user home directory must be writable so `~/.local/bin/` can be created.
- The bundled files in `src/omarchy_tweaker/script/` must be present.

See **[Bundled Scripts](scripts.md)** for the catalog, symlink behavior, and safety details.

---

## Environment variables

| Variable | Purpose |
|:--|:--|
| `OMARCHY_TWEAKER_LOG_DIR` | Override the log directory. |
| `XDG_STATE_HOME` | Base directory for logs when the override is unset. |
| `OMARCHY_REMOVE_NOTIFY` | Set to `false` internally during removal to suppress Omarchy removal notifications. |
| `OMARCHY_TWEAKER_PATCHES_DIR` | Override the directory used for plugin patch scripts. |
| `OMARCHY_TWEAKER_CONTAINERS_DIR` | Override the bundled container catalog directory. |
| `OMARCHY_TWEAKER_CONTAINERS_ROOT` | Override the prepared-container directory. |
| `OMARCHY_TWEAKER_CADDY_CONFIG` | Override the host Caddyfile path. |
| `OMARCHY_TWEAKER_CADDY_DIR` | Override the managed Caddy snippet directory. |
| `OMARCHY_TWEAKER_HYPR_DIR` | Override the directory containing bundled Hyprland files. |
| `OMARCHY_TWEAKER_DOTFILES_DIR` | Override the directory containing bundled dotfile catalogs. |
| `OMARCHY_TWEAKER_SCRIPTS_DIR` | Override the directory containing bundled helper scripts. |

Logs default to `$XDG_STATE_HOME/omarchy_tweaker/logs/` or `~/.local/state/omarchy_tweaker/logs/`.

---

## Examples

### Inspect the current system

```bash
omarchy-tweaker welcome
```

### Create a snapshot for automation

```bash
omarchy-tweaker snapshot --yes
```

### Review cleanup candidates without removing anything

```bash
omarchy-tweaker cleanup
```

Then press ++enter++ at each prompt without selecting items. Nothing is removed when the final selection is empty.

### Create the workspace directories

```bash
omarchy-tweaker directories
```

### Install selected packages

```bash
omarchy-tweaker packages
```

### Install selected plugins

```bash
omarchy-tweaker plugins
```

### Apply the bundled Hyprland configuration

```bash
omarchy-tweaker hypr
```

### Apply bundled dotfiles

```bash
omarchy-tweaker dotfiles
```

### Link the bundled helper scripts

```bash
omarchy-tweaker scripts
```

### Show global help

```bash
omarchy-tweaker --help
```

---

## Related pages

- [Getting Started](getting-started.md)
- [Cleanup](cleanup.md)
- [Directories](directories.md)
- [Packages](packages.md)
- [Plugins](plugins.md)
- [Hyprland](hypr.md)
- [Dotfiles](dotfiles.md)
- [Git Dotfiles](git.md)
- [Lazygit Dotfiles](lazygit.md)
- [Tig Dotfiles](tig.md)
- [Starship Dotfiles](starship.md)
- [Bundled Scripts](scripts.md)
- [Troubleshooting](troubleshooting.md)
