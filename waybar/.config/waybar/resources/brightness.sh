#!/usr/bin/env bash
# Brightness for laptop backlights (brightnessctl) and external monitors (ddcutil).
#
# DDC/CI is slow (~300ms to detect, ~200ms per call) and serialized per i2c bus, so:
#   - detected displays are cached until sway's outputs change (hotplug/layout),
#   - brightness values are cached and only read from hardware once per session,
#   - a requested value is written to the cache first (instant feedback in waybar),
#     then applied in the background under a per-display lock; stale requests
#     are skipped, so fast scrolling doesn't queue up dozens of ddcutil calls.
#
# When displays are linked, changes apply to all of them. Otherwise they apply
# to the display a waybar instance runs on ($WAYBAR_OUTPUT_NAME), or the focused
# output when called from a keybinding.
#
#   brightness.sh list                    -> "<id>\t<output>\t<label>\t<percent>" per display
#   brightness.sh status [output]         -> waybar JSON
#   brightness.sh set <pct> [target]      -> target: id, output name or "all"
#   brightness.sh up|down [step] [target] -> prints "<percent>\t<label>"
#   brightness.sh link [on|off|toggle]    -> prints 1 (linked) or 0
#   brightness.sh refresh                 -> re-detect displays and re-read values

cache="${XDG_RUNTIME_DIR:-/tmp}/waybar-brightness"
state="${XDG_STATE_HOME:-$HOME/.local/state}/waybar"
signal=8
mkdir -p "$cache" "$state"

sway_outputs() {
  swaymsg -t get_outputs -r 2>/dev/null
}

detect() {
  local outputs="$1" d conn
  for d in /sys/class/backlight/*; do
    [[ -e "$d" ]] || continue
    conn=$(jq -r 'first(.[] | select(.name | test("^(eDP|LVDS|DSI)")) | .name) // "-"' <<<"$outputs")
    printf 'backlight:%s\t%s\t%s\n' "${d##*/}" "$conn" "Built-in"
  done
  ddcutil detect --brief 2>/dev/null | awk '
    /I2C bus:/        { bus = $3; sub("/dev/i2c-", "", bus) }
    /DRM connector:/  { conn = $3; sub("^card[0-9]+-", "", conn) }
    /Monitor:/        { split($0, m, ":"); model = m[3] }
    /^$/ && bus != "" { printf "ddc:%s\t%s\t%s\n", bus, conn, model; bus = "" }
    END               { if (bus != "") printf "ddc:%s\t%s\t%s\n", bus, conn, model }'
}

# Prefix labels with the display's position ("Left (DELL U2719D)") when there are several
label() {
  local outputs="$1"
  local sides
  sides=$(jq -r '
    sort_by(.rect.x, .rect.y) | map(.name) as $n
    | ({"2": ["Left", "Right"], "3": ["Left", "Center", "Right"]}[$n | length | tostring] // []) as $s
    | range($s | length) | "\($n[.])\t\($s[.])"' <<<"$outputs" 2>/dev/null)
  awk -F'\t' -v OFS='\t' -v sides="$sides" '
    BEGIN { n = split(sides, l, "\n"); for (i = 1; i <= n; i++) { split(l[i], kv, "\t"); side[kv[1]] = kv[2] } }
    $2 in side { $3 = side[$2] " (" $3 ")" }
    { print }'
}

displays() {
  local outputs signature
  outputs=$(sway_outputs)
  signature=$(jq -c '[.[] | [.name, .serial, .rect.x, .rect.y]]' <<<"$outputs" 2>/dev/null)
  if [[ -f "$cache/displays" && "$signature" == "$(cat "$cache/signature" 2>/dev/null)" ]]; then
    cat "$cache/displays"
    return
  fi
  # Outputs changed: bus numbers may have moved, so drop cached values too
  find "$cache" -type f ! -name "*.lock" -delete
  detect "$outputs" | label "$outputs" > "$cache/displays.tmp.$$"
  mv "$cache/displays.tmp.$$" "$cache/displays"
  echo "$signature" > "$cache/signature"
  cat "$cache/displays"
}

read_hw() {
  case "$1" in
    backlight:*) brightnessctl -d "${1#backlight:}" -m | awk -F, '{ sub("%", "", $4); print $4 }' ;;
    ddc:*)       ddcutil --bus "${1#ddc:}" getvcp 10 --brief 2>/dev/null | awk '{ print $4 }' ;;
  esac
}

get() {
  local f="$cache/${1//:/_}"
  [[ -s "$f" ]] || { read_hw "$1" > "$f.tmp.$$" && mv "$f.tmp.$$" "$f"; }
  cat "$f"
}

