---
description: Usage examples, instructions, and cheat sheets for the bundled Starship prompt configuration.
icon: material/console
subtitle: Starship dotfile guide
mermaid: true
---

# Starship Dotfiles

This page is the practical usage guide for the custom Starship prompt configuration bundled
with Omarchy Tweaker. It explains what the custom setup does, how to use it, and how to
inspect or change each part.

For an explanation of the dotfile catalog system itself, see **[Dotfiles](dotfiles.md)**.

!!! note "Catalog scope"
    The Starship catalog only links the bundled configuration to `~/.config/starship.toml`.
    It does not install Starship, install a Nerd Font, or edit your shell startup file.

---

## What this custom setup gives you

The `starship` catalog installs a Catppuccin Mocha prompt with:

- A segmented left prompt for OS, user, directory, and Git state.
- A dense right prompt for language runtimes, containers, SSH context, time, and battery.
- Custom modules for QEMU/KVM VMs, Hugo projects, and terminal multiplexers.
- Nerd Font icons and Catppuccin colors defined directly in the config.
- Fast timeouts and conservative module behavior for interactive shell use.

```bash
omarchy-tweaker dotfiles
```

Accept the `starship` catalog when prompted.

---

## Quick start

```bash
omarchy-tweaker dotfiles
```

Then verify the linked config:

```bash
ls -l ~/.config/starship.toml
starship --version
starship config
starship explain
```

If the prompt does not appear, check your shell integration below.

---

## What gets installed

| Bundled source | Destination | What it does |
|:--|:--|:--|
| `starship` | `~/.config/starship.toml` | Complete Starship prompt config with Catppuccin Mocha palette, prompt layouts, modules, and custom modules. |

The catalog configuration is:

```text
src/omarchy_tweaker/dotfiles/starship/config.toml
```

It contains a single `[symlink]` entry:

```toml
[symlink]
starship = "~/.config/starship.toml"
```

No prompts, templates, or key setup are involved.

---

## Shell integration

The dotfile command links the config but does not enable Starship in your shell. If your
shell startup file does not already initialize Starship, add the matching line.

For zsh:

```bash
eval "$(starship init zsh)"
```

Then restart the shell:

```bash
exec zsh
```

Check the available integration commands with:

```bash
starship init zsh
```

!!! warning "The destination is a symlink"
    Editing `~/.config/starship.toml` in place writes through to the bundled source file.
    For temporary experiments this is fine. For permanent personal changes, keep a separate
    copy or edit the catalog in a checkout and rerun `omarchy-tweaker dotfiles`.

---

## What the custom configuration does

### Global behavior

| Setting | Value | Effect |
|:--|:--|:--|
| `$schema` | `https://starship.rs/config-schema.json` | Enables editor validation for the TOML config. |
| `command_timeout` | `1000` | Caps slow module commands at about one second. |
| `scan_timeout` | `100` | Caps directory scans at about 100 ms. |
| `add_newline` | `true` | Adds a blank line before the prompt. |
| `continuation_prompt` | `[▸▹ ](dimmed white)` | Sets the prompt shown for multiline input. |
| `palette` | `catppuccin_mocha` | Selects the Catppuccin Mocha palette defined in the same file. |

### Left prompt

| Module | What it shows |
|:--|:--|
| `$os` | Distribution icon, with explicit symbols for Arch, Ubuntu, Fedora, Debian, and others. |
| `$username` | Current user, always shown; root uses red styling. |
| `$directory` | Current path with common folder substitutions and truncated length. |
| `$git_branch` | Attached Git branch, truncated to 20 characters. |
| `$git_state` | Rebase, merge, revert, cherry-pick, or bisect state. |
| `$git_metrics` | Added and deleted line counts when the diff is non-zero. |
| `$git_status` | Conflict, ahead/behind, untracked, staged, modified, renamed, deleted, and stashed state. |
| `$line_break` | Moves the character prompt to a new line after Git information. |
| `$character` | Green `❯` on success, red `❯` on failure, and Vim-mode variants. |

### Right prompt

