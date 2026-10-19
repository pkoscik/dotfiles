#!/usr/bin/env bash
# Muted-gray status line:
# model · effort │ dir │ ctx · cost │ 5h ↻left · 7d ↻left │ time · +add −del │ git
export LC_NUMERIC=C  # pl_PL makes printf reject "1.23"
in=$(cat)
mkdir -p /tmp/claude-1000; printf '%s' "$in" > /tmp/claude-1000/statusline-last.json
j() { jq -r "$1 // empty" <<<"$in" 2>/dev/null; }

D=$'\033[38;5;240m' G=$'\033[38;5;250m' Y=$'\033[33m' R=$'\033[31m' Z=$'\033[0m'
SEP="${D} │ ${G}"

# "12%" colored gray / yellow >=70 / red >=90; "–" when unknown
pct() {
  [ -z "$1" ] && { printf '–'; return; }
  local n; n=$(printf '%.0f' "$1"); local c=$G
  [ "$n" -ge 90 ] && c=$R || { [ "$n" -ge 70 ] && c=$Y; }
  printf '%s%s%%%s' "$c" "$n" "$G"
}
# seconds -> 2h13m / 3d4h / 12m
dur() {
  local s=$1; [ "$s" -lt 0 ] && s=0
  local d=$((s/86400)) h=$((s%86400/3600)) m=$((s%3600/60))
  if [ $d -gt 0 ]; then printf '%dd %dh' $d $h
  elif [ $h -gt 0 ]; then printf '%dh %dm' $h $m
  else printf '%dm' $m; fi
}
# epoch or ISO timestamp -> " (2h 13m)"
left() {
  [ -z "$1" ] && return
  local t=$1; [[ $t =~ ^[0-9]+$ ]] || t=$(date -d "$t" +%s 2>/dev/null) || return
  [ "$t" -gt 9999999999 ] && t=$((t/1000))
  printf ' %s(%s)%s' "$D" "$(dur $((t - $(date +%s))))" "$G"
}

model=$(j '.model.display_name')
if [ -z "$model" ]; then  # claude-sonnet-5-5 -> Sonnet 5.5
  model=$(j '.model.id' | sed -E 's/^claude-//; s/-([0-9]+)-([0-9]+)$/ \1.\2/; s/^(.)/\u\1/')
fi
eff=$(j '.effort.level'); [ -z "$eff" ] && eff=$(jq -r '.effortLevel // empty' ~/.claude/settings.json)
cwd=$(j '.workspace.current_dir'); [ -z "$cwd" ] && cwd=$PWD
cost=$(j '.cost.total_cost_usd')
ms=$(j '.cost.total_duration_ms')
add=$(j '.cost.total_lines_added'); del=$(j '.cost.total_lines_removed')

out="${G}${model:-?} ${D}(${G}${eff:-–}${D})${SEP}$(basename "$cwd")"
out+="${SEP}${D}ctx:${G} $(pct "$(j '.context_window.used_percentage')") ${D}·${G} \$$(printf '%.2f' "${cost:-0}")"
out+="${SEP}${D}5h:${G} $(pct "$(j '.rate_limits.five_hour.used_percentage')")$(left "$(j '.rate_limits.five_hour.resets_at')")"
out+=" ${D}· 7d:${G} $(pct "$(j '.rate_limits.seven_day.used_percentage')")$(left "$(j '.rate_limits.seven_day.resets_at')")"

extra=""
[ -n "$ms" ] && extra="${D}session:${G} $(dur $((ms/1000)))"
if [ "${add:-0}" -gt 0 ] || [ "${del:-0}" -gt 0 ]; then extra+="${extra:+ ${D}·${G} }+${add:-0} −${del:-0}"; fi
[ -n "$extra" ] && out+="${SEP}${extra}"

if br=$(git -C "$cwd" symbolic-ref --short -q HEAD 2>/dev/null || git -C "$cwd" rev-parse --short HEAD 2>/dev/null); then
  n=$(git -C "$cwd" status --porcelain 2>/dev/null | wc -l)
  [ "$n" -gt 0 ] && out+="${SEP}$br ●$n" || out+="${SEP}$br ✓"
fi

printf '%s%s' "$out" "$Z"
