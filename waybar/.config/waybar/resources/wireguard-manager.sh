STATUS_CONNECTED_STR='{"text":"Connected","class":"connected","alt":"connected"}'
STATUS_DISCONNECTED_STR='{"text":"Disconnected","class":"disconnected","alt":"disconnected"}'
STATUS_HIDE_STR='{"text":"","class":"","alt":""}'

allowed_hostnames=("dell")

function status_wireguard() {
  ip link show dev wg >/dev/null 2>&1
  return $?
}

toggle_wireguard() {
  if status_wireguard; then
    pkexec wg-quick down wg
    echo DISABLE
  else
    pkexec wg-quick up wg
    echo ENABLE
  fi
}

hostname_allowed() {
  local current
  current="$(cat /etc/hostname)"
  for h in "${allowed_hostnames[@]}"; do
    [[ "$current" == "$h" ]] && return 0
  done
  return 1
}

case $1 in
  -s | --status)
    hostname_allowed || { echo "$STATUS_HIDE_STR"; exit 0; }
    status_wireguard && \
      echo "$STATUS_CONNECTED_STR" || \
      echo "$STATUS_DISCONNECTED_STR"
    ;;
  -t | --toggle)
    toggle_wireguard
    ;;
esac
