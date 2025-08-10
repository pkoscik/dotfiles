#!/usr/bin/env bash

# Detect correct temperature sensor dynamically
for d in /sys/class/hwmon/hwmon*; do
    name=$(<"$d/name")

    if [[ $name == "k10temp" ]]; then
        # AMD Ryzen: show Tctl
        for f in "$d"/temp*_label; do
            if [[ -f "$f" ]] && grep -q "Tctl" "$f"; then
                input_file="${f/_label/_input}"
                awk '{printf "%.0f\n", $1 / 1000}' "$input_file"
                exit 0
            fi
        done
    fi

    if [[ $name == "coretemp" ]]; then
        # Intel: pick Package id 0 (adjust if needed)
        for f in "$d"/temp*_label; do
            if [[ -f "$f" ]] && grep -q "Package id 0" "$f"; then
                input_file="${f/_label/_input}"
                awk '{printf "%.0f\n", $1 / 1000}' "$input_file"
                exit 0
            fi
        done
    fi
done

# Fallback: first temp*_input found
for f in /sys/class/hwmon/hwmon*/temp*_input; do
    awk '{printf "%.0f\n", $1 / 1000}' "$f"
    exit 0
done

echo "?"