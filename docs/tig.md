---
description: Usage examples, instructions, and cheat sheets for the bundled Tig configuration.
icon: material/source-branch
subtitle: Tig dotfile guide
mermaid: true
---

# Tig Dotfiles

This page is the practical usage guide for the custom Tig configuration bundled with
Omarchy Tweaker. It explains what the custom setup does, how to use it day to day, and how
to inspect or change each part.

For an explanation of the dotfile catalog system itself, see **[Dotfiles](dotfiles.md)**.

!!! note "Catalog scope"
    The `Tig` catalog only links the bundled configuration to `~/.config/tig/config`. It
    does not install Tig, Delta, Meld, `wl-copy`, or a terminal theme. The catalog directory
    is named `Tig`, so that is the name shown in the dotfiles confirmation prompt.

---

## What this custom setup gives you

The `Tig` catalog links a Catppuccin Mocha-oriented Tig configuration with:

- Mouse support, automatic refresh, smart-case search, and visible untracked files.
- UTF-8 commit graph drawing and a dense commit list with relative dates and ref labels.
- A detailed blame view with line numbers.
- ANSI-color-based Catppuccin styling that follows the terminal palette.
- Delta-powered diff views on `D` for commits, stashes, status, and staged files.
- Meld-powered directory diffs on `M` for commits and file changes.
- `g`/`G` jumps and a `y` binding that copies the selected commit hash with `wl-copy`.

```bash
omarchy-tweaker dotfiles
```

Accept the `Tig` catalog when prompted.

---

## Quick start

```bash
omarchy-tweaker dotfiles
```

Then verify the linked config and tools:

```bash
ls -l ~/.config/tig/config
tig --version
command -v delta
command -v meld
command -v wl-copy
tig
```

If colors, diff commands, or clipboard copying do not work, check the tool requirements
below.

---

## What gets installed

| Bundled source | Destination | What it does |
|:--|:--|:--|
| `config` | `~/.config/tig/config` | Complete Tig config with behavior, layout, Catppuccin ANSI colors, keybindings, Delta, Meld, and Wayland clipboard integration. |

The catalog configuration is:

```text
src/omarchy_tweaker/dotfiles/Tig/config.toml
```

It contains a single `[symlink]` entry:

```toml
[symlink]
config = "~/.config/tig/config"
```

No prompts, templates, key setup, shell startup edits, or package installation are involved.

!!! warning "The destination is a symlink"
    Editing `~/.config/tig/config` in place writes through to the bundled source file. For
    temporary experiments this is fine. For permanent personal changes, keep a separate
    copy or edit the catalog in a checkout and rerun `omarchy-tweaker dotfiles`.

---

## Requirements

| Tool | Used for |
|:--|:--|
| `tig` | The terminal Git interface itself. |
| `delta` | Styled diff views opened with `D`. |
| `meld` | Directory and file diffs opened with `M`. |
| `wl-copy` | Copying commit hashes on Wayland with `y`. |
| A Catppuccin terminal palette | Producing the intended ANSI color appearance. |
| A UTF-8 terminal | Drawing the Unicode commit graph. |
| `git` | All repository operations. |

Check the core commands with:

```bash
command -v tig
command -v delta
command -v meld
command -v wl-copy
git config --get diff.tool
```

The `M` binding expects Meld to be available as the Git difftool:

```bash
git config --global diff.tool meld
```

---

## Behavior settings

| Setting | Value | Effect |
|:--|:--|:--|
| `mouse` | `yes` | Enables mouse interaction. |
| `mouse-scroll` | `3` | Scrolls three lines per mouse wheel step. |
| `refresh-mode` | `auto` | Refreshes views automatically. |
| `refresh-interval` | `10` | Uses a ten-second refresh interval. |
| `ignore-case` | `smart-case` | Uses case-insensitive search unless a pattern has uppercase characters. |
| `wrap-lines` | `no` | Keeps long lines unwrapped. |
| `horizontal-scroll` | `33%` | Scrolls horizontally by about one third of the view. |
| `tab-size` | `4` | Displays tabs as four columns. |
| `editor-line-number` | `yes` | Opens the editor at the current line when available. |
| `show-changes` | `yes` | Shows changed files in status views. |
| `show-untracked` | `yes` | Shows untracked files in status views. |
| `diff-context` | `5` | Shows five lines of context around diff hunks. |

