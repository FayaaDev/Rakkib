-- WezTerm Configuration
-- =====================
-- Leader Key: CapsLock
--
-- SETUP REQUIRED ON macOS:
-- 1. Go to System Settings → Keyboard → Keyboard Shortcuts → Modifier Keys
-- 2. Select your keyboard from the dropdown
-- 3. Set "Caps Lock Key" to "No Action"
-- 4. Click Done
-- 5. Restart WezTerm
--
-- After setup, press CapsLock, then the corresponding key within 2 seconds

-- Keybindings:
-- 1. Tab Management:
--    - LEADER + c: Create a new tab
--    - LEADER + x: Close the current pane (with confirmation)
--    - LEADER + b: Switch to the previous tab
--    - LEADER + n: Switch to the next tab
--    - LEADER + <number>: Switch to a specific tab (0–9)
--
-- 2. Pane Splitting:
--    - LEADER + |: Split horizontally
--    - LEADER + -: Split vertically
--
-- 3. Pane Navigation:
--    - LEADER + h/j/k/l: Move left/down/up/right
--
-- 4. Pane Resizing:
--    - LEADER + Arrow Keys: Adjust pane size by 5 units

local wezterm = require "wezterm"
local act = wezterm.action

local config = {}

if wezterm.config_builder then
    config = wezterm.config_builder()
end

-- Performance
config.max_fps = 240
config.animation_fps = 240

-- Custom Configuration
local tab_style = "square"
local leader_prefix = wezterm.nerdfonts.fa_apple -- Apple logo

--[[
============================
Font
============================
]]
config.font = wezterm.font_with_fallback({ 'MesloLGS Nerd Font', "Maple Mono NF", "JetBrains Mono NL" })
config.font_size = 20

--[[
============================
Window Settings
============================
]]
config.window_decorations = "RESIZE"
config.window_background_opacity = 0.9
config.automatically_reload_config = true
config.window_close_confirmation = 'NeverPrompt'

--[[
============================
Colors
============================
]]
local color_scheme = "Catppuccin Macchiato"
config.color_scheme = color_scheme

local scheme_colors = {
    catppuccin = {
        macchiato = {
            rosewater = "f4dbd6",
            flamingo = "f0c6c6",
            crimson = "A51C30",
            mauve = "c6a0f6",
            red = "ed8796",
            maroon = "ee99a0",
            peach = "#f5a97f",
            yellow = "#eed49f",
            green = "#a6da95",
            teal = "#8bd5ca",
            sky = "#91d7e3",
            sapphire = "#7dc4e4",
            blue = "#8aadf4",
            lavender = "#b7bdf8",
            text = "#cad3f5",
            crust = "#181926",
        }
    }
}

local colors = {
    --border = scheme_colors.catppuccin.macchiato.teal,
    tab_bar_active_tab_fg = scheme_colors.catppuccin.macchiato.crimson,
    tab_bar_active_tab_bg = scheme_colors.catppuccin.macchiato.crimson,
    tab_bar_text = scheme_colors.catppuccin.macchiato.crust,
    arrow_foreground_leader = scheme_colors.catppuccin.macchiato.crimson,
    arrow_background_leader = scheme_colors.catppuccin.macchiato.crimson,
}

--[[
============================
Border
============================
]]
config.window_frame = {
    border_left_width = "0.4cell",
    border_right_width = "0.4cell",
    border_bottom_height = "0.15cell",
    border_top_height = "0.15cell",
    border_left_color = colors.border,
    border_right_color = colors.border,
    border_bottom_color = colors.border,
    border_top_color = colors.border,
}

--[[
============================
Keybindings
============================
]]
-- Leader key set to CapsLock which was remapped to F13 using the command:
-- hidutil property --set '{"UserKeyMapping"[{"HIDKeyboardModifierMappingSrc":0x700000039,"HIDKeyboardModifierMappingDst":0x700000068}]}'
-- Note: 0x700000039 is CapsLock; 0x700000068 is F13. To Remove this mapping re-run the command with swapped keys.

config.leader = { key = "a", mods = "CMD", timeout_milliseconds = 2000 }

