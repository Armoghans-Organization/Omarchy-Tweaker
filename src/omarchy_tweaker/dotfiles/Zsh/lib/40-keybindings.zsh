# ╭──────────────────────────────────────────────────────────────────────╮
# │                         ZSH KEYBINDINGS                              │
# │                    Fast • Clean • Reliable                           │
# ╰──────────────────────────────────────────────────────────────────────╯

# ──────────────────────────────────────────────────────────────────────
# Editor Mode
# ──────────────────────────────────────────────────────────────────────

[[ -o emacs ]] || set -o emacs

# ──────────────────────────────────────────────────────────────────────
# Zellij Session Manager
# ──────────────────────────────────────────────────────────────────────
lzj-widget() {
    zle -I
    _lzj </dev/tty >/dev/tty 2>&1
    zle reset-prompt
}

zle -N lzj-widget

# Alt + Z
bindkey -M emacs '^[z' lzj-widget
bindkey -M viins '^[z' lzj-widget

# ──────────────────────────────────────────────────────────────────────
# Tmux Session Manager
# ──────────────────────────────────────────────────────────────────────
ltx-widget() {
    zle -I
    local attach_file target
    attach_file="$(mktemp -t ltx-attach.XXXXXX)"
    LTX_ATTACH_FILE="$attach_file" _ltx </dev/tty >/dev/tty 2>&1
    if [[ -s "$attach_file" ]]; then
        target="$(<"$attach_file")"
        rm -f -- "$attach_file"
        if [[ -n "$TMUX" ]]; then
            tmux switch-client -t "$target"
            zle reset-prompt
        else
            BUFFER="tmux attach -t ${(q)target}"
            zle accept-line
        fi
    else
        rm -f -- "$attach_file"
        zle reset-prompt
    fi
}

zle -N ltx-widget

# Alt + T
bindkey -M emacs '^[t' ltx-widget
bindkey -M viins '^[t' ltx-widget

# ──────────────────────────────────────────────────────────────────────
# Atuin (Shell History Manager)
# ──────────────────────────────────────────────────────────────────────
atuin-ai-widget(){
    zle -I
    atuin ai inline </dev/tty >/dev/tty 2>&1
}

zle -N atuin-ai-widget

# Ctrl + R → Atuin Search
bindkey -M emacs '^R' atuin-search
bindkey -M viins '^R' atuin-search-viins

# ? → Atuin Ai Inline
bindkey -M emacs '?' atuin-ai-widget
bindkey -M viins '?' atuin-ai-widget

# ──────────────────────────────────────────────────────────────────────
# Hastebin (Pastebin Service)
# ──────────────────────────────────────────────────────────────────────
hastebin-widget() {
    zle -I
    _hastebin </dev/tty >/dev/tty 2>&1
    zle reset-prompt
}

hastebin-history-widget() {
    zle -I
    _hastebin history </dev/tty >/dev/tty 2>&1
    zle reset-prompt
}

zle -N hastebin-widget
zle -N hastebin-history-widget

# Alt + H
bindkey -M emacs '^[h' hastebin-widget
bindkey -M viins '^[h' hastebin-widget

# Alt + Shift + H
bindkey -M emacs '^[H' hastebin-history-widget
bindkey -M viins '^[H' hastebin-history-widget

# ──────────────────────────────────────────────────────────────────────
# Server (Run Local Server)
# ──────────────────────────────────────────────────────────────────────
server-widget() {
    zle -I
    _server </dev/tty >/dev/tty 2>&1
    zle reset-prompt
}

zle -N server-widget

# Alt + S
bindkey -M emacs '^[s' server-widget
bindkey -M viins '^[s' server-widget

# ──────────────────────────────────────────────────────────────────────
# Superfile (File Manager)
# ──────────────────────────────────────────────────────────────────────
superfile-widget() {
    zle -I
    spf </dev/tty >/dev/tty 2>&1
    zle reset-prompt
}

zle -N superfile-widget

# Alt + F
bindkey -M emacs '^[f' superfile-widget
bindkey -M viins '^[f' superfile-widget

# ──────────────────────────────────────────────────────────────────────
# LazyGit (Git Manager)
# ──────────────────────────────────────────────────────────────────────
lazygit-widget() {
    zle -I
    lazygit </dev/tty >/dev/tty 2>&1
    zle reset-prompt
}

zle -N lazygit-widget

# Alt + G
bindkey -M emacs '^[g' lazygit-widget
bindkey -M viins '^[g' lazygit-widget

# ──────────────────────────────────────────────────────────────────────
# LazyDocker (Docker Manager)
# ──────────────────────────────────────────────────────────────────────
lazydocker-widget() {
    zle -I
    lazydocker </dev/tty >/dev/tty 2>&1
    zle reset-prompt
}

zle -N lazydocker-widget

# Alt + D
bindkey -M emacs '^[d' lazydocker-widget
bindkey -M viins '^[d4' lazydocker-widget

# ──────────────────────────────────────────────────────────────────────
# Edit Command in $EDITOR
# ──────────────────────────────────────────────────────────────────────
edit-command-widget() {
    zle -I
    local tmpfile
    tmpfile="$(mktemp -t zsh-edit-command.XXXXXX)"
    print -r -- "$BUFFER" >| "$tmpfile"
    ${EDITOR:-vi} "$tmpfile"
    BUFFER="$(<"$tmpfile")"
    rm -f -- "$tmpfile"
    zle reset-prompt
}

zle -N edit-command-widget

# Alt + E
bindkey -M emacs '^[e' edit-command-widget
bindkey -M viins '^[e' edit-command-widget

# ──────────────────────────────────────────────────────────────────────
# Command Pallet
# ──────────────────────────────────────────────────────────────────────
command-pallet-widget() {
    emulate -L zsh
    zle -I                                   # the terminal is about to be used by someone else
    local tmp sel kind w
    (( $+commands[_pal] )) || { zle -M "pal is not in your PATH (put it in ~/.local/bin)"; return 1 }
    tmp="$(mktemp)" || return 1
    bindkey >| "$tmp"                        # the key table as this shell sees it right now
    sel="$(PAL_BINDKEYS="$tmp" command _pal --pick </dev/tty)"
    rm -f "$tmp"
    zle reset-prompt
    # `pal --pick` prints:  zsh <TAB> widget <TAB> key text   (tmux keys it runs itself)
    kind="${sel%%$'\t'*}"
    w="${${sel#*$'\t'}%%$'\t'*}"
    [[ "$kind" == zsh && -n "$w" ]] && zle "$w"
    zle redisplay
}
zle -N command-pallet-widget

# Alt + Shift + P
bindkey -M emacs '^[P' command-pallet-widget
bindkey -M viins '^[P' command-pallet-widget
