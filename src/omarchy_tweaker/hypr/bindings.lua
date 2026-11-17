-- ============================================================================
-- OMARCHY PERSONAL KEYBINDING OVERRIDES
-- ============================================================================
--
-- DESCRIPTION:
-- Personal Hyprland keybinding customizations loaded after Omarchy's defaults.
--
-- LOAD ORDER:
-- This file is loaded AFTER Omarchy's default bindings. Any conflicting
-- bindings defined here take precedence over the defaults.
--
-- CONFIGURATION GUIDELINES:
--   * Rebinding an existing key? Call hl.unbind() FIRST, then o.bind().
--   * Removing a default you never use? hl.unbind() alone is enough.
--   * Keep related bindings grouped under their respective categories.
--
-- INSPECTING KEYBINDINGS:
--   omarchy menu keybindings --print
--
-- GLOBAL OMARCHY CONFIGURATION:
--
-- Disable every Omarchy default binding:
--   Set this in ~/.config/hypr/hyprland.lua before requiring
--   default.hypr.omarchy:
--   omarchy_default_bindings = false
--
-- Disable all preinstalled application and webapp bindings:
--   omarchy_preinstalled_bindings = false
--
-- BINDING API:
--   o.bind(keys, description, command)
--       Registers a keybinding.
--
--   hl.unbind(keys)
--       Removes an existing default keybinding.
--
--   hl.bind(keys, dispatcher, options)
--       Registers a lower-level keybinding with additional options.
--
-- REASSIGNMENT NOTATION:
--   Original Action -> New Action
--   Original Action -> Unassigned
--
-- EXAMPLE:
--   hl.unbind("SUPER + SPACE")
--   o.bind("SUPER + SPACE", "Omarchy menu", "omarchy-menu toggle root")
--
-- LOGITECH MX KEYS EXAMPLES:
--   o.bind("SUPER + SHIFT + S", nil, "omarchy-capture-screenshot")
--   o.bind("SUPER + H", nil, "voxtype record toggle")
--   o.bind("SUPER + PERIOD", nil, "omarchy-shell shell toggle omarchy.emojis")
--
-- ============================================================================


-- ============================================================================
-- 01. HELPER FUNCTIONS AND UTILITIES
-- ============================================================================
--
-- Reusable functions shared by multiple keybindings.
-- Keeping common functionality here avoids duplicating implementation logic.
--
-- 01.1. Send keyboard shortcut once
-- 01.2. Detect active terminal window
-- 01.3. Universal keyboard shortcut dispatcher
-- ============================================================================


-- --------------------------------------------------------------------------
-- 01.1. SEND KEYBOARD SHORTCUT ONCE
-- --------------------------------------------------------------------------
--
-- Simulates a complete keyboard press using two separate events:
--
--   1. KEY DOWN: Simulates pressing the requested key combination.
--   2. KEY UP:   Simulates releasing the requested key combination.
--
-- A 50ms one-shot timer separates the events to ensure the receiving
-- application can register the complete keyboard interaction.
--
-- ARGUMENTS:
--   mods - Modifier combination, e.g. "CTRL" or "SHIFT".
--   key  - Keyboard key, e.g. "V" or "Insert".
--
-- RETURNS:
--   A callback that sends the requested keyboard shortcut.
-- --------------------------------------------------------------------------

local function send_shortcut_once(mods, key)
    return function()
        hl.dispatch(hl.dsp.send_key_state({ mods = mods, key = key, state = "down" }))

        hl.timer(function()
            hl.dispatch(hl.dsp.send_key_state({ mods = mods, key = key, state = "up" }))
        end, { timeout = 50, type = "oneshot" })
    end
end


-- --------------------------------------------------------------------------
-- 01.2. DETECT ACTIVE TERMINAL WINDOW
-- --------------------------------------------------------------------------
--
-- Determines whether the currently focused window belongs to a terminal.
--
-- Instead of maintaining a separate list of terminal applications, this
-- function uses the "terminal" tag defined in:
--
--   default/hypr/apps/terminals.lua
--
-- Dynamic window tags can contain a trailing "*" character. This is removed
-- before comparing the tag against "terminal".
--
-- RETURNS:
--   true  - Active window is a terminal.
--   false - No active window or active window is not a terminal.
-- --------------------------------------------------------------------------

