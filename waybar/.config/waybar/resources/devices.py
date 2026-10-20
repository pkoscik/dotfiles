#!/usr/bin/env python3
"""External drives and phones for waybar; a dimmed icon when nothing is mounted.

Updates on udisks and gvfs events (plugging in, mounting, unmounting) rather
than polling; a slow fallback refresh keeps the free-space tooltip current.
"""

import json
import selectors
import subprocess
import time

from sysinfo import external_devices, gvfs_mounts

FALLBACK_REFRESH = 30
DEBOUNCE = 0.3
ICON = "\U000f0553"


def human(n):
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or unit == "TiB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def status():
    # Drives without media (e.g. empty card readers) are only listed in the popup
    devices = [d for d in external_devices() if d["size"]]
    phones = gvfs_mounts()
    if not devices and not phones:
        return {"text": ICON, "class": "empty", "tooltip": "No external devices"}
    mounted = [d for d in devices if d["mountpoint"]] + phones
    lines = []
    for d in devices:
        if d["mountpoint"]:
            free = f", {human(d['free'])} free" if d["free"] is not None else ""
            lines.append(f"{d['label']}: {d['mountpoint']}{free}")
        elif not d["fstype"]:
            lines.append(f"{d['label']}: no filesystem ({human(d['size'])})")
        else:
            lines.append(f"{d['label']}: not mounted")
    lines += [f"{p['name']}: {p['uri']}" for p in phones]
    unmounted = len(devices) + len(phones) - len(mounted)
    return {
        "text": f"{ICON} {len(mounted)}" if mounted else ICON,
        "tooltip": "\n".join(lines),
        "class": "unmounted" if unmounted else "mounted",
    }


def main():
    selector = selectors.DefaultSelector()
    for argv in (["udisksctl", "monitor"], ["gio", "mount", "-o"]):
        try:
            proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            selector.register(proc.stdout, selectors.EVENT_READ)
        except OSError:
            pass

    last = None
    while True:
        current = json.dumps(status(), ensure_ascii=False)
        if current != last:
            print(current, flush=True)
            last = current
        events = selector.select(timeout=FALLBACK_REFRESH)
        # Drain the burst of lines a single plug-in produces, then refresh once
        deadline = time.monotonic() + DEBOUNCE
        while events and time.monotonic() < deadline:
            for key, _ in events:
                if not key.fileobj.read1(65536):
                    selector.unregister(key.fileobj)
            events = selector.select(timeout=max(deadline - time.monotonic(), 0))


if __name__ == "__main__":
    main()
