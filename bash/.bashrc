#
# ~/.bashrc
#

################################################################################
# If not running interactively, don't do anything
################################################################################
[[ $- != *i* ]] && return

################################################################################
# Environmental variables
################################################################################
export EDITOR=helix
export VISUAL=helix


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
alias xc='wl-copy -n'
alias hx='helix'
alias q='exit'
alias g='git'
alias tig='tig --submodule'
alias rcp='rsync -auhp --compress --human-readable --info=progress2'
alias lg='lazygit'

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
		echo "More than one virtual environment found, select one:"
		selected_venv=$(printf "%s\n" "${venv[@]}" | fzf)
		if [[ -z "$selected_venv" ]]; then
			echo "No virtual environment selected, aborting!"
			return 1
		fi
		echo "Activating virtual environment at $selected_venv"
		source $selected_venv/bin/activate
	elif [[ "$len" -eq 1 ]]; then
		echo "Activating virtual environment at ${venv[0]}"
		source ${venv[0]}/bin/activate
	else
		echo "No virtual environment found!"
		return 1
	fi
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

function get_zephyr_dts {
    local platform="$1"
    local sample="hello_world"
    local latest_zephyr=$(curl -sS http://zephyr-dashboard.renode.io/zephyr/latest)
    local temp_file=$(mktemp)  # XXX(pkoscik): needed to suppres the curl output for 404 page

    curl -sS --fail-with-body -o "$temp_file" http://zephyr-dashboard.renode.io/zephyr/"$latest_zephyr"/"$platform"/"$sample"/"$sample".dts
    local status=$?
    if [ $status -eq 0 ] && [ -s "$temp_file" ]; then
        cat "$temp_file"
    fi

    rm -f "$temp_file"
    return $status
}

function ffsilent {
	ffmpeg -i "$1" -c copy -an "${1%.*}-nosound.${1#*.}"
}

format_json() {
    if [[ -z "$1" ]]; then
        echo "Usage: format_json <filename>"
        return 1
    fi

    local filename="$1"

    if [[ ! -f "$filename" ]]; then
        echo "File not found: $filename"
        return 1
    fi

    jq . "$filename" > tmp.$.json && mv tmp.$.json "$filename"
    
    if [[ $? -eq 0 ]]; then
        echo "Formatted JSON file: $filename"
    else
        echo "Failed to format JSON file: $filename"
        return 1
    fi
}

# Disable 'Alt-N' bind
for i in "-" {0..9}; do bind -r "\e$i"; done

################################################################################
# Starship PS1
################################################################################
eval "$(starship init bash)"
eval "$(zoxide init bash)"


################################################################################
# fzf
################################################################################
source /usr/share/fzf/key-bindings.bash
source /usr/share/fzf/completion.bash
