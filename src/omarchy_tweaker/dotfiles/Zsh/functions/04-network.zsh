# ╭──────────────────────────────────────────────────────────────────────────╮
# │                              NETWORK HELPERS                             │
# ╰──────────────────────────────────────────────────────────────────────────╯

_ports() {
    local filter="${1:-}"
    _has ss || { _gum_error "ss not found"; return 1; }
    local rows
    rows="$(command ss -tulpenH 2>/dev/null | awk '{
        proto=toupper($1); state=$2; local=$5; proc="󰋼 -";
        if (match($0,/users:\(\("([^"]+)"/,m)) proc="󰆍 " m[1];
        gsub(/\*/,"0.0.0.0",local);
        printf "%s\t%s\t%s\t%s\n", proto, state, local, proc;
    }')"
    [[ -n "$rows" ]] || { _gum_info "No listening sockets"; return 0; }
    [[ -n "$filter" ]] && rows="$(print -r -- "$rows" | command grep -i -- "$filter")"
    [[ -n "$rows" ]] || { _gum_warn "No sockets matching: $filter"; return 1; }
    _gum_title "󰈀  Listening Ports" "${filter:+Filter: $filter • }$(print -r -- "$rows" | wc -l | tr -d ' ') sockets"
    print -r -- "$rows" | _gum_table --columns "󰒍 PROTO,󰋼 STATE,󰌘 LOCAL,󰆍 PROCESS"
}

_portkill() {
    local port="${1:-}" line
    if [[ -z "$port" ]]; then
        line="$(command ss -tulpenH 2>/dev/null | _gum_filter '󰈀  Select socket to kill')" || return 1
        port="${${(z)line}[5]##*:}"
    fi
    [[ "$port" == <-> ]] || { _gum_error "Invalid port: $port"; return 1; }
    local -a pids
    pids=(${(f)"$(command ss -tlnpH "sport = :$port" 2>/dev/null | command grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u)"})
    (( ${#pids[@]} )) || { _gum_error "No process listening on port $port"; return 1; }
    _confirm_danger "Kill port $port (PIDs: ${pids[*]})?" || return 1
    local pid; for pid in "${pids[@]}"; do
        command kill "$pid" 2>/dev/null && _gum_ok "Killed PID $pid" || _gum_warn "Failed PID $pid (try sudo)"
    done
}

_myip() {
    local lan wan
    lan="$(command ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')"
    wan="$(command curl -fsS --max-time 4 https://ipinfo.io/ip 2>/dev/null || print -r -- unavailable)"
    _gum_title "󰖟  Network Addresses"
    printf '󰩟 LAN\t%s\n󰖟 WAN\t%s\n' "${lan:-unknown}" "${wan:-unknown}" | _gum_table --columns "󰌘 TYPE,󰩟 ADDRESS"
}

_lanip() { command ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}'; }
_wanip() { command curl -fsS --max-time 4 https://ipinfo.io/ip 2>/dev/null; print; }

_serve() {
    local port="${1:-8000}" dir="${2:-.}"
    [[ "$port" == <-> ]] || { _gum_error "Port must be numeric"; return 1; }
    [[ -d "$dir" ]] || { _gum_error "Directory not found: $dir"; return 1; }
    _gum_card "󰖟  Local HTTP Server" "Dir:  ${dir:A}" "URL:  http://127.0.0.1:$port" "Stop: Ctrl+C"
    if _has python3; then command python3 -m http.server "$port" --bind 127.0.0.1 --directory "$dir"
    elif _has python; then (builtin cd -- "$dir" && command python -m SimpleHTTPServer "$port")
    else _gum_error "python3 not found"; return 1; fi
}
