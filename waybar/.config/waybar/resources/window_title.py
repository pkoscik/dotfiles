#!/usr/bin/env python3
"""Title of the focused window on this bar's output, for every output at once.

waybar's sway/window only shows a title on the focused output; this shows each
output's own focused window, with class "unfocused" on outputs without focus.
Streams waybar JSON lines on every sway window/workspace event.

    window_title.py [output]   (defaults to $WAYBAR_OUTPUT_NAME)
"""

import json
import os
import re
import subprocess
import sys
from html import escape

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("WAYBAR_OUTPUT_NAME")
MAX_LENGTH = 50
REWRITE = [
    (r"(.*) — Mozilla Firefox", "  \\1"),
    (r"(.*) - Google Chrome", "  \\1"),
    (r"helix (.*)", "ed [\\1]"),
]


def focused_leaf(node):
    """Follow sway's focus stack down to the window that has (or last had) focus."""
    while True:
        children = node.get("nodes", []) + node.get("floating_nodes", [])
        if not children:
            return None if node["type"] == "workspace" else node
        by_id = {child["id"]: child for child in children}
        node = next((by_id[i] for i in node.get("focus", []) if i in by_id), None)
        if node is None:
            return None


def has_focus(node):
    return node.get("focused") or any(
        has_focus(child) for child in node.get("nodes", []) + node.get("floating_nodes", [])
    )


def status():
    tree = json.loads(subprocess.run(["swaymsg", "-t", "get_tree", "-r"], capture_output=True, text=True).stdout)
    output = next((o for o in tree["nodes"] if o["name"] == OUTPUT), None)
    window = focused_leaf(output) if output else None
    if not window or not window.get("name"):
        return {"text": "", "class": "empty"}

    title = window["name"]
    text = title
    for pattern, replacement in REWRITE:
        text, count = re.subn(f"^{pattern}$", replacement, text)
        if count:
            break
    if len(text) > MAX_LENGTH:
        text = text[: MAX_LENGTH - 1] + "…"
    return {
        "text": escape(text, quote=False),
        "tooltip": escape(title, quote=False),
        "class": "focused" if has_focus(output) else "unfocused",
    }


def main():
    events = subprocess.Popen(
        ["swaymsg", "-t", "subscribe", "-m", '["window", "workspace", "output"]'],
        stdout=subprocess.PIPE,
        text=True,
    )
    last = None
    while True:
        current = json.dumps(status(), ensure_ascii=False)
        if current != last:
            print(current, flush=True)
            last = current
        if not events.stdout.readline():
            break


if __name__ == "__main__":
    main()
