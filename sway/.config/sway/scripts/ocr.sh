#!/bin/bash

tmp=`mktemp --suffix ".png"`

grim -g "$(slurp -d)" "$tmp"
if [ "$?" == "0" ]
then
    tesseract -l pol+eng $tmp - | wl-copy -n
    notify-send "screentool" "Area transcribed!"
fi
rm $tmp