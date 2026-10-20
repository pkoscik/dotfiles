#!/usr/bin/env python3
"""CPU usage, temperature, RAM and free disk space as a single waybar module.

Streams waybar JSON every few seconds; each value is colored on its own when it
gets high, and the module gets the worst state as its class.
"""

import json
import os
import time

from sysinfo import cpu_times, cpu_usage, meminfo, temperature, temperature_sensor

INTERVAL = 3
DISK = "/"
COLORS = {"warning": "#FFB86C", "critical": "#FF5555"}
ICONS = {"cpu": "", "temp": "", "memory": "\U000f035b", "disk": ""}


def state(value, warning, critical):
    return "critical" if value >= critical else "warning" if value >= warning else None


def colored(text, level):
    return f"<span color='{COLORS[level]}'>{text}</span>" if level else text


def gib(n):
    return f"{n / 1024**3:.1f} GiB"


def main():
    sensor = temperature_sensor()
    last = cpu_times()
    delay = 0.5  # first sample quickly, then every INTERVAL
    while True:
        time.sleep(delay)
        delay = INTERVAL
        now = cpu_times()
        cpu = cpu_usage(last, now)[0]
        last = now
        temp = temperature(sensor)
        mem = meminfo()
        used = mem["MemTotal"] - mem["MemAvailable"]
        ram = 100 * used / mem["MemTotal"]
        disk = os.statvfs(DISK)
        disk_total = disk.f_blocks * disk.f_frsize
        disk_free = disk.f_bavail * disk.f_frsize
        disk_free_pct = 100 * disk_free / disk_total

        levels = {
            "cpu": state(cpu, 70, 90),
            "temp": state(temp or 0, 75, 90),
            "memory": state(ram, 75, 90),
            "disk": state(100 - disk_free_pct, 85, 95),
        }
        parts = [
            colored(f"{ICONS['cpu']} {cpu:.0f}%", levels["cpu"]),
            colored(f"{ICONS['temp']} {temp:.0f}°C", levels["temp"]) if temp is not None else None,
            colored(f"{ICONS['memory']} {ram:.0f}%", levels["memory"]),
            colored(f"{ICONS['disk']} {disk_free_pct:.0f}%", levels["disk"]),
        ]
        tooltip = "\n".join(line for line in (
            f"CPU   {cpu:.0f}%",
            f"Temp  {temp:.0f}°C" if temp is not None else None,
            f"RAM   {gib(used)} / {gib(mem['MemTotal'])}",
            f"Disk  {gib(disk_free)} free of {gib(disk_total)} ({DISK})",
        ) if line)
        worst = "critical" if "critical" in levels.values() else "warning" if "warning" in levels.values() else ""
        print(json.dumps({"text": "  ".join(p for p in parts if p), "tooltip": tooltip, "class": worst}), flush=True)


if __name__ == "__main__":
    main()
