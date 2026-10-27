if test -x /opt/homebrew/bin/brew
    /opt/homebrew/bin/brew shellenv fish | source
end
fish_add_path --global ~/.local/bin
if test -d /Applications/Wireshark.app/Contents/MacOS
    fish_add_path --global --append /Applications/Wireshark.app/Contents/MacOS
end
