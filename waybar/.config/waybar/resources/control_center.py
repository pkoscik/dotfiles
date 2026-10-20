#!/usr/bin/env python3
"""Waybar popups: audio, brightness, network, performance, bluetooth, notifications and power.

    control_center.py <popup> [output]

Running the same popup again while it's open closes it, so it can be bound to on-click.
Audio goes through pactl (PipeWire's pulse server), brightness through
brightness.sh, which caches DDC/CI state so opening the popup stays instant.
"""

import json
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, GtkLayerShell, Pango  # noqa: E402
from sysinfo import cpu_times, cpu_usage, meminfo, temperature, temperature_sensor  # noqa: E402

RESOURCES = Path(__file__).resolve().parent
BRIGHTNESS = str(RESOURCES / "brightness.sh")
PIDFILE = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "waybar-control-center.pid"

# Ignore external updates to a slider this long after the user touched it,
# so in-flight pactl/ddcutil calls don't make the knob jump back.
SETTLE_SECONDS = 0.4

CSS = b"""
* {
  font-family: "JetBrainsMono Nerd Font", monospace;
  font-size: 12px;
  color: #F8F8F2;
}
window.catcher { background: transparent; }
window.popup { background: transparent; }

.card {
  background: rgba(40, 42, 54, 0.97);
  border: 1px solid #44475A;
  border-radius: 14px;
  padding: 14px 14px 10px 14px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.45);
  /* left/top leave room for the shadow; top+bottom stay constant while sliding */
  margin: 12px 0 10px 12px;
  animation: popup-in 160ms ease-out;
}
.card.closing { animation: popup-out 120ms ease-in forwards; }
@keyframes popup-in {
  from { opacity: 0; margin-top: 22px; margin-bottom: 0; }
  to { opacity: 1; margin-top: 12px; margin-bottom: 10px; }
}
@keyframes popup-out {
  from { opacity: 1; margin-top: 12px; margin-bottom: 10px; }
  to { opacity: 0; margin-top: 22px; margin-bottom: 0; }
}
.section-title {
  color: #6272A4;
  font-size: 10px;
  font-weight: bold;
  margin: 10px 2px 4px 2px;
}
.section-title.first { margin-top: 0; }
.dim { color: #6272A4; }
.app-name { font-weight: bold; }
.app-media { color: #6272A4; font-size: 10px; }
.percent { min-width: 38px; color: #BFBFBF; }
.empty { color: #6272A4; padding: 4px 2px; }

button {
  background: transparent;
  border: none;
  border-radius: 8px;
  box-shadow: none;
  padding: 2px 6px;
  min-height: 0;
  min-width: 0;
}
button:hover { background: #44475A; }
button.icon { font-size: 15px; min-width: 26px; }
button.icon.muted label { color: #FF5555; }
button.toggle.active label { color: #BD93F9; }

.device { padding: 6px 8px; background: #343746; border-radius: 9px; }
.device:hover { background: #44475A; }
.device-row { padding: 6px 10px; border-radius: 8px; }
.device-row.selected label { color: #BD93F9; }
list, list row { background: transparent; }
list row { border-radius: 8px; padding: 0; }
list row:hover { background: #44475A; }

scale { padding: 6px 4px; }
scale trough {
  min-height: 6px;
  border-radius: 3px;
  background: #44475A;
  border: none;
}
scale highlight {
  border-radius: 3px;
  background: #BD93F9;
  border: none;
}
scale.muted highlight { background: #6272A4; }
scale.brightness highlight { background: #F1FA8C; }
scale slider {
  min-width: 14px;
  min-height: 14px;
  margin: -5px;
  border-radius: 7px;
  background: #F8F8F2;
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
}
scale slider:hover { background: #FFFFFF; }
separator { background: #44475A; min-height: 1px; margin: 8px 0 2px 0; }

switch {
  background: #44475A;
  border: none;
  border-radius: 11px;
  min-width: 38px;
  min-height: 20px;
  box-shadow: none;
}
switch:checked { background: #BD93F9; }
switch slider {
  background: #F8F8F2;
  border: none;
  border-radius: 9px;
  min-width: 18px;
  min-height: 18px;
  margin: 1px;
  box-shadow: none;
}
switch image { color: transparent; }

.list-row { padding: 6px 8px; border-radius: 9px; }
.list-row.active { background: #343746; }
.row-icon { font-size: 16px; min-width: 22px; }
.list-row.active .row-icon { color: #BD93F9; }
.row-title { font-weight: bold; }
.row-subtitle { color: #6272A4; font-size: 10px; }
button.accent { background: #343746; }
button.accent:hover { background: #44475A; }
button.accent label { color: #BD93F9; }
button.footer { padding: 6px 8px; margin-top: 2px; }
button.footer label { color: #BFBFBF; }
.status { color: #FFB86C; padding: 2px; }
.traffic-rx { color: #8BE9FD; }
.traffic-tx { color: #FF79C6; }
.big { font-size: 20px; font-weight: bold; }
.big.warning { color: #FFB86C; }
.big.critical { color: #FF5555; }

levelbar trough {
  min-height: 6px;
  background: #44475A;
  border: none;
  border-radius: 3px;
  padding: 0;
}
levelbar block { border: none; border-radius: 3px; min-height: 6px; }
levelbar block.filled { background: #BD93F9; }
levelbar block.empty { background: transparent; }
levelbar.warning block.filled { background: #FFB86C; }
levelbar.critical block.filled { background: #FF5555; }
levelbar.vertical trough { min-width: 6px; min-height: 28px; }
levelbar.vertical block { min-width: 6px; min-height: 0; }
.usage-name { color: #BFBFBF; }
.usage-value { color: #BFBFBF; font-size: 11px; }
.proc-cpu, .proc-mem { color: #BFBFBF; }

entry {
  background: #343746;
  border: 1px solid #44475A;
  border-radius: 8px;
  padding: 4px 8px;
  box-shadow: none;
  color: #F8F8F2;
}
entry:focus { border-color: #BD93F9; }

.notification {
  padding: 8px 8px 8px 10px;
  border-radius: 10px;
  background: #343746;
  border-left: 3px solid transparent;
}
.notification.hover { background: #3C3F51; }
.notification.critical { border-left-color: #FF5555; }
.notification-app { color: #BD93F9; font-size: 10px; font-weight: bold; }
.notification-time { color: #6272A4; font-size: 10px; }
.notification-body { color: #BFBFBF; font-size: 11px; }
button.plain label { color: #BFBFBF; }

button.tile {
  background: #343746;
  border-radius: 12px;
  padding: 14px 6px 10px 6px;
}
button.tile:hover { background: #44475A; }
button.tile.danger:hover .tile-icon { color: #FF5555; }
button.tile.armed, button.tile.armed:hover { background: #FF5555; }
button.tile.armed label { color: #282A36; }
.tile-icon { font-size: 22px; color: #BD93F9; }
.tile-label { font-size: 11px; color: #BFBFBF; }
"""


class Throttle:
    """Runs only the latest requested command, one at a time per control."""

    def __init__(self):
        self.running = False
        self.pending = None

    def run(self, *argv):
        self.pending = [str(a) for a in argv]
        if not self.running:
            self._next()

    def _next(self, *_):
        argv, self.pending = self.pending, None
        self.running = argv is not None
        if argv is None:
            return
        flags = (
            GLib.SpawnFlags.SEARCH_PATH
            | GLib.SpawnFlags.DO_NOT_REAP_CHILD
            | GLib.SpawnFlags.STDOUT_TO_DEV_NULL
            | GLib.SpawnFlags.STDERR_TO_DEV_NULL
        )
        pid, *_ = GLib.spawn_async(argv, flags=flags)
        GLib.child_watch_add(GLib.PRIORITY_DEFAULT, pid, self._next)


def run(*argv):
    return subprocess.run(argv, capture_output=True, text=True).stdout


def pactl_json(*args):
    try:
        return json.loads(run("pactl", "-f", "json", *args))
    except json.JSONDecodeError:
        return [] if args[0] == "list" else {}


def spawn(*argv):
    subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def volume_percent(entry):
    channels = entry.get("volume", {}).values()
    return max((int(c["value_percent"].rstrip("%")) for c in channels), default=0)


def icon_label(text, *classes):
    label = Gtk.Label(label=text)
    for c in classes:
        label.get_style_context().add_class(c)
    return label


def title(text, first=False):
    label = icon_label(text.upper(), "section-title", *(["first"] if first else []))
    label.set_xalign(0)
    return label