| Module | What it shows |
|:--|:--|
| `$status` | Failed command status. |
| `${custom.vms}` | Count of running QEMU/KVM virtual machines. |
| `$container` | Container name when the shell is inside a container. |
| `$hostname` | Hostname only over SSH. |
| `$jobs` | Background job count when one or more jobs exist. |
| `$cpp`, `$cmake`, `$c` | C/C++/CMake toolchain versions. |
| `$python` | Python version and virtual environment. |
| `$nodejs`, `$rust`, `$golang` | Language runtime versions. |
| `$docker_context` | Active Docker context when Docker files are present. |
| `${custom.hugo}` | Hugo version inside a Hugo project. |
| `$localip` | Local IPv4 address only over SSH. |
| `$cmd_duration` | Duration of commands taking longer than one second. |
| `$package` | Package version in supported package projects. |
| `${custom.mux}` | Active Zellij or tmux session. |
| `$time` | Current time in `%I:%M %p` format. |
| `$battery` | Battery percentage with red and yellow warning thresholds. |

### Custom modules

| Module | Trigger | Command |
|:--|:--|:--|
| `custom.vms` | `pgrep` finds `qemu-system` | Counts QEMU/KVM processes with `pgrep -fc '[q]emu-system'`. |
| `custom.hugo` | Hugo is installed and a Hugo project layout is present | Runs `hugo version` and trims the output to the version. |
| `custom.mux` | `ZELLIJ` or `TMUX` is set | Prints `Zellij` or `tmux`. |

### Directory substitutions

| Path | Prompt label |
|:--|:--|
| `~` | `Home` |
| `Desktop` | `Desktop` |
| `Documents` | `Documents` |
| `Downloads` | `Downloads` |
| `.config` / `Config` | `Config` |
| `Github` / `github` | `Github` |
| `Gitlab` / `gitlab` | `Gitlab` |
| `node_modules` | `node_modules` |
| `.ssh` | `SSH` |

The directory module uses `truncation_length = 1` and an empty `truncation_symbol`.

### Git modules

| Setting | Effect |
|:--|:--|
| `git_branch.only_attached = true` | Shows the branch only when HEAD is attached. |
| `git_branch.truncation_length = 20` | Keeps long branch names compact. |
| `git_metrics.ignore_submodules = true` | Avoids submodule noise in added/deleted counts. |
| `git_metrics.only_nonzero_diffs = true` | Hides the metrics segment when there is no diff. |
| `git_status` symbols | Shows conflicts, ahead/behind counts, untracked, staged, modified, renamed, deleted, and stashed files. |

### Prompt character and status

| State | Symbol |
|:--|:--|
| Success | Green `❯` |
| Failure | Red `❯` |
| Vim command | Teal `❮` |
| Vim replace one | Lavender `❮` |
| Vim replace | Mauve `❮` |
| Vim visual | Yellow `❮` |
| Failed command status | Red `✘` |

### Battery thresholds

| Threshold | Style |
|:--|:--|
| 10% | Red, bold |
| 30% | Yellow |

---

## Custom configuration cheat sheet

### Inspect the active setup

| Task | Command |
|:--|:--|
| Show the linked config | `ls -l ~/.config/starship.toml` |
| Show the resolved source | `readlink -f ~/.config/starship.toml` |
| Print the effective config | `starship config` |
| Explain the current prompt | `starship explain` |
| Show Starship version | `starship --version` |
| Show zsh init script | `starship init zsh` |
| List configured section headings | `rg '^\[' ~/.config/starship.toml` |

### Common edits

| Goal | Setting to change |
|:--|:--|
| Change the theme | `palette` and the `[palettes.catppuccin_mocha]` table. |
| Disable a module | Remove it from `format` or `right_format`, or set its module `disabled = true`. |
| Change prompt colors | Edit the matching module `style` or `format` string. |
| Show more path segments | Increase `directory.truncation_length`. |
| Add a folder label | Add an entry under `[directory.substitutions]`. |
| Change branch length | Edit `git_branch.truncation_length`. |
| Hide VM count | Remove `${custom.vms}` from `right_format`. |
| Show command durations sooner | Lower `cmd_duration.min_time`. |
| Change the time format | Edit `time.time_format`. |
| Relax slow-module limits | Increase `command_timeout` or `scan_timeout`. |

After editing, reload the shell:

```bash
exec zsh
```

### Module requirement cheat sheet

