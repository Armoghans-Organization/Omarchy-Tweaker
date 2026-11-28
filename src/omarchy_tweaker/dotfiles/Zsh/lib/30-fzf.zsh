# ╭──────────────────────────────────────────────────────────────────────────╮
# │                             FZF & FZF-TAB                                │
# │                                                                          │
# │  Purpose: Configure FZF, FZF-TAB, interactive previews, and custom       │
# │           fuzzy-finder widgets for ZSH.                                  │
# ╰──────────────────────────────────────────────────────────────────────────╯

# ───────────────────────────────────────────────────────────────────────────
# 1. FZF Environment
# ───────────────────────────────────────────────────────────────────────────

# Default file search command.
# fd is faster than find and respects the exclusions below.
export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow \
    --exclude .git \
    --exclude node_modules \
    --exclude .venv \
    --exclude __pycache__ \
    --exclude .cache \
    --exclude .next \
    --exclude dist \
    --exclude build \
    --exclude target'

# Ctrl+T: File selection.
export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"

export FZF_CTRL_T_OPTS="
    --preview-window=right:65%:border-rounded:wrap
"

# Alt+C: Directory selection.
export FZF_ALT_C_OPTS="
    --preview='
        printf \"\n\n\"
        eza -lah \
            --group-directories-first \
            --icons=always \
            --color=always \
            --git \
            --tree --level=2 -- {}
    '
    --preview-window=right:60%:border-rounded:wrap
"

# ───────────────────────────────────────────────────────────────────────────
# 2. FZF Appearance
# ───────────────────────────────────────────────────────────────────────────

export FZF_DEFAULT_OPTS="
    --height=80%
    --layout=reverse
    --border=rounded
    --info=inline
    --prompt='❯ '
    --marker='✓'
    --pointer='▶'
    --separator='─'
    --scrollbar='┃'

    --cycle
    --multi
    --no-mouse

    --bind='ctrl-d:preview-half-page-down'
    --bind='ctrl-u:preview-half-page-up'
    --bind='ctrl-/:toggle-preview'

    --preview='
        printf \"\n\n\"
        bat --color=always \
            --style=numbers,changes \
            --line-range=:300 {} 2>/dev/null ||
        eza -lah --icons=always --color=always -- {}
    '

    --preview-window=right:65%:border-rounded:wrap

    --color=fg:#cdd6f4
    --color=bg:#1e1e2e
    --color=hl:#f38ba8
    --color=fg+:#cdd6f4
    --color=bg+:#313244
    --color=hl+:#f38ba8
    --color=info:#cba6f7
    --color=prompt:#89b4fa
    --color=pointer:#f5c2e7
    --color=marker:#a6e3a1
    --color=spinner:#f5c2e7
    --color=header:#f38ba8
    --color=border:#585b70
    --color=label:#cba6f7
"

# ───────────────────────────────────────────────────────────────────────────
# 3. Preview Window Presets
# ───────────────────────────────────────────────────────────────────────────

# Reusable preview layouts for custom widgets.
_fzf_preview_window='right:65%:wrap:border-rounded'
_fzf_custom_preview='right:50%:wrap:border-rounded'

# ───────────────────────────────────────────────────────────────────────────
# 4. FZF-TAB General Settings
# ───────────────────────────────────────────────────────────────────────────

# Use clean completion menus without individual borders.
_ftb_base=(--border=none --no-separator)

zstyle ':fzf-tab:*' fzf-flags \
    $_ftb_base \
    --preview-window=right:65%:wrap:noborder \
    --height=98%

# Use the same completion colors as LS_COLORS.
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}

# Completion group descriptions.
zstyle ':completion:*:descriptions' format \
    '%F{yellow}[%d]%f'

# Group completion results.
zstyle ':completion:*' group-name ''

# Scroll preview using Ctrl+D and Ctrl+U.
zstyle ':fzf-tab:*' fzf-bindings \
    'ctrl-d:preview-half-page-down' \
    'ctrl-u:preview-half-page-up'

# Switch between completion groups.
zstyle ':fzf-tab:*' switch-group ',' '.'

# ───────────────────────────────────────────────────────────────────────────
# 5. FZF-TAB File & Directory Preview
# ───────────────────────────────────────────────────────────────────────────

# Display detailed information for files and directories.
zstyle ':fzf-tab:complete:*:*' fzf-preview '
    local target="${(Q)realpath}"

    printf "\n\n"

    if [[ -d "$target" ]]; then
        eza -lah \
            --tree \
            --level=2 \
            --group-directories-first \
            --icons=always \
            --color=always \
            --git \
            --git-ignore \
            --time-style=long-iso \
            --header \
            -- "$target" 2>/dev/null

    elif [[ -f "$target" ]]; then
        bat --color=always \
            --paging=never \
            --style=numbers,changes \
            --line-range=:200 \
            -- "$target" 2>/dev/null ||
        file -- "$target"
    fi
'

