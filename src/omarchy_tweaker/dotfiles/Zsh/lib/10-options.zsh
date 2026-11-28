# ╭──────────────────────────────────────────────────────────────────────────╮
# │                              ZSH OPTIONS                                 │
# │                                                                          │
# │  Purpose: Configure Zsh shell behavior, navigation, completion,          │
# │           history, job control, and interactive usability.               │
# ╰──────────────────────────────────────────────────────────────────────────╯

# ───────────────────────────────────────────────────────────────────────────
# 1. NAVIGATION & DIRECTORY MANAGEMENT
# ───────────────────────────────────────────────────────────────────────────

# Configure directory navigation and directory stack behavior.
#
# AUTOCD:
#   Automatically change into a directory when its name is entered
#   directly as a command, without requiring the cd command.
#
#   Example:
#       ~/Documents
#       # Automatically changes into ~/Documents.
#
# AUTOPUSHD:
#   Automatically push the previous working directory onto the
#   directory stack whenever cd is used.
#
# PUSHD_IGNORE_DUPS:
#   Prevent duplicate directory entries from being added to
#   the directory stack.
#
# PUSHD_TO_HOME:
#   Make pushd without arguments behave like pushd $HOME.
#
# PUSHD_MINUS:
#   Reverse the meanings of '+' and '-' when navigating
#   the directory stack.
#
#   Example:
#       cd -     # Previous working directory.
#       pushd -  # Uses the reversed directory-stack convention.

setopt autocd
setopt autopushd
setopt pushd_ignore_dups
setopt pushd_to_home
setopt pushd_minus

# ───────────────────────────────────────────────────────────────────────────
# 2. GLOBBING & EXPANSION
# ───────────────────────────────────────────────────────────────────────────

# Configure filename matching, glob expansion, and directory handling.
#
# GLOB_DOTS:
#   Include hidden files and directories (starting with .)
#   when performing filename expansion.
#
#   Example:
#       ls *
#       # Also matches hidden entries.
#
# NUMERIC_GLOB_SORT:
#   Sort filenames containing numbers numerically instead of
#   alphabetically.
#
#   Example:
#       file1
#       file2
#       file10
#
#   Without this option, file10 may appear before file2.

setopt glob_dots
setopt numeric_glob_sort

# ───────────────────────────────────────────────────────────────────────────
# 3. COMMAND INTERACTION & CORRECTION
# ───────────────────────────────────────────────────────────────────────────

# Improve interactive command entry and spelling correction.
#
# CORRECT:
#   Suggest corrections when a command name appears to be
#   misspelled.
#
#   Example:
#       $ gti status
#       # Suggests git as a possible correction.
#
# AUTO_MENU:
#   Automatically display the completion menu when Tab is
#   pressed repeatedly and multiple matches are available.
#
# COMPLETE_IN_WORD:
#   Allow completion to begin from the middle of a word
#   instead of requiring the cursor to be at the end.
#
# INTERACTIVE_COMMENTS:
#   Allow comments beginning with '#' in interactive commands.
#
#   Example:
#       echo "Hello" # This is an interactive shell comment.

setopt correct
setopt auto_menu
setopt complete_in_word
setopt interactive_comments

# ───────────────────────────────────────────────────────────────────────────
# 4. COMPLETION BEHAVIOR
# ───────────────────────────────────────────────────────────────────────────

# Customize how Zsh displays and navigates completion candidates.
#
# AUTO_LIST:
#   Automatically display available completion candidates
#   when a completion request is ambiguous.
#
# MENU_COMPLETE:
#   Replace the current word with the first available completion
#   candidate instead of requiring another Tab press.
#
# ALWAYS_TO_END:
#   Move the cursor to the end of the completed word after
#   performing completion.
#
# These options improve interactive completion behavior,
# particularly when working with long commands and paths.

setopt auto_list
setopt menu_complete
setopt always_to_end

# ───────────────────────────────────────────────────────────────────────────
# 5. JOB CONTROL & NOTIFICATIONS
# ───────────────────────────────────────────────────────────────────────────

# Configure background job management and shell notifications.
#
# NOTIFY:
#   Report the completion or status changes of background jobs
#   immediately instead of waiting for the next shell prompt.
#
# CHECK_JOBS:
#   Warn before exiting the shell if background jobs are still
#   running or stopped.
#
# CHECK_RUNNING_JOBS:
#   Specifically check for running jobs before allowing the
#   shell to exit.
#
# MONITOR:
#   Enable job control in the interactive shell.
#
# Note:
#   Job control is normally enabled automatically in interactive
#   Zsh sessions. It is not explicitly configured here.

setopt notify
setopt check_jobs
setopt check_running_jobs

# ───────────────────────────────────────────────────────────────────────────
# 6. HISTORY & ATUIN INTEGRATION
# ───────────────────────────────────────────────────────────────────────────

# Delegate command history management to Atuin instead of
# maintaining a traditional Zsh history file.
#
# HISTFILE:
#   Unset the native Zsh history file location.
#
# SHARE_HISTORY:
#   Disable sharing history between active Zsh sessions.
#
# APPEND_HISTORY:
#   Disable automatic appending of commands to the native history file.
#
# INC_APPEND_HISTORY:
#   Disable writing commands to the native history file immediately
#   after execution.
#
# EXTENDED_HISTORY:
#   Disable native extended history timestamps and duration metadata.
#
# HIST_VERIFY:
#   Disable the verification step for history expansions.
#
# ATUIN COMPATIBILITY:
#   Configure Zsh Autosuggestions to use both history and
#   completion-based suggestions.
#
#   history:
#       Suggest commands from available shell history.
#
#   completion:
#       Suggest commands using the completion system.
#
# Important:
#   Ensure Atuin is initialized separately in your Zsh configuration.

unset HISTFILE
unsetopt share_history
unsetopt append_history
unsetopt inc_append_history
unsetopt extended_history
unsetopt hist_verify

ZSH_AUTOSUGGEST_STRATEGY=(history completion)

# ───────────────────────────────────────────────────────────────────────────
# 7. INTERACTIVE SAFETY
# ───────────────────────────────────────────────────────────────────────────

# Enable safeguards against accidental shell operations.
#
# NOCLOBBER:
#   Prevent output redirection from accidentally overwriting
#   existing files.
#
#   Example:
#       echo "Hello" > existing.txt
#       # Refused if existing.txt already exists.
#
#   Explicit overwrite:
#       echo "Hello" >! existing.txt
#
# IGNORE_EOF:
#   Prevent Ctrl+D from immediately closing the shell when
#   the command line is empty.
#
#   Useful for avoiding accidental terminal exits.
#
# BEEP:
#   Enable the terminal bell for certain errors and invalid
#   interactive operations.
#
#   This can be disabled with unsetopt beep if unwanted.

setopt noclobber
setopt ignore_eof
setopt beep

# ───────────────────────────────────────────────────────────────────────────
# 8. COMMAND LINE EDITING
# ───────────────────────────────────────────────────────────────────────────

# Configure the interactive command-line editing interface.
#
# EMACS:
#   Enable Emacs-style command-line editing.
#
#   Common key bindings:
#       Ctrl+A       Move to beginning of line
#       Ctrl+E       Move to end of line
#       Ctrl+W       Delete previous word
#       Ctrl+K       Delete to end of line
#       Ctrl+U       Delete entire line
#
# BINDKEY -E:
#   Explicitly activate the Emacs keymap.
#
# Note:
#   EMACS and bindkey -e select the same editing style.
#   Keeping both makes the intended editing mode explicit.

setopt emacs

bindkey -e
