---
description: Usage examples, instructions, and cheat sheets for the bundled lazygit configuration.
icon: material/source-branch
subtitle: Lazygit dotfile guide
mermaid: true
---

# Lazygit Dotfiles

This page is the practical usage guide for the custom lazygit configuration bundled with
Omarchy Tweaker. It explains what the custom setup does, how to use it day to day, and how
to inspect or change each part.

For an explanation of the dotfile catalog system itself, see **[Dotfiles](dotfiles.md)**.

!!! note "Catalog scope"
    The lazygit catalog only links the bundled configuration to
    `~/.config/lazygit/config.yml`. It does not install lazygit, Delta, Neovim, tig, or a
    Nerd Font.

---

## What this custom setup gives you

The `lazygit` catalog links a Catppuccin Mocha-themed lazygit configuration with:

- Rounded borders, Nerd Font file icons, mouse support, and an expanded focused side panel.
- A file tree, file change tabs, command log, branch hashes, and base-branch divergence.
- Branch colors for `main`, `master`, `feat`, `fix`, `hotfix`, `chore`, `docs`, and `refactor` branches.
- Delta diffs with side-by-side output, line numbers, and clickable file hyperlinks.
- Neovim integration for editing files and XDG-open integration for files and links.
- A guided Conventional Commit command on `c` in the Files panel.
- A file-history command on `t` in the commit files panel using tig.
- lazygit update checks every seven days with a prompt instead of silent updates.

```bash
omarchy-tweaker dotfiles
```

Accept the `lazygit` catalog when prompted.

---

## Quick start

```bash
omarchy-tweaker dotfiles
```

Then verify the linked config:

```bash
ls -l ~/.config/lazygit/config.yml
lazygit --version
lazygit
```

If the theme, icons, or external commands do not work, check the tool requirements below.

---

## What gets installed

| Bundled source | Destination | What it does |
|:--|:--|:--|
| `config` | `~/.config/lazygit/config.yml` | Complete lazygit config with GUI layout, Catppuccin Mocha theme, external commands, diff rendering, keybindings, and custom commands. |

The catalog configuration is:

```text
src/omarchy_tweaker/dotfiles/lazygit/config.toml
```

It contains a single `[symlink]` entry:

```toml
[symlink]
config = "~/.config/lazygit/config.yml"
```

No prompts, templates, key setup, shell startup edits, or package installation are involved.

!!! warning "The destination is a symlink"
    Editing `~/.config/lazygit/config.yml` in place writes through to the bundled source
    file. For temporary experiments this is fine. For permanent personal changes, keep a
    separate copy or edit the catalog in a checkout and rerun `omarchy-tweaker dotfiles`.

---

## Requirements

The config works best with these tools available:

| Tool | Used for |
|:--|:--|
| `lazygit` | The terminal UI itself. |
| `delta` | Styled diffs and log paging. |
| `nvim` | Opening files and jumping to a line from lazygit. |
| `tig` | The custom file-history command on `t`; see [Tig Dotfiles](tig.md) for its bundled config. |
| `xdg-open` | Opening files and links from lazygit. |
| A Nerd Font | Rendering file icons and spinner glyphs. |
| `git` | All repository operations. |

You can check the core tools with:

```bash
command -v lazygit
command -v delta
command -v nvim
command -v tig
command -v xdg-open
```

---

## GUI settings

### Layout

| Setting | Value | Effect |
|:--|:--|:--|
| `nerdFontsVersion` | `"3"` | Uses Nerd Font version 3 glyph names. |
| `showFileIcons` | `true` | Shows file icons in file lists. |
| `border` | `rounded` | Uses rounded panel borders. |
| `mouseEvents` | `true` | Enables mouse interaction. |
| `sidePanelWidth` | `0.30` | Gives side panels 30% of the width. |
| `expandFocusedSidePanel` | `true` | Expands the focused side panel. |
| `expandedSidePanelWeight` | `2` | Gives the expanded side panel twice the weight. |
| `mainPanelSplitMode` | `vertical` | Splits the main panel vertically. |
| `statusPanelView` | `dashboard` | Uses the dashboard-style status view. |

### Information density

| Setting | Effect |
|:--|:--|
| `showFileTree` | Shows the repository file tree. |
| `showFileChangeTabs` | Shows tabs for changed files. |
| `showListFooter` | Shows list footers. |
| `showPanelJumps` | Shows panel jump hints. |
| `showCommandLog` | Shows the command log. |
| `commandLogSize: 8` | Keeps an eight-line command log. |
| `showBottomLine: false` | Hides the bottom line. |
| `showRandomTip: true` | Shows random tips. |
| `showBranchCommitHash: true` | Shows the branch commit hash. |
| `showDivergenceFromBaseBranch: arrowAndNumber` | Shows ahead/behind divergence with an arrow and count. |