local function active_window_is_terminal()
    local window = hl.get_active_window()
    if not window then
        return false
    end

    for _, tag in ipairs(window.tags or {}) do
        if tag:gsub("%*$", "") == "terminal" then
            return true
        end
    end

    return false
end


-- --------------------------------------------------------------------------
-- 01.3. UNIVERSAL KEYBOARD SHORTCUT DISPATCHER
-- --------------------------------------------------------------------------
--
-- Creates a keyboard shortcut that behaves differently depending on the
-- currently focused application.
--
-- TERMINALS:
--   Uses the terminal-specific keyboard shortcut.
--
-- OTHER APPLICATIONS:
--   Uses the standard keyboard shortcut.
--
-- ARGUMENTS:
--   default_mods   - Modifier for ordinary applications.
--   default_key    - Key for ordinary applications.
--   terminal_mods  - Modifier for terminal applications.
--   terminal_key   - Key for terminal applications.
--
-- RETURNS:
--   A callback that detects the active window and sends the appropriate
--   keyboard shortcut.
-- --------------------------------------------------------------------------

local function universal_clipboard_shortcut(default_mods, default_key, terminal_mods, terminal_key)
    return function()
        if active_window_is_terminal() then
            send_shortcut_once(terminal_mods, terminal_key)()
        else
            send_shortcut_once(default_mods, default_key)()
        end
    end
end

-- ============================================================================
-- 02. UNBINDING PREINSTALLED DEFAULTS
-- ============================================================================
--
-- Removes selected stock Omarchy keybindings.
--
-- The freed key combinations are reused for personal applications, webapps,
-- window management, and other custom functionality.
--
-- REASSIGNMENT NOTATION:
--
--   Original Action -> New Action
--       The original shortcut is being reassigned to another function.
--
--   Original Action -> Unassigned
--       The original shortcut is being removed and is not reassigned here.
--
-- NOTE:
--   These calls only remove keybindings. They do not uninstall applications
--   or remove any associated packages.
--
-- CATEGORIES:
--   02.1. Webapps and online services
--   02.2. Applications and productivity
--   02.3. System and window management
--   02.4. Clipboard, emoji, and input
--   02.5. Launchers, menus, and plugins
--   02.6. System bar and hardware controls
--   02.7. Entertainment and media
-- ============================================================================


-- --------------------------------------------------------------------------
-- 02.1. WEBAPPS AND ONLINE SERVICES
-- --------------------------------------------------------------------------
--
-- Releases default shortcuts assigned to Omarchy's preinstalled webapps.
-- Several of these combinations are reused for alternative online services.
-- --------------------------------------------------------------------------

hl.unbind("SUPER + SHIFT + M")              -- Music -> YouTube Music
hl.unbind("SUPER + SHIFT + CTRL + G")       -- Google Messages -> Unassigned
hl.unbind("SUPER + SHIFT + P")              -- Google Photos -> Unassigned
hl.unbind("SUPER + SHIFT + S")              -- Google Maps -> Unassigned
hl.unbind("SUPER + SHIFT + SLASH")          -- Password -> Unassigned
hl.unbind("SUPER + SHIFT + G")              -- Signal -> Unassigned
hl.unbind("SUPER + SHIFT + ALT + E")        -- New Email -> Thunderbird
hl.unbind("SUPER + SHIFT + X")              -- X (Twitter) -> Unassigned
hl.unbind("SUPER + SHIFT + ALT + X")        -- X Post (Twitter) -> Unassigned
hl.unbind("SHIFT + ALT + D")                -- Download Video from Web App -> Unassigned
hl.unbind("SHIFT + ALT + L")                -- Copy URL from Web App -> Unassigned
hl.unbind("SUPER + SHIFT + ALT + G")        -- Whatsapp -> Unassigned


-- --------------------------------------------------------------------------
-- 02.2. APPLICATIONS AND PRODUCTIVITY
-- --------------------------------------------------------------------------
--
-- Releases default shortcuts assigned to applications and productivity tools.
-- --------------------------------------------------------------------------