# ───────────────────────────────────────────────────────────────────────────
# 6. FZF-TAB Command-Specific Previews
# ───────────────────────────────────────────────────────────────────────────

# SSH / Network:
# Display DNS information or matching SSH configuration.
zstyle ':fzf-tab:complete:(ssh|ping|traceroute):*' fzf-preview '
    getent hosts "$word" 2>/dev/null ||
    grep -A 8 -E "^Host[[:space:]]+$word([[:space:]]|$)" \
        ~/.ssh/config 2>/dev/null
'

# Environment variables:
# Display the currently assigned variable value.
zstyle ':fzf-tab:complete:(-parameter-|-set-|-export-):*' fzf-preview '
    print -r -- "${(P)word}" | bat \
        --color=always \
        --language=sh \
        --style=plain 2>/dev/null
'

# Systemd:
# Display service status.
zstyle ':fzf-tab:complete:systemctl-*:*' fzf-preview '
    systemctl status --no-pager "$word" 2>/dev/null
'

# IP:
# Display network interface information.
zstyle ':fzf-tab:complete:ip:*' fzf-preview '
    ip addr show dev "$word" 2>/dev/null ||
    ip route show 2>/dev/null
'

# Git:
# Display commit details or branch history.
zstyle ':fzf-tab:complete:git-(log|diff|show|checkout):*' fzf-preview '
    case "$group" in
        *commit*|*tag*)
            git show --color=always "$word" 2>/dev/null
            ;;
        *branch*)
            git log --color=always --oneline --graph \
                -n 20 "$word" 2>/dev/null
            ;;
    esac
'

# Archives:
# Inspect archive contents without extracting them.
zstyle ':fzf-tab:complete:*(tar|tgz|zip|unzip|gzip):*' fzf-preview '
    case "$word" in
        *.zip)
            unzip -l "$word" 2>/dev/null
            ;;
        *.tar|*.tar.gz|*.tgz)
            tar -tf "$word" 2>/dev/null
            ;;
        *.gz)
            gzip -l "$word" 2>/dev/null
            ;;
    esac
'

# Docker:
# Display container information.
zstyle ':fzf-tab:complete:docker-(start|stop|restart|logs|inspect):*' fzf-preview '
    docker inspect --format \
        "Name: {{.Name}}\nStatus: {{.State.Status}}\nImage: {{.Config.Image}}" \
        "$word" 2>/dev/null
'

# Processes:
# Display process details.
zstyle ':fzf-tab:complete:kill:*' fzf-preview '
    ps -p "$word" -o pid,ppid,user,%cpu,%mem,stat,etime,command \
        2>/dev/null
'

# Cache completion results
zstyle ':completion:*' use-cache yes
zstyle ':completion:*' cache-path ~/.cache/zsh/zcompcache

# ───────────────────────────────────────────────────────────────────────────
# 7. FZF-TAB Completion Exceptions
# ───────────────────────────────────────────────────────────────────────────

# Disable previews for command names.
zstyle ':fzf-tab:complete:-command-:*' fzf-preview ''
zstyle ':fzf-tab:complete:-command-:*' fzf-flags \
    $_ftb_base --preview-window=hidden

# Disable previews for command options.
zstyle ':fzf-tab:complete:*:options' fzf-preview ''
zstyle ':fzf-tab:complete:*:options' fzf-flags \
    $_ftb_base --preview-window=hidden

# ───────────────────────────────────────────────────────────────────────────
# 8. Tmux Integration
# ───────────────────────────────────────────────────────────────────────────

# Use a floating tmux popup when running inside tmux.
if [[ -n "$TMUX" ]]; then
    zstyle ':fzf-tab:*' fzf-command ftb-tmux-popup

    # Minimum popup dimensions.
    zstyle ':fzf-tab:*' popup-min-size 160 30
fi

# ───────────────────────────────────────────────────────────────────────────
# 9. Custom Widget: File & Directory Picker
# ───────────────────────────────────────────────────────────────────────────

# Ctrl+Alt+F
#
# Browse files and directories interactively.
# Directories change the current working directory.
# Files are inserted into the command line.

fzf_file_dir_picker() {
    local selected

    selected=$(
        fd --hidden --follow \
            --exclude .git \
            --exclude node_modules \
            --exclude .venv \
            --exclude __pycache__ \
            --exclude target \
            --exclude dist \
            --exclude build \
            . 2>/dev/null |
        fzf \
            --prompt='󰈞 Files / Directories ❯ ' \
            --preview='
                printf "\n\n"

                if [[ -d {} ]]; then
                    eza -lah \
                        --group-directories-first \
                        --icons=always \
                        --color=always \
                        --git -- {}
                else
                    bat --color=always \
                        --paging=never \
                        --style=numbers \
                        --line-range=:300 -- {} 2>/dev/null ||
                    file -- {}
                fi
            ' \
            --preview-window="$_fzf_preview_window"
    ) || return

    [[ -n "$selected" ]] || return

    if [[ -d "$selected" ]]; then
        builtin cd -- "$selected"
    else
        LBUFFER+="${(q)selected} "
    fi

    zle reset-prompt
}

