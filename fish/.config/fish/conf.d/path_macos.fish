if test (uname) = Darwin
    /opt/homebrew/bin/brew shellenv fish | source
    fish_add_path --global --append /Applications/Wireshark.app/Contents/MacOS
end
