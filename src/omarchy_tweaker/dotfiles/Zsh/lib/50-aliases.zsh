# ╭──────────────────────────────────────────────────────────────────────────╮
# │                               ZSH ALIASES                                │
# │                   Organized • Fast • Safe • NerdFont                     │
# ╰──────────────────────────────────────────────────────────────────────────╯

# ───────────────────────────────────────────────────────────────────────────
# 1. NAVIGATION
# ───────────────────────────────────────────────────────────────────────────

alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'
alias back='cd -'

alias downloads='cd ~/Downloads'
alias desktop='cd ~/Desktop'
alias documents='cd ~/Documents'
alias pictures='cd ~/Pictures'
alias videos='cd ~/Videos'
alias music='cd ~/Music'
alias projects='cd ~/Projects'
alias github='cd ~/Github'
alias clone='cd ~/Github/Clone'
alias dots='cd "${ZSH_CONFIG_DIR:-$HOME/.config/zsh}"'

if (( $+commands[zoxide] )); then
    alias cd='z'
    alias cdi='zi'
    alias j='zoxide query'
    alias ji='zoxide query -i'
fi

# ───────────────────────────────────────────────────────────────────────────
# 2. LISTING / FILE VIEW
# ───────────────────────────────────────────────────────────────────────────

if (( $+commands[eza] )); then
    alias ls='eza --icons=auto --group-directories-first --color=auto'
    alias l='eza -lah --icons=auto --group-directories-first --git'
    alias ll='eza -lh --icons=auto --group-directories-first --git'
    alias la='eza -lah --icons=auto --group-directories-first'
    alias lt='eza --tree --level=2 --icons=auto --group-directories-first'
    alias lta='eza --tree --level=2 -a --icons=auto --group-directories-first'
    alias lsd='eza -ldh --icons=auto --group-directories-first */(N)'
    alias lf='eza -lh --icons=always --only-files'
    alias lh='eza -ld --icons=always .*(N)'
else
    alias ls='command ls --color=auto'
    alias l='ls -lah --color=auto'
    alias ll='ls -lh --color=auto'
    alias la='ls -A --color=auto'
fi

if (( $+commands[bat] )); then
    alias cat='bat --paging=never --style=auto'
    alias bcat='command cat'
    alias less='bat --paging=always --style=auto'
fi

# ───────────────────────────────────────────────────────────────────────────
# 3. FILE OPERATIONS (helper-backed, safe)
# ───────────────────────────────────────────────────────────────────────────

alias md='mkdir -p'
alias mkcd='_mkcd'
alias new='_touchf'
alias touchf='_touchf'
alias rename='_rename'
alias cpv='_copy'
alias mvv='_move'
alias del='_delete'
alias backup='_backup'
alias tmpdir='_tmpdir'
alias edit='_edit_file'
alias open='_open'
alias here='_here'
alias edit-here='_edit_here'

# ───────────────────────────────────────────────────────────────────────────
# 4. ARCHIVES
# ───────────────────────────────────────────────────────────────────────────

alias extract='_extract'
alias compress='_compress'

# ───────────────────────────────────────────────────────────────────────────
# 5. GIT
# ───────────────────────────────────────────────────────────────────────────

alias g='git'
alias gs='git status -sb'
alias gst='git status'
alias gad='git add'
alias gaa='git add --all'
alias gap='git add --patch'
alias gcommit='_gcommit'
alias gcomit='_gcomit'
alias gamend='_gamend'
alias gco='_gcheckout'
alias gsw='git switch'
alias gbranch='_gbranch'
alias gba='git branch --all'
alias gbd='git branch --delete'
alias gpush='_gpush'
alias gpull='_gpull'
alias gfetch='_gfetch'
alias gl='_glog'
alias glog='git log'
alias glogp='git log --graph --decorate --stat'
alias gdiff='git diff'
alias gdiffs='git diff --staged'
alias gclone='_gclone'
alias gr='git remote -v'
alias gstash='git stash'
alias gstp='git stash pop'
alias groot='_groot'
alias gstatus='_gstatus'

# ───────────────────────────────────────────────────────────────────────────
# 6. SYSTEM / INFO
# ───────────────────────────────────────────────────────────────────────────

alias df='_df'
alias du='_du'
alias big='_bigfiles'
alias mem='_mem'
alias sys='_sysinfo'
alias path='_path'
alias aliass='_alias'
alias als='_alias'
alias reload='_reload'
alias zshrc='_zshrc'
alias mkproj='_mkproject'
alias c='clear'
alias cls='clear'

if (( $+commands[btop] )); then alias top='btop'; alias htop='btop'; fi
if (( $+commands[fastfetch] )); then alias ff='fastfetch'; alias neofetch='fastfetch'; fi
if (( $+commands[onefetch] )); then alias gfet='onefetch'; alias gitfetch='onefetch'; fi

