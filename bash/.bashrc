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
# Exports
################################################################################
export EDITOR=hx


################################################################################
# PATH
################################################################################
PATH=$PATH:/home/pkoscik/.cargo/bin
PATH=$PATH:/home/pkoscik/Renode/renode_1.14.0


################################################################################
# Aliases
################################################################################
alias grep='grep --color=auto'
alias l="exa -l --icons --no-user --group-directories-first  --time-style long-iso --git"
alias ll="exa -l --icons --group-directories-first  --time-style long-iso --git --all"
alias py="python"
alias xc='xsel -i -b'
alias q='exit'
alias da='xdg-open'

# Zellij
alias za='zellij attach $(zellij ls -s | fzf)'

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

# Disable 'Alt-N' bind
for i in "-" {0..9}; do bind -r "\e$i"; done

################################################################################
# Starship PS1
################################################################################
eval "$(starship init bash)"