# ───────────────────────────────────────────────────────────────────────────
# 10. Custom Widget: Git Log Search
# ───────────────────────────────────────────────────────────────────────────

# Ctrl+Alt+L
#
# Browse commit history and inspect commit diffs.

fzf_git_log_search() {
    git rev-parse --is-inside-work-tree &>/dev/null || {
        zle -M "Not inside a Git repository"
        return 1
    }

    local commit hash

    commit=$(
        git log --color=always \
            --format='%C(auto)%h %C(cyan)%ad %C(auto)%s %C(green)(%an)%Creset' \
            --date=short |
        fzf --ansi \
            --no-multi \
            --prompt='󰊢 Git Log ❯ ' \
            --preview='
                hash=$(printf "%s" {} | awk "{print \$1}")
                git show --color=always --stat --patch "$hash"
            ' \
            --preview-window="$_fzf_preview_window"
    ) || return

    [[ -n "$commit" ]] || return

    hash="${commit%% *}"

    LBUFFER+="git show ${(q)hash}"
    zle reset-prompt
}

# ───────────────────────────────────────────────────────────────────────────
# 11. Custom Widget: Environment Variable Picker
# ───────────────────────────────────────────────────────────────────────────

# Ctrl+Alt+V
#
# Browse exported environment variables and insert their values.

fzf_shell_variables() {
    local selected value

    selected=$(
        printenv |
        cut -d= -f1 |
        sort -u |
        fzf \
            --no-multi \
            --prompt='󰘳 Variables ❯ ' \
            --preview='
                printenv -- {} 2>/dev/null |
                bat --color=always \
                    --language=sh \
                    --style=plain
            ' \
            --preview-window="$_fzf_preview_window"
    ) || return

    [[ -n "$selected" ]] || return

    value="${(P)selected}"

    LBUFFER+="${(q)value} "
    zle reset-prompt
}

# ───────────────────────────────────────────────────────────────────────────
# 12. Custom Widget: Git Branch Switcher
# ───────────────────────────────────────────────────────────────────────────

# Ctrl+Alt+B
#
# Browse local and remote branches.
# Display recent commits for the selected branch.

fzf_git_branch() {
    git rev-parse --is-inside-work-tree &>/dev/null || {
        zle -M "Not inside a Git repository"
        return 1
    }

    local branch

    branch=$(
        git branch --all --no-color |
        sed -E 's/^[* ]+//' |
        awk '!seen[$0]++' |
        fzf \
            --no-multi \
            --prompt='󰊢 Git Branch ❯ ' \
            --preview='
                branch=$(printf "%s" {} | sed "s#^remotes/##")
                git log -8 --color=always \
                --oneline --decorate "$branch" 2>/dev/null
            ' \
            --preview-window="$_fzf_custom_preview"
    ) || return

    [[ -n "$branch" ]] || return

    # Remove the remote prefix for easier handling.
    branch="${branch#remotes/}"

    # Switch to an existing local branch.
    if git show-ref --verify --quiet "refs/heads/$branch"; then
        git switch -- "$branch"

    # Create a tracking branch for a remote branch.
    elif git show-ref --verify --quiet "refs/remotes/$branch"; then
        local local_branch="${branch#*/}"

        if git show-ref --verify --quiet "refs/heads/$local_branch"; then
            git switch -- "$local_branch"
        else
            git switch --track -c "$local_branch" "$branch"
        fi

    else
        zle -M "Branch not found: $branch"
        return 1
    fi

    zle reset-prompt
}

# ───────────────────────────────────────────────────────────────────────────
# 13. Custom Widget: Zoxide Directory Search
# ───────────────────────────────────────────────────────────────────────────

# Ctrl+Z
#
# Search frequently visited directories with Zoxide.
# Navigate directly to the selected directory.

fzf_zoxide_jump() {
    (( $+commands[zoxide] )) || {
        zle -M "Install zoxide first"
        return 1
    }

    local dir

    dir=$(zoxide query -i) || return

    [[ -n "$dir" && -d "$dir" ]] || return

    BUFFER="cd ${(q)dir}"
    zle accept-line
}

# ───────────────────────────────────────────────────────────────────────────
# 14. Register ZLE Widgets
# ───────────────────────────────────────────────────────────────────────────

zle -N fzf_file_dir_picker
zle -N fzf_git_log_search
zle -N fzf_shell_variables
zle -N fzf_git_branch
zle -N fzf_zoxide_jump

# ───────────────────────────────────────────────────────────────────────────
# 15. Keybindings
# ───────────────────────────────────────────────────────────────────────────

# File and directory picker.
bindkey '^[^F' fzf_file_dir_picker

# Git log search.
bindkey '^[^L' fzf_git_log_search

# Environment variable picker.
bindkey '^[^V' fzf_shell_variables

# Git branch switcher.
bindkey '^[^B' fzf_git_branch

# Zoxide directory search.
bindkey '^Z' fzf_zoxide_jump