---

## Layout settings

| Setting | Value | Effect |
|:--|:--|:--|
| `line-graphics` | `utf-8` | Uses Unicode box-drawing characters for the commit graph. |
| `vertical-split` | `auto` | Lets Tig choose vertical splitting when useful. |
| `split-view-height` | `65%` | Gives the upper split view 65% of the height. |
| `main-view` | `id:no date:relative author:abbreviated commit-title:graph=v2,refs=yes,overflow=no` | Shows a dense commit graph with relative dates, abbreviated authors, and ref labels. |
| `blame-view` | `id:yes,color file-name:auto author:abbreviated date:relative line-number:yes,interval=1 text` | Shows file blame with line numbers and relative dates. |

The experimental `reference-format` icon line is intentionally commented out. Enable it in
your own copy only if your terminal and font render those icons correctly.

---

## Catppuccin Mocha colors

The config uses terminal ANSI colors instead of hardcoded hex values. That lets Tig follow
the Catppuccin palette already configured in the Omarchy terminal.

| ANSI mapping | Catppuccin meaning |
|:--|:--|
| `magenta` | Pink |
| `cyan` | Teal |
| `8` | Surface |

### Base colors

| Element | Foreground | Background/style | Purpose |
|:--|:--|:--|:--|
| `default` | `default` | `default` | Normal text. |
| `cursor` | `default` | `8`, bold | Current selection. |
| `status` | `green` | `default` | Status bar. |
| `title-focus` | `black` | `magenta`, bold | Focused view title. |
| `title-blur` | `default` | `8` | Unfocused view title. |
| `delimiter` | `magenta` | `default` | Delimiters. |
| `header` | `blue` | `default`, bold | Column headers. |
| `line-number` | `8` | `default` | Blame line numbers. |
| `id` | `yellow` | `default` | Object IDs. |
| `date` | `cyan` | `default` | Dates. |
| `author` | `blue` | `default` | Authors. |
| `mode` | `magenta` | `default` | Mode indicators. |
| `overflow` | `red` | `default` | Overflow markers. |
| `directory` | `blue` | `default`, bold | Directories. |
| `graph-commit` | `magenta` | `default` | Commit graph nodes. |
| `search-result` | `black` | `yellow` | Search matches. |

### Ref and status colors

| Element | Color | Purpose |
|:--|:--|:--|
| `main-head` | `green`, bold | Current branch head. |
| `main-remote` | `yellow` | Remote refs. |
| `main-tracked` | `red` | Tracked refs. |
| `main-tag` / `main-local-tag` | `magenta` | Tags. |
| `main-ref` | `cyan` | Other refs. |
| `stat-staged` | `green` | Staged changes. |
| `stat-unstaged` | `red` | Unstaged changes. |
| `stat-untracked` | `magenta` | Untracked files. |

### Diff colors

| Element | Color | Purpose |
|:--|:--|:--|
| `diff-header` | `blue` | Diff headers. |
| `diff-chunk` | `magenta` | Hunk boundaries. |
| `diff-add` | `green` | Added lines. |
| `diff-del` | `red` | Deleted lines. |
| `diff-stat` | `cyan` | Diff statistics. |

### Graph palette

`palette-0` through `palette-13` repeat `magenta`, `yellow`, `cyan`, `green`, `red`, and
`blue` so commit graph branches receive distinct colors without leaving the terminal
palette.

---

## Keybinding cheat sheet

