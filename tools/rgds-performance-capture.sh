#!/bin/sh
# Low-rate, read-only on-device performance capture. Run over SSH during gameplay.
# Usage: sh rgds-performance-capture.sh [seconds=60] [interval=2]
# Output is TSV on stdout; does not include ROM paths, tokens or player names.
set -eu
duration=${1:-60}
interval=${2:-2}
case "$duration:$interval" in *[!0-9:]*|:*|*:) exit 2;; esac
[ "$duration" -ge 1 ] && [ "$duration" -le 600 ] && [ "$interval" -ge 1 ] && [ "$interval" -le 60 ] || exit 2
readval() { if [ -r "$1" ]; then tr '\n' ' ' < "$1" | sed 's/ *$//'; else printf NA; fi; }
version=$(readval /etc/banana/version)
printf '# firmware\t%s\n' "$version"
printf '# kernel\t%s\n' "$(uname -r)"
printf '# board\t%s\n' "$(tr -d '\000' < /proc/device-tree/model 2>/dev/null || true)"
printf '# cpu_policy\tgovernor\tavailable_khz\n'
for d in /sys/devices/system/cpu/cpufreq/policy*; do
  [ -d "$d" ] || continue
  printf '# %s\t%s\t%s\n' "${d##*/}" "$(readval "$d/scaling_governor")" "$(readval "$d/scaling_available_frequencies")"
done
for d in /sys/class/devfreq/*; do
  [ -d "$d" ] || continue
  printf '# devfreq %s\t%s\t%s\n' "${d##*/}" "$(readval "$d/governor")" "$(readval "$d/available_frequencies")"
done
printf 'seconds\tkind\tid\tfields\n'
start=$(cut -d. -f1 /proc/uptime)
while :; do
  now=$(cut -d. -f1 /proc/uptime); elapsed=$((now-start))
  awk -v t="$elapsed" '/^cpu[0-9]* /{printf "%d\tcpu_ticks\t%s\t",t,$1; for(i=2;i<=NF;i++) printf "%s%s",$i,(i==NF?"\n":" ")}' /proc/stat
  for d in /sys/devices/system/cpu/cpufreq/policy*; do
    [ -d "$d" ] || continue
    printf '%s\tcpu_khz\t%s\t%s %s %s\n' "$elapsed" "${d##*/}" "$(readval "$d/scaling_cur_freq")" "$(readval "$d/scaling_min_freq")" "$(readval "$d/scaling_max_freq")"
  done
  for d in /sys/class/devfreq/*; do
    [ -d "$d" ] || continue
    printf '%s\tdevfreq_hz\t%s\t%s %s %s\n' "$elapsed" "${d##*/}" "$(readval "$d/cur_freq")" "$(readval "$d/min_freq")" "$(readval "$d/max_freq")"
  done
  for d in /sys/class/thermal/thermal_zone*; do
    [ -d "$d" ] || continue
    printf '%s\ttemp_mC\t%s\t%s %s\n' "$elapsed" "${d##*/}" "$(readval "$d/type")" "$(readval "$d/temp")"
  done
  awk -v t="$elapsed" '/^(MemAvailable|SwapFree|MemTotal):/{printf "%s\tmem_kib\t%s\t%s\n",t,$1,$2}' /proc/meminfo
  for d in /proc/[0-9]*; do
    [ -r "$d/comm" ] || continue
    name=$(cat "$d/comm" 2>/dev/null) || continue
    case "$name" in bananads|bananafront|banana-ui|retroarch|drastic|superdrastic|sc4_game_linux)
      for task in "$d"/task/*; do
        [ -r "$task/stat" ] || continue
        awk -v t="$elapsed" -v n="$name" '{
          id=$1;sub(/^.*\) /,"");split($0,a," ");
          printf "%s\tthread_ticks\t%s:%s\t%s %s %s\n",t,n,id,a[12],a[13],a[37]
        }' "$task/stat" 2>/dev/null || :
      done;;
    esac
  done
  [ "$elapsed" -ge "$duration" ] && break
  sleep "$interval"
done
