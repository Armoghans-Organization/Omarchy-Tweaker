# ╭──────────────────────────────────────────────────────────────────────────╮
# │                               MISC HELPERS                               │
# ╰──────────────────────────────────────────────────────────────────────────╯

_zshrc() {
    local cfg="${ZSH_CONFIG_DIR:-$HOME/.config/zsh}"
    local file
    file="$(command find "$cfg" -type f \( -name '*.zsh' -o -name 'zshrc' -o -name '.zshrc' \) 2>/dev/null | sort | _gum_filter '󰒓  Edit Zsh config')" || return 1
    [[ -n "$file" ]] || return 1
    "${EDITOR:-nvim}" -- "$file"
    if _is_tty && _gum_confirm '󰑐  Reload zsh now?'; then exec "${SHELL:-zsh}" -i; fi
}

_reload() { _gum_info "󰑐  Reloading zsh..."; exec "${SHELL:-zsh}" -i; }

_mkproject() {
    local name="${1:-}"
    [[ -n "$name" ]] || name="$(_gum_input 'project-name' '' '󰉋  New project')" || return 1
    [[ -n "$name" ]] || return 1
    local dir="${PROJECTS_DIR:-$HOME/Projects}/$name"
    command mkdir -p -- "$dir" && builtin cd -- "$dir" || return 1
    _gum_ok "󰉋  Project: $dir"
}

_note() {
    emulate -L zsh

    local file="${NOTES_FILE:-$HOME/Documents/notes.md}"
    local action title body tags query selected line preview_cmd
    local stamp
    local -a matches

    (( $+commands[gum] )) || {
        print -u2 "󰅚  Error: gum is required."
        return 1
    }

    command mkdir -p -- "${file:h}" || return 1
    [[ -e "$file" ]] || : > "$file" || return 1

    # ── Dashboard ────────────────────────────────────────────────
    if [[ -n "${1:-}" ]]; then
        action="$1"
    else
        gum style \
            --border rounded \
            --border-foreground 6 \
            --padding "1 2" \
            --margin "0 0 1 0" \
            "$(gum style --bold --foreground 6 '󰠮  NOTES')"$'\n'\
            "$(gum style --foreground 7 "󰈙  ${file:t}  ·  $(wc -l < "$file" | tr -d ' ') lines")"$'\n'\
            "$(gum style --foreground 8 "${file:h}")"

        action=$(gum choose \
            --cursor="➜ " \
            --cursor.foreground 6 \
            --selected.foreground 6 \
            --header="What would you like to do?" \
            "󰏫  New note" \
            "󰍉  Search notes" \
            "󰄉  Recent notes" \
            "󰈔  Open notes file") || return 0
    fi

    case "$action" in
        "󰏫  New note"|"New note"|new)
            title=$(gum input \
                --header="󰏫  New note" \
                --prompt="Title  " \
                --placeholder="What is this note about?") || return 0

            # Trim surrounding whitespace.
            title="${title##[[:space:]]#}"
            title="${title%%[[:space:]]#}"

            [[ -n "$title" ]] || {
                gum style --foreground 1 "󰅚  A title is required."
                return 1
            }

            body=$(gum write \
                --width 80 \
                --char-limit 0 \
                --placeholder="Write something worth remembering..." \
                --header="󰓝  $title · Ctrl+D saves · Esc cancels") ||
                return 0

            [[ -n "${body//[[:space:]]/}" ]] || {
                gum style --foreground 3 "󰋔  Empty note discarded."
                return 0
            }

            tags=$(gum input \
                --header="󰓹  Add tags (optional)" \
                --prompt="Tags  " \
                --placeholder="work, ideas, personal") || tags=""

            stamp=$(date '+%Y-%m-%d %H:%M')

            {
                print -r -- "## $title"
                print -r -- "<!-- $stamp -->"
                [[ -z "$tags" ]] || print -r -- "**Tags:** $tags"
                print
                print -r -- "$body"
                print
                print
            } >> "$file" || {
                gum style --foreground 1 "󰅚  Failed to save note."
                return 1
            }

            gum style \
                --border rounded \
                --border-foreground 2 \
                --padding "1 2" \
                "$(gum style --bold --foreground 2 '󰄬  Note saved successfully')"$'\n'\
                "$(gum style --foreground 7 "$title")"$'\n'\
                "$(gum style --foreground 8 "󰥔  $stamp")"
            ;;

        "󰍉  Search notes"|"Search notes"|search)
            (( $+commands[rg] )) || {
                gum style --foreground 1 "󰅚  Install ripgrep (rg) to search notes."
                return 1
            }

            query=$(gum input \
                --header="󰍉  Search your notes" \
                --prompt="Search  " \
                --placeholder="Type keywords to find...") || return 0

            [[ -n "$query" ]] || return 0

            if (( $+commands[bat] )); then
                preview_cmd="bat --color=always --style=numbers --language=markdown --highlight-line {1} ${(q)file}"
            else
                preview_cmd="awk 'NR >= {1}-8 && NR <= {1}+12 {printf \"%5d  %s\\n\", NR, \$0}' ${(q)file}"
            fi

            selected=$(
                command rg -n -i -F -- "$query" "$file" |
                    fzf \
                        --delimiter=: \
                        --with-nth=2.. \
                        --prompt='󰍉  Search > ' \
                        --header='↑↓ Navigate · Enter View · Esc Back' \
                        --height=85% \
                        --layout=reverse \
                        --border=rounded \
                        --preview="$preview_cmd" \
                        --preview-window='right,60%,border-left' \
                        --preview-label=' 󰈙  Note Preview '
            ) || return 0

            line="${selected%%:*}"

            if [[ "$line" == <-> ]]; then
                if (( $+commands[bat] )); then
                    bat --paging=always --style=numbers \
                        --language=markdown \
                        --highlight-line "$line" "$file"
                else
                    sed -n "$(( line > 5 ? line - 5 : 1 )),$(( line + 12 ))p" "$file" |
                        gum pager
                fi
            fi
            ;;

        "󰄉  Recent notes"|"Recent notes"|recent)
            local recent

            if (( $+commands[rg] )); then
                recent=$(rg -n '^## ' "$file" | tail -20)
            else
                recent=$(grep -n '^## ' "$file" | tail -20)
            fi

            if [[ -z "$recent" ]]; then
                gum style --foreground 3 "󰋔  No notes found yet."
                return 0
            fi

            gum style \
                --border rounded \
                --border-foreground 6 \
                --padding "0 2" \
                --bold "󰄉  Recent Notes"

            print -r -- "$recent" |
                gum pager --show-line-numbers
            ;;

        "󰈔  Open notes file"|"Open notes file"|open)
            _notes
            ;;

        *)
            gum style --foreground 1 "󰅚  Unknown action: $action"
            return 1
            ;;
    esac
}

