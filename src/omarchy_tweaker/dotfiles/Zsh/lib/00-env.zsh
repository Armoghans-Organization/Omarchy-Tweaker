# ╭──────────────────────────────────────────────────────────────────────────╮
# │                       ZSH ENVIRONMENT VARIABLES                          │
# │                      Shared defaults for shell + tools                   │
# ╰──────────────────────────────────────────────────────────────────────────╯

# ───────────────────────────────────────────────────────────────────────────
# 1. XDG / ZSH PATHS
# ───────────────────────────────────────────────────────────────────────────

export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"

typeset -g ZSH_CONFIG_DIR="${ZSH_CONFIG_DIR:-$XDG_CONFIG_HOME/zsh}"
typeset -g ZSH_LIB_DIR="${ZSH_LIB_DIR:-$ZSH_CONFIG_DIR/lib}"
typeset -g ZSH_FUNCTIONS_DIR="${ZSH_FUNCTIONS_DIR:-$ZSH_CONFIG_DIR/functions}"
typeset -g ZSH_CACHE_DIR="${ZSH_CACHE_DIR:-$XDG_CACHE_HOME/zsh}"
typeset -g ZSH_STATE_DIR="${ZSH_STATE_DIR:-$XDG_STATE_HOME/zsh}"


[[ -d "$ZSH_CACHE_DIR" ]] || mkdir -p -- "$ZSH_CACHE_DIR"
[[ -d "$ZSH_STATE_DIR" ]] || mkdir -p -- "$ZSH_STATE_DIR"

# ───────────────────────────────────────────────────────────────────────────
# 2. DEFAULT EDITORS / PAGER
# ───────────────────────────────────────────────────────────────────────────

export EDITOR="${EDITOR:-nvim}"
export VISUAL="${VISUAL:-$EDITOR}"
export SUDO_EDITOR="${SUDO_EDITOR:-$EDITOR}"
export FCEDIT="${FCEDIT:-$EDITOR}"

export PAGER="${PAGER:-less -RFKX -i -j.5 --mouse --wheel-lines=3}"
export LESS="${LESS:-FRX}"
export LESSHISTFILE='-'

# ───────────────────────────────────────────────────────────────────────────
# 3. GPG / MAN / BAT
# ───────────────────────────────────────────────────────────────────────────

if [[ -t 0 ]]; then
    export GPG_TTY="${GPG_TTY:-$(tty 2>/dev/null)}"
fi

if (( $+commands[bat] )); then
    export MANPAGER="sh -c 'col -bx | bat -l man -p'"
    export MANROFFOPT='-c'
fi

# ───────────────────────────────────────────────────────────────────────────
# 4. PLUGIN MANAGER
# ───────────────────────────────────────────────────────────────────────────

export PLUG_JOBS="${PLUG_JOBS:-4}"
export PLUG_QUIET="${PLUG_QUIET:-1}"
export PLUG_COMPINIT="${PLUG_COMPINIT:-1}"
export PLUG_MAX_LOG_SIZE="${PLUG_MAX_LOG_SIZE:-1048576}"
export PLUG_OMZ_LIB="${PLUG_OMZ_LIB:-functions clipboard}"

# ───────────────────────────────────────────────────────────────────────────
# 5. TOOL DEFAULTS
# ───────────────────────────────────────────────────────────────────────────

export NPM_CONFIG_UPDATE_NOTIFIER=false
export PYTHONDONTWRITEBYTECODE=1
export PYTHONSTARTUP="${PYTHONSTARTUP:-$HOME/.local/bin/startup.py}"

# FZF defaults; detailed FZF styling lives in 30-fzf.zsh.
export FZF_DEFAULT_OPTS="${FZF_DEFAULT_OPTS:-}"

# UI icons/colors used by helper functions.
typeset -gA ZSH_UI=(
    [ok]='󰄬' [err]='󰅙' [warn]='󰀦' [info]='󰋼' [ask]='󰋗' [debug]='󰃤'
    [file]='󰈔' [dir]='󰉋' [git]='󰊢' [net]='󰖟' [pkg]='󰏗' [sys]='󰍛'
    [arrow]='󰜴' [dot]='•'
)