hl.unbind("SUPER + SHIFT + ALT + M")        -- Music TUI -> Unassigned
hl.unbind("SUPER + SHIFT + O")              -- Obsidian -> Notion
hl.unbind("SUPER + SHIFT + E")              -- Email -> File Manager (Admin)
hl.unbind("SUPER + SHIFT + RETURN")         -- Browser -> Zen Browser
hl.unbind("SUPER + SHIFT + ALT + B")        -- Browser (Private) -> Brave Browser
hl.unbind("SUPER + SHIFT + B")              -- Browser -> Chromium Browser
hl.unbind("SUPER + SHIFT + F")              -- File Manager -> Unassigned
hl.unbind("SUPER + SHIFT + ALT + F")        -- File Manager (CWD) -> Superfile
hl.unbind("SUPER + ALT + SHIFT + F")        -- File Manager (CWD) -> Superfile
hl.unbind("SUPER + SHIFT + C")              -- Calendar -> Claude
hl.unbind("SUPER + SHIFT + N")              -- Editor -> Unassigned
hl.unbind("SUPER + SHIFT + W")              -- Omawrite -> Unassigned


-- --------------------------------------------------------------------------
-- 02.3. SYSTEM AND WINDOW MANAGEMENT
-- --------------------------------------------------------------------------
--
-- Releases default shortcuts assigned to window operations, workspace
-- layouts, screen locking, and window appearance.
-- --------------------------------------------------------------------------

hl.unbind("SUPER + F")                      -- Full screen -> Full Width
hl.unbind("SUPER + ALT + F")                -- Full Width -> Full screen
hl.unbind("SUPER + Q")                      -- Close Window -> Unassigned
hl.unbind("CTRL + ALT + DELETE")            -- Close all windows -> Unassigned
hl.unbind("SUPER + CTRL + L")               -- Lock Screen -> Toggle workspace layout
hl.unbind("SUPER + L")                      -- Cycle workspace layout -> Lock Screen
hl.unbind("SUPER + ALT + L")                -- Cycle workspace layout back -> Unassigned
hl.unbind("SUPER + ALT + BRACKETLEFT")      -- Make webcam overlay smaller -> Unassigned
hl.unbind("SUPER + ALT + BRACKETRIGHT")     -- Make webcam overlay larger -> Unassigned
hl.unbind("SUPER + A")                      -- Select all -> Unassigned


-- --------------------------------------------------------------------------
-- 02.4. CLIPBOARD, EMOJI, AND INPUT
-- --------------------------------------------------------------------------
--
-- Releases default shortcuts assigned to clipboard operations, emoji
-- selection, notification dismissal, and input language switching.
-- --------------------------------------------------------------------------

hl.unbind("SUPER + V")                      -- Universal Paste -> Clipboard Manager
hl.unbind("SUPER + CTRL + V")               -- Clipboard Manager -> Universal Paste
hl.unbind("SUPER + CTRL + E")               -- Emojis -> SUPER + COMMA
hl.unbind("SUPER + COMMA")                  -- Dismiss -> Dismiss last notification
hl.unbind("SUPER + I")                      -- Switch input language -> Unassigned
hl.unbind("SUPER + SHIFT + I")              -- Switch input language back -> Unassigned


-- --------------------------------------------------------------------------
-- 02.5. LAUNCHERS, MENUS, AND PLUGINS
-- --------------------------------------------------------------------------
--
-- Releases shortcuts used by Omarchy's default launchers and menus.
-- These combinations are reused for Spotlight and App Grid.
-- --------------------------------------------------------------------------

hl.unbind("SUPER + CTRL + T")               -- Theme Menu -> Unassigned
hl.unbind("ALT + SPACE")                    -- Toggle dictation -> Spotlight
hl.unbind("SUPER + ALT + SPACE")            -- Apps -> App Grid


-- --------------------------------------------------------------------------
-- 02.6. SYSTEM BAR AND HARDWARE CONTROLS
-- --------------------------------------------------------------------------
--
-- Releases shortcuts associated with Omarchy's system bar and hardware
-- information panels.
-- --------------------------------------------------------------------------

hl.unbind("SUPER + CTRL + A")               -- Audio Panel (bar) -> Unassigned
hl.unbind("SUPER + CTRL + ALT + B")         -- Show Battery Remaining -> Unassigned
hl.unbind("SUPER + CTRL + ALT + D")         -- Calendar (bar) -> Unassigned
hl.unbind("SUPER + CTRL + ALT + T")         -- Show time (bar) -> Unassigned
hl.unbind("SUPER + CTRL + ALT + W")         -- Toggle weather (bar) -> Unassigned
hl.unbind("SUPER + CTRL + ALT + E")         -- World Clock -> Unassigned
hl.unbind("SUPER + CTRL + B")               -- Bluetooth (bar) -> Unassigned


