STATUS_CONNECTED_STR='{"text":"Connected","class":"connected","alt":"connected"}'
STATUS_DISCONNECTED_STR='{"text":"Disconnected","class":"disconnected","alt":"disconnected"}'

function status_wireguard() {
  ip link show dev wg >/dev/null 2>&1
  return $?
}

function toggle_wireguard() {
  # TODO: finish this
  status_wireguard && \
     echo ENABLE || \
     echo DISABLE
}

case $1 in
  -s | --status)
    status_wireguard && echo $STATUS_CONNECTED_STR || echo $STATUS_DISCONNECTED_STR
    ;;
esac
