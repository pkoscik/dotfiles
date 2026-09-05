# macOS 26.5.2 (25F84)

```
brew bundle --file macos/Brewfile
bash macos/defaults.sh
stow fish helix wezterm git lazygit lf
chsh -s /opt/homebrew/bin/fish
```

## shortcuts (`defaults.sh`)

- nuke all `Keyboard Settings` hotkeys, keep
  - `Cmd+Space` -> Apps (160)
  - `Cmd+Shift+S` -> screenshot (31)
- key hold = repeat (`ApplePressAndHoldEnabled=0`, `KeyRepeat=2`, `InitialKeyRepeat=15`)
- Globe/Fn = nothing
- all hot corners off
- dock: autohide, no recents, tilesize 24