-- --------------------------------------------------------------------------
-- 02.7. ENTERTAINMENT AND MEDIA
-- --------------------------------------------------------------------------
--
-- Releases the default activity-monitor shortcut.
-- --------------------------------------------------------------------------

hl.unbind("SUPER + SHIFT + T")              -- Activity (btop) -> Unassigned

-- ============================================================================
-- 03. LAUNCHERS AND OVERLAYS
-- ============================================================================
--
-- Custom launchers and overlays providing quick access to applications,
-- files, and desktop functionality.
--
-- 03.1. Spotlight
-- 03.2. App Grid
-- ============================================================================


-- --------------------------------------------------------------------------
-- 03.1. SPOTLIGHT
-- --------------------------------------------------------------------------
--
-- KEY:
--   ALT + SPACE
--
-- DESCRIPTION:
--   Quick application and file search.
--
-- COMPONENT:
--   io.github.maajix.spotlight
--
-- BEHAVIOUR:
--   Toggles the Spotlight shell component.
-- --------------------------------------------------------------------------

o.bind("ALT + SPACE", "Spotlight",
    "omarchy-shell shell toggle io.github.maajix.spotlight '{}'")


-- --------------------------------------------------------------------------
-- 03.2. APP GRID
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + ALT + SPACE
--
-- DESCRIPTION:
--   Full-screen application launcher.
--
-- COMPONENT:
--   matthewjaybarr.app-grid
--
-- BEHAVIOUR:
--   Toggles the App Grid shell component.
-- --------------------------------------------------------------------------

o.bind("SUPER + ALT + SPACE", "App grid",
    "omarchy-shell shell toggle matthewjaybarr.app-grid '{}'")

-- ============================================================================
-- 04. KEYBINDINGS HINT AND LEARNING SYSTEM
-- ============================================================================
--
-- Integration with the Nejcc Keybindings Hint plugin.
--
-- Provides an on-screen reference for keyboard shortcuts.
--
-- 04.1. Open keybindings popup
-- 04.2. Close keybindings popup
-- 04.3. Toggle keybindings hint
-- 04.4. Toggle learning mode
-- ============================================================================


-- --------------------------------------------------------------------------
-- 04.1. OPEN KEYBINDINGS POPUP
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER_L
--
-- BEHAVIOUR:
--   Summons the keybinding hint overlay when the left SUPER key is held.
--
-- OPTIONS:
--   long_press = true  : Trigger after a long press.
--   ignore_mods = true : Ignore modifier-state restrictions.
--
-- NOTE:
--   Uses hl.bind() because o.bind() does not expose these options.
-- --------------------------------------------------------------------------

hl.bind("SUPER_L", hl.dsp.exec_cmd("omarchy-shell shell summon nejcc.keybindings-hint"),
    { long_press = true, ignore_mods = true })


-- --------------------------------------------------------------------------
-- 04.2. CLOSE KEYBINDINGS POPUP
-- --------------------------------------------------------------------------
--
-- KEY:
--   HOME
--
-- BEHAVIOUR:
--   Hides the keybinding hint overlay.
-- --------------------------------------------------------------------------

o.bind("HOME", "Close Keybindings Hints", "omarchy-shell shell hide nejcc.keybindings-hint")


-- --------------------------------------------------------------------------
-- 04.3. TOGGLE KEYBINDINGS HINT
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + SHIFT + K
--
-- BEHAVIOUR:
--   Toggles the visibility of the keybinding hint overlay.
-- --------------------------------------------------------------------------

o.bind("SUPER + SHIFT + K", "Toggle keybindings hint",
    "omarchy-shell shell summon nejcc.keybindings-hint '{\"enabled\":\"toggle\"}'")


-- --------------------------------------------------------------------------
-- 04.4. TOGGLE LEARNING MODE
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + CTRL + SHIFT + K
--
-- BEHAVIOUR:
--   Toggles learning mode, displaying every binding instead of only
--   contextual keybinding hints.
-- --------------------------------------------------------------------------

o.bind("SUPER + CTRL + SHIFT + K", "Toggle keybindings hint learning",
    "omarchy-shell shell summon nejcc.keybindings-hint '{\"learning\":\"toggle\"}'")

