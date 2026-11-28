# ╭──────────────────────────────────────────────────────────────────────────╮
# │                          ZSH UI / HELPER UTILITIES                       │
# │                Fast, reusable, sexy gum-powered shell helpers            │
# ╰──────────────────────────────────────────────────────────────────────────╯

# UI helpers. Define always; keep heavy behavior out of load path.

typeset -gA ZSH_UI
: ${ZSH_UI[ok]:='󰄬'}
: ${ZSH_UI[err]:='󰅙'}
: ${ZSH_UI[warn]:='󰀦'}
: ${ZSH_UI[info]:='󰋼'}
: ${ZSH_UI[ask]:='󰋗'}
: ${ZSH_UI[debug]:='󰃤'}
: ${ZSH_UI[search]:=''}
: ${ZSH_UI[git]:='󰊢'}
: ${ZSH_UI[file]:='󰈔'}
: ${ZSH_UI[dir]:='󰉋'}
: ${ZSH_UI[net]:='󰖟'}
: ${ZSH_UI[sys]:='󰍛'}
: ${ZSH_UI[pkg]:='󰏗'}
: ${ZSH_UI[arrow]:='󰜴'}

typeset -gA ZSH_THEME
typeset -g _ZSH_THEME_LOADED=0

_ui_has() { (( $+commands[$1] )); }
_has() { (( $+commands[$1] )); }
_has_gum() { (( $+commands[gum] )); }

_ui_load_theme() {
    (( _ZSH_THEME_LOADED )) && return 0
    _ZSH_THEME_LOADED=1
    # defaults (ANSI-friendly, theme-agnostic)
    ZSH_THEME=(
        [bg]="" [fg]="" [accent]="#89b4fa" [muted]="#6c7086"
        [ok]="#a6e3a1" [warn]="#f9e2af" [err]="#f38ba8" [info]="#89dceb"
        [border]="#89b4fa" [header]="#cba6f7" [title]="#f5c2e7"
        [select]="#f5c2e7" [dim]="#585b70" [alt]="#74c7ec"
    )
    local -a candidates=()
    [[ -n "${OMARCHY_THEME_PATH:-}" ]] && candidates+=("${OMARCHY_THEME_PATH}/colors.toml")
    candidates+=(
        "${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/current/theme/colors.toml"
        "/usr/share/omarchy/current/theme/colors.toml"
    )
    if (( $+commands[omarchy] )); then
        local cur; cur="$(command omarchy theme current 2>/dev/null | tail -n1)"
        [[ -n "$cur" ]] && candidates+=("/usr/share/omarchy/themes/$cur/colors.toml" "${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/themes/$cur/colors.toml")
    fi
    local f k v
    for f in "${candidates[@]}"; do
        [[ -r "$f" ]] || continue
        while IFS='=' read -r k v; do
            k="${k//[[:space:]]/}"; v="${v##[[:space:]]}"; v="${v%%[[:space:]]}"
            v="${v%\"}"; v="${v#\"}"; v="${v%\'}"; v="${v#\'}"
            [[ "$k" == \#* || -z "$k" || -z "$v" ]] && continue
            case "$k" in
                accent) ZSH_THEME[accent]="$v"; ZSH_THEME[border]="$v"; ZSH_THEME[info]="$v" ;;
                selection|cursor) ZSH_THEME[select]="$v"; ZSH_THEME[header]="$v" ;;
                foreground|fg|bright_foreground) ZSH_THEME[fg]="$v" ;;
                background|bg) ZSH_THEME[bg]="$v" ;;
                muted|dark_foreground) ZSH_THEME[muted]="$v"; ZSH_THEME[dim]="$v" ;;
                red) ZSH_THEME[err]="$v" ;;
                green) ZSH_THEME[ok]="$v" ;;
                yellow|orange) ZSH_THEME[warn]="$v" ;;
                blue|cyan) ZSH_THEME[alt]="$v" ;;
                magenta) ZSH_THEME[title]="$v" ;;
            esac
        done < "$f"
        break
    done
    return 0
}

