#!/usr/bin/env bash
set -euo pipefail

HOME_DIR="${HOME:?HOME is not set}"

OUTPUT="compose.agents.yaml"
ENV_FILE="${OMNIROUTE_ENV_FILE:-.env}"

OUTPUT_TMP="$(mktemp)"
MOUNTS_TMP="$(mktemp)"
ENVIRONMENT_TMP="$(mktemp)"
trap 'rm -f "$OUTPUT_TMP" "$MOUNTS_TMP" "$ENVIRONMENT_TMP"' EXIT

# Read a KEY=VALUE entry from the rendered .env without sourcing it.
env_value() {
  local key="$1"
  local file="$2"
  [[ -f "$file" ]] || return 0

  local line
  line="$(grep -E "^${key}=" "$file" | tail -n 1 || true)"
  [[ -n "$line" ]] || return 0
  printf '%s' "${line#*=}"
}

yaml_quote() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

add_mount() {
  local host_path="$1"
  local container_path="$2"
  local mode="${3:-ro}"
  [[ -e "$host_path" ]] || return 0
  printf '      - "%s:%s:%s"\n' "$host_path" "$container_path" "$mode" >> "$MOUNTS_TMP"
}

add_env() {
  printf '      %s: "%s"\n' "$1" "$(yaml_quote "$2")" >> "$ENVIRONMENT_TMP"
}

node_bin="$(env_value HOST_NODE_BIN "$ENV_FILE")"

# Convert a host path to the path it has inside the container.
container_path() {
  local host_path="$1"
  if [[ -n "$node_bin" && "$host_path" == "$node_bin/"* ]]; then
    printf '/host-node/bin/%s' "${host_path#"$node_bin/"}"
  elif [[ "$host_path" == "$HOME_DIR/.local/bin/"* ]]; then
    printf '/host-local/bin/%s' "${host_path##*/}"
  else
    printf '%s' "$host_path"
  fi
}

is_mise_shim() {
  local file="$1"
  [[ -r "$file" ]] || return 1
  head -n 5 "$file" 2>/dev/null | grep -q 'mise'
}

# Follow symlinks so npm-installed tools that link into ../lib keep working when
# only their own directory is mounted.
real_path() {
  readlink -f "$1" 2>/dev/null || printf '%s\n' "$1"
}

# Resolve a real executable, preferring the tool's mise installation so the
# container never executes a host-only mise shim.
resolve_binary() {
  local binary="$1"
  local path

  if command -v mise >/dev/null 2>&1; then
    path="$(mise which "$binary" 2>/dev/null || true)"
    if [[ -n "$path" && -x "$path" ]]; then
      printf '%s\n' "$(real_path "$path")"
      return 0
    fi
  fi

  path="$(command -v "$binary" 2>/dev/null || true)"
  if [[ -n "$path" && -x "$path" ]] && ! is_mise_shim "$path"; then
    printf '%s\n' "$(real_path "$path")"
    return 0
  fi

  local candidate
  for candidate in "$HOME_DIR/.local/bin/$binary" "${node_bin:+$node_bin/$binary}"; do
    [[ -n "$candidate" && -x "$candidate" ]] || continue
    is_mise_shim "$candidate" && continue
    printf '%s\n' "$(real_path "$candidate")"
    return 0
  done

  return 1
}

tool_binaries() {
  case "$1" in
    cursor) printf 'agent\ncursor\n' ;;
    continue) printf 'cn\n' ;;
    kilo) printf 'kilocode\n' ;;
    *) printf '%s\n' "$1" ;;
  esac
}

declare -A TOOL_ENV=(
  [claude]=CLI_CLAUDE_BIN
  [codex]=CLI_CODEX_BIN
  [gemini]=CLI_GEMINI_BIN
  [opencode]=CLI_OPENCODE_BIN
  [pi]=CLI_PI_BIN
  [hermes]=CLI_HERMES_BIN
  [omp]=CLI_OMP_BIN
  [grok]=CLI_GROK_BUILD_BIN
  [amp]=CLI_AMP_BIN
  [cursor]=CLI_CURSOR_BIN
  [droid]=CLI_DROID_BIN
  [openclaw]=CLI_OPENCLAW_BIN
  [cline]=CLI_CLINE_BIN
  [continue]=CLI_CONTINUE_BIN
  [kilo]=CLI_KILO_BIN
  [qwen]=CLI_QWEN_BIN
  [aider]=CLI_AIDER_BIN
  [goose]=CLI_GOOSE_BIN
  [crush]=CLI_CRUSH_BIN
  [devin]=CLI_DEVIN_BIN
  [qoder]=CLI_QODER_BIN
)