-- ============================================================================
-- 05. PLUGIN INTEGRATIONS
-- ============================================================================
--
-- Manually loads configuration files belonging to installed Omarchy plugins.
--
-- Each integration:
--   1. Constructs the expected plugin configuration path.
--   2. Checks whether the configuration file exists.
--   3. Loads the configuration using dofile().
--   4. Uses pcall() to prevent loading errors from interrupting this file.
--
-- Missing plugin files are silently skipped.
--
-- 05.1. Fathom
-- 05.2. Close Guard
-- ============================================================================


-- --------------------------------------------------------------------------
-- 05.1. FATHOM
-- --------------------------------------------------------------------------
--
-- PURPOSE:
--   Window navigation helper.
--
-- CONFIGURATION:
--   ~/.config/omarchy/plugins/io.github.mtolhuys.fathom/hypr/fathom.lua
--
-- LOADING:
--   Loads the plugin's Hyprland configuration when the file exists.
-- --------------------------------------------------------------------------

do
    local fathom = os.getenv("HOME")
        .. "/.config/omarchy/plugins/io.github.mtolhuys.fathom/hypr/fathom.lua"
    local file = io.open(fathom, "r")
    if file then
        file:close()
        pcall(dofile, fathom)
    end
end


-- --------------------------------------------------------------------------
-- 05.2. CLOSE GUARD
-- --------------------------------------------------------------------------
--
-- PURPOSE:
--   Additional protection around window-closing operations.
--
-- CONFIGURATION:
--   ~/.config/omarchy/plugins/io.github.ayandexyz.close-guard/hypr/close-guard.lua
--
-- LOADING:
--   Loads the plugin's Hyprland configuration when the file exists.
-- --------------------------------------------------------------------------

do
    local guard = os.getenv("HOME") .. "/.config/omarchy/plugins/io.github.ayandexyz.close-guard/hypr/close-guard.lua"
    local file = io.open(guard, "r")
    if file then
        file:close()
        pcall(dofile, guard)
    end
end

-- ============================================================================
-- 06. WEB APPLICATIONS
-- ============================================================================
--
-- Custom webapp shortcuts.
--
-- Applications are launched through Omarchy's webapp launcher.
--
-- 06.1. YouTube Music
-- 06.2. Claude
-- 06.3. OpenWebUI
-- 06.4. Notion
-- ============================================================================


-- --------------------------------------------------------------------------
-- 06.1. YOUTUBE MUSIC
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + SHIFT + M
--
-- URL:
--   https://music.youtube.com/
--
-- BEHAVIOUR:
--   Opens YouTube Music as a web application.
-- --------------------------------------------------------------------------

o.bind("SUPER + SHIFT + M", "YouTube Music",
    "omarchy-launch-webapp https://music.youtube.com/")


-- --------------------------------------------------------------------------
-- 06.2. CLAUDE
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + SHIFT + C
--
-- URL:
--   https://claude.ai/
--
-- BEHAVIOUR:
--   Opens Claude as a web application.
-- --------------------------------------------------------------------------

o.bind("SUPER + SHIFT + C", "Claude",
    "omarchy-launch-webapp https://claude.ai/")


-- --------------------------------------------------------------------------
-- 06.3. OPENWEBUI
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + SHIFT + L
--
-- URL:
--   http://open-webui.localhost
--
-- BEHAVIOUR:
--   Opens the locally hosted OpenWebUI instance.
-- --------------------------------------------------------------------------

o.bind("SUPER + SHIFT + L", "OpenWebUI",
    "omarchy-launch-webapp http://open-webui.localhost")


-- --------------------------------------------------------------------------
-- 06.4. NOTION
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + SHIFT + O
--
-- URL:
--   https://app.notion.com/login
--
-- BEHAVIOUR:
--   Opens Notion as a web application.
-- --------------------------------------------------------------------------

o.bind("SUPER + SHIFT + O", "Notion",
    "omarchy-launch-webapp https://app.notion.com/login")

--- ============================================================================
-- 07. APPLICATION LAUNCHERS
-- ============================================================================
--
-- Native desktop applications and terminal-based utilities.
--
-- 07.1. Email client
-- 07.2. Web browsers
-- 07.3. File managers
-- 07.4. System monitoring
-- 07.5. Terminal and development tools
-- ============================================================================


-- --------------------------------------------------------------------------
-- 07.1. EMAIL CLIENT
-- --------------------------------------------------------------------------

-- Thunderbird: Desktop email client.
-- KEY: SUPER + SHIFT + ALT + E

o.bind("SUPER + SHIFT + ALT + E", "Thunderbird",
    "/usr/bin/thunderbird")


