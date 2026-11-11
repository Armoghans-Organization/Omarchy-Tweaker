---
description: Common fixes for terminal prompts, Omarchy commands, snapshots, cleanup, and documentation builds.
icon: material/help-circle
subtitle: Fixes and diagnosis
mermaid: true
---

# Troubleshooting

Common problems and how to diagnose them.

```mermaid
flowchart TD
    A[Problem] --> B{Command found?}
    B -- No --> C[Install it or run through uv]
    B -- Yes --> D{Prompt skipped?}
    D -- Yes --> E[Use an interactive terminal]
    D -- No --> F{Omarchy command found?}
    F -- No --> G[Check PATH and Omarchy install]
    F -- Yes --> H{Snapshot or cleanup?}
    H -- Snapshot --> I[Run omarchy snapshot create]
    H -- Cleanup --> J[Check discovery rules]
    J --> K[See Cleanup]
```

| Symptom | Likely cause | Next step |
|:--|:--|:--|
| `omarchy-tweaker` not found | Checkout not on `PATH`, or tool bin directory missing | Run through `uv` or install globally. |
| Snapshot or cleanup skipped | No interactive TTY | Run directly in a terminal. |
| `omarchy` not found | Omarchy CLI not on `PATH` | Verify the Omarchy installation. |
| Snapshot fails | Snapshot tooling, permissions, or disk space | Run `omarchy snapshot create` directly. |
| Cleanup list is empty | Items do not match discovery rules | Check the category-specific commands below. |
| Removal fails | `sudo`, package state, or package-manager lock | Run the underlying Omarchy command directly. |
| Icons are missing | Terminal lacks a Nerd Font | Install and configure a Nerd Font. |
| Docs build fails | Generated files or broken links | See [Development](development.md#troubleshooting). |

---

## The `omarchy-tweaker` command is not found

From a source checkout, run it through `uv`:

```bash
uv run omarchy-tweaker --help
```

To install the command globally:

```bash
uv tool install .
```

If you already installed it, make sure uv's tool directory is on `PATH`:

```bash
uv tool dir --bin
```

---

## Interactive steps are skipped

Snapshot confirmation and cleanup selection require an interactive terminal. They check
that both standard input and standard output are TTYs.

```text
Snapshot skipped: confirmation requires an interactive terminal.
Cleanup skipped: selecting items requires an interactive terminal.
```

Run the command directly in a terminal instead of through a pipe, IDE runner, CI job, or
non-interactive shell. For snapshot automation, use `--yes`:

```bash
omarchy-tweaker snapshot --yes
```

Cleanup intentionally has no non-interactive removal mode.

---

## The `omarchy` command is not found

Omarchy Tweaker delegates snapshot and removal work to Omarchy commands.

```bash
command -v omarchy
```

If nothing is printed, `omarchy` is not on `PATH`. Confirm that you are running Omarchy
Linux and that the Omarchy CLI is installed and available in your shell.

---

## Snapshot creation fails

Run the underlying command directly:

```bash
omarchy snapshot create
```

Check that Omarchy's snapshot tooling is configured, `snapper` is available if your setup
uses it, there is enough disk space, and permissions are not blocking the operation.
Omarchy Tweaker uses a **600 second** timeout; a timeout is reported as a failure.

---

## Cleanup shows no items

Cleanup discovers items at runtime. Check the category that is empty:

| Category | Check | Rule |
|:--|:--|:--|
| Packages | `pacman -Qq` | Must be installed and in Omarchy's preinstall removal list. |
| Web apps | `ls ~/.local/share/applications/*.desktop` | `Exec` must use `omarchy-launch-webapp` or `omarchy-webapp-handler`. |
| TUIs | Same directory | `Exec` must use `$TERMINAL` or `xdg-terminal-exec` with `-e`. |
| Mise wrappers | `rg '^\s*mise use -g\b' ~/.local/bin` | Regular, non-symlink file up to **128,000 bytes**. |

See **[Cleanup](cleanup.md#discovery)** for the full discovery rules.

---

## Package removal fails

Run the underlying command directly:

```bash
omarchy pkg drop <package>
```

Common causes include a `sudo` password prompt or expired authentication, a package that is
no longer installed, another package-manager process holding a lock, or a package required
by another installed package. Cleanup reports failed items and exits with code `1`.

---

## A Mise wrapper cannot be removed

Cleanup only unlinks paths that are absolute, name a file, and resolve inside your home
directory. If the wrapper is a symlink or lives outside the home directory, cleanup refuses
to remove it. Remove it manually after verifying the path.

---

## Icons look wrong or are missing

The UI uses Nerd Font glyphs. Install a Nerd Font and configure your terminal to use it.
Missing glyphs do not affect functionality.

---

## Where are the logs?

Logs default to `$XDG_STATE_HOME/omarchy_tweaker/logs/` or
`~/.local/state/omarchy_tweaker/logs/`. List recent logs with:

```bash
ls -lt "${XDG_STATE_HOME:-$HOME/.local/state}/omarchy_tweaker/logs" | head
```

Override the directory for one run with `OMARCHY_TWEAKER_LOG_DIR`. See
**[Getting Started](getting-started.md#logs)** for locations and log contents. Review logs
before sharing them publicly.

---

### Collect diagnostics

```mermaid
sequenceDiagram
    actor User
    participant Terminal
    participant App as omarchy-tweaker
    participant Logs
    User->>Terminal: Run command
    Terminal->>App: Execute
    App-->>Terminal: Output and exit code
    App->>Logs: Write session log
    User->>Logs: Read recent log
```

## Still stuck?

Collect the following before opening an issue:

- The exact command you ran.
- The terminal output.
- The relevant log file.
- Your Omarchy version and Python version.
- Whether the command was run in an interactive terminal.

Report bugs at [GitHub Issues](https://github.com/Armoghans-Organization/Omarchy-Tweaker/issues).

---

## Related pages

- [Getting Started](getting-started.md)
- [Commands](commands.md)
- [Cleanup](cleanup.md)
- [Development](development.md)
