# pkoscik dotfiles

A _mostly_ sane set of configuration files.

X11/i3 dotfiles are backed up [here](https://github.com/pkoscik/dotfiles-old).

## Installation

The dotfiles are managed by __GNU Stow__:

```bash
cd ~
git clone https://github.com/pkoscik/dotfiles
cd dotfiles
stow <directory name>
```

## Firefox configuration

```
general.autoScroll: true
mousewheel.min_line_scroll_amount: 120
mousewheel.default.delta_multiplier_{x,y,z}: 30
```
