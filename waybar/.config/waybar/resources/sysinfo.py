"""System stats shared by performance.py (bar) and control_center.py (popup)."""

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
