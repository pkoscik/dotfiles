#
# ~/.bash_profile
#

[[ -f ~/.bashrc ]] && . ~/.bashrc
[[ $(tty) == /dev/tty1 ]] && exec ssh-agent hyprland