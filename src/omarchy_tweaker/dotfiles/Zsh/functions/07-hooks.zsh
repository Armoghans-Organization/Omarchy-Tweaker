# ╭──────────────────────────────────────────────────────────────────────────╮
# │                             ZSH HOOKS / LAZY                             │
# ╰──────────────────────────────────────────────────────────────────────────╯

autoload -U add-zsh-hook

typeset -g _ZSH_LAST_GIT_ROOT=""

# Run onefetch only on real directory changes into a repo root, and only if tty.
run_onefetch_on_cd() {
    (( $+commands[onefetch] )) || return 0
    [[ -t 1 ]] || return 0
    local root
    root="$(command git rev-parse --show-toplevel 2>/dev/null)" || { _ZSH_LAST_GIT_ROOT=""; return 0; }
    [[ "$root" == "$_ZSH_LAST_GIT_ROOT" ]] && return 0
    _ZSH_LAST_GIT_ROOT="$root"
    [[ "$PWD" -ef "$root" ]] || return 0
    command clear
    command onefetch
}

# Lazy-load fnm node version only when .nvmrc/.node-version exists in tree.
load_node_version() {
    (( $+commands[fnm] )) || return 0
    local dir="$PWD" version_file=""
    while [[ "$dir" != "/" ]]; do
        [[ -f "$dir/.nvmrc" ]] && { version_file="$dir/.nvmrc"; break; }
        [[ -f "$dir/.node-version" ]] && { version_file="$dir/.node-version"; break; }
        dir="${dir:h}"
    done
    if [[ -n "$version_file" ]]; then
        eval "$(command fnm env --shell zsh)"
        command fnm use --install-if-missing --silent-if-unchanged "$(<"$version_file")" >/dev/null 2>&1
    fi
}

add-zsh-hook chpwd run_onefetch_on_cd
add-zsh-hook chpwd load_node_version

# Initial run: only if already in a git repo root; skip noisy onefetch on shell startup? keep but fast check.
load_node_version