### Behavior

| Setting | Value | Effect |
|:--|:--|:--|
| `scrollHeight` | `2` | Scrolls two lines at a time. |
| `scrollOffMargin` | `4` | Keeps context around the cursor. |
| `filterMode` | `fuzzy` | Uses fuzzy matching for filters. |
| `useHunkModeInStagingView` | `true` | Enables hunk-level staging. |
| `wrapLinesInStagingView` | `true` | Wraps long lines while staging. |
| `skipDiscardChangeWarning` | `false` | Keeps the discard confirmation. |
| `skipStashWarning` | `false` | Keeps the stash confirmation. |
| `skipNoStagedFilesWarning` | `false` | Keeps the no-staged-files confirmation. |
| `timeFormat` | `"02 Jan 06"` | Uses a compact date format. |
| `shortTimeFormat` | `"3:04PM"` | Uses a compact clock format. |

### Side panels

The side panels are arranged in this order:

```yaml
sidePanels:
  - [status]
  - [files, worktrees, submodules]
  - [branches, remotes, tags]
  - [commits, reflog]
  - [stash]
```

### Branch colors

| Branch pattern | Color | Typical use |
|:--|:--|:--|
| `^(main\|master)$` | `#cba6f7` | Default branches. |
| `^feat` | `#a6e3a1` | Features. |
| `^fix` | `#f38ba8` | Bug fixes. |
| `^hotfix` | `#fab387` | Urgent fixes. |
| `^(chore\|docs\|refactor)` | `#f9e2af` | Maintenance, documentation, and refactors. |

---

## Catppuccin Mocha theme

The theme block matches the Catppuccin Mocha palette used by the bundled Starship prompt.

| Theme key | Color | Used for |
|:--|:--|:--|
| `activeBorderColor` | `#8bd5ca`, bold | Focused panel borders. |
| `inactiveBorderColor` | `#a5adcb` | Unfocused panel borders. |
| `searchingActiveBorderColor` | `#eed49f` | Active search. |
| `optionsTextColor` | `#8aadf4` | Option text. |
| `selectedLineBgColor` | `#363a4f` | Selected lines. |
| `inactiveViewSelectedLineBgColor` | `#6e738d` | Selected lines in inactive views. |
| `unstagedChangesColor` | `#ed8796` | Unstaged changes. |
| `defaultFgColor` | `#cad3f5` | Default foreground text. |

---

## External commands

| Action | Command |
|:--|:--|
| Edit file | `nvim {{filename}}` |
| Edit file at line | `nvim +{{line}} {{filename}}` |
| Edit file at line and wait | `nvim +{{line}} {{filename}}` |
| Open directory in editor | `nvim {{dir}}` |
| Open file | `xdg-open {{filename}}` |
| Open link | `xdg-open {{link}}` |
| Edit in terminal | `true` |

`promptToReturnFromSubprocess: false` prevents lazygit from pausing with a
“press enter to return” prompt after tig, meld, or Neovim exits.

---

## Git workflow

### Diffs and paging

Delta is configured for both diff rendering and paging:

```text
delta
--features=mantis-shrimp
--paging=never
--side-by-side
--line-numbers
--hyperlinks
--hyperlinks-file-link-format="lazygit-edit://{path}:{line}"
```

This gives side-by-side diffs with line numbers and hyperlinks that can reopen the matched
file and line in Neovim.

### Logs and commits

| Setting | Value | Effect |
|:--|:--|:--|
| `branchLogCmd` | `git log --graph --color=always --abbrev-commit --decorate --date=relative` | Shows a compact decorated branch graph. |
| `allBranchesLogCmds` | Same style with `--all` | Shows all branches in the log view. |
| `localBranchSortOrder` | `date` | Sorts local branches by date. |
| `remoteBranchSortOrder` | `date` | Sorts remote branches by date. |
| `log.order` | `"topo-order"` | Uses topological log ordering. |
| `log.showGraph` | `"always"` | Always shows the graph. |
| `log.showWholeGraph` | `true` | Shows the whole graph. |
| `commit.autoWrapCommitMessage` | `true` | Wraps long commit messages. |
| `commit.autoWrapWidth` | `72` | Wraps at 72 characters. |
| `mainBranches` | `master`, `main` | Marks both as main branches. |

