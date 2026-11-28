# ╭──────────────────────────────────────────────────────────────────────────╮
# │                             ARCHIVE UTILITIES                            │
# ╰──────────────────────────────────────────────────────────────────────────╯

_extract() {
    local f="${1:-}"
    [[ -n "$f" ]] || { _gum_info "Usage: extract <archive> [dest]"; return 1; }
    [[ -f "$f" ]] || { _gum_error "Archive not found: $f"; return 1; }
    local dest="${2:-.}"
    command mkdir -p -- "$dest" || return 1
    _gum_section "󰛫  EXTRACT ARCHIVE"
    _gum_info "Source: $f"
    _gum_info "Destination: $dest"
    local rc=0
    case "${f:l}" in
        *.tar.gz|*.tgz)   _gum_spin "Extracting tar.gz" command tar -xzf "$f" -C "$dest" ;;
        *.tar.bz2|*.tbz2) _gum_spin "Extracting tar.bz2" command tar -xjf "$f" -C "$dest" ;;
        *.tar.xz|*.txz)   _gum_spin "Extracting tar.xz" command tar -xJf "$f" -C "$dest" ;;
        *.tar.zst|*.tzst) _gum_spin "Extracting tar.zst" command tar --zstd -xf "$f" -C "$dest" ;;
        *.tar)            _gum_spin "Extracting tar" command tar -xf "$f" -C "$dest" ;;
        *.zip)            _gum_spin "Extracting zip" command unzip -q "$f" -d "$dest" ;;
        *.7z)             _gum_spin "Extracting 7z" command 7z x "$f" "-o$dest" >/dev/null ;;
        *.rar)            _gum_spin "Extracting rar" command unrar x -op"$dest" "$f" >/dev/null ;;
        *.gz)             _gum_spin "Extracting gz" command gzip -dk "$f" ;;
        *.zst)            _gum_spin "Extracting zst" command zstd -dk "$f" ;;
        *) _gum_error "Unsupported archive: $f"; return 1 ;;
    esac || rc=$?
    (( rc == 0 )) && _gum_ok "Extracted: ${f:t}" || _gum_error "Extraction failed: $f"
    return $rc
}

_compress() {
    local format="" out=""
    if (( $# < 2 )); then
        _gum_info "Usage: compress <tar.gz|tar.zst|tar.xz|zip|7z> <output> <paths...>"
        return 1
    fi
    case "$1" in
        tar.gz|tgz|tar.zst|tzst|tar.xz|txz|tar|zip|7z)
            format="$1"; out="${2:-}"; shift 2 ;;
        *)
            out="$1"; shift
            case "$out" in
                *.tar.gz) format="tar.gz" ;; *.tar.zst) format="tar.zst" ;; *.tar.xz) format="tar.xz" ;;
                *.tar.bz2) format="tar.bz2" ;; *.tar) format="tar" ;; *.zip) format="zip" ;; *.7z) format="7z" ;;
                *) _gum_error "Unknown archive format: $out"; return 1 ;;
            esac ;;
    esac
    (( $# >= 1 )) || { _gum_error "No input paths provided"; return 1; }
    [[ -n "$out" ]] || { _gum_error "Output path required"; return 1; }
    local -a inputs=("$@")
    local p; for p in "${inputs[@]}"; do _path_exists "$p" || { _gum_error "Missing: $p"; return 1; }; done
    _gum_section "󰗄  CREATE ARCHIVE"
    _gum_info "Format: $format"
    _gum_info "Output: $out"
    _gum_info "Items:  ${#inputs[@]}"
    _path_exists "$out" && { _gum_error "Output already exists: $out"; return 1; }
    if _is_tty; then
        _gum_confirm "Create archive '${out:t}'?" || { _gum_warn "Cancelled"; return 1; }
    fi
    local rc=0
    case "$format" in
        tar.gz|tgz)   _gum_spin "Compressing tar.gz" command tar -czf "$out" -- "${inputs[@]}" ;;
        tar.zst|tzst) _gum_spin "Compressing tar.zst" command tar --zstd -cf "$out" -- "${inputs[@]}" ;;
        tar.xz|txz)   _gum_spin "Compressing tar.xz" command tar -cJf "$out" -- "${inputs[@]}" ;;
        tar)          _gum_spin "Compressing tar" command tar -cf "$out" -- "${inputs[@]}" ;;
        zip)          _gum_spin "Compressing zip" command zip -qr "$out" "${inputs[@]}" ;;
        7z)           _gum_spin "Compressing 7z" command 7z a "$out" "${inputs[@]}" >/dev/null ;;
        *) _gum_error "Unsupported format: $format"; return 1 ;;
    esac || rc=$?
    (( rc == 0 )) && _gum_ok "Created: $out" || _gum_error "Compression failed"
    return $rc
}