# Open the notes file in $EDITOR
_notes() {
    emulate -L zsh

    local file="${NOTES_FILE:-$HOME/Documents/notes.md}"
    local editor="${VISUAL:-${EDITOR:-nvim}}"
    local -a editor_cmd

    command mkdir -p -- "${file:h}" || return 1

    if [[ ! -f "$file" ]]; then
        : > "$file" || return 1
        gum style --foreground 2 "󰄬  Created ${file:t}"
    fi

    # Allow EDITOR values containing arguments, e.g. "code --wait".
    editor_cmd=("${(@z)editor}")

    (( ${#editor_cmd} )) || editor_cmd=(vi)

    if (( $+commands[gum] )); then
        gum style \
            --border rounded \
            --border-foreground 6 \
            --padding "1 2" \
            "$(gum style --bold --foreground 6 '󰈔  NOTES EDITOR')"$'\n'\
            "$(gum style --foreground 7 "󰈙  ${file:t}")"$'\n'\
            "$(gum style --foreground 8 "󰉋  ${file:h} · $(wc -l < "$file" | tr -d ' ') lines")"
    fi

    "${editor_cmd[@]}" "$file"
}

_envgrep() {
    local q="${1:-}"
    [[ -n "$q" ]] || { _gum_info "Usage: envgrep <pattern>"; return 1; }
    _gum_title "󰌪  Environment Variables" "match: $q"
    local rows
    rows="$(printenv | command grep -i -- "$q" | sort | awk -F= '{
      v=substr($0,length($1)+2); if(length(v)>100) v=substr(v,1,97)"...";
      printf "%s\t%s\n",$1,v
    }')"
    [[ -n "$rows" ]] || { _gum_warn "No env vars matching: $q"; return 1; }
    print -r -- "$rows" | _gum_table --columns "󰌪 VAR,󰋽 VALUE"
}

_psgrep() {
    local q="${1:-}"
    [[ -n "$q" ]] || { _gum_info "Usage: psgrep <pattern>"; return 1; }
    _gum_title "󰍹  Processes" "match: $q"
    local rows
    rows="$(command ps aux | command awk -v q="$q" 'NR==1{next} tolower($0)~tolower(q){
      cmd=""; for(i=11;i<=NF;i++) cmd=cmd $i " ";
      gsub(/"/,"\047",cmd); gsub(/\t/," ",cmd);
      if(length(cmd)>70) cmd=substr(cmd,1,67)"...";
      printf "%s\t%s\t%s\t%s\t%s\n",$1,$2,$3,$4,cmd
    }')"
    [[ -n "$rows" ]] || { _gum_warn "No processes matching: $q"; return 1; }
    print -r -- "$rows" | _gum_table --columns "󰀉 USER,󰐣 PID,󰓅 CPU%,󰍛 MEM%,󰆍 COMMAND"
}
