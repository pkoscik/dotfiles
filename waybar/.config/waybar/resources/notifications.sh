#!/usr/bin/env bash
# Dunst do-not-disturb toggle for waybar (signal 9 refreshes it)

case "$1" in
  -t | --toggle)
    dunstctl set-paused toggle
    pkill -RTMIN+9 waybar
    ;;
  *)
    if [[ "$(dunstctl is-paused)" == true ]]; then
      waiting=$(dunstctl count waiting)
      (( waiting > 0 )) && text="󰂛 $waiting" || text="󰂛"
      printf '{"text":"%s","class":"paused","tooltip":"Notifications paused (%s waiting)"}\n' "$text" "$waiting"
    else
      echo '{"text":"󰂚","class":"active","tooltip":"Notifications on"}'
    fi
    ;;
esac
