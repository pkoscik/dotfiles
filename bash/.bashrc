#
# ~/.bashrc
#

################################################################################
# If not running interactively, don't do anything
################################################################################
[[ $- != *i* ]] && return


################################################################################
# Fallback PS1
################################################################################
PS1='[\u@\h \W]\$ '


################################################################################
# Aliases
################################################################################
alias l="exa -l --icons --no-user --group-directories-first  --time-style long-iso --git"
alias ll="exa -l --icons --group-directories-first  --time-style long-iso --git --all"
alias bm="bashmount"
alias xc='xsel -i -b'
alias q='exit'

# Navigation
alias ..='cd ..'
alias -- -='cd -'

################################################################################
# Functions
################################################################################
function venv {	
	venv=($(ls -a | grep venv))
	len=${#venv[@]}
	if [[ "$len" -gt 1 ]]; then
		echo "More than one virtual environment found, aborting!"
		return 1
	else
		echo "Activating virtual environment at $venv"
		source $venv/bin/activate
	fi
}

function venvc {
  if [ ! -n "$1" ]; then
		venv_name=".venv"
	else
		venv_name=$1
	fi
	python -m venv "$venv_name"
	venv
}

function mkcd {
  if [ ! -n "$1" ]; then
    echo "Enter a directory name"
  elif [ -d $1 ]; then
    echo "\`$1' already exists"
  else
    mkdir $1 && cd $1
  fi
}

# Disable 'Alt-N' bind
for i in "-" {0..9}; do bind -r "\e$i"; done

################################################################################
# Starship PS1
################################################################################
eval "$(starship init bash)"


################################################################################
# fzf
################################################################################
source /usr/share/fzf/key-bindings.bash
source /usr/share/fzf/completion.bash
