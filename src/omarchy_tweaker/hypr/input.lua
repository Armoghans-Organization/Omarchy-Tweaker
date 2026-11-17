-- ============================================================================
-- OMARCHY PERSONAL INPUT OVERRIDES
-- ============================================================================
--
-- DESCRIPTION:
-- Personal input-device, touchpad, scrolling, and gesture customizations.
--
-- CONFIGURATION:
-- This file contains personal input overrides that replace or extend
-- Omarchy's default input configuration.
--
-- CONFIGURATION GUIDELINES:
--   * Keep only personal input overrides in this file.
--   * Omarchy's default input settings are replaced where explicitly specified.
--   * Application-specific scrolling settings are managed through o.window().
--   * Custom touchpad gestures are registered through hl.gesture().
--
-- CATEGORIES:
--   01. General input configuration
--   02. Touchpad configuration
--   03. Workspace navigation gestures
--   04. Smooth workspace cycling logic
--
-- ============================================================================

-- ============================================================================
-- 01. GENERAL INPUT CONFIGURATION
-- ============================================================================
--
-- Global input-device configuration.
--
-- These settings control general pointer sensitivity and mouse acceleration.
--
-- SETTINGS:
--   01.1. Pointer sensitivity
--   01.2. Mouse acceleration profile
-- ============================================================================

hl.config({
    input = {
        -- ------------------------------------------------------------------
        -- 01.1. POINTER SENSITIVITY
        -- ------------------------------------------------------------------
        --
        -- Controls the sensitivity of the mouse and trackpad.
        --
        -- VALUE:
        --   0
        --
        -- DEFAULT:
        --   0
        --
        -- Positive values increase sensitivity, while negative values
        -- decrease it.
        -- ------------------------------------------------------------------

        sensitivity = 0,

        -- ------------------------------------------------------------------
        -- 01.2. MOUSE ACCELERATION PROFILE
        -- ------------------------------------------------------------------
        --
        -- Controls how pointer movement responds to physical movement speed.
        --
        -- PROFILE:
        --   flat
        --
        -- BEHAVIOUR:
        --   Disables adaptive mouse acceleration, providing a more consistent
        --   relationship between physical movement and cursor movement.
        --
        -- DEFAULT:
        --   adaptive
        -- ------------------------------------------------------------------

        accel_profile = "flat",

        -- ==================================================================
        -- 02. TOUCHPAD CONFIGURATION
        -- ==================================================================
        --
        -- Settings specifically for touchpad input devices.
        --
        -- These options control scrolling, clicking, typing behaviour,
        -- and multi-finger dragging.
        --
        -- SETTINGS:
        --   02.1. Natural scrolling
        --   02.2. Clickfinger behaviour
        --   02.3. Scroll speed
        --   02.4. Disable touchpad while typing
        --   02.5. Three-finger dragging
        -- ==================================================================

        touchpad = {
            -- --------------------------------------------------------------
            -- 02.1. NATURAL SCROLLING
            -- --------------------------------------------------------------
            --
            -- Controls the direction of touchpad scrolling.
            --
            -- VALUE:
            --   false
            --
            -- BEHAVIOUR:
            --   Uses conventional scrolling rather than natural/inverted
            --   scrolling.
            --
            -- NOTE:
            --   With natural scrolling enabled, moving fingers upward
            --   generally moves the document upward.
            -- --------------------------------------------------------------

            natural_scroll = false,

            -- --------------------------------------------------------------
            -- 02.2. CLICKFINGER BEHAVIOUR
            -- --------------------------------------------------------------
            --
            -- Controls how multi-finger touchpad clicks are interpreted.
            --
            -- VALUE:
            --   false
            --
            -- BEHAVIOUR:
            --   Disables clickfinger-based button selection.
            --
            -- NOTE:
            --   This preserves the alternative touchpad button-area
            --   behaviour instead of assigning right-click based on
            --   the number of fingers used.
            -- --------------------------------------------------------------

            clickfinger_behavior = false,

            -- --------------------------------------------------------------
            -- 02.3. TOUCHPAD SCROLL SPEED
            -- --------------------------------------------------------------
            --
            -- Controls the scrolling speed of the touchpad.
            --
            -- VALUE:
            --   0.6
            --
            -- BEHAVIOUR:
            --   Applies a reduced scrolling factor for more controlled
            --   touchpad scrolling.
            -- --------------------------------------------------------------

            scroll_factor = 0.6,

            -- --------------------------------------------------------------
            -- 02.4. DISABLE TOUCHPAD WHILE TYPING
            -- --------------------------------------------------------------
            --
            -- Controls whether the touchpad is disabled temporarily while
            -- typing on the keyboard.
            --
            -- VALUE:
            --   true
            --
            -- BEHAVIOUR:
            --   Helps prevent accidental pointer movement and clicks
            --   while typing.
            -- --------------------------------------------------------------

            disable_while_typing = true,

            -- --------------------------------------------------------------
            -- 02.5. THREE-FINGER DRAGGING
            -- --------------------------------------------------------------
            --
            -- Controls the touchpad's three-finger dragging behaviour.
            --
            -- VALUE:
            --   0
            --
            -- INTENDED BEHAVIOUR:
            --   Left-click-and-drag using three fingers.
            -- --------------------------------------------------------------

            drag_3fg = 0
        }
    }
})

