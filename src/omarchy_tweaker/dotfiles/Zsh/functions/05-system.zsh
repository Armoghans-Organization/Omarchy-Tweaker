# ╭──────────────────────────────────────────────────────────────────────────╮
# │                              SYSTEM HELPERS                              │
# ╰──────────────────────────────────────────────────────────────────────────╯

_path() {
    _gum_title "󰆍  PATH Entries" "Execution order • ${#path[@]} entries"
    local i=1 p
    for p in "${(@)path}"; do
        local icon="󰉋"; [[ -d "$p" ]] || icon="󰀦"
        printf '%d\t%s %s\n' "$i" "$icon" "$p"
        ((i++))
    done | _gum_table --columns "󰉻 #,󰉋 DIRECTORY"
}

_alias() {
    local filter="${1:-}"
    (( ${#aliases[@]} )) || { _gum_warn "No aliases defined"; return 0; }
    local name i=1
    local -a rows_arr=()
    for name in ${(ko)aliases}; do
        local val="${aliases[$name]}"
        if [[ -z "$filter" || "$name" == *"$filter"* || "$val" == *"$filter"* ]]; then
            rows_arr+=("$(printf '%d\t%s\t%s' "$i" "$name" "$val")")
            ((i++))
        fi
    done
    local out; out="${(F)rows_arr}"
    [[ -n "$out" ]] || { _gum_warn "No aliases matching: $filter"; return 1; }
    local count=$((i-1))
    _gum_title "󰌌  Aliases" "$count ${filter:+matching \"$filter\" }defined"
    print -r -- "$out" | _gum_table --columns "󰉻 #,󰌌 ALIAS,󰆍 COMMAND"
    print
    _gum_dim "󰋼 Tip: aliass [filter] to search • unalias <name> to remove"
}

_df() {
    _has df || { _gum_error "df not found"; return 1; }
    _gum_title "󰋊  Disk Space" "Mounted filesystems"
    command df -hP -x tmpfs -x devtmpfs 2>/dev/null | \
        awk 'NR==1{next} {
            use=$5; gsub(/%/,"",use); icon="󰄬"; if(use+0>=90) icon="󰀦"; else if(use+0>=75) icon="󰈸";
            target=$6; for(i=7;i<=NF;i++) target=target" "$i;
            printf "%s %s\t%s\t%s\t%s\t%s\t%s\n", icon,$1,$2,$3,$4,$5,target
        }' | _gum_table --columns "󰋊 FILESYSTEM,󰁹 SIZE,󰓅 USED,󰁹 AVAIL,󰓅 USE%,󰉋 MOUNT"
}

_du() {
    local dir="${1:-.}"
    [[ -d "$dir" ]] || { _gum_error "Directory not found: $dir"; return 1; }
    _gum_title "󰉋  Disk Usage" "${dir:A}"
    command du -h -d 1 -- "$dir" 2>/dev/null | sort -hr | head -15 | \
        awk '{size=$1; $1=""; sub(/^[ \t]+/,""); printf "%s\t%s\n",size,$0}' | \
        _gum_table --columns "󰁹 SIZE,󰉋 PATH"
}

_bigfiles() {
    local dir="${1:-.}" n="${2:-20}"
    [[ -d "$dir" ]] || { _gum_error "Directory not found: $dir"; return 1; }
    [[ "$n" == <-> ]] || n=20
    _gum_title "󰈙  Largest Files" "${dir:A} • top $n"
    local raw
    if _has fd; then
        raw="$(command fd --type f --hidden --exclude .git . "$dir" -0 2>/dev/null | command xargs -0 -r du -b 2>/dev/null)"
    else
        raw="$(command find "$dir" -type f -not -path '*/.git/*' -printf '%s\t%p\n' 2>/dev/null)"
    fi
    [[ -n "$raw" ]] || { _gum_warn "No files found"; return 0; }
    print -r -- "$raw" | sort -nr | head -n "$n" | awk -F'\t' '{
        b=$1; $1=""; sub(/^\t/,""); p=$0;
        split("B KiB MiB GiB TiB",u," "); i=1; d=b; while(d>=1024&&i<5){d/=1024;i++}
        if(i==1) sz=sprintf("%d %s",d,u[i]); else sz=sprintf("%.1f %s",d,u[i]);
        printf "%s\t%s\n", sz, p
    }' | _gum_table --columns "󰁹 SIZE,󰈔 FILE"
}

_mem() {
    _has free || { _gum_error "free not found"; return 1; }
    _gum_title "󰍛  Memory Usage" "RAM & swap"
    command free -h | awk 'NR==1{next}
      /^Mem:/{printf "󰍛 RAM\t%s\t%s\t%s\t%s\t%s\t%s\n",$2,$3,$4,$5,$6,$7}
      /^Swap:/{printf "󰾴 SWAP\t%s\t%s\t%s\t-\t-\t-\n",$2,$3,$4}' | \
      _gum_table --columns "󰉺 TYPE,󰁹 TOTAL,󰓅 USED,󰁹 FREE,󰍛 SHARED,󰆼 CACHE,󰒋 AVAIL"
}

_sysinfo() {
    _gum_title "󰒓  System Info"
    local host kernel uptime_s shell_v cpu mem_total
    host="${HOST:-$(hostname -s 2>/dev/null)}"
    kernel="$(uname -r 2>/dev/null)"
    uptime_s="$(uptime -p 2>/dev/null || uptime 2>/dev/null)"
    shell_v="zsh ${ZSH_VERSION:-unknown}"
    cpu="$(command lscpu 2>/dev/null | awk -F: '/Model name/{gsub(/^[ \t]+/,"",$2); print $2; exit}')"
    mem_total="$(command free -h 2>/dev/null | awk '/^Mem:/{print $2; exit}')"
    {
        printf '󰌢 Host\t%s\n' "$host"
        printf '󰌽 Kernel\t%s\n' "$kernel"
        printf '󰅐 Uptime\t%s\n' "$uptime_s"
        printf '󰆍 Shell\t%s\n' "$shell_v"
        printf '󰏫 Editor\t%s\n' "${EDITOR:-unknown}"
        printf '󰻠 CPU\t%s\n' "${cpu:-unknown}"
        printf '󰍛 RAM\t%s\n' "${mem_total:-unknown}"
    } | _gum_table --columns "󰋼 KEY,󰋽 VALUE"
}

_envsearch() {
    local q="${1:-}"
    local rows
    if [[ -n "$q" ]]; then
        rows="$(printenv | command grep -i -- "$q" | sort | command awk -F= '{k=$1; $1=""; sub(/^=/,"",$0); print k"\t"$0}')"
    else
        rows="$(printenv | sort | command awk -F= '{k=$1; $1=""; sub(/^=/,"",$0); print k"\t"$0}')"
    fi
    [[ -n "$rows" ]] || { _gum_warn "No environment variables matched"; return 1; }
    _gum_title "󰏗  Environment Variables"
    [[ -n "$q" ]] && _gum_subtitle "filter: $q"
    print -r -- "$rows" | _gum_table --columns "󰋼 KEY,󰋽 VALUE"
}

_hist_top() {
    local n="${1:-15}"
    [[ "$n" =~ ^[0-9]+$ ]] || n=15
    local rows
    rows="$(fc -ln 1 2>/dev/null | command awk '{cmd=$1; for(i=2;i<=NF;i++) cmd=cmd" "$i; c[cmd]++} END{for(k in c) printf "%s\t%s\n",c[k],k}' | command sort -nr | head -n "$n")"
    [[ -n "$rows" ]] || { _gum_warn "No history available"; return 1; }
    _gum_title "󰋚  Top Commands"
    _gum_subtitle "from shell history • top $n"
    print -r -- "$rows" | _gum_table --columns "󰆙 COUNT,󰆍 COMMAND"
}
