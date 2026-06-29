local wezterm = require("wezterm")
local config = wezterm.config_builder()

config.font = wezterm.font("JetBrains Mono", { weight = "Regular" })
config.font_size = 12.0
config.initial_cols = 100
config.initial_rows = 30

config.window_decorations = "TITLE|RESIZE"
config.window_padding = { left = 4, right = 4, top = 4, bottom = 4 }
config.hide_tab_bar_if_only_one_tab = true

config.scrollback_lines = 10000000

-- Always confirm before closing
config.window_close_confirmation = "AlwaysPrompt"
config.skip_close_confirmation_for_processes_named = {}

-- macOS: treat both Option keys as Alt
config.send_composed_key_when_left_alt_is_pressed = false
config.send_composed_key_when_right_alt_is_pressed = false

config.default_cursor_style = "SteadyBar"
config.hide_mouse_cursor_when_typing = true
config.selection_word_boundary = " \t\n{}[]()<>,│`|:\"'"

local act = wezterm.action
local is_macos = wezterm.target_triple:find("darwin") ~= nil

-- WezTerm ignores the match type when Search is given an empty string, so it
-- always opens case-sensitive (wezterm issue #7236). Workaround: seed a
-- non-empty case-insensitive pattern (which *does* set the mode), then clear
-- the pattern. ClearPattern keeps the case-insensitive mode for an empty box.
local search_insensitive = act.Multiple({
  act.Search({ CaseInSensitiveString = "_" }),
  act.CopyMode("ClearPattern"),
})

-- Keybindings
config.keys = {
  { key = "Return", mods = "CTRL|SHIFT", action = act.SpawnWindow },
  { key = "f", mods = "CTRL|SHIFT", action = search_insensitive },
  {
    key = "w",
    mods = is_macos and "SUPER" or "CTRL|SHIFT",
    action = act.CloseCurrentTab({ confirm = true }),
  },
}

config.mouse_bindings = {
  {
    event = { Down = { streak = 1, button = "Middle" } },
    mods = "NONE",
    action = wezterm.action.PasteFrom("PrimarySelection"),
  },
}

-- Vim-like copy mode: add `/` and `?` to start a search while in copy mode
-- Enter copy mode with Ctrl+Shift+X, search with Ctrl+Shift+F
local copy_mode = wezterm.gui.default_key_tables().copy_mode
table.insert(copy_mode, {
  key = "/",
  mods = "NONE",
  action = search_insensitive,
})
table.insert(copy_mode, {
  key = "/",
  mods = "SHIFT",
  action = search_insensitive,
})
config.key_tables = { copy_mode = copy_mode }

return config
