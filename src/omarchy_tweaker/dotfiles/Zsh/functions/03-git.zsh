# ╭──────────────────────────────────────────────────────────────────────────╮
# │                               GIT HELPERS                                │
# ╰──────────────────────────────────────────────────────────────────────────╯

_git_repo() { command git rev-parse --is-inside-work-tree >/dev/null 2>&1; }
_git_require() { _git_repo || { _gum_error "󰊢  Not a git repository"; return 1; }; }

_gfetch() { _git_require || return 1; _gum_spin "Fetching remotes" command git fetch --prune --tags "$@" && _gum_ok "Fetch complete"; }
_gpull()  { _git_require || return 1; _gum_spin "Pulling changes" command git pull --ff-only "$@" && _gum_ok "Pull complete"; }
_gpush()  { _git_require || return 1; _gum_spin "Pushing commits" command git push "$@" && _gum_ok "Push complete"; }

_gclone() {
    local repo="${1:-}"
    [[ -n "$repo" ]] || repo="$(_gum_input 'https://github.com/user/repo.git' '' '󰊢  Clone repository')" || return 1
    [[ -n "$repo" ]] || return 1
    _gum_spin "Cloning repository" command git clone -- "$repo" "${@:2}" && _gum_ok "Cloned: $repo"
}

_gcheckout() {
    _git_require || return 1
    local branch="${1:-}"
    if [[ -z "$branch" ]]; then
        branch="$(command git branch --all --format='%(refname:short)' | sed 's#^origin/##' | awk '!seen[$0]++' | _gum_filter '󰘬  Checkout branch')" || return 1
    fi
    [[ -n "$branch" ]] || return 1
    command git checkout -- "$branch" && _gum_ok "Checked out: $branch"
}

_gbranch() {
    _git_require || return 1
    if ! _is_tty; then command git branch --all --format='%(refname:short)'; return 0; fi
    local branch
    branch="$(command git branch --all --format='%(refname:short)' | command sed '/^$/d' | _gum_filter '󰘬  Select branch')" || return 1
    [[ -n "$branch" ]] || return 1
    command git switch -- "$branch" && _gum_ok "Switched to: $branch"
}

_gcommit() {
    _git_require || return 1
    local msg="${*:-}"
    [[ -n "$msg" ]] || msg="$(_gum_input 'feat: describe change' '' '󰜘  Commit message')" || return 1
    [[ -n "$msg" ]] || { _gum_error "Commit message required"; return 1; }
    command git commit -m "$msg" && _gum_ok "Committed"
}

_gcomit() {
    _git_require || return 1
    local type scope summary body msg
    type="$(_gum_choose '󰜘  Commit type' feat fix docs style refactor perf test build ci chore revert)" || return 1
    scope="$(_gum_input 'scope (optional)' '' '󰜘  Scope')" || return 1
    summary="$(_gum_input 'short summary' '' '󰜘  Summary')" || return 1
    [[ -n "$summary" ]] || { _gum_error "Summary required"; return 1; }
    [[ -n "$scope" ]] && msg="$type($scope): $summary" || msg="$type: $summary"
    body="$(command gum write --header='󰜘  Body (optional, Ctrl+D to finish)' --placeholder='Details...' --width=80 --height=6)" || return 1
    if [[ -n "${body//[[:space:]]/}" ]]; then command git commit -m "$msg" -m "$body"; else command git commit -m "$msg"; fi
    _gum_ok "Committed: $msg"
}

_gamend() {
    _git_require || return 1
    local msg body
    msg="$(_gum_input 'commit message' "$(command git log -1 --pretty=%s 2>/dev/null)" '󰜘  Amend message')" || return 1
    [[ -n "$msg" ]] || { _gum_error "Message required"; return 1; }
    body="$(command gum write --header='󰜘  Amend body (optional, Ctrl+D)' --value="$(command git log -1 --pretty=%b 2>/dev/null)" --width=80 --height=6)" || return 1
    if [[ -n "${body//[[:space:]]/}" ]]; then command git commit --amend -m "$msg" -m "$body"; else command git commit --amend -m "$msg"; fi
    _gum_ok "Amended latest commit"
}

_groot() {
    _git_require || return 1
    builtin cd -- "$(command git rev-parse --show-toplevel)" || return 1
    _gum_ok "󰊢  ${PWD/#$HOME/~}"
}

_glog() {
    _git_require || return 1
    local n="${1:-10}"
    [[ "$n" == <-> ]] || n=10
    _gum_title "󰊢  Git Log" "last $n commits"
    command git --no-pager log --graph --decorate --oneline -n "$n"
}


_gstatus() {
    _git_require || return 1
    _gum_title "󰊢  Git Status" "$(command git rev-parse --abbrev-ref HEAD 2>/dev/null)"
    command git status -sb
}
