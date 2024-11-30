#!/bin/bash

packages=$(awk '/## Arch packages/{flag=1; next} /## Firefox configuration/{flag=0} flag' "README.md" | tr '\n' ' ' | tr -d '\`' | xargs)

echo "Installing $(echo $packages | wc -w) packages"
if [ -n "$packages" ]; then
  sudo pacman -Syu $packages
else
  echo "No packages found!"
  exit 1
fi