# ───────────────────────────────────────────────────────────────────────────
# 7. NETWORK
# ───────────────────────────────────────────────────────────────────────────

alias ports='_ports'
alias portkill='_portkill'
alias myip='_myip'
alias localip='_lanip'
alias publicip='_wanip'
alias serve='_serve'
alias ping='ping -c 5'
alias wget='wget -c'
alias curlh='curl -I'

# ───────────────────────────────────────────────────────────────────────────
# 8. PACKAGE / TOOL SHORTCUTS (guarded)
# ───────────────────────────────────────────────────────────────────────────

if (( $+commands[pacman] )); then
    alias pms='sudo pacman -S'
    alias pmr='sudo pacman -Rns'
    alias pmu='sudo pacman -Syu'
    alias pmq='pacman -Ss'
fi
if (( $+commands[yay] )); then
    alias ys='yay -S'
    alias yu='yay -Syu'
    alias yss='yay -Ss'
fi
if (( $+commands[docker] )); then
    alias d='docker'
    alias dc='docker compose'
    alias dps='docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
    alias dimg='docker images'
    alias dlog='docker logs -f'
fi

if (( $+commands[python3] )); then alias py='python3'; alias venv='python3 -m venv .venv'; fi
if (( $+commands[npm] )); then alias ni='npm install'; alias nr='npm run'; alias nrd='npm run dev'; fi
if (( $+commands[uv] )); then alias uvr='uv run'; alias uvs='uv sync'; fi
if (( $+commands[nvim] )); then alias vim='nvim'; alias vi='nvim'; alias nano='nvim';alias emacs='nvim'; fi

# ───────────────────────────────────────────────────────────────────────────
# 9. SAFETY / QUALITY OF LIFE
# ───────────────────────────────────────────────────────────────────────────

alias grep='grep --color=auto'
alias diffc='delta'
alias ip='ip -color=auto'
alias cp='cp -iv'
alias mv='mv -iv'
alias rm='rm -Iv --preserve-root'
alias mkdir='mkdir -pv'
alias chmod='chmod --preserve-root'
alias chown='chown --preserve-root'
alias please='sudo'
alias sudo='sudo '  # allow alias expansion after sudo

# ───────────────────────────────────────────────────────────────────────────
# 10. QUICK UTILITIES
# ───────────────────────────────────────────────────────────────────────────

alias md5='md5sum'
alias sha1='sha1sum'
alias sha256='sha256sum'
alias sha512='sha512sum'
alias now='date +"%Y-%m-%d %H:%M:%S"'
alias nowutc='date -u +"%Y-%m-%dT%H:%M:%SZ"'
alias week='date +%V'
alias today='date +"%A, %B %d %Y"'
alias epoch='date +%s'
alias fpathls='print -l $fpath'

if (( $+commands[wl-copy] )); then
    alias copy='wl-copy'
    alias paste='wl-paste'
elif (( $+commands[xclip] )); then
    alias copy='xclip -selection clipboard'
    alias paste='xclip -selection clipboard -o'
fi

if (( $+commands[wl-copy] )) && [[ -f ~/.ssh/id_ed25519.pub ]]; then
    alias pubkey='cat ~/.ssh/id_ed25519.pub | wl-copy && echo "󰄬 SSH public key copied"'
fi

alias help='man'
alias where='which'
alias tl='tldr'
alias cpuinfo='lscpu'
alias weather='curl -fsS wttr.in'
alias note='_note'
alias notes='_notes'

# ───────────────────────────────────────────────────────────────────────────
# 11. GIT EXTRAS
# ───────────────────────────────────────────────────────────────────────────

alias gundo='git reflog --date=iso -10'
alias gss='git stash show -p'
alias gclean='git clean -fdn'
alias gcleanf='git clean -fd'
alias gcontrib='git shortlog -sn --all --no-merges'

# ───────────────────────────────────────────────────────────────────────────
# 12. SYSTEM / PROCESS EXTRAS
# ───────────────────────────────────────────────────────────────────────────

alias psg='_psgrep'
alias myps='ps -u "$USER" -o pid,%cpu,%mem,comm'
alias envs='_envsearch'
alias htopcmds='_hist_top'
alias jctlerr='journalctl -p err -b --no-pager | tail -n 50'
alias jctlf='journalctl -f'
alias sysfailed='systemctl --failed'
alias ffind='_ffind'
alias dfind='_dfind'

# ───────────────────────────────────────────────────────────────────────────
# 13. SUGGESTED / OPTIONAL
# ───────────────────────────────────────────────────────────────────────────
alias nh=' '    # Atuin History Ignore
alias ,=' '     # Atuin History Ignore
alias dirs='dirs -v'
alias lazyzellij="_lzj"
alias lzj="_lzj"
alias lazytmux="_ltx"
alias ltx="_ltx"
alias hastebin="_hastebin"
alias server="_server"
alias pal="_pal"
alias envgrep="_envgrep"
