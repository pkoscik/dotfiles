#!/bin/sh
# list root superproject + all nested submodules as "label|abspath", for the lazygit picker
r=$(git rev-parse --show-toplevel) || exit 1
while s=$(git -C "$r" rev-parse --show-superproject-working-tree) && [ -n "$s" ]; do r=$s; done
echo "$(basename "$r") (root)|$r"
git -C "$r" submodule foreach --recursive --quiet 'echo "$displaypath|$toplevel/$sm_path"'
