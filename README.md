# pkoscik dotfiles

A _mostly_ sane set of configuration files.

X11/i3 dotfiles are backed up [here](https://github.com/pkoscik/dotfiles-old).

## Installation

Packages can be installed using the `install.sh` script.

The dotfiles are managed by __GNU Stow__:

```bash
cd ~
git clone https://github.com/pkoscik/dotfiles
cd dotfiles
stow <directory name>
```

## Arch packages

```
alacritty
bat
brightnessctl
dunst
eza
firefox
fish
fzf
git-delta
helix
highlight
i3status
jq
lazygit
lf
mergiraf
neofetch
playerctl
rofi-wayland
starship
stow
sway
swaybg
swayidle
swaylock
tig
ttf-font-awesome
ttf-jetbrains-mono
ttf-jetbrains-mono-nerd
uv
wl-clipboard
zoxide
```

## Firefox configuration

```
general.autoScroll: true
mousewheel.min_line_scroll_amount: 120
mousewheel.default.delta_multiplier_{x,y,z}: 30
```