config.keys = {
    -- Original keybindings
    { key = 'LeftArrow',  mods = 'SHIFT', action = wezterm.action.SendKey { key = 'A', mods = 'CTRL' } }, -- ⇧← = ^A
    { key = 'RightArrow', mods = 'SHIFT', action = wezterm.action.SendKey { key = 'E', mods = 'CTRL' } }, -- ⇧→ = ^E
    { key = 'LeftArrow',  mods = 'CMD', action = wezterm.action.SendString "\x1bb" }, -- backward-word
    { key = 'RightArrow', mods = 'CMD', action = wezterm.action.SendString "\x1bf" }, -- forward-word
    { key = 'Backspace', mods = 'CMD', action = wezterm.action.SendKey { key = 'w', mods = 'CTRL' } }, -- CMD+Backspace del
    
    -- Rename Tabs

    {
        mods = "LEADER",
        key = "v",
        action = act.PromptInputLine {
            description = "Rename current tab",
            action = wezterm.action_callback(function(window, pane, line)
                if line then
                    window:active_tab():set_title(line)
                end
            end),
        },
    },

    -- Leader-based keybindings
    {
        mods = "LEADER",
        key = "c",
        action = wezterm.action.SpawnTab "CurrentPaneDomain",
    },

    {
        mods = "LEADER",
        key = "q",
        action = wezterm.action.CloseCurrentPane { confirm = false }
    },
    {
        mods = "LEADER",
        key = "LeftArrow",
        action = wezterm.action.ActivateTabRelative(-1)
    },
    {
        mods = "LEADER",
        key = "RightArrow",
        action = wezterm.action.ActivateTabRelative(1)
    },
    {
        mods = "LEADER",
        key = "/",
        action = wezterm.action.SplitHorizontal { domain = "CurrentPaneDomain" }
    },
    {
        mods = "LEADER",
        key = "-",
        action = wezterm.action.SplitVertical { domain = "CurrentPaneDomain" }
    },
    {
        mods = "LEADER",
        key = "b",
        action = wezterm.action.ActivatePaneDirection "Left"
    },
    -- {
    --     mods = "LEADER",
    --     key = "",
    --     action = wezterm.action.ActivatePaneDirection "Down"
    -- },
    -- {
    --     mods = "LEADER",
    --     key = "",
    --     waction = wezterm.action.ActivatePaneDirection "Up"
    -- },
    {
        mods = "LEADER",
        key = "n",
        action = wezterm.action.ActivatePaneDirection "Right"
    },
    {
        mods = "LEADER",
        key = "h",
        action = wezterm.action.AdjustPaneSize { "Left", 5 }
    },
    {
        mods = "LEADER",
        key = "j",
        action = wezterm.action.AdjustPaneSize { "Right", 5 }
    },
    {
        mods = "LEADER",
        key = "DownArrow",
        action = wezterm.action.AdjustPaneSize { "Down", 5 }
    },
    {
        mods = "LEADER",
        key = "UpArrow",
        action = wezterm.action.AdjustPaneSize { "Up", 5 }
    },
}

-- Leader + number to activate tabs 0-9
for i = 0, 9 do
    table.insert(config.keys, {
        key = tostring(i),
        mods = "LEADER",
        action = wezterm.action.ActivateTab(i),
    })
end

--[[
============================
Tab Bar
============================
]]
config.hide_tab_bar_if_only_one_tab = false
config.tab_bar_at_bottom = true
config.use_fancy_tab_bar = false
config.tab_and_split_indices_are_zero_based = true

local function tab_title(tab_info)
    local title = tab_info.tab_title
    if title and #title > 0 then
        return title
    end
    return tab_info.active_pane.title
end

wezterm.on(
    "format-tab-title",
    function(tab, tabs, panes, config, hover, max_width)
        local title = " " .. tab.tab_index .. ": " .. tab_title(tab) .. " "
        local left_edge_text = ""
        local right_edge_text = ""

        if tab_style == "rounded" then
            title = tab.tab_index .. ": " .. tab_title(tab)
            title = wezterm.truncate_right(title, max_width - 2)
            left_edge_text = wezterm.nerdfonts.ple_left_half_circle_thick
            right_edge_text = wezterm.nerdfonts.ple_right_half_circle_thick
        end

        if tab.is_active then
            return {
                { Background = { Color = colors.tab_bar_active_tab_bg } },
                { Foreground = { Color = colors.tab_bar_active_tab_fg } },
                { Text = left_edge_text },
                { Background = { Color = colors.tab_bar_active_tab_fg } },
                { Foreground = { Color = colors.tab_bar_text } },
                { Text = title },
                { Background = { Color = colors.tab_bar_active_tab_bg } },
                { Foreground = { Color = colors.tab_bar_active_tab_fg } },
                { Text = right_edge_text },
            }
        end
    end
)

--[[
============================
Leader Active Indicator
============================
]]
wezterm.on("update-status", function(window, _)
    local solid_left_arrow = ""
    local arrow_foreground = { Foreground = { Color = colors.arrow_foreground_leader } }
    local arrow_background = { Background = { Color = colors.arrow_background_leader } }
    local prefix = ""

    if window:leader_is_active() then
        prefix = " " .. leader_prefix

        if tab_style == "rounded" then
            solid_left_arrow = wezterm.nerdfonts.ple_right_half_circle_thick
        else
            solid_left_arrow = wezterm.nerdfonts.pl_left_hard_divider
        end

        local tabs = window:mux_window():tabs_with_info()

        if tab_style ~= "rounded" then
            for _, tab_info in ipairs(tabs) do
                if tab_info.is_active and tab_info.index == 0 then
                    arrow_background = { Foreground = { Color = colors.tab_bar_active_tab_fg } }
                    solid_left_arrow = wezterm.nerdfonts.pl_right_hard_divider
                    break
                end
            end
        end
    end

    window:set_left_status(wezterm.format {
        { Background = { Color = colors.arrow_foreground_leader } },
        { Text = prefix },
        arrow_foreground,
        arrow_background,
        { Text = solid_left_arrow }
    })
end)

return config