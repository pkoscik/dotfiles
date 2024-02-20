# pkoscik dotfiles

A _mostly_ sane set of configuration files. 

## Installation

The dotfiles are managed by __GNU Stow__:

```
cd ~
git clone https://github.com/pkoscik/dotfiles
cd dotfiles
stow <directory name>
```

## Arch packages

```
alacritty
eza
firefox
helix
i3
lf
rofi
starship
stow
tig
ttf-jetbrains-mono
ttf-jetbrains-mono-nerd
```

## Firefox configuration

```
general.autoScroll: true
general.autoScroll: false
mousewheel.min_line_scroll_amount: 120
mousewheel.default.delta_multiplier_{x,y,z}: 30
```
