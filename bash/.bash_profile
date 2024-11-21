#
# ~/.bash_profile
#

EDITOR=helix
VISUAL=helix

[[ -f ~/.bashrc ]] && . ~/.bashrc
[[ $(tty) == /dev/tty1 ]] && exec ssh-agent hyprland
