#!/usr/bin/env bash
if [[ -n "$ROFI_INFO" ]]; then
  swaymsg "[con_id=$ROFI_INFO] focus" >/dev/null
  exit 0
fi

printf '\0markup-rows\x1ftrue\n\0no-custom\x1ftrue\n'
swaymsg -t get_tree -r | jq -j '
  .. | objects | select(.type? == "workspace") | (if .name == "__i3_scratch" then "scratchpad" else .name end) as $ws
  | .. | objects | select((.type? == "con" or .type? == "floating_con") and .pid?)
  | "<span alpha=\"55%\">\($ws | @html)</span>  \(.name // "" | @html)",
    "\u0000icon\u001f\(.app_id // .window_properties.class // "" | ascii_downcase)",
    "\u001finfo\u001f\(.id)\n"'