-- ============================================================================
-- 03. WORKSPACE NAVIGATION GESTURES
-- ============================================================================
--
-- Custom touchpad gestures for navigating between Hyprland workspaces.
--
-- CONFIGURATION:
--   03.1. Three-finger horizontal workspace swipe
--
-- GESTURE:
--   Fingers:    3
--   Direction:  horizontal
--   Action:     workspace
--
-- PURPOSE:
--   Allows workspace navigation using a three-finger horizontal swipe.
-- ============================================================================


-- --------------------------------------------------------------------------
-- 03.1. THREE-FINGER HORIZONTAL WORKSPACE SWIPE
-- --------------------------------------------------------------------------
--
-- GESTURE:
--   Three-finger horizontal swipe.
--
-- DIRECTION:
--   horizontal
--
-- ACTION:
--   workspace
--
-- BEHAVIOUR:
--   Registers Hyprland's workspace gesture for horizontal three-finger
--   touchpad navigation.
--
-- NOTE:
--   This is separate from the custom vertical workspace cycling logic
--   defined in the next section.
-- --------------------------------------------------------------------------

hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })


-- ============================================================================
-- 04. SMOOTH WORKSPACE CYCLING LOGIC
-- ============================================================================
--
-- Custom vertical three-finger gestures for cycling between workspaces.
--
-- This section implements a movement threshold and a time-based debounce
-- mechanism to reduce accidental or repeated workspace switching.
--
-- CONFIGURATION:
--   04.1. Gesture tracking variables
--   04.2. Workspace cycling callback
--   04.3. Three-finger downward workspace cycling
--   04.4. Three-finger upward workspace cycling
-- ============================================================================


-- --------------------------------------------------------------------------
-- 04.1. GESTURE TRACKING VARIABLES
-- --------------------------------------------------------------------------
--
-- last_trigger:
--   Stores the time of the last workspace-switch action.
--
-- move_ticks:
--   Counts how many times the gesture callback has been triggered.
--
-- These variables are shared by the workspace cycling callbacks.
-- --------------------------------------------------------------------------

local last_trigger = 0
local move_ticks = 0


-- --------------------------------------------------------------------------
-- 04.2. WORKSPACE CYCLING CALLBACK
-- --------------------------------------------------------------------------
--
-- Creates a callback responsible for cycling to the next or previous
-- workspace.
--
-- ARGUMENT:
--   reverse:
--       true  - Cycle to the previous workspace.
--       false - Cycle to the next workspace.
--
-- MOVEMENT THRESHOLD:
--   The callback waits for at least three movement ticks before attempting
--   a workspace switch.
--
-- DEBOUNCE:
--   Uses os.time() to track the last trigger time.
--
-- DISPATCH:
--   Calls Hyprland's window.cycle_next dispatcher.
--
-- NOTE:
--   The original callback logic is preserved, including its movement
--   threshold and timing condition.
-- --------------------------------------------------------------------------

local function cycle_smooth(reverse)
    return function()
        move_ticks = move_ticks + 1

        -- Wait for 3 movement ticks so diagonal/accidental touches settle first.
        if move_ticks < 3 then return end

        -- Get the current wall-clock time.
        local now = os.time()

        -- Allow the first eligible movement tick to trigger immediately.
        -- Otherwise, wait until at least one second has passed since the
        -- previous trigger.
        if now - last_trigger >= 1 or move_ticks == 3 then
            last_trigger = now

            -- Dispatch the workspace cycling operation.
            -- reverse = true  : Previous workspace.
            -- reverse = false : Next workspace.
            hl.dispatch(hl.dsp.window.cycle_next({ prev = reverse }))
        end
    end
end


-- --------------------------------------------------------------------------
-- 04.3. THREE-FINGER DOWNWARD WORKSPACE CYCLING
-- --------------------------------------------------------------------------
--
-- GESTURE:
--   Three-finger downward swipe.
--
-- DIRECTION:
--   down
--
-- ACTION:
--   cycle_smooth(true)
--
-- BEHAVIOUR:
--   Cycles to the previous workspace.
-- --------------------------------------------------------------------------

hl.gesture({ fingers = 3, direction = "down", action = cycle_smooth(true) })


-- --------------------------------------------------------------------------
-- 04.4. THREE-FINGER UPWARD WORKSPACE CYCLING
-- --------------------------------------------------------------------------
--
-- GESTURE:
--   Three-finger upward swipe.
--
-- DIRECTION:
--   up
--
-- ACTION:
--   cycle_smooth(false)
--
-- BEHAVIOUR:
--   Cycles to the next workspace.
-- --------------------------------------------------------------------------

hl.gesture({ fingers = 3, direction = "up", action = cycle_smooth(false) })


-- ============================================================================
-- END OF PERSONAL INPUT OVERRIDES
-- ============================================================================
--
-- Global input settings, touchpad configuration, application-specific
-- scrolling, and custom workspace gestures are defined above.
--
-- ============================================================================
