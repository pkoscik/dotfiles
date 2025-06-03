#!/usr/bin/fish

set command $argv[1]
set file (realpath $argv[2])
set line $argv[3]

# enter the file repository
cd (dirname $file)

# get and cd into repository root
set repo_dir (git rev-parse --show-toplevel)
cd $repo_dir


switch $command
    case blame
        set sha (git blame --root -L$line,$line -- $file | cut -d' ' -f 1)
        git log --pretty=format:"%h by %ae on %ad%n%n%s" -n 1 --date=short $sha
end