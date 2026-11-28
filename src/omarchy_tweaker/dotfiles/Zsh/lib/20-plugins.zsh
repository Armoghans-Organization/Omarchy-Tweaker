# ╭──────────────────────────────────────────────────────────────────────────╮
# │                              ZSH Plugins                                 │
# │                                                                          │
# │  Purpose: This file installs Plug and ZSH plugins. It is loaded by       │
# │           the main ZSH configuration file.                               │
# ╰──────────────────────────────────────────────────────────────────────────╯


# ───────────────────────────────────────────────────────────────────────────
# 1. Install Plug Plugin Manager
# ───────────────────────────────────────────────────────────────────────────

PLUG_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}/plug/plug.git"
if [[ ! -d "$PLUG_HOME" ]]; then
    gum style --foreground 212 --border normal --padding "1 2" --margin "1 0" "Installing plug.zsh plugin manager..."
    if ! git clone --depth=1 https://github.com/Armoghan-ul-Mohmin/plug.git "$PLUG_HOME" > /dev/null 2>&1; then
        gum style --foreground 196 --border normal --padding "1 2" --margin "1 0" "Failed to install plug.zsh plugin manager. Please check your internet connection and try again."
        return 1
    fi
fi
source "$PLUG_HOME/plug.zsh"

# ───────────────────────────────────────────────────────────────────────────
# 2. Install ZSH Plugins
# ───────────────────────────────────────────────────────────────────────────

plug install zsh-users/zsh-autosuggestions
plug install Aloxaf/fzf-tab
plug install zdharma-continuum/fast-syntax-highlighting
plug install MichaelAquilina/zsh-you-should-use

# ───────────────────────────────────────────────────────────────────────────
# 3. Install OMZ ZSH Plugins
# ───────────────────────────────────────────────────────────────────────────

plug omz command-not-found
plug omz copyfile

# ───────────────────────────────────────────────────────────────────────────
# 4. Tools Initialization
# ───────────────────────────────────────────────────────────────────────────

plug eval add starship starship init zsh
plug eval add fzf fzf --zsh
plug eval add zoxide zoxide init zsh
plug eval add atuin atuin init zsh

# ──────────────────────────────────────────────────────────────────────────
# 5. Tools Completions
# ──────────────────────────────────────────────────────────────────────────

plug completion gen atuin atuin gen-completions -s zsh
plug completion gen zellij zellij setup --generate-completion zsh
plug completion gen gh gh completion -s zsh
plug completion gen mise mise completion zsh
plug completion gen uv uv generate-shell-completion zsh

# ──────────────────────────────────────────────────────────────────────────
# 6. Plugins Settings
# ──────────────────────────────────────────────────────────────────────────

export YSU_MESSAGE_POSITION="before"
if [[ -t 2 ]] && (( $+commands[tput] )); then
    YSU_MESSAGE_FORMAT="
$(tput bold)$(tput setaf 3)
Found existing %alias_type for \
$(tput setaf 5)\"%command\"$(tput setaf 3)
You should use: \
$(tput setaf 2)\"%alias\"$(tput sgr0)
"
fi
