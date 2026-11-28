# ╭──────────────────────────────────────────────────────────────────────────╮
# │                             FILE OPERATIONS                              │
# ╰──────────────────────────────────────────────────────────────────────────╯

_edit_file() {
    local file="${1:-}"
    [[ -n "$file" ]] || { _gum_info "Usage: edit <file>"; return 1; }
    [[ -d "$file" ]] && { _gum_error "󰉋 '$file' is a directory"; return 1; }
    [[ -f "$file" ]] || { _gum_error "󰈔 File not found: $file"; return 1; }
    _gum_info "󰏫 Opening ${file:t} in ${EDITOR:-nvim}"
    "${EDITOR:-nvim}" -- "$file"
}

_open() {
    local target="${1:-.}"
    _path_exists "$target" || { _gum_error "Path not found: $target"; return 1; }
    if _has xdg-open; then _gum_spin "Opening ${target:t}" xdg-open "$target" >/dev/null 2>&1 || xdg-open "$target" >/dev/null 2>&1 &!
    elif _has open; then open "$target"
    else _gum_error "No opener found (xdg-open/open)"; return 1; fi
}

_here() { _open "${1:-.}"; }

_edit_here() {
    local dir="${1:-.}"
    [[ -d "$dir" ]] || { _gum_error "Directory not found: $dir"; return 1; }
    if _has code; then _gum_info "󰨞 Opening in VS Code"; code -- "$dir"
    elif _has nvim; then _gum_info "󰏫 Opening in Neovim"; nvim -- "$dir"
    else _gum_error "No editor found"; return 1; fi
}

_mkcd() {
    local dir="${1:-}"
    [[ -n "$dir" ]] || { _gum_info "Usage: mkcd <directory>"; return 1; }
    [[ -e "$dir" && ! -d "$dir" ]] && { _gum_error "Path exists and is not a directory: $dir"; return 1; }
    command mkdir -p -- "$dir" || { _gum_error "Failed to create: $dir"; return 1; }
    builtin cd -- "$dir" || return 1
    _gum_ok "󰉋  Entered: ${PWD/#$HOME/~}"
}

_touchf() {
    local file="${1:-}"
    [[ -n "$file" ]] || { _gum_info "Usage: touchf <file>"; return 1; }
    [[ "$file" == */ || "$file" == "." || "$file" == ".." ]] && { _gum_error "Invalid filename: $file"; return 1; }
    [[ -e "$file" || -L "$file" ]] && { _gum_error "Already exists: $file"; return 1; }
    local parent="${file:h}"
    command mkdir -p -- "$parent" || { _gum_error "Failed to create parent: $parent"; return 1; }
    [[ -w "$parent" ]] || { _gum_error "No write permission: $parent"; return 1; }
    command touch -- "$file" && _gum_ok "󰈔  Created: ${file/#$HOME/~}" || { _gum_error "Failed to create: $file"; return 1; }
}

_rename() {
    local src="${1:-}" dst="${2:-}"
    [[ -n "$src" && -n "$dst" ]] || { _gum_info "Usage: rename <source> <destination>"; return 1; }
    _path_exists "$src" || { _gum_error "Source not found: $src"; return 1; }
    [[ "$src:A" == "$dst:A" ]] && { _gum_warn "Source and destination are identical"; return 1; }
    _path_exists "$dst" && { _gum_error "Destination exists: $dst"; return 1; }
    [[ -d "${dst:h}" ]] || { _gum_error "Destination directory missing: ${dst:h}"; return 1; }
    _gum_confirm "󰑕  Rename '${src:t}' → '${dst:t}'?" || { _gum_warn "Cancelled"; return 1; }
    _gum_spin "Renaming" command mv -n -- "$src" "$dst" && _gum_ok "Renamed: ${src:t} → ${dst:t}"
}

_copy() {
    local src="${1:-}" dst="${2:-}"
    [[ -n "$src" && -n "$dst" ]] || { _gum_info "Usage: cpv <source> <destination>"; return 1; }
    _path_exists "$src" || { _gum_error "Source not found: $src"; return 1; }
    _path_exists "$dst" && { _gum_error "Destination exists: $dst"; return 1; }
    [[ -d "${dst:h}" ]] || { _gum_error "Destination directory missing: ${dst:h}"; return 1; }
    _gum_confirm "󰆏  Copy '${src:t}' → '${dst:t}'?" || { _gum_warn "Cancelled"; return 1; }
    _gum_spin "Copying" command cp -a -- "$src" "$dst" && _gum_ok "Copied: ${src:t} → ${dst:t}"
}

