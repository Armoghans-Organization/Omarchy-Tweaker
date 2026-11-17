-- =============================================================================
-- WORKSPACES CONFIGURATION
-- =============================================================================
-- Configure workspace organization and automatic application placement.
--
-- Applications matching the rules below will automatically open in their
-- assigned workspaces.
--
-- Workspace overview:
--   3. Code Editors
--   4. Browsers
--   5. AI Tools
--   6. Music and Media
--   7. Communication
--   8. Virtualization

-- -----------------------------------------------------------------------------
-- 01. WORKSPACE 3 — CODE EDITORS
-- -----------------------------------------------------------------------------
-- Keep development environments together.

o.window("com.microsoft.VSCode", { workspace = "3" })

-- -----------------------------------------------------------------------------
-- 02. WORKSPACE 4 — BROWSERS
-- -----------------------------------------------------------------------------
-- Keep regular web browsers together.

o.window("zen", { workspace = "4" })
o.window("chromium", { workspace = "4" })
o.window("brave", { workspace = "4" })

-- -----------------------------------------------------------------------------
-- 03. WORKSPACE 5 — AI TOOLS
-- -----------------------------------------------------------------------------
-- Dedicated workspace for browser-based AI applications.
-- These match Chrome web-app window classes.

o.window("chrome-chatgpt.com__-Default", { workspace = "5" })
o.window("chrome-claude.ai__-Default", { workspace = "5" })
o.window("chrome-grok.com__-Default", { workspace = "5" })

-- -----------------------------------------------------------------------------
-- 04. WORKSPACE 6 — MUSIC AND MEDIA
-- -----------------------------------------------------------------------------
-- Keep music applications and media playback together.

o.window("chrome-youtube.com__-Default", { workspace = "6" })
o.window("chrome-music.youtube.com__-Default", { workspace = "6" })
o.window("mpv", { workspace = "6" })

-- -----------------------------------------------------------------------------
-- 05. WORKSPACE 7 — COMMUNICATION
-- -----------------------------------------------------------------------------
-- Keep messaging, social networking, and email applications together.

o.window("chrome-web.whatsapp.com__-Default", { workspace = "7" })
o.window("chrome-discord.com__channels_@me-Default", { workspace = "7" })
o.window("org.mozilla.Thunderbird", { workspace = "7" })
o.window("chrome-www.linkedin.com__-Default", { workspace = "7" })

-- -----------------------------------------------------------------------------
-- 06. WORKSPACE 8 — VIRTUALIZATION
-- -----------------------------------------------------------------------------
-- Keep virtualization and emulation tools together.
o.window("virt-manager", { workspace = "8" })

-- -----------------------------------------------------------------------------
-- 07. WORKSPACE Rules (Apps Behaviour)
-- -----------------------------------------------------------------------------
-- Configure application behavior.

-- VS Code
hl.window_rule({
    match = { class = ".*VSCode.*" },
    scrolling_width = 1.0,
})

-- Brave
hl.window_rule({
    match = { class = ".*brave.*" },
    scrolling_width = 1.0,
})

-- Chrome / Chrome web apps
hl.window_rule({
    match = { class = "^chrome-.*" },
    scrolling_width = 1.0,
})

hl.window_rule({
    match = { class = "^chromium*" },
    scrolling_width = 1.0,
})

-- Zen
hl.window_rule({
    match = { class = ".*zen.*" },
    scrolling_width = 1.0,
})

-- Virt-manager
hl.window_rule({
    match = { class = ".*virt-manager.*" },
    scrolling_width = 1.0,
})
