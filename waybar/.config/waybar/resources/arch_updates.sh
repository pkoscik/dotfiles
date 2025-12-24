#!/usr/bin/env bash

if command -v yay >/dev/null 2>&1; then
  command="yay"
else
  command="pacman"
fi

count_updates() {
  "$command" -Qu 2>/dev/null | wc -l
}

run_update() {
  if [[ "$command" == "pacman" ]]; then
    alacritty --class 'popup' -e bash -c "sudo pacman -Syu; echo; read -p 'Press enter to close...'"
  else
    alacritty --class 'popup' -e bash -c "yay -Syu; echo; read -p 'Press enter to close...'"
  fi
}

case "$1" in
  -s|--status)
    updates=$(count_updates)
    if [[ "$updates" -gt 0 ]]; then
      echo "updates: $updates"
    else
      echo "$STATUS_HIDE_STR"
    fi
    ;;
  -u)
    run_update
    ;;
esac