-- --------------------------------------------------------------------------
-- 07.2. WEB BROWSERS
-- --------------------------------------------------------------------------
--
-- Includes standard and private browsing shortcuts.
--
-- Private browsing options are passed directly to the browser executable.
-- --------------------------------------------------------------------------

-- Zen Browser: Standard browsing.
-- KEY: SUPER + SHIFT + RETURN

o.bind("SUPER + SHIFT + RETURN", "Zen Browser",
    "/usr/bin/zen-browser")


-- Zen Browser: Private browsing.
-- KEY: SUPER + CTRL + ALT + RETURN
-- OPTIONS: Private window and safe mode.

o.bind("SUPER + CTRL + ALT + RETURN", "Zen Browser (Private)",
    "/usr/bin/zen-browser --private-window --safe-mode")


-- Brave Browser: Standard browsing.
-- KEY: SUPER + SHIFT + ALT + B

o.bind("SUPER + SHIFT + ALT + B", "Brave Browser",
    "/usr/bin/brave-origin")


-- Brave Browser: Private browsing.
-- KEY: SUPER + CTRL + ALT + B
-- OPTIONS: Incognito mode and extensions disabled.

o.bind("SUPER + CTRL + ALT + B", "Brave Browser (Private)",
    "/usr/bin/brave-origin --incognito --disable-extensions")


-- Chromium: Standard browsing.
-- KEY: SUPER + SHIFT + B

o.bind("SUPER + SHIFT + B", "Chromium Browser",
    "/usr/bin/chromium")


-- Chromium: Private browsing.
-- KEY: SUPER + CTRL + SHIFT + B
-- OPTIONS: Incognito mode and extensions disabled.

o.bind("SUPER + CTRL + SHIFT + B", "Chromium Browser (Private)",
    "/usr/bin/chromium --incognito --disable-extensions")


-- --------------------------------------------------------------------------
-- 07.3. FILE MANAGEMENT
-- --------------------------------------------------------------------------
--
-- Shortcuts for graphical and terminal-based file managers.
-- --------------------------------------------------------------------------

-- Nautilus: Standard file manager.
-- KEY: SUPER + E

o.bind("SUPER + E", "File Manager",
    "/usr/bin/nautilus")


-- Nautilus: Open administrative locations using admin://.
-- KEY: SUPER + SHIFT + E

o.bind("SUPER + SHIFT + E", "File Manager (Admin)",
    "/usr/bin/nautilus admin:///")


-- Superfile: Terminal-based file manager.
-- KEY: SUPER + ALT + SHIFT + F

o.bind("SUPER + ALT + SHIFT + F", "Superfile",
    "exec omarchy-launch-terminal bash -c 'spf'")


-- --------------------------------------------------------------------------
-- 07.4. SYSTEM MONITORING
-- --------------------------------------------------------------------------
--
-- Launches btop inside an Omarchy-managed terminal.
-- --------------------------------------------------------------------------

-- btop: Interactive system resource monitor.
-- KEY: SUPER + SHIFT + ESCAPE

o.bind("SUPER + SHIFT + ESCAPE", "System Monitor",
    "exec omarchy-launch-terminal bash -c 'btop'")


-- --------------------------------------------------------------------------
-- 07.5. TERMINAL AND DEVELOPMENT TOOLS
-- --------------------------------------------------------------------------
--
-- Launches Zellij using a persistent session named Work.
--
-- If the Work session already exists, it attaches to that session.
-- Otherwise, it creates a new session with the same name.
-- --------------------------------------------------------------------------

-- Zellij: Terminal multiplexer.
-- KEY: SUPER + ALT + Z
-- SESSION: Work

o.bind("SUPER + ALT + Z", "Zellij",
    "exec omarchy-launch-terminal bash -c 'zellij attach Work || zellij -s Work'")

-- ============================================================================
-- 08. WINDOW MANAGEMENT
-- ============================================================================
--
-- Custom shortcuts for window appearance and navigation.
--
-- 08.1. Radial menu
-- 08.2. Full width
-- 08.3. Fullscreen
-- ============================================================================


-- --------------------------------------------------------------------------
-- 08.1. RADIAL MENU
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + R
--
-- BEHAVIOUR:
--   Opens the Omarchy radial menu.
-- --------------------------------------------------------------------------

o.bind("SUPER + R", "Radial menu",
    "omarchy-shell radial open")


