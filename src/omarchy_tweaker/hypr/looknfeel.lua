-- =============================================================================
-- APPEARANCE AND WINDOW EFFECTS
-- =============================================================================
-- Customize Omarchy's default look and feel.

-- -----------------------------------------------------------------------------
-- 01. GENERAL WINDOW BEHAVIOR
-- -----------------------------------------------------------------------------

hl.config({
    general = {
        -- Use a Niri-like scrolling layout instead of the traditional tiling layout.
        layout = "scrolling",
    },
})

-- -----------------------------------------------------------------------------
-- 02. WINDOW DECORATION
-- -----------------------------------------------------------------------------

hl.config({
    decoration = {
        -- Apply rounded corners to windows.
        rounding = 8,

        -- Dim inactive windows to visually distinguish them from the focused window.
        -- dim_strength controls the intensity of the dimming effect.
        -- 0.0 = no dimming, 1.0 = maximum dimming.
        dim_inactive = true,
        dim_strength = 0.15,
    },
})

-- -----------------------------------------------------------------------------
-- 03. WINDOW ANIMATIONS
-- -----------------------------------------------------------------------------

hl.config({
    animations = {
        -- Enable window and workspace animations.
        enabled = true,
    },
})

-- =============================================================================
-- LAYER RULES
-- =============================================================================
-- Configure visual effects for individual Wayland layer surfaces.
-- These rules customize blur, transparency handling, animations, and dimming
-- around selected Omarchy components and plugins.


-- -----------------------------------------------------------------------------
-- 04. SPOTLIGHT
-- -----------------------------------------------------------------------------
hl.layer_rule({
    match = { namespace = "omarchy-spotlight" },
    blur = true,            -- Apply background blur behind the Spotlight overlay.
    ignore_alpha = 0.2,     -- Ignore alpha values below this threshold when applying blur.
    animation = "fade",     -- Fade the overlay in and out.
})


-- -----------------------------------------------------------------------------
-- 05. APPLICATION SWITCHER
-- -----------------------------------------------------------------------------
hl.layer_rule({
    match = { namespace = "omarchy-switcher" },
    blur = true,            -- Blur the background behind the application switcher.
    ignore_alpha = 0.2,     -- Ignore alpha values below this threshold when applying blur.
    animation = "fade",     -- Use a fade transition when showing or hiding the switcher.
})

-- -----------------------------------------------------------------------------
-- 06. CLIPBOARD MANAGER
-- -----------------------------------------------------------------------------
hl.layer_rule({
    match = { namespace = "alanfortlink-clipboard" },
    blur = true,            -- Blur the background behind the clipboard manager.
    ignore_alpha = 0.2,     -- Ignore alpha values below this threshold when applying blur.
    animation = "slide",    -- Slide the clipboard manager into and out of view.
    dim_around = true,      -- Dim surrounding content while the clipboard manager is open.
})

-- -----------------------------------------------------------------------------
-- 07. KEYBINDINGS HINT
-- -----------------------------------------------------------------------------
hl.layer_rule({
    match = { namespace = "nejcc-keybindings-hint" },
    blur = true,            -- Blur the background behind the keybinding hints.
    ignore_alpha = 0.2,     -- Ignore alpha values below this threshold when applying blur.
    animation = "slide",    -- Use a sliding transition.
    dim_around = true,      -- Dim surrounding content while the hints are displayed.
})

-- -----------------------------------------------------------------------------
-- 08. RADIAL MENU
-- -----------------------------------------------------------------------------
hl.layer_rule({
    match = { namespace = "radial-menu" },
    blur = true,            -- Blur the background behind the radial menu.
    ignore_alpha = 0.2,     -- Ignore alpha values below this threshold when applying blur.
    dim_around = true,      -- Dim surrounding content while the radial menu is open.
})

-- -----------------------------------------------------------------------------
-- 09. OMARCHY MENU
-- -----------------------------------------------------------------------------
hl.layer_rule({
    match = { namespace = "omarchy-menu" },
    blur = true,            -- Blur the background behind the Omarchy menu.
    ignore_alpha = 0.2,     -- Ignore alpha values below this threshold when applying blur.
    animation = "fade",     -- Fade the menu in and out.
    dim_around = true,      -- Dim surrounding content while the menu is open.
})
