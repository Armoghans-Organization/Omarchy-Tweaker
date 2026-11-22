#! /usr/bin/env bash

set -Eeuo pipefail

SESSION="Omarchy-Tweaker"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LAYOUT="$SCRIPT_DIR/session.kdl"

error() {
    gum style --foreground 196 "✖ $1" >&2
    exit 1
}

# Dependencies
command -v gum >/dev/null 2>&1 || {
    echo "Error: gum is not installed." >&2
    exit 1
}

command -v zellij >/dev/null 2>&1 || error "Zellij is not installed."

# Prevent nested sessions
[[ -z "${ZELLIJ:-}" ]] || error "Already inside a Zellij session."

# Check layout
[[ -f "$LAYOUT" ]] || error "session.kdl not found."

# Detect existing session by exact name
SESSION_LIST=$(zellij list-sessions --no-formatting 2>&1) || {
    if [[ "$SESSION_LIST" == *"No active zellij sessions found."* ]]; then
        SESSION_LIST=""
    else
        error "Unable to retrieve Zellij sessions: $SESSION_LIST"
    fi
}

SESSION_INFO=$(
    printf '%s\n' "$SESSION_LIST" |
    awk -v name="$SESSION" '$1 == name { print; exit }'
)

# Remove existing session
if [[ -n "$SESSION_INFO" ]]; then
    if [[ "$SESSION_INFO" == *"EXITED"* ]]; then
        zellij delete-session "$SESSION" --force &>/dev/null ||
            error "Failed to delete exited session."
    else
        zellij kill-session "$SESSION" &>/dev/null ||
            error "Failed to terminate existing session."
    fi
fi

# Create and enter fresh session
exec zellij --new-session-with-layout "$LAYOUT" --session "$SESSION"
