#!/usr/bin/env bash

if command -v yay >/dev/null 2>&1; then
  command="yay"
else
  command="pacman"
fi

cache="${XDG_RUNTIME_DIR:-/tmp}/waybar-arch-updates"

# checkupdates (pacman-contrib) syncs a temp db; plain -Qu only sees the last -Sy
fetch_updates() {
  {
    checkupdates
    [[ "$command" == "yay" ]] && yay -Qua
  } 2>/dev/null
}

# One waybar instance per output runs this concurrently; checkupdates shares
# its temp db, so racing runs give different counts. Serialize and share a cache.
list_updates() {
  exec 9>"$cache.lock"
  flock 9
  [[ -n $(find "$cache" -mmin -1 2>/dev/null) ]] || fetch_updates >"$cache"
  cat "$cache"
}

run_update() {
  if [[ "$command" == "pacman" ]]; then
    alacritty --class 'popup' -e bash -c "sudo pacman -Syu; echo; read -p 'Press enter to close...'"
  else
    alacritty --class 'popup' -e bash -c "yay -Syu; echo; read -p 'Press enter to close...'"
  fi
  rm -f "$cache"
  pkill -RTMIN+10 waybar
}

case "$1" in
  -s|--status)
    updates=$(list_updates)
    if [[ -n "$updates" ]]; then
      count=$(wc -l <<<"$updates")
      # Tooltip: first 30 packages, "name old -> new"
      jq -cn --arg count "$count" --arg list "$(head -30 <<<"$updates")" --arg more "$(( count > 30 ? count - 30 : 0 ))" \
        '{text: "󰏗 \($count)", tooltip: ($list + (if $more != "0" then "\n… and \($more) more" else "" end))}'
    else
      echo '{"text":""}'
    fi
    ;;
  -u)
    run_update
    ;;
esac