| Module | Needed for it to appear |
|:--|:--|
| `$os` | Starship detects the distribution. |
| `$git_branch`, `$git_status` | Current directory is inside a Git repository. |
| `$python`, `$nodejs`, `$rust`, `$golang` | Corresponding runtime is installed and the directory looks like a project. |
| `$docker_context` | Docker context is available and Docker files are present. |
| `${custom.hugo}` | `hugo` is installed and a Hugo project layout is detected. |
| `${custom.vms}` | A `qemu-system` process is running and `pgrep` is available. |
| `${custom.mux}` | `ZELLIJ` or `TMUX` is set in the environment. |
| `$hostname`, `$localip` | The session is over SSH. |
| `$battery` | Battery information is exposed by the system. |
| `$status` | The previous command failed. |

---

## Verification

### Confirm Starship is active

```bash
starship --version
starship init zsh
starship explain
```

### Confirm the config is linked

```bash
ls -l ~/.config/starship.toml
readlink -f ~/.config/starship.toml
```

Expected source:

```text
src/omarchy_tweaker/dotfiles/starship/starship
```

### Confirm glyph rendering

The prompt uses Nerd Font icons such as `󰣇`, ``, and `❯`. If icons appear as boxes or
missing glyphs, configure a Nerd Font in your terminal and re-run `starship explain`.

---

## Backups and restore

If `~/.config/starship.toml` already exists as a regular file or an incorrect symlink, it is
backed up before replacement:

```text
starship.toml.bak.<YYYYMMDD-HHMMSS>
```

List backups:

```bash
ls -la ~/.config/starship.toml.bak.*
```

Restore the newest backup manually:

```bash
backup="$(ls -t ~/.config/starship.toml.bak.* | head -n 1)"
cp "$backup" ~/.config/starship.toml
```

If linking fails, the command attempts to restore the backup automatically.

---

## Customize the catalog

The catalog is controlled by:

```text
src/omarchy_tweaker/dotfiles/starship/config.toml
```

Current configuration:

```toml
[symlink]
starship = "~/.config/starship.toml"
```

Rules:

- The source name `starship` must match the bundled file name.
- The destination must start with `~/` and stay inside the home directory.
- Additional entries can be added to the catalog without changing Python code.

To add another prompt-related dotfile, place the file in the catalog directory and add
another `[symlink]` entry.

---

## Troubleshooting

| Symptom | Check |
|:--|:--|
| Prompt does not change | Confirm `eval "$(starship init zsh)"` is in `~/.zshrc`, then run `exec zsh`. |
| `starship: command not found` | Install Starship; the dotfile catalog only links configuration. |
| Icons appear as boxes | Install and select a Nerd Font in your terminal. |
| Config file is missing | Run `ls -l ~/.config/starship.toml` and rerun `omarchy-tweaker dotfiles`. |
| Edits disappear after rerunning dotfiles | Check whether you edited the symlink source; use a separate copy for personal changes. |
| Prompt feels slow | Increase `scan_timeout`, increase `command_timeout`, or remove expensive custom modules. |
| `custom.vms` never shows | Check `pgrep -f '[q]emu-system'` and whether a VM is running. |
| `custom.hugo` never shows | Check `command -v hugo` and whether the project has `hugo.toml`, `config.toml`, or `config/_default`. |
| `custom.mux` never shows | Check whether `ZELLIJ` or `TMUX` is set in the current shell. |
| Git modules do not show | Confirm the current directory is inside a Git repository and HEAD is attached. |
| Battery module does not show | Confirm the system exposes battery information to Starship. |
| Command skipped immediately | The dotfiles command requires an interactive terminal. |

---

## Safety notes

- The catalog only creates or replaces one symlink.
- Existing destinations are backed up before replacement.
- No shell startup file is modified automatically.
- No secrets, keys, or credentials are included in the prompt config.
- Custom modules run small local commands; remove any module you do not want to run.

---

## Related pages

- [Dotfiles](dotfiles.md)
- [Bat Dotfiles](bat.md)
- [Git Dotfiles](git.md)
- [Lazygit Dotfiles](lazygit.md)
- [Tig Dotfiles](tig.md)
- [Tmux Dotfiles](tmux.md)
- [Superfile Dotfiles](superfile.md)
- [Zellij Dotfiles](zellij.md)
- [Commands](commands.md)
- [Security](security.md)
- [Troubleshooting](troubleshooting.md)