apply() {
  local id="$1" f="$cache/${1//:/_}"
  (
    flock 9
    local want; want=$(<"$f")
    [[ "$want" == "$(cat "$f.applied" 2>/dev/null)" ]] && exit 0
    case "$id" in
      backlight:*) brightnessctl -q -d "${id#backlight:}" set "$want%" ;;
      ddc:*)       ddcutil --bus "${id#ddc:}" --noverify setvcp 10 "$want" ;;
    esac
    echo "$want" > "$f.applied"
  ) 9>"$cache/${id//:/_}.lock"
}

set_one() {
  local id="$1" pct="$2" f="$cache/${1//:/_}"
  (( pct < 0 )) && pct=0
  (( pct > 100 )) && pct=100
  echo "$pct" > "$f.tmp.$$" && mv "$f.tmp.$$" "$f"
  apply "$id" >/dev/null 2>&1 &
}

# Serialize cache read-modify-write between concurrent invocations (fast scrolling)
lock_state() {
  exec 8>"$cache/state.lock"
  flock 8
}

linked() {
  [[ "$(cat "$state/brightness-linked" 2>/dev/null || echo 1)" == 1 ]]
}

focused_output() {
  sway_outputs | jq -r '.[] | select(.focused) | .name'
}

# Display ids for a target (id, output name or "all"); defaults per the link state
targets() {
  local want="$1"
  if [[ -z "$want" ]]; then
    if linked; then want=all; else want="${WAYBAR_OUTPUT_NAME:-$(focused_output)}"; fi
  fi
  local ids
  ids=$(displays | awk -F'\t' -v w="$want" 'w == "all" || $1 == w || $2 == w { print $1 }')
  # e.g. a bar on a monitor without DDC/CI: control everything rather than nothing
  [[ -n "$ids" ]] || ids=$(displays | cut -f1)
  echo "$ids"
}

# "<average percent>\t<label>" of the given ids
summary() {
  local sum=0 n=0 v id label
  for id in "$@"; do
    v=$(get "$id")
    [[ -n "$v" ]] || continue
    sum=$(( sum + v )); n=$(( n + 1 ))
  done
  (( n > 0 )) || return 1
  if (( n == 1 )); then
    label=$(displays | awk -F'\t' -v id="$1" '$1 == id { print $3 }')
  else
    label="All displays"
  fi
  printf '%s\t%s\n' $(( sum / n )) "$label"
}

icon() {
  local icons=(󰃞 󰃟 󰃝 󰃠)
  echo "${icons[$(( $1 * 3 / 100 ))]}"
}

case "$1" in
  list)
    while IFS=$'\t' read -r id conn name; do
      printf '%s\t%s\t%s\t%s\n' "$id" "$conn" "$name" "$(get "$id")"
    done < <(displays)
    ;;
  status)
    # Show this bar's monitor; fall back to the average of all displays
    mapfile -t ids < <(targets "${2:-${WAYBAR_OUTPUT_NAME:-all}}")
    IFS=$'\t' read -r pct _ < <(summary "${ids[@]}") || { echo '{"text":""}'; exit 0; }
    linked && class=linked || class=unlinked
    tooltip=$(while IFS=$'\t' read -r id _ name; do
      printf '%s: %s%%\\n' "$name" "$(get "$id")"
    done < <(displays))
    linked && tooltip+="󰌹 Linked" || tooltip+="󰌺 Not linked"
    printf '{"text":"%s %s%%","tooltip":"%s","percentage":%s,"class":"%s"}\n' \
      "$(icon "$pct")" "$pct" "$tooltip" "$pct" "$class"
    ;;
  set)
    lock_state
    mapfile -t ids < <(targets "$3")
    for id in "${ids[@]}"; do set_one "$id" "$2"; done
    flock -u 8
    pkill -RTMIN+$signal waybar
    ;;
  up|down)
    step=${2:-5}
    [[ "$1" == down ]] && step=-$step
    lock_state
    mapfile -t ids < <(targets "$3")
    for id in "${ids[@]}"; do set_one "$id" $(( $(get "$id") + step )); done
    flock -u 8
    pkill -RTMIN+$signal waybar
    summary "${ids[@]}"
    ;;
  link)
    case "$2" in
      on)     echo 1 > "$state/brightness-linked" ;;
      off)    echo 0 > "$state/brightness-linked" ;;
      toggle) linked && echo 0 > "$state/brightness-linked" || echo 1 > "$state/brightness-linked" ;;
    esac
    [[ -n "$2" ]] && pkill -RTMIN+$signal waybar
    linked && echo 1 || echo 0
    ;;
  refresh)
    rm -f "$cache/signature"
    for id in $(displays | cut -f1); do get "$id" >/dev/null & done
    wait
    pkill -RTMIN+$signal waybar
    ;;
  *)
    sed -n 's/^#   //p' "$0" >&2
    exit 1
    ;;
esac
