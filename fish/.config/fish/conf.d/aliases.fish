if status is-interactive
    alias l 'eza -l --icons --no-user --group-directories-first  --time-style long-iso --git'
    alias ll 'eza -l --icons --group-directories-first  --time-style long-iso --git --all'
    alias df1='df --type btrfs --type ext4 --type ext3 --type ext2 --type vfat --type iso9660'
    alias manfind "man -k . | fzf | cut -d ' ' -f 1,2 | tr -d '\(\)' | xargs man"
    alias renode 'env STARTUP_COMMAND=include\ @/home/pkoscik/.renoderc renode'


    alias xc 'wl-copy -n'
    abbr q 'exit'
    abbr g 'git'
    abbr tig 'tig --submodule'
    abbr rcp 'rsync -auhp --compress --human-readable --info=progress2'
    abbr lg 'lazygit'

    abbr .. 'cd ..'
    abbr - 'cd -'
end
