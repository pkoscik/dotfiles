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
adwaita-cursors
adwaita-fonts
adwaita-icon-theme
alacritty
bat
blueman
bluetui
brightnessctl
btop
cliphist
ddcutil
difftastic
dunst
eza
fastfetch
fd
ffmpegthumbnailer
file-roller
firefox
fish
fzf
git-delta
gnome-disk-utility
gnome-keyring
gnome-text-editor
gnome-themes-extra
grim
gtk-layer-shell
gvfs
gvfs-gphoto2
gvfs-mtp
helix
highlight
jq
lazygit
lf
libnotify
loupe
mpv
nautilus
network-manager-applet
networkmanager
pacman-contrib
papers
pipewire-pulse
playerctl
polkit-gnome
python-gobject
qt5-wayland
qt6-wayland
ripgrep
rofi
seahorse
slurp
stow
sway
swaybg
swayidle
swaylock
tesseract
tesseract-data-eng
tesseract-data-pol
tig
ttf-jetbrains-mono
ttf-jetbrains-mono-nerd
udiskie
udisks2
uv
waybar
wireguard-tools
wiremix
wireplumber
wl-clipboard
xdg-desktop-portal-gtk
xdg-desktop-portal-wlr
xdg-user-dirs
xdg-utils
xorg-xhost
xorg-xwayland
```

## Firefox configuration

```
general.autoScroll: true
mousewheel.min_line_scroll_amount: 120
mousewheel.default.delta_multiplier_{x,y,z}: 30
```