class SliderRow(Gtk.Box):
    """[icon/mute button] [=====o----] [42%]"""

    def __init__(self, icons, on_change, on_icon=None, css_class=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.icons = icons
        self.on_change = on_change
        self.muted = False
        self.dragging = False
        self.touched = 0.0

        self.button = Gtk.Button()
        self.button.get_style_context().add_class("icon")
        self.button.add(Gtk.Label())
        if on_icon:
            self.button.connect("clicked", lambda *_: on_icon())
        else:
            self.button.set_sensitive(False)
        self.pack_start(self.button, False, False, 0)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale.set_draw_value(False)
        self.scale.set_hexpand(True)
        if css_class:
            self.scale.get_style_context().add_class(css_class)
        self.handler = self.scale.connect("value-changed", self._changed)
        self.scale.connect("button-press-event", self._press)
        self.scale.connect("button-release-event", self._release)
        self.pack_start(self.scale, True, True, 0)

        self.percent = icon_label("", "percent")
        self.percent.set_xalign(1)
        self.pack_start(self.percent, False, False, 0)

    def _press(self, *_):
        self.dragging = True

    def _release(self, *_):
        self.dragging = False
        self.touched = time.monotonic()

    def _changed(self, scale):
        self.touched = time.monotonic()
        value = int(scale.get_value())
        self._render(value)
        self.on_change(value)

    def _render(self, value):
        self.percent.set_text(f"{value}%")
        icon = self.icons[-1] if self.muted else self.icons[min(value * (len(self.icons) - 1) // 101, len(self.icons) - 2)]
        self.button.get_child().set_text(icon)
        ctx = self.button.get_style_context()
        scale_ctx = self.scale.get_style_context()
        for c in (ctx, scale_ctx):
            (c.add_class if self.muted else c.remove_class)("muted")

    def update(self, value, muted=False, force=False):
        self.muted = muted
        busy = self.dragging or time.monotonic() - self.touched < SETTLE_SECONDS
        if force or not busy:
            with self.scale.handler_block(self.handler):
                self.scale.set_value(value)
        self._render(int(self.scale.get_value()))


VOLUME_ICONS = ["󰕿", "󰖀", "󰕾", "󰝟"]
MIC_ICONS = ["󰍬", "󰍬", "󰍭"]
BRIGHTNESS_ICONS = ["󰃞", "󰃟", "󰃝", "󰃠", "󰃠"]
CHEVRON_DOWN, CHEVRON_UP, CHECK = "\uf078", "\uf077", "\U000f012c"


class DevicePicker(Gtk.Box):
    """Current device as a button; expands into a list to pick the default one."""

    def __init__(self, icon, on_select):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.on_select = on_select
        self.devices = []
        self.default = None

        self.header = Gtk.Button()
        self.header.get_style_context().add_class("device")
        box = Gtk.Box(spacing=8)
        box.pack_start(icon_label(icon), False, False, 0)
        self.current = Gtk.Label(xalign=0)
        self.current.set_ellipsize(Pango.EllipsizeMode.END)
        box.pack_start(self.current, True, True, 0)
        self.chevron = icon_label(CHEVRON_DOWN, "dim")
        box.pack_start(self.chevron, False, False, 0)
        self.header.add(box)
        self.header.connect("clicked", self._toggle)
        self.pack_start(self.header, False, False, 0)

        self.revealer = Gtk.Revealer()
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.revealer.set_transition_duration(150)
        self.list = Gtk.ListBox()
        self.list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list.connect("row-activated", self._activated)
        self.revealer.add(self.list)
        self.pack_start(self.revealer, False, False, 0)

    def _toggle(self, *_):
        expanded = not self.revealer.get_reveal_child()
        self.revealer.set_reveal_child(expanded)
        self.chevron.set_text(CHEVRON_UP if expanded else CHEVRON_DOWN)

    def _activated(self, _, row):
        self.on_select(self.devices[row.get_index()][0])
        self._toggle()

    def update(self, devices, default):
        """devices: [(name, description)]"""
        self.current.set_text(next((d for n, d in devices if n == default), "No device"))
        self.header.set_tooltip_text(self.current.get_text())
        if devices == self.devices and self.default == default:
            return
        self.devices, self.default = devices, default
        for row in self.list.get_children():
            self.list.remove(row)
        for name, description in devices:
            box = Gtk.Box(spacing=8)
            box.get_style_context().add_class("device-row")
            selected = name == default
            if selected:
                box.get_style_context().add_class("selected")
            box.pack_start(icon_label(CHECK if selected else " "), False, False, 0)
            label = Gtk.Label(label=description, xalign=0)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            box.pack_start(label, True, True, 0)
            self.list.add(box)
        self.list.show_all()


class MixerRow(Gtk.Box):
    """Per-application stream: icon, name, media title and a volume slider."""

    def __init__(self, index):
        super().__init__(spacing=10)
        self.index = index
        self.throttle = Throttle()

        self.icon = Gtk.Image()
        self.icon.set_valign(Gtk.Align.CENTER)
        self.pack_start(self.icon, False, False, 2)

        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        names = Gtk.Box(spacing=6)
        self.name = icon_label("", "app-name")
        self.name.set_xalign(0)
        self.media = icon_label("", "app-media")
        self.media.set_xalign(0)
        self.media.set_ellipsize(Pango.EllipsizeMode.END)
        names.pack_start(self.name, False, False, 0)
        names.pack_start(self.media, True, True, 0)
        column.pack_start(names, False, False, 0)
        self.slider = SliderRow(
            VOLUME_ICONS,
            lambda v: self.throttle.run("pactl", "set-sink-input-volume", self.index, f"{v}%"),
            lambda: spawn("pactl", "set-sink-input-mute", str(self.index), "toggle"),
        )
        column.pack_start(self.slider, False, False, 0)
        self.pack_start(column, True, True, 0)

    def update(self, stream):
        props = stream.get("properties", {})
        app = props.get("application.name") or props.get("application.process.binary") or "Unknown"
        media = props.get("media.name", "")
        self.name.set_text(app)
        self.media.set_text("" if media == app else media)
        self.set_tooltip_text(f"{app}: {media}" if media and media != app else app)
        theme = Gtk.IconTheme.get_default()
        candidates = [
            props.get("application.icon_name"),
            props.get("application.process.binary"),
            app.lower().replace(" ", "-"),
            "audio-x-generic",
        ]
        icon = next(c for c in candidates if c and theme.has_icon(c))
        self.icon.set_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR)
        self.slider.update(min(volume_percent(stream), 100), stream.get("mute", False))


class Popup:
    """A card anchored above the bar's right end, closed by Escape or clicking outside."""

    def __init__(self, output=None):
        self.catchers = []
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
        self.monitor = self._find_monitor(output)
        self._make_catchers()
        self.window = self._make_window()
        self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.card.get_style_context().add_class("card")
        self.card.set_size_request(380, -1)
        self.window.add(self.card)
        self.closing = False

    def show(self):
        self.window.show_all()
        # show_all() also reveals widgets that refresh() hid, so apply visibility again
        self.refresh()

    def refresh(self):
        pass

    def dismiss(self):
        """Fade/slide out (see .card.closing in CSS), then quit."""
        if self.closing:
            return
        self.closing = True
        self.card.get_style_context().add_class("closing")
        GLib.timeout_add(130, Gtk.main_quit)

    def close(self):
        pass

    def _find_monitor(self, output):
        """Map a sway output name to a GdkMonitor (GTK3 has no connector names)."""
        if not output:
            return None
        try:
            outputs = json.loads(run("swaymsg", "-t", "get_outputs", "-r"))
            rect = next(o["rect"] for o in outputs if o["name"] == output)
        except (json.JSONDecodeError, StopIteration):
            return None
        display = Gdk.Display.get_default()
        for i in range(display.get_n_monitors()):
            monitor = display.get_monitor(i)
            g = monitor.get_geometry()
            if (g.x, g.y, g.width, g.height) == (rect["x"], rect["y"], rect["width"], rect["height"]):
                return monitor
        return None

    def _layer_window(self, css_class, layer):
        window = Gtk.Window()
        window.get_style_context().add_class(css_class)
        visual = window.get_screen().get_rgba_visual()
        if visual:
            window.set_visual(visual)
        window.set_app_paintable(True)
        GtkLayerShell.init_for_window(window)
        GtkLayerShell.set_namespace(window, "control-center")
        GtkLayerShell.set_layer(window, layer)
        return window

    def _make_catchers(self):
        """Invisible full-screen surfaces under the popup: clicking outside closes it."""
        display = Gdk.Display.get_default()
        for i in range(display.get_n_monitors()):
            catcher = self._layer_window("catcher", GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_monitor(catcher, display.get_monitor(i))
            for edge in GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT, GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM:
                GtkLayerShell.set_anchor(catcher, edge, True)
            GtkLayerShell.set_exclusive_zone(catcher, -1)
            catcher.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            catcher.connect("button-press-event", lambda *_: self.dismiss())
            catcher.show_all()
            self.catchers.append(catcher)

    def _make_window(self):
        window = self._layer_window("popup", GtkLayerShell.Layer.OVERLAY)
        if self.monitor:
            GtkLayerShell.set_monitor(window, self.monitor)
        GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_margin(window, GtkLayerShell.Edge.RIGHT, 6)
        GtkLayerShell.set_keyboard_mode(window, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        window.connect("key-press-event", self._key)
        window.connect("destroy", Gtk.main_quit)
        return window

    def _key(self, _, event):
        if event.keyval == Gdk.KEY_Escape:
            self.dismiss()


class AudioPopup(Popup):
    """Output device, volume, per-app mixer and microphone."""

    def __init__(self, output=None):
        super().__init__(output)
        self.mixer_rows = {}
        self.refresh_source = None
        self.sink_throttle = Throttle()
        self.source_throttle = Throttle()
        card = self.card

        # Output
        card.pack_start(title("Output", first=True), False, False, 0)
        self.sink_picker = DevicePicker("󰓃", lambda name: spawn("pactl", "set-default-sink", name))
        card.pack_start(self.sink_picker, False, False, 0)
        self.sink_slider = SliderRow(
            VOLUME_ICONS,
            lambda v: self.sink_throttle.run("pactl", "set-sink-volume", self.default_sink, f"{v}%"),
            lambda: spawn("pactl", "set-sink-mute", self.default_sink, "toggle"),
        )
        card.pack_start(self.sink_slider, False, False, 0)

        # Applications
        card.pack_start(title("Applications"), False, False, 0)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_propagate_natural_height(True)
        scroller.set_max_content_height(300)
        self.mixer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.mixer_empty = icon_label("Nothing is playing", "empty")
        self.mixer_empty.set_xalign(0)
        self.mixer_empty.set_no_show_all(True)
        self.mixer.pack_start(self.mixer_empty, False, False, 0)
        scroller.add(self.mixer)
        card.pack_start(scroller, False, False, 0)

        # Microphone
        self.mic_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.mic_box.set_no_show_all(True)
        self.mic_box.pack_start(title("Microphone"), False, False, 0)
        self.source_picker = DevicePicker("󰍬", lambda name: spawn("pactl", "set-default-source", name))
        self.mic_box.pack_start(self.source_picker, False, False, 0)
        self.source_slider = SliderRow(
            MIC_ICONS,
            lambda v: self.source_throttle.run("pactl", "set-source-volume", self.default_source, f"{v}%"),
            lambda: spawn("pactl", "set-source-mute", self.default_source, "toggle"),
        )
        self.mic_box.pack_start(self.source_slider, False, False, 0)
        for child in self.mic_box.get_children():
            child.show_all()
        card.pack_start(self.mic_box, False, False, 0)

        self._subscribe()

    def _subscribe(self):
        """Live updates (volume keys, apps starting/stopping, devices appearing)."""
        self.subscription = subprocess.Popen(
            ["pactl", "subscribe"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        GLib.unix_fd_add_full(
            GLib.PRIORITY_DEFAULT,
            self.subscription.stdout.fileno(),
            GLib.IOCondition.IN | GLib.IOCondition.HUP,
            self._on_event,
        )

    def _on_event(self, fd, condition):
        if not os.read(fd, 65536):
            return False
        if self.refresh_source is None:
            self.refresh_source = GLib.timeout_add(60, self._debounced_refresh)
        return True

    def _debounced_refresh(self):
        self.refresh_source = None
        self.refresh()
        return False

    def refresh(self):
        info = pactl_json("info")
        self.default_sink = info.get("default_sink_name", "@DEFAULT_SINK@")
        self.default_source = info.get("default_source_name", "@DEFAULT_SOURCE@")

        sinks = pactl_json("list", "sinks")
        self.sink_picker.update([(s["name"], s["description"]) for s in sinks], self.default_sink)
        sink = next((s for s in sinks if s["name"] == self.default_sink), None)
        if sink:
            self.sink_slider.update(min(volume_percent(sink), 100), sink["mute"])

        sources = [
            s for s in pactl_json("list", "sources")
            if s.get("properties", {}).get("device.class") != "monitor" and not s["name"].endswith(".monitor")
        ]
        self.source_picker.update([(s["name"], s["description"]) for s in sources], self.default_source)
        source = next((s for s in sources if s["name"] == self.default_source), None)
        if source:
            self.source_slider.update(min(volume_percent(source), 100), source["mute"])
        self.mic_box.set_visible(bool(sources))

        streams = {s["index"]: s for s in pactl_json("list", "sink-inputs")}
        for index in list(self.mixer_rows):
            if index not in streams:
                self.mixer.remove(self.mixer_rows.pop(index))
        for index, stream in streams.items():
            if index not in self.mixer_rows:
                row = MixerRow(index)
                self.mixer_rows[index] = row
                self.mixer.pack_start(row, False, False, 0)
                row.show_all()
            self.mixer_rows[index].update(stream)
        self.mixer_empty.set_visible(not self.mixer_rows)

    def close(self):
        self.subscription.terminate()


class BrightnessPopup(Popup):
    """A slider per display, optionally linked so they move together."""

    def __init__(self, output=None):
        super().__init__(output)
        self.throttle = Throttle()

        header = Gtk.Box(spacing=2)
        header.pack_start(title("Brightness", first=True), True, True, 0)
        self.reload_button = Gtk.Button()
        self.reload_button.add(Gtk.Label(label="󰑐"))
        self.reload_button.set_tooltip_text("Re-read values from the displays")
        self.reload_button.connect("clicked", self._reload)
        header.pack_start(self.reload_button, False, False, 0)
        self.link_button = Gtk.Button()
        self.link_button.get_style_context().add_class("toggle")
        self.link_button.add(Gtk.Label())
        self.link_button.connect("clicked", self._toggle_link)
        header.pack_start(self.link_button, False, False, 0)
        self.card.pack_start(header, False, False, 0)

        self.rows_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.card.pack_start(self.rows_box, False, False, 0)

    def refresh(self):
        self.linked = run(BRIGHTNESS, "link").strip() == "1"
        displays = []
        for line in run(BRIGHTNESS, "list").splitlines():
            ident, _output, label, value = (line.split("\t") + [""] * 4)[:4]
            if value.isdigit():
                displays.append((ident, label, int(value)))

        for child in self.rows_box.get_children():
            self.rows_box.remove(child)
        self.rows = {}
        if not displays:
            empty = icon_label("No controllable displays", "empty")
            empty.set_xalign(0)
            self.rows_box.pack_start(empty, False, False, 0)
        for ident, label, value in displays:
            name = icon_label(label, "dim")
            name.set_xalign(0)
            name.set_margin_start(32)
            self.rows_box.pack_start(name, False, False, 0)
            row = SliderRow(BRIGHTNESS_ICONS, lambda v, i=ident: self._set(i, v), css_class="brightness")
            row.update(value, force=True)
            self.rows[ident] = row
            self.rows_box.pack_start(row, False, False, 0)
        self.rows_box.show_all()
        self.link_button.set_no_show_all(len(displays) < 2)
        self.link_button.set_visible(len(displays) > 1)
        self._render_link()

    def _set(self, ident, value):
        if self.linked:
            for other, row in self.rows.items():
                if other != ident:
                    row.update(value, force=True)
        self.throttle.run(BRIGHTNESS, "set", value, "all" if self.linked else ident)

    def _reload(self, *_):
        """DDC reads are slow: re-read in the background, then rebuild the sliders."""
        self.reload_button.set_sensitive(False)
        flags = GLib.SpawnFlags.DO_NOT_REAP_CHILD | GLib.SpawnFlags.STDOUT_TO_DEV_NULL | GLib.SpawnFlags.STDERR_TO_DEV_NULL
        pid, *_ = GLib.spawn_async([BRIGHTNESS, "refresh"], flags=flags)

        def done(*_):
            self.refresh()
            self.reload_button.set_sensitive(True)

        GLib.child_watch_add(GLib.PRIORITY_DEFAULT, pid, done)

    def _toggle_link(self, *_):
        self.linked = run(BRIGHTNESS, "link", "toggle").strip() == "1"
        self._render_link()

    def _render_link(self):
        self.link_button.get_child().set_text("󰌹  Linked" if self.linked else "󰌺  Separate")
        ctx = self.link_button.get_style_context()
        (ctx.add_class if self.linked else ctx.remove_class)("active")
        self.link_button.set_tooltip_text(
            "Sliders move together" if self.linked else "Each display has its own slider"
        )


GLYPHS = {
    "ethernet": "\U000f0200",
    "wifi": ["\U000f092f", "\U000f091f", "\U000f0922", "\U000f0925", "\U000f0928"],
    "wifi-off": "\U000f092e",
    "lock": "\U000f033e",
    "vpn": "\U000f0582",
    "down": "\U000f01da",
    "up": "\U000f0552",
    "close": "\U000f0156",
    "refresh": "\U000f0450",
    "settings": "\U000f0493",
    "open": "\U000f03cc",
    "cpu": "\U000f0ee0",
    "temp": "\U000f050f",
    "memory": "\U000f035b",
    "disk": "\U000f02ca",
    "bluetooth": "\U000f00af",
    "bluetooth-off": "\U000f00b2",
    "battery": "\U000f0079",
    "bell": "\U000f009a",
    "bell-off": "\U000f009b",
}

# org.bluez Device1.Icon -> glyph
BLUETOOTH_ICONS = {
    "audio-headset": "\U000f02ce",
    "audio-headphones": "\U000f02cb",
    "audio-card": "\U000f04c3",
    "input-mouse": "\U000f037d",
    "input-keyboard": "\U000f030c",
    "input-gaming": "\U000f02b4",
    "input-tablet": "\U000f04f7",
    "phone": "\U000f03f2",
    "computer": "\U000f07c0",
}


def run_async(argv, done=None):
    """Run a command in a thread; call done(returncode, output) on the main loop."""

    def worker():
        proc = subprocess.run(argv, capture_output=True, text=True)
        if done:
            GLib.idle_add(done, proc.returncode, (proc.stdout + proc.stderr).strip())

    threading.Thread(target=worker, daemon=True).start()


def human_bytes(n, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti"):
        if abs(n) < 1024 or unit == "Ti":
            return f"{n:.0f} {unit}{suffix}" if unit == "" else f"{n:.1f} {unit}{suffix}"
        n /= 1024


def flat_button(text, on_click, *classes, tooltip=None):
    button = Gtk.Button()
    button.add(Gtk.Label(label=text))
    for c in classes:
        button.get_style_context().add_class(c)
    if tooltip:
        button.set_tooltip_text(tooltip)
    button.connect("clicked", lambda *_: on_click())
    return button


def header(text, *widgets, first=True):
    box = Gtk.Box(spacing=6)
    box.pack_start(title(text, first=first), True, True, 0)
    for widget in widgets:
        widget.set_valign(Gtk.Align.CENTER)
        box.pack_start(widget, False, False, 0)
    return box


def footer(text, on_click):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.pack_start(Gtk.Separator(), False, False, 0)
    button = flat_button(text, on_click, "footer")
    button.get_child().set_xalign(0)
    box.pack_start(button, False, False, 0)
    return box


def set_state_class(widget, value, warning, critical):
    ctx = widget.get_style_context()
    ctx.remove_class("warning")
    ctx.remove_class("critical")
    if value >= critical:
        ctx.add_class("critical")
    elif value >= warning:
        ctx.add_class("warning")


def meter(vertical=False):
    bar = Gtk.LevelBar()
    bar.set_min_value(0)
    bar.set_max_value(1)
    for name in (Gtk.LEVEL_BAR_OFFSET_LOW, Gtk.LEVEL_BAR_OFFSET_HIGH, Gtk.LEVEL_BAR_OFFSET_FULL):
        bar.remove_offset_value(name)
    if vertical:
        bar.set_orientation(Gtk.Orientation.VERTICAL)
        bar.set_inverted(True)
    return bar


class ListRow(Gtk.Box):
    """[icon] title / subtitle [trailing widgets]"""

    def __init__(self, icon, text, subtitle="", *trailing, css_class=None):
        super().__init__(spacing=10)
        self.get_style_context().add_class("list-row")
        if css_class:
            self.get_style_context().add_class(css_class)
        glyph = icon_label(icon, "row-icon")
        glyph.set_valign(Gtk.Align.CENTER)
        self.pack_start(glyph, False, False, 0)
        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        column.set_valign(Gtk.Align.CENTER)
        name = icon_label(text, "row-title")
        name.set_xalign(0)
        name.set_ellipsize(Pango.EllipsizeMode.END)
        column.pack_start(name, False, False, 0)
        if subtitle:
            sub = icon_label(subtitle, "row-subtitle")
            sub.set_xalign(0)
            sub.set_ellipsize(Pango.EllipsizeMode.END)
            column.pack_start(sub, False, False, 0)
        self.pack_start(column, True, True, 0)
        for widget in trailing:
            widget.set_valign(Gtk.Align.CENTER)
            self.pack_start(widget, False, False, 0)


class Sparkline(Gtk.DrawingArea):
    """Filled line graph of the last N samples, one series per color."""

    def __init__(self, colors, height=44, samples=60, maximum=None):
        super().__init__()
        self.colors = colors
        self.maximum = maximum
        self.series = [deque([0.0] * samples, maxlen=samples) for _ in colors]
        self.set_size_request(-1, height)
        self.connect("draw", self._draw)

    def push(self, *values):
        for series, value in zip(self.series, values):
            series.append(value)
        self.queue_draw()

    def _draw(self, widget, cr):
        width, height = widget.get_allocated_width(), widget.get_allocated_height()
        radius = 8
        cr.new_sub_path()
        cr.arc(width - radius, radius, radius, -math.pi / 2, 0)
        cr.arc(width - radius, height - radius, radius, 0, math.pi / 2)
        cr.arc(radius, height - radius, radius, math.pi / 2, math.pi)
        cr.arc(radius, radius, radius, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.set_source_rgb(0x34 / 255, 0x37 / 255, 0x46 / 255)
        cr.fill_preserve()
        cr.clip()

        top = self.maximum or max(max(max(s) for s in self.series), 1)
        for series, color in zip(self.series, self.colors):
            r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
            step = width / (len(series) - 1)
            points = [(i * step, height - 3 - v / top * (height - 8)) for i, v in enumerate(series)]
            cr.move_to(0, height)
            for x, y in points:
                cr.line_to(x, y)
            cr.line_to(width, height)
            cr.close_path()
            cr.set_source_rgba(r, g, b, 0.18)
            cr.fill()
            cr.move_to(*points[0])
            for x, y in points[1:]:
                cr.line_to(x, y)
            cr.set_source_rgba(r, g, b, 0.95)
            cr.set_line_width(1.5)
            cr.stroke()


# Network ----------------------------------------------------------------------


def nmcli_rows(*args):
    """nmcli terse output split into fields (':' is escaped as '\\:' inside values)."""
    out = run("nmcli", "-t", *args)
    return [
        [field.replace("\\:", ":").replace("\\\\", "\\") for field in re.split(r"(?<!\\):", line)]
        for line in out.splitlines()
    ]


def wifi_icon(signal_strength):
    icons = GLYPHS["wifi"]
    return icons[min(int(signal_strength or 0) * len(icons) // 101, len(icons) - 1)]


class NetworkPopup(Popup):
    """Active connections with live traffic, VPN toggles and Wi-Fi networks."""

    def __init__(self, output=None):
        super().__init__(output)
        self.state = {}
        self.counters = None
        self.primary = None
        self.password_for = None

        self.wifi_switch = Gtk.Switch()
        self.wifi_switch.set_no_show_all(True)
        self.wifi_handler = self.wifi_switch.connect("notify::active", self._toggle_wifi)
        self.card.pack_start(header("Network", self.wifi_switch), False, False, 0)

        self.connections = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.card.pack_start(self.connections, False, False, 0)

        traffic = Gtk.Box(spacing=12)
        self.rx_label = icon_label("", "traffic-rx")
        self.tx_label = icon_label("", "traffic-tx")
        traffic.pack_start(self.rx_label, False, False, 2)
        traffic.pack_start(self.tx_label, False, False, 0)
        self.card.pack_start(traffic, False, False, 2)
        self.graph = Sparkline(["#8BE9FD", "#FF79C6"], height=40)
        self.card.pack_start(self.graph, False, False, 2)

        self.vpn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.card.pack_start(self.vpn_box, False, False, 0)

        self.wifi_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.wifi_box.set_no_show_all(True)
        rescan = flat_button(GLYPHS["refresh"], self._rescan, tooltip="Scan for networks")
        self.wifi_box.pack_start(header("Wi-Fi", rescan, first=False), False, False, 0)
        self.wifi_list = Gtk.ListBox()
        self.wifi_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.wifi_list.connect("row-activated", self._wifi_activated)
        self.wifi_box.pack_start(self.wifi_list, False, False, 0)
        self.password_revealer = Gtk.Revealer()
        password_row = Gtk.Box(spacing=6)
        self.password = Gtk.Entry()
        self.password.set_visibility(False)
        self.password.set_placeholder_text("Password")
        self.password.connect("activate", lambda *_: self._connect_with_password())
        password_row.pack_start(self.password, True, True, 0)
        password_row.pack_start(flat_button("Connect", self._connect_with_password, "accent"), False, False, 0)
        self.password_revealer.add(password_row)
        self.wifi_box.pack_start(self.password_revealer, False, False, 4)
        for child in self.wifi_box.get_children():
            child.show_all()
        self.card.pack_start(self.wifi_box, False, False, 0)

        self.status = icon_label("", "status")
        self.status.set_xalign(0)
        self.status.set_line_wrap(True)
        self.status.set_no_show_all(True)
        self.card.pack_start(self.status, False, False, 0)

        editor = "nm-connection-editor" if GLib.find_program_in_path("nm-connection-editor") else None
        self.card.pack_start(
            footer(
                f"{GLYPHS['settings']}  Connection settings",
                lambda: self._launch([editor] if editor else ["alacritty", "--class", "popup", "-e", "nmtui"]),
            ),
            False, False, 0,
        )

        self.refresh()
        self._sample_traffic()
        self.ticks = 0
        GLib.timeout_add(1000, self._tick)

    def _launch(self, argv):
        spawn(*argv)
        self.dismiss()

    def _tick(self):
        self._sample_traffic()
        self.ticks += 1
        if self.ticks % 3 == 0:
            self.refresh()
        return True

    def _sample_traffic(self):
        if not self.primary:
            self.rx_label.set_text(f"{GLYPHS['down']} —")
            self.tx_label.set_text(f"{GLYPHS['up']} —")
            return
        base = Path("/sys/class/net") / self.primary / "statistics"
        try:
            now = (time.monotonic(), int((base / "rx_bytes").read_text()), int((base / "tx_bytes").read_text()))
        except OSError:
            return
        if self.counters and self.counters[0] != self.primary:
            self.counters = None
        if self.counters:
            _, (t0, rx0, tx0) = self.counters
            dt = max(now[0] - t0, 1e-3)
            rx, tx = (now[1] - rx0) / dt, (now[2] - tx0) / dt
            self.rx_label.set_text(f"{GLYPHS['down']} {human_bytes(rx)}/s")
            self.tx_label.set_text(f"{GLYPHS['up']} {human_bytes(tx)}/s")
            self.graph.push(rx, tx)
        self.counters = (self.primary, now)

    def refresh(self):
        devices = nmcli_rows("-f", "DEVICE,TYPE,STATE,CONNECTION", "device")
        connected = [d for d in devices if len(d) == 4 and d[1] in ("ethernet", "wifi") and d[2] == "connected"]
        has_wifi = any(d[1] == "wifi" for d in devices if len(d) == 4)
        wifi_on = run("nmcli", "radio", "wifi").strip() == "enabled"
        self.primary = connected[0][0] if connected else None

        details = []
        for device, kind, _, connection in connected:
            info = dict(
                (row[0], row[1]) for row in nmcli_rows("-f", "IP4.ADDRESS", "device", "show", device)
                if len(row) == 2
            )
            ip = info.get("IP4.ADDRESS[1]", "")
            speed = ""
            try:
                mbps = int((Path("/sys/class/net") / device / "speed").read_text())
                speed = f"{mbps} Mb/s" if mbps > 0 else ""
            except (OSError, ValueError):
                pass
            details.append((device, kind, connection, ip, speed))

        networks = []
        if has_wifi and wifi_on:
            seen = {}
            for row in nmcli_rows("-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "no"):
                if len(row) != 4 or not row[1]:
                    continue
                in_use, ssid, strength, security = row[0] == "*", row[1], int(row[2] or 0), row[3]
                if ssid not in seen or strength > seen[ssid][1] or in_use:
                    seen[ssid] = (in_use or seen.get(ssid, (False,))[0], strength, security)
            networks = sorted(((s, *v) for s, v in seen.items()), key=lambda n: (not n[1], -n[2]))[:12]

        saved = nmcli_rows("-f", "NAME,TYPE,ACTIVE", "connection", "show")
        known = {row[0] for row in saved if len(row) == 3 and row[1] == "802-11-wireless"}
        vpns = [(row[0], row[2] == "yes") for row in saved if len(row) == 3 and row[1] in ("vpn", "wireguard")]

        state = {"details": details, "networks": networks, "known": known, "vpns": vpns, "wifi": (has_wifi, wifi_on)}
        if state == self.state:
            return
        self.state = state
        self.known = known

        for child in self.connections.get_children():
            self.connections.remove(child)
        if not details:
            empty = icon_label(f"{GLYPHS['wifi-off']}  Not connected", "empty")
            empty.set_xalign(0)
            self.connections.pack_start(empty, False, False, 0)
        for device, kind, connection, ip, speed in details:
            if kind == "wifi":
                strength = next((n[2] for n in networks if n[1]), 100)
                icon = wifi_icon(strength)
                trailing = [flat_button(GLYPHS["close"], lambda d=device: self._run(["nmcli", "device", "disconnect", d]),
                                        tooltip="Disconnect")]
            else:
                icon, trailing = GLYPHS["ethernet"], []
            subtitle = " · ".join(x for x in (device, ip, speed) if x)
            self.connections.pack_start(ListRow(icon, connection, subtitle, *trailing, css_class="active"), False, False, 0)
        self.connections.show_all()

        for child in self.vpn_box.get_children():
            self.vpn_box.remove(child)
        if vpns:
            self.vpn_box.pack_start(header("VPN", first=False), False, False, 0)
            for name, active in vpns:
                switch = Gtk.Switch(active=active)
                switch.connect("notify::active", lambda s, _, n=name: self._run(
                    ["nmcli", "connection", "up" if s.get_active() else "down", "id", n]))
                self.vpn_box.pack_start(ListRow(GLYPHS["vpn"], name, "", switch), False, False, 0)
        self.vpn_box.show_all()

        with self.wifi_switch.handler_block(self.wifi_handler):
            self.wifi_switch.set_active(wifi_on)
        self.wifi_switch.set_visible(has_wifi)
        self.wifi_box.set_visible(has_wifi and wifi_on)
        for row in self.wifi_list.get_children():
            self.wifi_list.remove(row)
        self.networks = networks
        for ssid, in_use, strength, security in networks:
            secured = security not in ("", "--")
            subtitle = "Connected" if in_use else ("Saved" if ssid in known else (security if secured else "Open"))
            trailing = [icon_label(GLYPHS["lock"], "dim")] if secured else []
            self.wifi_list.add(ListRow(wifi_icon(strength), ssid, subtitle, *trailing,
                                       css_class="active" if in_use else None))
        self.wifi_list.show_all()

    def _set_status(self, text):
        self.status.set_text(text)
        self.status.set_visible(bool(text))

    def _run(self, argv, message=None):
        if message:
            self._set_status(message)

        def done(code, output):
            self._set_status("" if code == 0 else output.splitlines()[-1] if output else "Failed")
            self.state = {}
            self.refresh()

        run_async(argv, done)

    def _toggle_wifi(self, switch, _):
        self._run(["nmcli", "radio", "wifi", "on" if switch.get_active() else "off"])

    def _rescan(self):
        self._set_status("Scanning…")
        run_async(["nmcli", "device", "wifi", "rescan"],
                  lambda *_: GLib.timeout_add(2500, lambda: (self._set_status(""), self.refresh(), False)[-1]))

    def _wifi_activated(self, _, row):
        ssid, in_use, _, security = self.networks[row.get_index()]
        if in_use:
            return
        if ssid in self.known:
            self._run(["nmcli", "connection", "up", "id", ssid], f"Connecting to {ssid}…")
        elif security in ("", "--"):
            self._run(["nmcli", "device", "wifi", "connect", ssid], f"Connecting to {ssid}…")
        else:
            self.password_for = ssid
            self.password.set_placeholder_text(f"Password for {ssid}")
            self.password_revealer.set_reveal_child(True)
            self.password.grab_focus()

    def _connect_with_password(self):
        if not self.password_for:
            return
        ssid, secret = self.password_for, self.password.get_text()
        self.password.set_text("")
        self.password_revealer.set_reveal_child(False)
        self.password_for = None
        self._run(["nmcli", "device", "wifi", "connect", ssid, "password", secret], f"Connecting to {ssid}…")


# Performance ------------------------------------------------------------------


def process_times():
    """{name: (cpu ticks, rss bytes, count)} summed over processes with the same name."""
    page = os.sysconf("SC_PAGE_SIZE")
    result = {}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            data = Path(f"/proc/{pid}/stat").read_text()
        except OSError:
            continue
        name = data[data.index("(") + 1:data.rindex(")")]
        fields = data[data.rindex(")") + 2:].split()
        ticks, rss, count = result.get(name, (0, 0, 0))
        result[name] = (ticks + int(fields[11]) + int(fields[12]), rss + int(fields[21]) * page, count + 1)
    return result


def mounted_disks():
    """Real block-device filesystems, one mountpoint per device (btrfs subvolumes repeat)."""
    disks = {}
    for line in Path("/proc/mounts").read_text().splitlines():
        source, target = line.split()[:2]
        target = target.replace("\\040", " ")
        if source.startswith("/dev/") and (source not in disks or len(target) < len(disks[source])):
            disks[source] = target
    return sorted(disks.values(), key=lambda t: (t != "/", t))


class PerformancePopup(Popup):
    """CPU graph and cores, memory, disks and the busiest processes."""

    def __init__(self, output=None):
        super().__init__(output)
        self.clock_ticks = os.sysconf("SC_CLK_TCK")
        self.sensor = temperature_sensor()
        monitor = "btop" if GLib.find_program_in_path("btop") else "htop"

        self.card.pack_start(header("Processor"), False, False, 0)
        summary = Gtk.Box(spacing=10)
        self.cpu_label = icon_label("", "big")
        summary.pack_start(self.cpu_label, False, False, 2)
        self.cpu_details = icon_label("", "dim")
        self.cpu_details.set_xalign(0)
        self.cpu_details.set_ellipsize(Pango.EllipsizeMode.END)
        summary.pack_start(self.cpu_details, True, True, 0)
        self.card.pack_start(summary, False, False, 0)
        self.graph = Sparkline(["#BD93F9"], height=48, maximum=100)
        self.card.pack_start(self.graph, False, False, 4)
        cores = Gtk.Box(spacing=3, homogeneous=True)
        self.core_bars = []
        for _ in cpu_times()[1:]:
            bar = meter(vertical=True)
            self.core_bars.append(bar)
            cores.pack_start(bar, True, True, 0)
        self.card.pack_start(cores, False, False, 2)

        self.card.pack_start(title("Memory"), False, False, 0)
        self.memory_rows = {}
        for key, name in (("ram", "RAM"), ("swap", "Swap")):
            self.memory_rows[key] = self._usage_row(name)

        self.card.pack_start(title("Disks"), False, False, 0)
        self.disk_rows = {mount: self._usage_row(mount) for mount in mounted_disks()}

        self.card.pack_start(title("Top processes"), False, False, 0)
        self.processes = Gtk.Grid(column_spacing=12, row_spacing=2)
        self.process_labels = []
        for i in range(6):
            labels = [icon_label("", "proc-name"), icon_label("", "proc-cpu"), icon_label("", "proc-mem")]
            labels[0].set_xalign(0)
            labels[0].set_hexpand(True)
            labels[0].set_ellipsize(Pango.EllipsizeMode.END)
            for column, label in enumerate(labels):
                if column:
                    label.set_xalign(1)
                self.processes.attach(label, column, i, 1, 1)
            self.process_labels.append(labels)
        self.card.pack_start(self.processes, False, False, 0)

        self.card.pack_start(
            footer(f"{GLYPHS['open']}  Open {monitor}", lambda: self._launch(monitor)), False, False, 0
        )

        self.last_cpu = cpu_times()
        self.last_procs = (time.monotonic(), process_times())
        GLib.timeout_add(400, lambda: (self.update(), False)[-1])
        GLib.timeout_add(1000, lambda: (self.update(), True)[-1])

    def _launch(self, monitor):
        spawn("alacritty", "--class", "popup", "-e", monitor)
        self.dismiss()

    def _usage_row(self, name):
        row = Gtk.Box(spacing=8)
        label = icon_label(name, "usage-name")
        label.set_xalign(0)
        label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        label.set_width_chars(13)
        label.set_max_width_chars(13)
        row.pack_start(label, False, False, 0)
        bar = meter()
        bar.set_valign(Gtk.Align.CENTER)
        row.pack_start(bar, True, True, 0)
        value = icon_label("", "usage-value")
        value.set_xalign(1)
        value.set_width_chars(len("1023.9 GiB / 1023.9 GiB"))
        row.pack_start(value, False, False, 0)
        self.card.pack_start(row, False, False, 2)
        return bar, value

    def _set_usage(self, row, used, total, warning=0.75, critical=0.9):
        bar, value = row
        fraction = used / total if total else 0
        bar.set_value(fraction)
        set_state_class(bar, fraction, warning, critical)
        value.set_text(f"{human_bytes(used)} / {human_bytes(total)}")

    def update(self):
        now = cpu_times()
        usage = cpu_usage(self.last_cpu, now)
        self.last_cpu = now
        total, cores = usage[0], usage[1:]
        self.cpu_label.set_text(f"{total:.0f}%")
        set_state_class(self.cpu_label, total, 70, 90)
        self.graph.push(total)
        for bar, value in zip(self.core_bars, cores):
            bar.set_value(value / 100)
            set_state_class(bar, value, 70, 90)

        details = []
        freqs = []
        for f in Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_cur_freq"):
            try:
                freqs.append(int(f.read_text()))
            except (OSError, ValueError):
                pass
        if freqs:
            details.append(f"{sum(freqs) / len(freqs) / 1e6:.2f} GHz")
        temp = temperature(self.sensor)
        if temp is not None:
            details.append(f"{GLYPHS['temp']}{temp:.0f}°C")
        details.append("load " + " ".join(f"{x:.2f}" for x in os.getloadavg()))
        self.cpu_details.set_text("  ·  ".join(details))

        mem = meminfo()
        self._set_usage(self.memory_rows["ram"], mem["MemTotal"] - mem["MemAvailable"], mem["MemTotal"])
        self._set_usage(self.memory_rows["swap"], mem["SwapTotal"] - mem["SwapFree"], mem["SwapTotal"])

        for mount, row in self.disk_rows.items():
            try:
                st = os.statvfs(mount)
            except OSError:
                continue
            total_bytes = st.f_blocks * st.f_frsize
            self._set_usage(row, total_bytes - st.f_bfree * st.f_frsize, total_bytes, 0.85, 0.95)

        t1, procs = time.monotonic(), process_times()
        t0, previous = self.last_procs
        self.last_procs = (t1, procs)
        elapsed = max(t1 - t0, 1e-3) * self.clock_ticks
        busiest = sorted(
            ((100 * (ticks - previous.get(name, (ticks,))[0]) / elapsed, name, rss, count)
             for name, (ticks, rss, count) in procs.items()),
            reverse=True,
        )[: len(self.process_labels)]
        for labels, (cpu, name, rss, count) in zip(self.process_labels, busiest):
            labels[0].set_text(f"{name} ({count})" if count > 1 else name)
            labels[1].set_text(f"{cpu:.0f}%")
            labels[2].set_text(human_bytes(rss))


# Bluetooth --------------------------------------------------------------------


class BluetoothPopup(Popup):
    """Adapter power, paired devices (connect/disconnect/forget) and discovery."""

    BLUEZ = "org.bluez"

    def __init__(self, output=None):
        super().__init__(output)
        self.adapter = None
        self.discovering = False
        self.busy = set()
        self.refresh_source = None
        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM)

        self.power = Gtk.Switch()
        self.power_handler = self.power.connect("notify::active", self._toggle_power)
        self.card.pack_start(header("Bluetooth", self.power), False, False, 0)

        self.devices = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.card.pack_start(self.devices, False, False, 0)

        self.scan_button = flat_button(GLYPHS["refresh"], self._toggle_scan, tooltip="Scan for devices")
        self.available_header = header("Available", self.scan_button, first=False)
        self.card.pack_start(self.available_header, False, False, 0)
        self.available = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.card.pack_start(self.available, False, False, 0)

        self.status = icon_label("", "status")
        self.status.set_xalign(0)
        self.status.set_line_wrap(True)
        self.status.set_no_show_all(True)
        self.card.pack_start(self.status, False, False, 0)

        self.card.pack_start(
            footer(f"{GLYPHS['open']}  Open bluetui", lambda: self._launch()), False, False, 0
        )

        self.bus.signal_subscribe(
            self.BLUEZ, None, None, None, None, Gio.DBusSignalFlags.NONE, self._on_signal
        )

    def _launch(self):
        spawn("alacritty", "--class", "bluetui", "-e", "bluetui")
        self.dismiss()

    def _call(self, path, interface, method, args=None, done=None, timeout=30000):
        def finished(bus, result):
            try:
                bus.call_finish(result)
                error = None
            except GLib.Error as e:
                error = e.message.split(":")[-1].strip()
            if done:
                done(error)
            self._schedule_refresh()

        self.bus.call(self.BLUEZ, path, interface, method, args, None,
                      Gio.DBusCallFlags.NONE, timeout, None, finished)

    def _set_property(self, path, interface, name, value):
        self._call(path, "org.freedesktop.DBus.Properties", "Set",
                   GLib.Variant("(ssv)", (interface, name, value)))

    def _on_signal(self, *_):
        self._schedule_refresh()

    def _schedule_refresh(self):
        if self.refresh_source is None:
            self.refresh_source = GLib.timeout_add(150, self._debounced_refresh)

    def _debounced_refresh(self):
        self.refresh_source = None
        self.refresh()
        return False

    def _set_status(self, text):
        self.status.set_text(text)
        self.status.set_visible(bool(text))

    def refresh(self):
        try:
            reply = self.bus.call_sync(
                self.BLUEZ, "/", "org.freedesktop.DBus.ObjectManager", "GetManagedObjects",
                None, GLib.VariantType("(a{oa{sa{sv}}})"), Gio.DBusCallFlags.NONE, 2000, None,
            )
            objects = reply.unpack()[0]
        except GLib.Error:
            objects = {}

        adapters = [p for p, ifaces in objects.items() if "org.bluez.Adapter1" in ifaces]
        for child in self.devices.get_children() + self.available.get_children():
            child.get_parent().remove(child)

        if not adapters:
            self.adapter = None
            self.power.set_visible(False)
            self.available_header.set_visible(False)
            empty = icon_label(f"{GLYPHS['bluetooth-off']}  No Bluetooth adapter", "empty")
            empty.set_xalign(0)
            self.devices.pack_start(empty, False, False, 0)
            self.devices.show_all()
            return

        self.adapter = adapters[0]
        adapter = objects[self.adapter]["org.bluez.Adapter1"]
        powered = adapter.get("Powered", False)
        self.discovering = adapter.get("Discovering", False)
        with self.power.handler_block(self.power_handler):
            self.power.set_active(powered)
        self.power.set_visible(True)
        self.available_header.set_visible(powered)
        self.scan_button.get_child().set_text("\U000f04db" if self.discovering else GLYPHS["refresh"])
        self.scan_button.set_tooltip_text("Stop scanning" if self.discovering else "Scan for devices")

        devices = []
        for path, ifaces in objects.items():
            device = ifaces.get("org.bluez.Device1")
            if not device or device.get("Adapter") != self.adapter:
                continue
            battery = ifaces.get("org.bluez.Battery1", {}).get("Percentage")
            devices.append((path, device, battery))
        devices.sort(key=lambda d: (not d[1].get("Connected", False), d[1].get("Alias", "").lower()))

        if not powered:
            empty = icon_label("Bluetooth is off", "empty")
            empty.set_xalign(0)
            self.devices.pack_start(empty, False, False, 0)

        paired = [d for d in devices if d[1].get("Paired")] if powered else []
        if powered and not paired:
            empty = icon_label("No paired devices", "empty")
            empty.set_xalign(0)
            self.devices.pack_start(empty, False, False, 0)
        for path, device, battery in paired:
            connected = device.get("Connected", False)
            parts = ["Connected" if connected else "Paired"]
            if battery is not None:
                parts.append(f"{GLYPHS['battery']} {battery}%")
            if path in self.busy:
                action = icon_label("…", "dim")
            else:
                action = flat_button("Disconnect" if connected else "Connect",
                                     lambda p=path, c=connected: self._connect(p, not c),
                                     "accent" if not connected else "plain")
            forget = flat_button(GLYPHS["close"], lambda p=path: self._forget(p), tooltip="Forget device")
            icon = BLUETOOTH_ICONS.get(device.get("Icon", ""), GLYPHS["bluetooth"])
            self.devices.pack_start(
                ListRow(icon, device.get("Alias", device.get("Address", "?")), "  ·  ".join(parts),
                        action, forget, css_class="active" if connected else None),
                False, False, 0,
            )

        unpaired = [d for d in devices if not d[1].get("Paired") and "Name" in d[1]] if powered else []
        if powered and not unpaired:
            hint = "Searching…" if self.discovering else "Press scan to look for devices"
            empty = icon_label(hint, "empty")
            empty.set_xalign(0)
            self.available.pack_start(empty, False, False, 0)
        for path, device, _ in unpaired[:10]:
            action = icon_label("…", "dim") if path in self.busy else flat_button(
                "Pair", lambda p=path: self._pair(p), "accent")
            icon = BLUETOOTH_ICONS.get(device.get("Icon", ""), GLYPHS["bluetooth"])
            self.available.pack_start(ListRow(icon, device["Name"], "", action), False, False, 0)

        self.devices.show_all()
        self.available.show_all()

    def _toggle_power(self, switch, _):
        self._set_property(self.adapter, "org.bluez.Adapter1", "Powered", GLib.Variant("b", switch.get_active()))

    def _toggle_scan(self):
        method = "StopDiscovery" if self.discovering else "StartDiscovery"
        self._call(self.adapter, "org.bluez.Adapter1", method)

    def _finish(self, path, error):
        self.busy.discard(path)
        self._set_status(f"Failed: {error}" if error else "")

    def _connect(self, path, connect):
        self.busy.add(path)
        self._call(path, "org.bluez.Device1", "Connect" if connect else "Disconnect",
                   done=lambda e: self._finish(path, e))
        self.refresh()

    def _pair(self, path):
        self.busy.add(path)
        self._set_status("Pairing… confirm on the device if asked")

        def paired(error):
            if error:
                self._finish(path, error)
                return
            self._set_property(path, "org.bluez.Device1", "Trusted", GLib.Variant("b", True))
            self._call(path, "org.bluez.Device1", "Connect", done=lambda e: self._finish(path, e))

        self._call(path, "org.bluez.Device1", "Pair", done=paired, timeout=60000)
        self.refresh()

    def _forget(self, path):
        self._call(self.adapter, "org.bluez.Adapter1", "RemoveDevice", GLib.Variant("(o)", (path,)))

    def close(self):
        if self.adapter and self.discovering:
            try:
                self.bus.call_sync(self.BLUEZ, self.adapter, "org.bluez.Adapter1", "StopDiscovery",
                                   None, None, Gio.DBusCallFlags.NONE, 1000, None)
            except GLib.Error:
                pass


# Notifications ----------------------------------------------------------------


def relative_time(microseconds):
    """dunst timestamps are CLOCK_MONOTONIC microseconds, same as time.monotonic()."""
    seconds = max(time.monotonic() - microseconds / 1e6, 0)
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size:
            return f"{int(seconds // size)}{unit} ago"
    return "now"


def plain_text(markup):
    """dunst bodies may contain a small subset of HTML-ish markup."""
    return re.sub(r"<[^>]+>", "", markup).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").strip()


class NotificationRow(Gtk.EventBox):
    def __init__(self, notification, on_open, on_dismiss):
        super().__init__()
        row = Gtk.Box(spacing=10)
        ctx = row.get_style_context()
        ctx.add_class("notification")
        if notification["urgency"] == "CRITICAL":
            ctx.add_class("critical")
        self.add(row)

        icon = self._icon(notification)
        icon.set_valign(Gtk.Align.START)
        row.pack_start(icon, False, False, 0)

        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        meta = Gtk.Box(spacing=6)
        app = icon_label(notification["app"] or "Notification", "notification-app")
        app.set_xalign(0)
        meta.pack_start(app, True, True, 0)
        meta.pack_start(icon_label(relative_time(notification["timestamp"]), "notification-time"), False, False, 0)
        column.pack_start(meta, False, False, 0)
        summary = icon_label(plain_text(notification["summary"]), "row-title")
        summary.set_xalign(0)
        summary.set_line_wrap(True)
        summary.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        summary.set_max_width_chars(36)
        column.pack_start(summary, False, False, 0)
        body = plain_text(notification["body"])
        if body:
            label = icon_label(body, "notification-body")
            label.set_xalign(0)
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            label.set_max_width_chars(36)
            label.set_lines(3)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            column.pack_start(label, False, False, 0)
        row.pack_start(column, True, True, 0)

        dismiss = flat_button(GLYPHS["close"], lambda: on_dismiss(notification["id"]), tooltip="Dismiss")
        dismiss.set_valign(Gtk.Align.START)
        row.pack_start(dismiss, False, False, 0)

        def hover(_, event, on):
            if event.detail != Gdk.NotifyType.INFERIOR:
                (ctx.add_class if on else ctx.remove_class)("hover")

        self.connect("enter-notify-event", hover, True)
        self.connect("leave-notify-event", hover, False)

        # Clicking the notification shows it again, where its actions can be used
        self.set_tooltip_text("Click to show again")
        self.connect("button-release-event", lambda *_: on_open(notification["id"]))

    @staticmethod
    def _icon(notification):
        path = notification["icon"]
        if path and os.path.isfile(path):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 28, 28, True)
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except GLib.Error:
                pass
        theme = Gtk.IconTheme.get_default()
        name = (notification["app"] or "").lower().replace(" ", "-")
        if name and theme.has_icon(name):
            return Gtk.Image.new_from_icon_name(name, Gtk.IconSize.DND)
        return icon_label(GLYPHS["bell"], "row-icon")


class NotificationsPopup(Popup):
    """dunst history: dismiss one, clear all, re-show, and do not disturb."""

    SHOWN = 8

    def __init__(self, output=None):
        super().__init__(output)
        self.history = None

        self.dnd = Gtk.Switch()
        self.dnd.set_tooltip_text("Do not disturb")
        self.dnd_handler = self.dnd.connect("notify::active", self._toggle_dnd)
        dnd_label = icon_label(GLYPHS["bell-off"], "dim")
        dnd_label.set_tooltip_text("Do not disturb")
        self.clear = flat_button("Clear all", self._clear, "plain")
        self.card.pack_start(header("Notifications", self.clear, dnd_label, self.dnd), False, False, 0)

        self.waiting = icon_label("", "status")
        self.waiting.set_xalign(0)
        self.waiting.set_no_show_all(True)
        self.card.pack_start(self.waiting, False, False, 0)

        # No ScrolledWindow: GTK3 underestimates the height of wrapped labels inside one
        self.list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.card.pack_start(self.list, False, False, 0)

        GLib.timeout_add(2000, lambda: (self.refresh(), True)[-1])

    def refresh(self):
        try:
            data = json.loads(run("dunstctl", "history"))["data"][0]
        except (json.JSONDecodeError, KeyError, IndexError):
            data = []
        history = [
            {key: n.get(field, {}).get("data", "") for key, field in (
                ("id", "id"), ("app", "appname"), ("summary", "summary"), ("body", "body"),
                ("timestamp", "timestamp"), ("icon", "icon_path"), ("urgency", "urgency"))}
            for n in data
        ]
        paused = run("dunstctl", "is-paused").strip() == "true"
        with self.dnd.handler_block(self.dnd_handler):
            self.dnd.set_active(paused)
        waiting = int(run("dunstctl", "count", "waiting").strip() or 0) if paused else 0
        self.waiting.set_text(f"{waiting} notification{'s' if waiting != 1 else ''} held back while paused")
        self.waiting.set_visible(waiting > 0)
        self.clear.set_sensitive(bool(history))

        if history == self.history:
            return
        self.history = history
        for child in self.list.get_children():
            self.list.remove(child)
        if not history:
            empty = icon_label(f"{GLYPHS['bell']}  No notifications", "empty")
            empty.set_xalign(0)
            self.list.pack_start(empty, False, False, 0)
        for notification in history[:self.SHOWN]:
            self.list.pack_start(NotificationRow(notification, self._open, self._dismiss), False, False, 0)
        if len(history) > self.SHOWN:
            more = icon_label(f"{len(history) - self.SHOWN} older", "empty")
            more.set_xalign(0)
            self.list.pack_start(more, False, False, 0)
        self.list.show_all()

    def _signal_bar(self):
        spawn("pkill", "-RTMIN+9", "waybar")

    def _toggle_dnd(self, switch, _):
        run("dunstctl", "set-paused", "true" if switch.get_active() else "false")
        self._signal_bar()
        self.refresh()

    def _dismiss(self, ident):
        run("dunstctl", "history-rm", str(ident))
        self.refresh()

    def _open(self, ident):
        run("dunstctl", "history-pop", str(ident))
        self.refresh()

    def _clear(self):
        run("dunstctl", "history-clear")
        self.refresh()


# Power ------------------------------------------------------------------------


def uptime():
    seconds = int(float(Path("/proc/uptime").read_text().split()[0]))
    days, rest = divmod(seconds, 86400)
    hours, minutes = divmod(rest // 60, 60)
    return " ".join(f"{v}{u}" for v, u in ((days, "d"), (hours, "h"), (minutes, "m")) if v) or "just now"


class PowerPopup(Popup):
    """Lock / suspend / hibernate / log out / reboot / shut down tiles.

    Log out, reboot and shut down ask for a second click to confirm.
    """

    LOCK = str(Path.home() / ".config/sway/scripts/lock.sh")
    ACTIONS = [
        ("lock", "\U000f033e", "Lock", None, False),
        ("suspend", "\U000f04b2", "Suspend", ["systemctl", "suspend"], False),
        ("hibernate", "\U000f0717", "Hibernate", ["systemctl", "hibernate"], False),
        ("logout", "\U000f0343", "Log out", ["swaymsg", "exit"], True),
        ("reboot", "\U000f0709", "Reboot", ["systemctl", "reboot"], True),
        ("poweroff", "\U000f0425", "Shut down", ["systemctl", "poweroff"], True),
    ]

    def __init__(self, output=None):
        super().__init__(output)
        self.armed = None
        self.disarm_source = None

        self.card.pack_start(header("Session", icon_label(f"up {uptime()}", "dim")), False, False, 0)
        grid = Gtk.Grid(column_spacing=6, row_spacing=6, column_homogeneous=True)
        self.tiles = {}
        for i, (key, icon, text, command, confirm) in enumerate(self.ACTIONS):
            tile = Gtk.Button()
            ctx = tile.get_style_context()
            ctx.add_class("tile")
            if confirm:
                ctx.add_class("danger")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.pack_start(icon_label(icon, "tile-icon"), False, False, 0)
            label = icon_label(text, "tile-label")
            box.pack_start(label, False, False, 0)
            tile.add(box)
            tile.connect("clicked", lambda _, k=key: self._activate(k))
            self.tiles[key] = (tile, label, text)
            grid.attach(tile, i % 3, i // 3, 1, 1)
        self.card.pack_start(grid, False, False, 4)

    def _activate(self, key):
        _, _, _, command, confirm = next(a for a in self.ACTIONS if a[0] == key)
        if confirm and self.armed != key:
            self._disarm()
            self.armed = key
            tile, label, _ = self.tiles[key]
            tile.get_style_context().add_class("armed")
            label.set_text("Confirm?")
            self.disarm_source = GLib.timeout_add(3000, self._expire)
            return
        if key == "lock":
            command = [self.LOCK] if os.access(self.LOCK, os.X_OK) else ["swaylock", "-f", "-c", "000000"]
        spawn(*command)
        self.dismiss()

    def _expire(self):
        self.disarm_source = None
        return self._disarm()

    def _disarm(self):
        if self.disarm_source:
            GLib.source_remove(self.disarm_source)
            self.disarm_source = None
        if self.armed:
            tile, label, text = self.tiles[self.armed]
            tile.get_style_context().remove_class("armed")
            label.set_text(text)
            self.armed = None
        return False


POPUPS = {
    "audio": AudioPopup,
    "brightness": BrightnessPopup,
    "network": NetworkPopup,
    "performance": PerformancePopup,
    "bluetooth": BluetoothPopup,
    "notifications": NotificationsPopup,
    "power": PowerPopup,
}


def close_running():
    """Close a running popup and return its kind, so clicking again toggles it."""
    try:
        pid, kind = PIDFILE.read_text().split()
        if "control_center" not in Path(f"/proc/{pid}/cmdline").read_text():
            return None
        os.kill(int(pid), signal.SIGTERM)
        return kind
    except (OSError, ValueError):
        return None


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else ""
    if kind not in POPUPS:
        sys.exit(f"usage: {sys.argv[0]} {{{'|'.join(POPUPS)}}} [output]")
    if close_running() == kind:
        return
    PIDFILE.write_text(f"{os.getpid()} {kind}")

    output = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("WAYBAR_OUTPUT_NAME")
    popup = POPUPS[kind](output)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: popup.dismiss())
    popup.show()
    try:
        Gtk.main()
    finally:
        popup.close()
        if PIDFILE.read_text().split()[0] == str(os.getpid()):
            PIDFILE.unlink()


if __name__ == "__main__":
    main()
