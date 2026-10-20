"""System stats shared by performance.py (bar) and control_center.py (popup)."""

import json
import re
import subprocess
from pathlib import Path


def cpu_times():
    """[(busy, total)] for the whole CPU followed by each core, from /proc/stat."""
    result = []
    for line in Path("/proc/stat").read_text().splitlines():
        if not line.startswith("cpu"):
            break
        values = [int(v) for v in line.split()[1:]]
        idle = values[3] + values[4]
        result.append((sum(values) - idle, sum(values)))
    return result


def cpu_usage(before, after):
    """Percent busy per entry of two cpu_times() samples."""
    return [
        100 * (b1 - b0) / (t1 - t0) if t1 > t0 else 0
        for (b0, t0), (b1, t1) in zip(before, after)
    ]


def temperature_sensor():
    """AMD Tctl, Intel package temperature, else the first sensor found."""
    hwmon = sorted(Path("/sys/class/hwmon").glob("hwmon*"))
    wanted = {"k10temp": "Tctl", "coretemp": "Package id 0"}
    for d in hwmon:
        try:
            label = wanted.get((d / "name").read_text().strip())
        except OSError:
            continue
        for f in d.glob("temp*_label") if label else ():
            if f.read_text().strip() == label:
                return Path(str(f).replace("_label", "_input"))
    return next((f for d in hwmon for f in sorted(d.glob("temp*_input"))), None)


def temperature(sensor):
    try:
        return int(sensor.read_text()) / 1000 if sensor else None
    except (OSError, ValueError):
        return None


def meminfo():
    """/proc/meminfo in bytes."""
    result = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        result[key] = int(value.split()[0]) * 1024
    return result


def external_devices():
    """Filesystems on hot-plugged drives (USB sticks, SD cards, external disks).

    [{path, drive, label, model, fstype, size, mountpoint, free, total, transport}].
    A drive without any filesystem (empty card reader, blank disk) is listed once
    with fstype None; size 0 means there is no media in it.
    """
    columns = "NAME,PATH,PKNAME,LABEL,SIZE,FSTYPE,MOUNTPOINTS,HOTPLUG,TYPE,TRAN,MODEL,VENDOR,FSSIZE,FSAVAIL"
    try:
        out = subprocess.run(["lsblk", "--list", "-J", "-b", "-o", columns], capture_output=True, text=True).stdout
        nodes = {n["name"]: n for n in json.loads(out)["blockdevices"]}
    except (json.JSONDecodeError, KeyError):
        return []

    def drive_of(node):
        while node.get("pkname") in nodes and node.get("type") != "disk":
            node = nodes[node["pkname"]]
        return node

    def model_of(drive):
        return " ".join(x.strip() for x in (drive.get("vendor") or "", drive.get("model") or "") if x and x.strip())

    devices = []
    with_filesystem = set()
    for node in nodes.values():
        drive = drive_of(node)
        if not node.get("fstype") or node["fstype"] == "swap" or not drive.get("hotplug"):
            continue
        with_filesystem.add(drive["path"])
        model = model_of(drive)
        mountpoint = next((m for m in node.get("mountpoints") or [] if m), None)
        devices.append({
            "path": node["path"],
            "drive": drive["path"],
            "label": node.get("label") or model or node["name"],
            "model": model,
            "fstype": node["fstype"],
            "size": node.get("size") or 0,
            "mountpoint": mountpoint,
            "free": node.get("fsavail"),
            "total": node.get("fssize"),
            "transport": drive.get("tran") or "",
        })
    for drive in nodes.values():
        if drive.get("type") == "disk" and drive.get("hotplug") and drive["path"] not in with_filesystem:
            devices.append({
                "path": drive["path"], "drive": drive["path"], "label": model_of(drive) or drive["name"],
                "model": model_of(drive), "fstype": None, "size": drive.get("size") or 0,
                "mountpoint": None, "free": None, "total": None, "transport": drive.get("tran") or "",
            })
    return sorted(devices, key=lambda d: d["path"])


def gvfs_mounts():
    """Phones/cameras and other non-block mounts handled by gvfs: [{name, uri}]."""
    out = subprocess.run(["gio", "mount", "-l"], capture_output=True, text=True).stdout
    mounts = []
    for line in out.splitlines():
        match = re.match(r"^\s*Mount\(\d+\): (.*) -> (\S+)$", line)
        if match and not match.group(2).startswith("file://"):
            mounts.append({"name": match.group(1), "uri": match.group(2)})
    return mounts
