#!/bin/bash
cliphist list \
    | rofi -dmenu -i -p Clipboard -display-columns 2 -theme-str 'mode-switcher { enabled: false; }' \
    | cliphist decode \
    | wl-copy