-- --------------------------------------------------------------------------
-- 08.2. FULL WIDTH
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + F
--
-- BEHAVIOUR:
--   Maximizes the active window without using standard fullscreen mode.
--
-- MODE:
--   maximized
-- --------------------------------------------------------------------------

o.bind("SUPER + F", "Full width",
    hl.dsp.window.fullscreen({ mode = "maximized" }))


-- --------------------------------------------------------------------------
-- 08.3. FULLSCREEN
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + ALT + F
--
-- BEHAVIOUR:
--   Uses fullscreen mode for the active window.
--
-- MODE:
--   fullscreen
-- --------------------------------------------------------------------------

o.bind("SUPER + ALT + F", "Full screen",
    hl.dsp.window.fullscreen({ mode = "fullscreen" }))


-- ============================================================================
-- 09. SYSTEM AND SESSION CONTROLS
-- ============================================================================
--
-- System-level shortcuts for locking the session and changing workspace
-- layouts.
--
-- 09.1. Lock system
-- 09.2. Toggle workspace layout
-- ============================================================================


-- --------------------------------------------------------------------------
-- 09.1. LOCK SYSTEM
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + L
--
-- BEHAVIOUR:
--   Locks the current system session using Omarchy's lock command.
-- --------------------------------------------------------------------------

o.bind("SUPER + L",
    "Lock system", "omarchy-system-lock")


-- --------------------------------------------------------------------------
-- 09.2. TOGGLE WORKSPACE LAYOUT
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + CTRL + L
--
-- BEHAVIOUR:
--   Toggles the current workspace layout using Omarchy's layout management
--   script.
-- --------------------------------------------------------------------------

o.bind("SUPER + CTRL + L", "Toggle workspace layout",
    "omarchy-hyprland-workspace-layout-toggle")


-- ============================================================================
-- 10. CLIPBOARD MANAGEMENT
-- ============================================================================
--
-- Clipboard-related shortcuts.
--
-- 10.1. Clipboard manager
-- 10.2. Universal paste
-- ============================================================================


-- --------------------------------------------------------------------------
-- 10.1. CLIPBOARD MANAGER
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + V
--
-- BEHAVIOUR:
--   Opens or hides Omarchy's clipboard manager.
-- --------------------------------------------------------------------------

o.bind("SUPER + V", "Clipboard manager",
    "omarchy-shell shell toggle omarchy.clipboard")


-- --------------------------------------------------------------------------
-- 10.2. UNIVERSAL PASTE
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + CTRL + V
--
-- BEHAVIOUR:
--   Automatically selects the appropriate paste shortcut based on the
--   currently focused application.
--
-- NORMAL APPLICATIONS:
--   CTRL + V
--
-- TERMINALS:
--   SHIFT + INSERT
--
-- The active window is detected through the terminal tag
-- --------------------------------------------------------------------------

o.bind("SUPER + CTRL + V", "Universal paste",
    universal_clipboard_shortcut("CTRL", "V", "SHIFT", "Insert"))

-- ============================================================================
-- 11. INPUT AND NOTIFICATION CONTROLS
-- ============================================================================
--
-- Shortcuts for emoji selection and notification management.
--
-- 11.1. Emoji picker
-- 11.2. Dismiss last notification
-- ============================================================================


-- --------------------------------------------------------------------------
-- 11.1. EMOJI PICKER
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + COMMA
--
-- BEHAVIOUR:
--   Opens or hides Omarchy's emoji picker.
-- --------------------------------------------------------------------------

o.bind("SUPER + COMMA", "Emojis",
    "omarchy-shell shell toggle omarchy.emojis")


-- --------------------------------------------------------------------------
-- 11.2. DISMISS LAST NOTIFICATION
-- --------------------------------------------------------------------------
--
-- KEY:
--   SUPER + CTRL + E
--
-- BEHAVIOUR:
--   Dismisses the most recent notification.
-- --------------------------------------------------------------------------

o.bind("SUPER + CTRL + E", "Dismiss last notification",
    "omarchy-shell notifications dismissOne")


-- ============================================================================
-- END OF PERSONAL KEYBINDING OVERRIDES
-- ============================================================================
--
-- All personal keybindings, helper functions, plugin integrations, and
-- application launchers are defined above.
--
-- Default Omarchy bindings not explicitly unbound remain unchanged.
--
-- ============================================================================
