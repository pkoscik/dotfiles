set fish_greeting "$(date +%c)"

if status is-interactive
    abbr l 'exa -l --icons --no-user --group-directories-first  --time-style long-iso --git'
    abbr ll 'exa -l --icons --group-directories-first  --time-style long-iso --git --all'
    abbr bm 'bashmount'
    abbr xc 'wl-copy -n'
    abbr hx 'helix'
    abbr q 'exit'
    abbr g 'git'
    abbr tig 'tig --submodule'
    abbr rcp 'rsync -auhp --compress --human-readable --info=progress2'
    abbr lg 'lazygit'

    abbr .. 'cd ..'
    abbr - 'cd -'

    starship init fish | source
end