_ui_c() { _ui_load_theme; print -r -- "${ZSH_THEME[$1]:-${2:-#89b4fa}}"; }
_ui_hex_to_ansi() {
    local hex="${1#\#}" bold="${2:-0}" r g b
    [[ "$hex" =~ ^[0-9A-Fa-f]{6}$ ]] || { print -r -- "\033[38;5;81m"; return; }
    r=$((16#${hex[1,2]})); g=$((16#${hex[3,4]})); b=$((16#${hex[5,6]}))
    if [[ "$bold" == "1" ]]; then printf '\033[1;38;2;%d;%d;%dm' "$r" "$g" "$b"
    else printf '\033[38;2;%d;%d;%dm' "$r" "$g" "$b"; fi
}


# Fallbacks when gum is unavailable
if ! _has_gum; then
  _gum_style() { print -r -- "$@"; }
  _gum_title() { print; print -r -- "== $1 =="; [[ -n "${2:-}" ]] && print -r -- " $2"; }
  _gum_section(){ print; print -r -- "-- $* --"; }
  _gum_ok()    { print -r -- "[OK] $*"; }
  _gum_info()  { print -r -- "[INFO] $*"; }
  _gum_warn()  { print -r -- "[WARN] $*" >&2; }
  _gum_error() { print -r -- "[ERR] $*" >&2; }
  _gum_debug() { [[ -n "${ZSH_DEBUG:-}" ]] && print -r -- "[DBG] $*"; }
  _gum_dim()   { print -r -- "$*"; }
  _gum_badge() { print -r -- "[$*]"; }
  _gum_kv()    { printf '%s\t%s\n' "$1" "$2"; }
  _gum_card()  { local t="$1"; shift; print -r -- "[$t]"; print -r -- "$@"; }
  _gum_confirm(){ local p="${1:-Continue?}"; shift 2>/dev/null||true; print -n "? $p [y/N] "; local r; read -r r; [[ "$r" == [yY]* ]]; }
  _gum_input() { local ph="${1:-}" v="${2:-}" h="${3:-}"; [[ -n "$h" ]] && print -r -- "$h"; local out; print -n "$ph "; read -r out; print -r -- "${out:-$v}"; }
  _gum_choose() { local h="$1"; shift; print -r -- "$h" >&2; local x; select x in "$@"; do print -r -- "$x"; break; done; }
  _gum_filter() { local h="$1"; shift; if (( $+commands[fzf] )); then command fzf --prompt="$h> "; else local x; select x in "$@"; do print -r -- "$x"; break; done; fi; }
  _gum_spin()  { local t="$1"; shift; _gum_info "$t"; "$@"; }
  _gum_table() { command column -t -s $'\t'; }
fi

_gum_style() { command gum style "$@"; }

_gum_title() {
    local title="$1" subtitle="${2:-}"
    print
    local line="󰫢 $title"
    if _has_gum; then
        command gum style --border double --border-foreground "$(_ui_c border)" --foreground "$(_ui_c title)" --bold --padding "0 3" --margin "0 0" "$line"
        [[ -n "$subtitle" ]] && command gum style --foreground "$(_ui_c muted)" --italic --padding "0 2" "  $subtitle"
    else
        print -r -- "== $line =="; [[ -n "$subtitle" ]] && print -r -- "  $subtitle"
    fi
}

_gum_section() {
    print
    if _has_gum; then
        command gum style --foreground "$(_ui_c info)" --bold "╭─ 󰉋 $*"
        command gum style --foreground "$(_ui_c dim)"  "╰──────────────────────────────────────────────"
    else
        print -r -- "-- $* --"
    fi
}

_gum_subtitle() {
    local text="${1:-}"
    [[ -n "$text" ]] || return 0
    local muted="$(_ui_c muted)"
    if _has_gum; then
        command gum style --foreground "$muted" --italic "  ${text}"
    else
        print -r -- "  $text"
    fi
}

_gum_ok()    { command gum style --foreground "$(_ui_c ok)"  " ${ZSH_UI[ok]}  $*"; }
_gum_info()  { command gum style --foreground "$(_ui_c info)"  " ${ZSH_UI[info]}  $*"; }
_gum_warn()  { command gum style --foreground "$(_ui_c warn)" " ${ZSH_UI[warn]}  $*"; }
_gum_error() { command gum style --foreground "$(_ui_c err)" --bold " ${ZSH_UI[err]}  $*" >&2; }
_gum_debug() { [[ -n "${ZSH_DEBUG:-}" ]] && command gum style --foreground "$(_ui_c dim)" " ${ZSH_UI[debug]}  $*"; }
_gum_dim()   { command gum style --foreground "$(_ui_c muted)" " $*"; }
_gum_badge() { command gum style --foreground "$(_ui_c bg "#1e1e2e")" --background "$(_ui_c accent)" --bold --padding "0 1" --margin "0 0 0 1" "$*"; }
_gum_kv()    { printf '%s\t%s\n' "$1" "$2"; }

_gum_card() {
    local title="$1"; shift
    command gum style --border rounded --border-foreground "$(_ui_c border)" --padding "1 2" --margin "0 1" \
        "$( command gum style --foreground "$(_ui_c header)" --bold "$title" )" "$@"
}

_gum_usage() {
    local cmd="$1" desc="$2"; shift 2
    _gum_title "$cmd" "$desc"
    local line
    for line in "$@"; do _gum_dim "  $line"; done
}

_gum_divider() { command gum style --foreground "$(_ui_c dim)" "  ─────────────────────────────────────────────"; }

_gum_confirm() {
    local prompt="${1:-Are you sure?}"
    shift 2>/dev/null || true
    if _has_gum && _is_tty; then
        command gum confirm "$prompt" \
            --affirmative "󰄬 Yes" --negative "󰅖 No" \
            --selected.background "$(_ui_c select)" --selected.foreground "$(_ui_c bg "#1e1e2e")" \
            --unselected.background "$(_ui_c dim)" --unselected.foreground "$(_ui_c fg "#cdd6f4")" \
            --prompt.foreground "$(_ui_c info)" "$@"
    else
        local reply
        print -n "? $prompt [y/N] "
        read -r reply
        [[ "$reply" == [yY] || "$reply" == [yY][eE][sS] ]]
    fi
}

_gum_input() {
    local placeholder="${1:-Type here...}" value="${2:-}" header="${3:-}"
    if _has_gum && _is_tty; then
        local -a args=(--prompt "󰌌 " --prompt.foreground "$(_ui_c info)" --cursor.mode blink --cursor.foreground "$(_ui_c select)" --placeholder "$placeholder" --value "$value" --width 60)
        [[ -n "$header" ]] && args+=(--header "$header" --header.foreground "$(_ui_c header)")
        command gum input "${args[@]}"
    else
        [[ -n "$header" ]] && print -r -- "$header"
        local out; print -n "${placeholder}: "; read -r out; print -r -- "${out:-$value}"
    fi
}

_gum_choose() {
    local header="${1:-Choose an option}"; shift
    if _has_gum && _is_tty; then
        command gum choose --header "$header" --header.foreground "$(_ui_c header)" --cursor.foreground "$(_ui_c select)" --selected.foreground "$(_ui_c select)" --item.foreground "$(_ui_c fg "#cdd6f4")" "$@"
    else
        print -r -- "$header" >&2; local x; select x in "$@"; do print -r -- "$x"; break; done
    fi
}

_gum_filter() {
    local header="${1:-Filter}"; shift
    if _has_gum && _is_tty; then
        command gum filter --header "$header" --header.foreground "$(_ui_c header)" --prompt "${ZSH_UI[search]} " --prompt.foreground "$(_ui_c info)" --indicator.foreground "$(_ui_c select)" --selected-indicator.foreground "$(_ui_c select)" --match.foreground "$(_ui_c accent)" "$@"
    else
        command fzf --prompt="$header> " 2>/dev/null || { local x; select x in "$@"; do print -r -- "$x"; break; done; }
    fi
}

_gum_spin() {
    local title="${1:-Working...}"; shift
    if _has_gum && _is_tty; then
        command gum spin --spinner dot --spinner.foreground "$(_ui_c select)" --title.foreground "$(_ui_c info)" --title "󰔟  $title" -- "$@"
    else
        _gum_info "󰔟  $title..."
        "$@"
    fi
}

_gum_table() {
    local -a cols=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --columns) IFS=',' read -rA cols <<< "$2"; shift 2 ;;
            --widths|--height|--file|--separator|--border.foreground|--header.foreground|--cell.foreground|--selected.foreground) shift 2 ;;
            --print|--border|--border.*|--header.*|--cell.*|--selected.*) shift ;;
            *) shift ;;
        esac
    done
    local data
    data="$(command cat)"
    [[ -n "$data" ]] || { _gum_warn "No data to display"; return 0; }

    local tsv=""
    if (( ${#cols[@]} )); then
        local h; local IFS=$'\t'; h="${cols[*]}"; IFS=$' \t\n'
        tsv="${h}"$'\n'"${data}"
    else
        tsv="$data"
    fi

    local border_c header_c cell_c alt_c tw
    border_c="$(_ui_hex_to_ansi "$(_ui_c border)")"
    header_c="$(_ui_hex_to_ansi "$(_ui_c header)" 1)"
    cell_c="$(_ui_hex_to_ansi "$(_ui_c fg "#cdd6f4")")"
    alt_c="$(_ui_hex_to_ansi "$(_ui_c alt)")"
    tw="${COLUMNS:-$(command tput cols 2>/dev/null || echo 120)}"
    print -r -- "$tsv" | command awk -F'\t' -v hdr="${#cols[@]}" -v tw="$tw" -v border="$border_c" -v header="$header_c" -v cellc="$cell_c" -v alt="$alt_c" '
    function vislen(s){ gsub(/\033\[[0-9;]*[A-Za-z]/,"",s); return length(s) }
    function rep(ch,n, i,out){ out=""; for(i=0;i<n;i++) out=out ch; return out }
    function wrap(s,w, arr,    i,c,cur,outn,lastbreak,pref,ch) {
      gsub(/\033\[[0-9;]*[A-Za-z]/,"",s)
      if(w<8) w=8
      if(length(s)<=w){ arr[1]=s; return 1 }
      cur=""; outn=0
      for(i=1;i<=length(s);i++){
        c=substr(s,i,1)
        cur=cur c
        if(length(cur)>=w){
          lastbreak=0
          for(pref=w;pref>=1;pref--){
            ch=substr(cur,pref,1)
            if(ch==" "||ch=="/"||ch==":"||ch=="."||ch=="-"||ch=="_"||ch=="@"){ lastbreak=pref; break }
          }
          if(lastbreak>1){
            arr[++outn]=substr(cur,1,lastbreak)
            cur=substr(cur,lastbreak+1)
            sub(/^ +/,"",cur)
          } else {
            arr[++outn]=substr(cur,1,w)
            cur=substr(cur,w+1)
          }
        }
      }
      if(cur!=""){ sub(/^ +/,"",cur); if(cur!="") arr[++outn]=cur }
      if(outn<1){ arr[1]=s; outn=1 }
      return outn
    }
    function splitline(line,nf,a, n2,b,i,rest,j){
      nf=split(line,a,"\t")
      if(hdr>0 && nf<hdr){ n2=split(line,b,/  +/); if(n2>nf){ nf=n2; for(i=1;i<=nf;i++) a[i]=b[i] } }
      if(hdr==2 && nf<2){
        rest=line; gsub(/^ +| +$/,"",rest)
        if(match(rest,/  +/)){ a[1]=substr(rest,1,RSTART-1); a[2]=substr(rest,RSTART+RLENGTH); nf=2 }
        else {
          n2=split(rest,b,/ +/)
          if(n2>=3){ a[1]=b[1]" "b[2]; a[2]=b[3]; for(i=4;i<=n2;i++) a[2]=a[2]" "b[i]; nf=2 }
          else if(n2==2){ a[1]=b[1]; a[2]=b[2]; nf=2 }
        }
      }
      if(hdr>2 && nf<hdr){
        rest=line; gsub(/^ +| +$/,"",rest)
        nf=0; delete b
        n2=split(rest,b,/ +/)
        if(n2>=hdr){
          if(hdr==6){
            a[1]=b[1]; for(i=2;i<=n2-5;i++) a[1]=a[1]" "b[i]
            a[2]=b[n2-4]; a[3]=b[n2-3]; a[4]=b[n2-2]; a[5]=b[n2-1]; a[6]=b[n2]
            nf=6
          } else {
            for(i=1;i<hdr;i++) a[i]=b[i]
            a[hdr]=b[hdr]; for(i=hdr+1;i<=n2;i++) a[hdr]=a[hdr]" "b[i]
            nf=hdr
          }
        }
      }
      return nf
    }
    BEGIN{ nrows=0; ncols=0; if(tw<40) tw=120 }
    {
      nrows++; raw[nrows]=$0
      nf=splitline($0,0,a)
      if(nf>ncols)ncols=nf
      for(i=1;i<=nf;i++){ v=a[i]; gsub(/^ +| +$/,"",v); cell[nrows,i]=v; l=vislen(v); if(l>w[i])w[i]=l }
    }
    END{
      if(nrows==0) exit
      if(hdr>0) ncols=hdr
      for(r=1;r<=nrows;r++){
        nf=splitline(raw[r],0,a)
        if(hdr>0 && r>1 && nf<2) nf=split(raw[r],a,/  +/)
        if(hdr>0 && nf>hdr){ for(i=hdr+1;i<=nf;i++) a[hdr]=a[hdr]" "a[i]; nf=hdr }
        for(i=1;i<=ncols;i++){ v=(i<=nf?a[i]:""); gsub(/^ +| +$/,"",v); cell[r,i]=v; l=vislen(v); if(l>w[i])w[i]=l }
      }
      overhead=3*ncols+1; avail=tw-overhead; if(avail<ncols*6) avail=ncols*6
      for(i=1;i<=ncols;i++){ if(w[i]<3) w[i]=3 }
      sum=0; for(i=1;i<=ncols;i++) sum+=w[i]
      if(sum>avail){
        # identify preferred wrap column: last column, or widest non-numeric
        wi=ncols
        mx=0
        for(i=1;i<=ncols;i++){ if(num[i]==0 && w[i]>mx){ mx=w[i]; wi=i } }
        fixed=0; for(i=1;i<=ncols;i++) if(i!=wi) fixed+=w[i]
        w[wi]=avail-fixed
        if(w[wi]<10) w[wi]=10
        # if still too big, shrink other wide text cols gently
        sum=0; for(i=1;i<=ncols;i++) sum+=w[i]
        while(sum>avail){
          mx=0; mi=0
          for(i=1;i<=ncols;i++){ if(i==wi) continue; if(w[i]>mx){ mx=w[i]; mi=i } }
          if(mi==0 || mx<=6) { w[wi]=avail-(sum-w[wi]); if(w[wi]<8) w[wi]=8; break }
          w[mi]--; sum--
        }
      }
      R="\033[0m"; B=border; H=header; C=cellc; A=alt
      printf "%s╭",B; for(i=1;i<=ncols;i++){ printf "%s",rep("─",w[i]+2); if(i<ncols) printf "┬"; } printf "╮%s\n",R
      for(i=1;i<=ncols;i++) num[i]=1
      for(r=(hdr>0?2:1);r<=nrows;r++) for(i=1;i<=ncols;i++){ v=cell[r,i]; gsub(/\033\[[0-9;]*[A-Za-z]/,"",v); if(v!="" && v !~ /^[-+0-9.,:]+(%|[KMGTP]i?B?|B)?$/) num[i]=0 }
      for(r=1;r<=nrows;r++){
        maxl=1
        for(i=1;i<=ncols;i++){ nl=wrap(cell[r,i],w[i],arr); lc[r,i]=nl; for(k=1;k<=nl;k++) wc[r,i,k]=arr[k]; if(nl>maxl) maxl=nl }
        for(k=1;k<=maxl;k++){
          printf "%s│%s",B,R
          for(i=1;i<=ncols;i++){
            v=(k<=lc[r,i]?wc[r,i,k]:"")
            col=(r==1 && hdr>0)?H:((i==1)?A:C)
            if(r>1 && num[i] && hdr>0){ nsp=w[i]-vislen(v); if(nsp<0)nsp=0; printf " %s%s%s%s %s│%s",col,rep(" ",nsp),v,R,B,R }
            else { nsp=w[i]-vislen(v); if(nsp<0)nsp=0; printf " %s%s%s%s %s│%s",col,v,rep(" ",nsp),R,B,R }
          }
          printf "\n"
        }
        if(r==1 && hdr>0){ printf "%s├",B; for(i=1;i<=ncols;i++){ printf "%s",rep("─",w[i]+2); if(i<ncols) printf "┼"; } printf "┤%s\n",R }
      }
      printf "%s╰",B; for(i=1;i<=ncols;i++){ printf "%s",rep("─",w[i]+2); if(i<ncols) printf "┴"; } printf "╯%s\n",R
    }'
}


# ── Utility helpers ────────────────────────────────────────────────────────
_require_cmd() { command -v "$1" &>/dev/null || { _gum_error "Required command not found: $1"; return 1; }; }
_is_tty() { [[ -t 0 && -t 1 ]]; }
_path_exists() { [[ -e "$1" ]]; }
_safe_name() { local n="${1:-}"; n="${n//[^a-zA-Z0-9._-]/_}"; print -r -- "$n"; }
_human_bytes() {
    local b="${1:-0}" d=0 s=0
    local -a u=(B KiB MiB GiB TiB PiB)
    while (( b > 1024 && d < 5 )); do s=$(( b % 1024 * 10 / 1024 )); b=$(( b / 1024 )); ((d++)); done
    if (( d == 0 )); then print -r -- "${b} B"; else print -r -- "${b}.${s} ${u[$((d+1))]}"; fi
}
_confirm_danger() {
    local prompt="${1:-Dangerous action. Continue?}"
    _gum_warn "$prompt"
    _gum_confirm "$prompt"
}