_move() {
    local src="${1:-}" dst="${2:-}"
    [[ -n "$src" && -n "$dst" ]] || { _gum_info "Usage: mvv <source> <destination>"; return 1; }
    _path_exists "$src" || { _gum_error "Source not found: $src"; return 1; }
    _path_exists "$dst" && { _gum_error "Destination exists: $dst"; return 1; }
    [[ -d "${dst:h}" ]] || { _gum_error "Destination directory missing: ${dst:h}"; return 1; }
    [[ -d "$src" && "$dst:A" == "$src:A"/* ]] && { _gum_error "Cannot move directory into itself"; return 1; }
    _gum_confirm "󰆾  Move '${src:t}' → '${dst:t}'?" || { _gum_warn "Cancelled"; return 1; }
    _gum_spin "Moving" command mv -n -- "$src" "$dst" && _gum_ok "Moved: ${src:t} → ${dst:t}"
}

_delete() {
    local target="${1:-}"
    [[ -n "$target" ]] || { _gum_info "Usage: del <path>"; return 1; }
    _path_exists "$target" || { _gum_error "Path not found: $target"; return 1; }
    [[ "$target:A" == "/" || "$target:A" == "$HOME:A" ]] && { _gum_error "Protected path: $target"; return 1; }
    local kind="file"; [[ -d "$target" && ! -L "$target" ]] && kind="directory"
    _confirm_danger "Permanently delete $kind '${target:t}'?" || { _gum_warn "Cancelled"; return 1; }
    _gum_spin "Deleting $kind" command rm -rf -- "$target" && _gum_ok "Deleted $kind: ${target:t}"
}

_backup() {
    local src="${1:-}" ts dst size
    [[ -n "$src" ]] || { _gum_info "Usage: backup <path>"; return 1; }
    _path_exists "$src" || { _gum_error "Path not found: $src"; return 1; }
    ts=$(date '+%Y%m%d_%H%M%S')
    dst="${src%/}.bak.${ts}"
    _gum_spin "Creating backup" command cp -a -- "$src" "$dst" || { _gum_error "Backup failed"; return 1; }
    size=$(command du -sh -- "$dst" 2>/dev/null | awk '{print $1}')
    _gum_ok "󰁯  Backup created: ${dst:t} ${size:+($size)}"
}

_tmpdir() {
    local dir
    dir="$(command mktemp -d "${TMPDIR:-/tmp}/zsh-tmp.XXXXXXXX")" || { _gum_error "mktemp failed"; return 1; }
    _gum_card "󰉋  Temporary Workspace" "Path: $dir" "Cleanup: automatic on exit" >/dev/null
    ( builtin cd -- "$dir" && exec "${SHELL:-zsh}" -i )
    local rc=$?
    command rm -rf -- "$dir" && _gum_ok "Cleaned temp dir: ${dir:t}"
    return $rc
}

_ffind() {
    local pattern="${1:-}"
    local dir="${2:-.}"
    [[ -n "$pattern" ]] || { _gum_error "Usage: ffind <name-pattern> [dir]"; return 1; }
    local rows
    rows="$(command find "$dir" -type f -iname "*${pattern}*" 2>/dev/null | head -n 200 | command awk -F/ '{print $NF"	"$0}')"
    [[ -n "$rows" ]] || { _gum_warn "No files matching: $pattern"; return 1; }
    _gum_title "󰈞  Find Files"
    _gum_subtitle "$pattern in $dir"
    print -r -- "$rows" | _gum_table --columns "󰈔 FILE,󰉋 PATH"
}

_dfind() {
    local pattern="${1:-}"
    local dir="${2:-.}"
    [[ -n "$pattern" ]] || { _gum_error "Usage: dfind <name-pattern> [dir]"; return 1; }
    local rows
    rows="$(command find "$dir" -type d -iname "*${pattern}*" 2>/dev/null | head -n 200 | command awk -F/ '{print $NF"	"$0}')"
    [[ -n "$rows" ]] || { _gum_warn "No directories matching: $pattern"; return 1; }
    _gum_title "󰉋  Find Directories"
    _gum_subtitle "$pattern in $dir"
    print -r -- "$rows" | _gum_table --columns "󰉋 DIR,󰉋 PATH"
}