### Updates

```yaml
update:
  method: prompt
  days: 7
```

lazygit checks for updates every seven days and prompts instead of updating without
confirmation. The dotfile command itself does not install or update lazygit.

---

## Keybinding cheat sheet

| Key | Context | Action |
|:--|:--|:--|
| `q` | Universal | Quit lazygit. |
| `Q` | Universal | Quit without changing directory. |
| `left` / `h` | Universal | Move to the previous block. |
| `right` / `l` | Universal | Move to the next block. |
| `1`–`7` | Universal | Toggle and jump to a panel. |
| `Tab` / `[` | Universal | Go to the next tab. |
| `Backtab` / `]` | Universal | Go to the previous tab. |
| `p` | Universal | Push. |
| `P` | Universal | Pull. |
| `C` | Files | Commit changes. |
| `c` | Files | Guided Conventional Commit. |
| `t` | Commit files | Show history of the selected file with tig. |

The config intentionally leaves default push, pull, tab, and `h`/`l` behavior close to
lazygit defaults. Custom commands use specific contexts because a context-specific custom
key takes priority over a global custom key.

---

## Conventional Commit command

Press `c` in the Files panel to start the guided Conventional Commit command.

The prompts are:

1. **Type of change**: `feat`, `fix`, `docs`, `refactor`, `style`, `perf`, `test`, `build`, `ci`, `chore`, or `revert`.
2. **Scope**: optional.
3. **Breaking change**: `no` or `yes`.
4. **Message**: the short commit subject.
5. **Body**: optional.
6. **Confirm**: create the commit.

The command builds a message in this shape:

```text
type(optional-scope)!: message

optional body
```

It then runs `git commit --message ...`, using a second `--message` argument when a body is
provided.

---

## File history command

Press `t` in the commit files panel to run:

```bash
tig <selected-commit-hash> -- <selected-file>
```

The command opens in the terminal through lazygit’s `output: terminal` setting.

---

## Verification and troubleshooting

Check the linked file and available tools:

```bash
ls -l ~/.config/lazygit/config.yml
lazygit --version
command -v delta
command -v nvim
command -v tig
```

| Symptom | Check |
|:--|:--|
| Icons render as boxes | Install and configure a Nerd Font; the config uses Nerd Font version 3 glyphs. |
| Diffs are not side-by-side | Confirm `delta` is installed and supports the `mantis-shrimp` feature. |
| Editor actions fail | Confirm `nvim` is installed and available on `PATH`. |
| File/link open actions fail | Confirm `xdg-open` is installed and available on `PATH`. |
| `t` file history fails | Confirm `tig` is installed and available on `PATH`. |
| `c` does nothing | Focus the Files panel and confirm the custom command is present in the linked config. |
| Config changes do not appear | Confirm the destination symlink points to the bundled `config` file and that `XDG_CONFIG_HOME` is not overriding the config location. |
| Subprocesses pause after exiting | Confirm `promptToReturnFromSubprocess: false` is loaded. |
| Command skipped immediately | The dotfiles command requires an interactive terminal. |

If lazygit still ignores the file, inspect the symlink target:

```bash
readlink -f ~/.config/lazygit/config.yml
```

---

## Customization

For temporary experiments, edit `~/.config/lazygit/config.yml` directly and restart
lazygit. Because the destination is a symlink, those edits change the bundled source file
inside the checkout.

For durable personal customization:

1. Keep a separate copy of the config outside the managed catalog.
2. Edit the catalog source in your Omarchy Tweaker checkout.
3. Rerun `omarchy-tweaker dotfiles`.
4. Review the backup created for the previous destination.

New keybindings belong under `keybinding:` with the correct context. New custom commands
belong under `customCommands:` and should use a specific context such as `files` or
`commitFiles` rather than `global`.

---

## Safety notes

- The catalog only creates or replaces one symlink.
- Existing destinations are backed up before replacement.
- No shell startup files are modified.
- No secrets, keys, or credentials are stored in the config.
- Custom commands call local tools such as `git`, `nvim`, `tig`, `delta`, and `xdg-open`.
- The `c` custom command creates a commit immediately after confirmation.
- Review the generated command and staged changes before confirming commits.

---

## Related pages

- [Dotfiles](dotfiles.md)
- [Git Dotfiles](git.md)
- [Tig Dotfiles](tig.md)
- [Starship Dotfiles](starship.md)
- [Commands](commands.md)
- [Security](security.md)
- [Troubleshooting](troubleshooting.md)
