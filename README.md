# pkoscik dotfiles

A _mostly_ sane set of configuration files. 

## Installation

The dotfiles are managed by __GNU Stow__:

```bash
cd ~
git clone https://github.com/pkoscik/dotfiles
cd dotfiles
stow <directory name>
```

## Arch packages

```text
alacritty
dunst
eza
feh
firefox
flameshot
fzf
helix
i3
lf
ripgrep
rofi
starship
stow
tig
ttf-jetbrains-mono
ttf-jetbrains-mono-nerd
```

## Firefox configuration

```text
general.autoScroll: true
mousewheel.min_line_scroll_amount: 120
mousewheel.default.delta_multiplier_{x,y,z}: 30
```

## Touchpad configuration

```text
Section "InputClass"
    Identifier "touchpad"
    Driver "libinput"
    MatchIsTouchpad "on"
    Option "Tapping" "on"
    Option "NaturalScrolling" "true"
EndSection
```

## `/etc/environment` configuration

```text
EDITOR=hx
VISUAL=hx
MOZ_USE_XINPUT2=1
```