declare -A SEEN_PATHS=()
EXTRA_PATHS=("/host-node/bin")

add_extra_path() {
  local path="$1"
  [[ -n "$path" ]] || return 0
  [[ -n "${SEEN_PATHS[$path]:-}" ]] && return 0
  SEEN_PATHS["$path"]=1
  EXTRA_PATHS+=("$path")
}

hermes_found=0

for tool in "${!TOOL_ENV[@]}"; do
  resolved=""
  while IFS= read -r binary; do
    [[ -n "$binary" ]] || continue
    if resolved="$(resolve_binary "$binary")"; then
      break
    fi
    resolved=""
  done < <(tool_binaries "$tool")

  [[ -n "$resolved" ]] || continue

  in_container="$(container_path "$resolved")"
  add_env "${TOOL_ENV[$tool]}" "$in_container"
  add_extra_path "$(dirname "$in_container")"
  printf 'Found: %s -> %s\n' "$tool" "$in_container"

  if [[ "$tool" == "hermes" ]]; then
    hermes_found=1
  fi
done

# The tool directories come before /host-local/bin so mise shims in ~/.local/bin
# cannot shadow the real binaries.
add_extra_path "/host-local/bin"
extra_paths="$(IFS=:; printf '%s' "${EXTRA_PATHS[*]}")"
add_env "CLI_EXTRA_PATHS" "$extra_paths"
add_env "PATH" "$extra_paths:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

if [[ -d "$HOME_DIR/.pi/agent" ]]; then
  add_env "PI_CODING_AGENT_DIR" "/home/node/.pi/agent"
fi

if [[ -d "$HOME_DIR/.hermes" ]]; then
  add_env "HERMES_HOME" "/home/node/.hermes"
fi

# OpenCode resolves its config from $HOME/.config/opencode and ignores
# CLI_CONFIG_HOME, so mount that directory where the container expects it.
add_mount "$HOME_DIR/.config/opencode" "/home/node/.config/opencode" "rw"

if [[ -n "$node_bin" ]]; then
  add_mount "$node_bin" "/host-node/bin" "ro"
fi

add_mount "$HOME_DIR/.local/bin" "/host-local/bin" "ro"
add_mount "$HOME_DIR/.local/share/mise/installs" "$HOME_DIR/.local/share/mise/installs" "ro"

if [[ "$hermes_found" == "1" ]]; then
  add_mount "$HOME_DIR/.local/share/uv/python" "$HOME_DIR/.local/share/uv/python" "ro"
fi

# Known agent configuration directories.
declare -A AGENTS=(
  [".claude"]="/home/node/.claude"
  [".codex"]="/home/node/.codex"
  [".factory"]="/home/node/.factory"
  [".openclaw"]="/home/node/.openclaw"
  [".pi"]="/home/node/.pi"
  [".omp"]="/home/node/.omp"
  [".grok"]="/home/node/.grok"
  [".hermes"]="/home/node/.hermes"
  [".gemini"]="/home/node/.gemini"
  [".qwen"]="/home/node/.qwen"
  [".config/goose"]="/home/node/.config/goose"
  [".continue"]="/home/node/.continue"
  [".aider"]="/home/node/.aider"
  [".roo"]="/home/node/.roo"
  [".cursor"]="/home/node/.cursor"
  [".config/cursor"]="/home/node/.config/cursor"
  [".config/Cursor"]="/home/node/.config/Cursor"
  [".cline"]="/home/node/.cline"
  [".kilocode"]="/home/node/.kilocode"
  [".config/crush"]="/home/node/.config/crush"
  [".config/zed"]="/home/node/.config/zed"
  [".config/github-copilot"]="/home/node/.config/github-copilot"
  [".copilot"]="/home/node/.copilot"
  [".local/share/kilo"]="/home/node/.local/share/kilo"
)

for source in "${!AGENTS[@]}"; do
  host_path="$HOME_DIR/$source"
  container_path="${AGENTS[$source]}"

  if [[ -d "$host_path" ]]; then
    add_mount "$host_path" "$container_path" "rw"
    echo "Found: $host_path"
  fi
done

{
  echo "services:"
  echo "  omniroute:"
  if [[ -s "$ENVIRONMENT_TMP" ]]; then
    echo "    environment:"
    cat "$ENVIRONMENT_TMP"
  fi
  if [[ -s "$MOUNTS_TMP" ]]; then
    echo "    volumes:"
    cat "$MOUNTS_TMP"
  else
    echo "    volumes: []"
  fi
} > "$OUTPUT_TMP"

mv "$OUTPUT_TMP" "$OUTPUT"

echo
echo "Generated $OUTPUT"
