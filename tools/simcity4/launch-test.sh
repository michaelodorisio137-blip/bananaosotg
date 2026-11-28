#!/bin/sh
# Start only from an isolated, prepared profile. Never use the original data folder.
set -eu
[ "$#" -ge 2 ] || { echo "Usage: $0 /path/to/sc4_game_linux /path/to/prepared-profile [engine args]" >&2; exit 2; }
bin=$(realpath "$1"); profile=$(realpath "$2"); shift 2
[ -x "$bin" ] && [ -s "$profile/inventory.json" ] && [ -d "$profile/GameData" ] && [ -d "$profile/home" ] || { echo "Missing executable or prepared profile" >&2; exit 1; }
export HOME="$profile/home"
export XDG_CONFIG_HOME="$HOME/config" XDG_DATA_HOME="$HOME/data" XDG_CACHE_HOME="$HOME/cache"
export SC4_GAME_CONTENTS="$profile"
export AZEEZ_SC4_RGDS=1
cd "$profile"
exec "$bin" --size 640x480 --scale 1 --fullscreen -intro:off "$@"
