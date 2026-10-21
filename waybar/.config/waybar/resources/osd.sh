#!/usr/bin/env bash
# Media key handler with an on-screen progress bar (via dunst, see the [osd] rule in dunstrc).
#
#   osd.sh volume up|down|mute
#   osd.sh mic mute
#   osd.sh brightness up|down

step=5
resources="$(dirname "$(realpath "$0")")"

osd() {
  local icon="$1" text="$2" value="$3"
  notify-send -a osd -u low -t 1200 \
    -h string:x-dunst-stack-tag:osd \
    ${value:+-h "int:value:$value"} \
    "$icon  $text"
}

# wpctl prints "Volume: 0.45" or "Volume: 0.45 [MUTED]"
wp_state() {
  wpctl get-volume "$1" | awk '{ printf "%d %s\n", $2 * 100 + 0.5, ($3 == "[MUTED]") }'
}

case "$1 $2" in
  "volume up")   wpctl set-mute @DEFAULT_AUDIO_SINK@ 0; wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ "$step%+" ;;
  "volume down") wpctl set-volume @DEFAULT_AUDIO_SINK@ "$step%-" ;;
  "volume mute") wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle ;;
  "mic mute")    wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle 2>/dev/null ;;
  "brightness up"|"brightness down")
    # brightness.sh prints "<percent>\t<label>"
    IFS=$'\t' read -r pct label < <("$resources/brightness.sh" "$2" "$step")
    [[ -n "$pct" ]] || exit 1
    icons=(󰃞 󰃟 󰃝 󰃠)
    osd "${icons[$(( pct * 3 / 100 ))]}" "Brightness  $pct%  ($label)" "$pct"
    exit 0
    ;;
  *) echo "usage: $0 volume up|down|mute | mic mute | brightness up|down" >&2; exit 1 ;;
esac

if [[ "$1" == volume ]]; then
  read -r vol muted < <(wp_state @DEFAULT_AUDIO_SINK@)
  if (( muted )); then
    osd 󰝟 "Muted"
  else
    icons=(󰕿 󰖀 󰕾)
    osd "${icons[$(( (vol > 100 ? 100 : vol) * 2 / 100 ))]}" "Volume  $vol%" "$vol"
  fi
elif ! wpctl inspect @DEFAULT_AUDIO_SOURCE@ >/dev/null 2>&1; then
  osd 󰍭 "No microphone"
else
  read -r vol muted < <(wp_state @DEFAULT_AUDIO_SOURCE@)
  (( muted )) && osd 󰍭 "Microphone muted" || osd 󰍬 "Microphone  $vol%" "$vol"
fi