| Key | View | Action |
|:--|:--|:--|
| `g` | Generic | Move to the first line. |
| `G` | Generic/main | Move to the last line. |
| `D` | Main, diff, log, blame, refs | Open the selected commit through Delta with `git show %(commit) \| delta --paging=always`. |
| `D` | Stash | Open the selected stash through Delta with `git stash show -p %(stash) \| delta --paging=always`. |
| `D` | Status, stage | Open the selected file diff through Delta with `git diff HEAD -- %(file) \| delta --paging=always`. |
| `M` | Main, diff | Open a Meld directory diff for the selected commit with `git difftool --dir-diff %(commit)^ %(commit)`. |
| `M` | Status | Open the selected file in Meld with `git difftool --no-prompt -- %(file)`. |
| `y` | Generic | Copy the selected commit hash with `wl-copy`. |

Delta views use their pager, so press `q` to return to Tig.

---

## Integration with lazygit and Git

- The bundled lazygit config opens Tig from the commit files panel with `t`; see **[Lazygit Dotfiles](lazygit.md)**.
- The bundled Git config uses Delta for terminal diffs and sets `status.showUntrackedFiles = all`; see **[Git Dotfiles](git.md)**.
- Tig complements those tools by providing a keyboard-first repository browser with full-screen Delta and Meld actions.

---

## Verification and troubleshooting

Check the linked file and tool chain:

```bash
ls -l ~/.config/tig/config
tig --version
delta --version
git config --get diff.tool
```

| Symptom | Check |
|:--|:--|
| Colors are not Catppuccin-like | Configure the terminal with the Catppuccin palette; Tig uses ANSI color names. |
| Commit graph shows odd characters | Use a UTF-8 locale and a terminal with Unicode line-drawing support. |
| `D` shows plain diffs | Confirm `delta` is installed and available on `PATH`. |
| `M` fails | Confirm `meld` is installed and `git config --get diff.tool` returns `meld`. |
| `y` fails | Confirm `wl-copy` is installed and the session is Wayland-based. |
| Mouse does not work | Confirm the terminal supports mouse reporting. |
| Untracked files do not appear | Confirm the config is loaded and `show-untracked = yes` is present. |
| Config changes do not appear | Check `XDG_CONFIG_HOME`; Tig may read `$XDG_CONFIG_HOME/tig/config` instead of `~/.config/tig/config`. |
| Command skipped immediately | The dotfiles command requires an interactive terminal. |

Inspect the actual symlink target when needed:

```bash
readlink -f ~/.config/tig/config
```

---

## Customization

For temporary experiments, edit `~/.config/tig/config` directly and restart Tig. Because
the destination is a symlink, those edits change the bundled source file inside the
checkout.

For durable personal customization:

1. Keep a separate copy of the config outside the managed catalog.
2. Edit the catalog source in your Omarchy Tweaker checkout.
3. Rerun `omarchy-tweaker dotfiles`.
4. Review the backup created for the previous destination.

Additional Tig bindings belong under the `bind` syntax with the correct view context, such
as `generic`, `main`, `diff`, `status`, or `stash`.

---

## Safety notes

- The catalog only creates or replaces one symlink.
- Existing destinations are backed up before replacement.
- No shell startup files are modified.
- No secrets, keys, or credentials are stored in the config.
- Custom bindings run local commands through `sh` or Git difftool.
- The `y` binding copies a commit hash to the Wayland clipboard.
- The `M` binding opens external diff tools; review changes before applying them.

---

## Related pages

- [Dotfiles](dotfiles.md)
- [Git Dotfiles](git.md)
- [Lazygit Dotfiles](lazygit.md)
- [Starship Dotfiles](starship.md)
- [Superfile Dotfiles](superfile.md)
- [Zellij Dotfiles](zellij.md)
- [Commands](commands.md)
- [Security](security.md)
- [Troubleshooting](troubleshooting.md)
