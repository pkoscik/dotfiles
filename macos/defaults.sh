#!/usr/bin/env bash
# macOS 26.5.2 (25F84)
set -euo pipefail

activate_settings() {
  local bin=/System/Library/PrivateFrameworks/SystemAdministration.framework/Resources/activateSettings
  [[ -x "$bin" ]] && "$bin" -u
}

# --- keyboard ---
defaults write -g ApplePressAndHoldEnabled -bool false
defaults write -g KeyRepeat -int 2
defaults write -g InitialKeyRepeat -int 15
defaults write com.apple.HIToolbox AppleFnUsageType -int 0
defaults write -g NSUserKeyEquivalents -dict-add "Cycle Through Windows" '\0'
defaults write -g NSUserKeyEquivalents -dict-add "Move Focus to Next Window" '\0'
defaults write com.apple.finder NSUserKeyEquivalents -dict-add "Cycle Through Windows" '\0'

# --- dock / corners / tiling ---
defaults write com.apple.dock autohide -bool true
defaults write com.apple.dock "show-recents" -bool false
defaults write com.apple.dock tilesize -int 24
for corner in tl tr bl br; do
  defaults write com.apple.dock "wvous-${corner}-corner" -int 1
  defaults write com.apple.dock "wvous-${corner}-modifier" -int 0
done
defaults write com.apple.WindowManager EnableTilingOptionAccelerator -bool false

# --- spotlight ---
python3 - << 'PY'
import subprocess
items = [
    ("APPLICATIONS", 1),
    ("SYSTEM_PREFS", 1),
    ("MENU_EXPRESSION", 0),
    ("MENU_DEFINITION", 0),
    ("MENU_CONVERSION", 0),
    ("MENU_OTHER", 0),
    ("MENU_WEBSEARCH", 0),
    ("MENU_SPOTLIGHT_SUGGESTIONS", 0),
    ("BOOKMARKS", 0),
    ("CONTACT", 0),
    ("DIRECTORIES", 0),
    ("DOCUMENTS", 0),
    ("MESSAGES", 0),
    ("EVENT_TODO", 0),
    ("FONTS", 0),
    ("IMAGES", 0),
    ("MOVIES", 0),
    ("MUSIC", 0),
    ("PDF", 0),
    ("PRESENTATIONS", 0),
    ("SPREADSHEETS", 0),
    ("SOURCE", 0),
    ("TIPS", 0),
    ("EMAIL", 0),
]
args = ["defaults", "write", "com.apple.Spotlight", "orderedItems", "-array"]
for name, enabled in items:
    args.append("{ enabled = %d; name = %s; }" % (enabled, name))
subprocess.check_call(args)
subprocess.check_call(["defaults", "write", "com.apple.Spotlight", "parsecEnabled", "-bool", "false"])
subprocess.check_call(["defaults", "write", "com.apple.Spotlight", "isPasteboardHistoryEnabled", "-bool", "false"])
PY

# --- symbolic hotkeys ---
python3 - << 'PY'
import plistlib, subprocess, pathlib, xml.etree.ElementTree as ET

UNBOUND = [65535, 65535, 0]
KEEP = {
    31: [115, 1, 1179648],
    160: [32, 49, 1048576],
}
TABLE_IDS = {
    7, 8, 9, 10, 11, 12, 13, 15, 17, 19, 21, 23, 25, 26, 27, 28, 29, 30, 31,
    32, 33, 34, 35, 36, 37, 52, 53, 54, 55, 56, 57, 59, 60, 61, 64, 65,
    79, 80, 81, 82, 98,
    *range(118, 134),
    156, 159, 160, 162, 163, 175, 179, 181, 182, 184, 190,
    *range(215, 220), 222, 223, 224, *range(225, 234), 235,
    *range(237, 252), 256, 257, 258, 260,
}

def ids_from_xml(path):
    found = set()
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return found
    names = {"sybmolichotkey", "slow_sybmolichotkey", "prefs_sybmolichotkey"}
    children = list(root.iter())
    for i, el in enumerate(children):
        if el.tag == "key" and el.text in names and i + 1 < len(children):
            nxt = children[i + 1]
            if nxt.tag == "integer" and nxt.text:
                found.add(int(nxt.text))
    return found

base = pathlib.Path("/System/Library/ExtensionKit/Extensions/KeyboardSettings.appex/Contents/Resources")
xml_ids = ids_from_xml(base / "en.lproj/DefaultShortcutsTable.xml")
xml_ids |= ids_from_xml(base / "DefaultSpacesShortcuts.xml")

raw = subprocess.check_output(["defaults", "export", "com.apple.symbolichotkeys", "-"])
p = plistlib.loads(raw)
keys = {int(k): v for k, v in p.get("AppleSymbolicHotKeys", {}).items()}
all_ids = TABLE_IDS | xml_ids | set(keys)

def set_key(idx, enabled, params):
    entry = dict(keys.get(idx) or {})
    entry["enabled"] = bool(enabled)
    entry["value"] = {"parameters": list(params), "type": "standard"}
    keys[idx] = entry

for idx in all_ids:
    set_key(idx, False, UNBOUND)
for idx, params in KEEP.items():
    set_key(idx, True, params)

p["AppleSymbolicHotKeys"] = {str(k): v for k, v in keys.items()}
tmp = pathlib.Path("/tmp/pkoscik-symbolichotkeys.plist")
tmp.write_bytes(plistlib.dumps(p, fmt=plistlib.FMT_XML))
subprocess.check_call(["defaults", "import", "com.apple.symbolichotkeys", str(tmp)])
print(f"hotkeys: {len(all_ids)} disabled, keep {sorted(KEEP)}")
PY

activate_settings
killall Dock Spotlight SystemUIServer 2>/dev/null || true
